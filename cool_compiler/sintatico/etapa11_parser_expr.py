"""Parser das expressões de COOL, por descida recursiva.

Em COOL quase tudo é expressão, então este arquivo é a maior parte da gramática.

A gramática do manual é AMBÍGUA e RECURSIVA À ESQUERDA:

    expr ::= expr + expr | expr * expr | expr.metodo(...) | ...

Recursão à esquerda é fatal para descida recursiva: uma função que começa
chamando a si mesma sem consumir nada entra em laço infinito. E a ambiguidade
não diz se 1 - 2 - 3 é (1-2)-3 ou 1-(2-3).

As duas coisas se resolvem com a mesma reescrita clássica — trocar a recursão
à esquerda por ITERAÇÃO:

    Aditiva   ::= Multiplic ( ('+' | '-') Multiplic )*
    Multiplic ::= Unaria    ( ('*' | '/') Unaria    )*

O `*` vira um while, e como o nó é reconstruído a cada volta
(esquerda = BinaryOp(op, esquerda, direita)), a associatividade à esquerda sai
de graça. A cascata de não-terminais, por sua vez, codifica a precedência.

PRECEDENCE CLIMBING (a função parse_binary) é a generalização dessa cascata:
em vez de uma função por nível de precedência, uma função só com um parâmetro
`min_precedence` e a tabela da etapa 10. Menos código repetido, mesma árvore.

Ordem das funções neste arquivo = ordem da cascata, do operador mais FRACO
para o mais FORTE:

    parse_expression   ->  <-
    parse_not          ->  not
    parse_binary       ->  <= < =  |  + -  |  * /     (dirigido por tabela)
    parse_unary        ->  isvoid, ~
    parse_dispatch_chain -> @ e .
    parse_primary      ->  literais, nomes, ( ), e as construções fechadas
"""

from ..lexico.etapa1_tokens import TokenType
from .etapa10_precedencia import (
    BINARY_OPERATORS, COMPARISON_TOKENS, MIN_PRECEDENCE, Assoc,
)
from .etapa6_ast import (
    Assign, BinaryOp, Block, BoolConst, Case, CaseBranch, Dispatch, ErrorExpr,
    Expr, If, IntConst, IsVoid, Let, Neg, New, Not, ObjectId, StaticDispatch,
    StringConst, While,
)
from .etapa8_erros_sintaticos import SYNC_EXPR, ParseError
from .etapa9_cursor import Cursor


class ExpressionParser(Cursor):
    """Camada de expressões, montada sobre o Cursor da etapa 9."""

    # ----------------------------------------------------------------------
    # 1. Atribuição: o nível mais fraco
    # ----------------------------------------------------------------------

    def parse_expression(self) -> Expr:
        """expr ::= OBJECTID '<-' expr | <nivel do not>

        Este é o ponto de entrada de toda expressão, e é deliberadamente
        GULOSO: chamado de dentro de um let, de um if ou de um argumento, ele
        consome tudo que conseguir. Essa gula é o que implementa a regra do
        let (ver parse_let).
        """
        # ÚNICO lugar da gramática que precisa de lookahead de 2. Ao ver um
        # OBJECTID ainda não dá para saber se é `x <- 1` (atribuição) ou `x`
        # (uma variável, talvez seguida de `.f()`). E aqui a decisão precisa
        # vir ANTES do consumo: se não for atribuição, o OBJECTID tem que
        # continuar disponível para parse_primary lá embaixo.
        if self.check(TokenType.OBJECTID) and self.check_ahead(1, TokenType.ASSIGN):
            nome = self.advance()                 # OBJECTID
            self.advance()                        # <-
            # Recursão à DIREITA: x <- y <- 1 vira x <- (y <- 1), que é o que
            # a associatividade à direita significa.
            return Assign(nome.lexeme, self.parse_expression(), nome.line)
        return self.parse_not()

    # ----------------------------------------------------------------------
    # 2. not
    # ----------------------------------------------------------------------

    def parse_not(self) -> Expr:
        """expr ::= 'not' expr | <nivel dos binarios>

        `not` é prefixo e mais fraco que qualquer comparação, então
        `not a < b` é `not (a < b)` — o operando é lido pelo nível de baixo,
        que já consome a comparação inteira.

        Chamar a si mesma, e não parse_binary direto, é o que aceita `not not x`.
        """
        if self.check(TokenType.NOT):
            token = self.advance()
            return Not(self.parse_not(), token.line)
        return self.parse_binary(MIN_PRECEDENCE)

    # ----------------------------------------------------------------------
    # 3. Operadores binários (precedence climbing)
    # ----------------------------------------------------------------------

    def parse_binary(self, min_precedence: int) -> Expr:
        """Lê uma cadeia de operadores binários de precedência >= min_precedence.

        O parâmetro min_precedence é um PISO: a função só aceita operadores
        que ligam pelo menos tão forte quanto ele. É assim que uma função só
        faz o papel das três (Comparacao, Aditiva, Multiplic) da cascata.
        """
        esquerda = self.parse_unary()

        while True:
            info = BINARY_OPERATORS.get(self.peek().type)
            # Ou não é operador binário, ou liga mais fraco do que este nível
            # aceita: em ambos os casos, quem chamou é que resolve.
            if info is None or info.precedence < min_precedence:
                return esquerda

            op_token = self.advance()

            # Piso + 1 para operadores associativos à ESQUERDA: assim o lado
            # direito NÃO consegue consumir outro operador do mesmo nível, ele
            # sobra para a próxima volta do while, e o nó cresce para a
            # esquerda. Fosse associativo à direita, o piso seria
            # info.precedence (sem o +1), e o lado direito engoliria a cadeia.
            direita = self.parse_binary(info.precedence + 1)
            esquerda = BinaryOp(info.operator, esquerda, direita, op_token.line)

            if info.assoc is Assoc.NON_ASSOC:
                # COOL declara <= < = como %nonassoc: a < b < c não tem
                # leitura definida e é erro.
                #
                # Parar aqui é seguro: qualquer operador MAIS FORTE (+, *) já
                # foi consumido pela chamada recursiva acima, então a única
                # coisa que ainda poderia aparecer neste ponto é outro
                # comparador — exatamente o caso que queremos rejeitar.
                if self.peek().type in COMPARISON_TOKENS:
                    raise self.error(
                        self.peek(),
                        "operadores de comparacao nao podem ser encadeados; "
                        "use parenteses",
                    )
                return esquerda

    # ----------------------------------------------------------------------
    # 4. Prefixos isvoid e ~
    # ----------------------------------------------------------------------

    def parse_unary(self) -> Expr:
        """expr ::= 'isvoid' expr | '~' expr | <nivel do dispatch>

        A tabela oficial diz que ~ é mais forte que isvoid, mas entre dois
        operadores PREFIXOS a precedência relativa não muda nada: `isvoid ~x`
        e `~isvoid x` só têm uma leitura possível cada um. O que importa é que
        os dois sejam mais fortes que * e /, e isso já está garantido pelo fato
        de parse_binary chamar esta função.

        Por isso um nível só, recursivo em si mesmo. Separá-los em duas funções
        estritamente encadeadas (parse_isvoid -> parse_neg) faria o parser
        REJEITAR `~isvoid x`, que o bison aceita.
        """
        if self.check(TokenType.ISVOID):
            token = self.advance()
            return IsVoid(self.parse_unary(), token.line)
        if self.check(TokenType.TILDE):
            token = self.advance()
            return Neg(self.parse_unary(), token.line)
        return self.parse_dispatch_chain()

    # ----------------------------------------------------------------------
    # 5. Dispatch: .metodo(...) e @Tipo.metodo(...)
    # ----------------------------------------------------------------------

    def parse_dispatch_chain(self) -> Expr:
        """expr ::= primary ( '.' OBJECTID args | '@' TYPEID '.' OBJECTID args )*

        Também era recursiva à esquerda no manual (expr.metodo(...)), e também
        virou iteração. Cada volta do while embrulha o que já foi lido, então
        a.f().g().h() sai aninhado à esquerda, que é a ordem de avaliação.
        """
        expressao = self.parse_primary()

        while True:
            if self.check(TokenType.AT):
                # @ em COOL só aparece imediatamente seguido de .Tipo.metodo,
                # então a decisão continua sendo de um token só.
                token = self.advance()
                tipo = self.expect(TokenType.TYPEID,
                                   "esperava o nome do tipo depois de '@'")
                self.expect(TokenType.DOT, "esperava '.' depois de '@Tipo'")
                metodo = self.expect(TokenType.OBJECTID,
                                     "esperava o nome do metodo depois de '.'")
                expressao = StaticDispatch(expressao, tipo.lexeme, metodo.lexeme,
                                           self.parse_arguments(), token.line)
            elif self.check(TokenType.DOT):
                token = self.advance()
                metodo = self.expect(TokenType.OBJECTID,
                                     "esperava o nome do metodo depois de '.'")
                expressao = Dispatch(expressao, metodo.lexeme,
                                     self.parse_arguments(), token.line)
            else:
                return expressao

    def parse_arguments(self) -> list[Expr]:
        """args ::= '(' [ expr (',' expr)* ] ')'

        Repare que aqui a vírgula é SEPARADOR: não aparece depois do último
        argumento. É o oposto do ';' de um bloco, que é terminador.
        """
        self.expect(TokenType.LPAREN, "esperava '(' para abrir a lista de argumentos")
        argumentos: list[Expr] = []
        if not self.check(TokenType.RPAREN):
            argumentos.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                argumentos.append(self.parse_expression())
        self.expect(TokenType.RPAREN, "esperava ')' para fechar a lista de argumentos")
        return argumentos

    # ----------------------------------------------------------------------
    # 6. Expressões primárias
    # ----------------------------------------------------------------------

    def parse_primary(self) -> Expr:
        """O fundo da cascata: o que não é operador.

        Inclui as construções FECHADAS (if, while, bloco, let, case). Elas têm
        delimitador próprio de início e de fim, então não competem por
        precedência com ninguém e podem morar aqui embaixo.
        """
        token = self.peek()

        match token.type:
            case TokenType.IF:
                return self.parse_if()
            case TokenType.WHILE:
                return self.parse_while()
            case TokenType.LBRACE:
                return self.parse_block()
            case TokenType.LET:
                return self.parse_let()
            case TokenType.CASE:
                return self.parse_case()

            case TokenType.NEW:
                self.advance()
                tipo = self.expect(TokenType.TYPEID,
                                   "esperava um nome de tipo depois de 'new'")
                return New(tipo.lexeme, token.line)

            case TokenType.LPAREN:
                self.advance()
                interna = self.parse_expression()
                self.expect(TokenType.RPAREN,
                            "esperava ')' para fechar a expressao entre parenteses")
                # Parênteses NÃO viram nó. Eles já fizeram o trabalho deles ao
                # decidir o formato da árvore; guardá-los não acrescentaria
                # informação nenhuma à fase semântica.
                return interna

            case TokenType.INT_CONST:
                self.advance()
                return IntConst(token.value, token.line)
            case TokenType.STR_CONST:
                self.advance()
                return StringConst(token.value, token.line)
            case TokenType.BOOL_CONST:
                self.advance()
                return BoolConst(token.value, token.line)

            case TokenType.OBJECTID:
                self.advance()
                # FATORAÇÃO À ESQUERDA: em vez de espiar adiante para decidir
                # entre `f(1)` e `f`, consumimos o identificador (que é comum
                # às duas alternativas) e só então olhamos o que veio. É o que
                # um gerador LALR(1) faz implicitamente.
                if self.check(TokenType.LPAREN):
                    return Dispatch(None, token.lexeme,
                                    self.parse_arguments(), token.line)
                return ObjectId(token.lexeme, token.line)

        raise self.error(token, "esperava uma expressao")

    # ----------------------------------------------------------------------
    # 7. Construções fechadas
    # ----------------------------------------------------------------------

    def parse_if(self) -> Expr:
        token = self.expect(TokenType.IF, "esperava 'if'")
        condicao = self.parse_expression()
        self.expect(TokenType.THEN, "esperava 'then' depois da condicao do 'if'")
        entao = self.parse_expression()
        # Em COOL o else é obrigatório: o if é expressão e precisa ter valor
        # nos dois caminhos.
        self.expect(TokenType.ELSE, "esperava 'else' (em COOL o 'else' e obrigatorio)")
        senao = self.parse_expression()
        self.expect(TokenType.FI, "esperava 'fi' para fechar o 'if'")
        return If(condicao, entao, senao, token.line)

    def parse_while(self) -> Expr:
        token = self.expect(TokenType.WHILE, "esperava 'while'")
        condicao = self.parse_expression()
        self.expect(TokenType.LOOP, "esperava 'loop' depois da condicao do 'while'")
        corpo = self.parse_expression()
        self.expect(TokenType.POOL, "esperava 'pool' para fechar o 'while'")
        return While(condicao, corpo, token.line)

    def parse_block(self) -> Expr:
        """expr ::= '{' [ expr ';' ]+ '}'

        Atenção: aqui o ';' é TERMINADOR, aparece depois de todas as expressões
        inclusive a última. É diferente da vírgula dos argumentos, que é
        separador. E o bloco exige PELO MENOS UMA expressão.

        Cuidado para não confundir este bloco com as chaves do corpo de um
        método: lá as chaves delimitam UMA expressão e não levam ';'.
        """
        token = self.expect(TokenType.LBRACE, "esperava '{'")
        expressoes: list[Expr] = []

        while not self.check(TokenType.RBRACE) and not self.at_end():
            try:
                expressoes.append(self.parse_expression())
                self.expect(TokenType.SEMI,
                            "todo comando de um bloco termina com ';'")
            except ParseError:
                # Fronteira de recuperação: uma expressão ruim não derruba o
                # bloco inteiro. Deixa um buraco marcado e tenta a próxima.
                expressoes.append(ErrorExpr("expressao invalida no bloco",
                                            self.peek().line))
                self.synchronize(SYNC_EXPR)
                self.match(TokenType.SEMI)

        self.expect(TokenType.RBRACE, "esperava '}' para fechar o bloco")
        if not expressoes:
            self.error(token, "um bloco { } precisa de pelo menos uma expressao")
        return Block(expressoes, token.line)

    def parse_let(self) -> Expr:
        """expr ::= 'let' binding (',' binding)* 'in' expr
           binding ::= OBJECTID ':' TYPEID [ '<-' expr ]

        Aqui mora o ponto mais interessante da etapa. No bison, esta regra é
        ambígua: em `let x : Int in x + 1`, ao chegar no '+' o parser pode
        REDUZIR (fechando o let, deixando o corpo ser só `x`) ou DESLOCAR
        (estendendo o corpo para `x + 1`). O conflito é resolvido à mão, com
        uma declaração %prec LET que escolhe o shift.

        Em descida recursiva essa escolha NÃO EXISTE. O corpo é lido por
        parse_expression, que é o nível mais fraco da cascata e consome tudo
        que conseguir, parando só num token que nenhuma regra de expressão
        aceita (';', ')', '}', ',', 'then', 'else', 'fi', 'loop', 'pool',
        'of', 'esac', EOF). Ser guloso É a regra "o let se estende o máximo
        possível". Ganhamos de graça o que o bison precisa declarar.
        """
        self.expect(TokenType.LET, "esperava 'let'")

        # (nome, tipo, inicializacao, linha)
        bindings: list[tuple[str, str, Expr | None, int]] = []
        while True:
            nome = self.expect(TokenType.OBJECTID,
                               "esperava o nome da variavel do 'let'")
            self.expect(TokenType.COLON,
                        "esperava ':' depois do nome da variavel do 'let'")
            tipo = self.expect(TokenType.TYPEID,
                               "esperava o tipo da variavel do 'let'")
            inicial = None
            if self.match(TokenType.ASSIGN):
                inicial = self.parse_expression()
            bindings.append((nome.lexeme, tipo.lexeme, inicial, nome.line))
            if not self.match(TokenType.COMMA):
                break

        self.expect(TokenType.IN, "esperava 'in' depois das declaracoes do 'let'")
        corpo = self.parse_expression()

        # Vários bindings viram vários Let aninhados, montados de TRÁS PARA
        # FRENTE: o último binding é o mais interno, e o escopo de cada um
        # passa a ser exatamente o corpo do Let que o carrega.
        for nome_var, tipo_var, inicial, linha in reversed(bindings):
            corpo = Let(nome_var, tipo_var, inicial, corpo, linha)
        return corpo

    def parse_case(self) -> Expr:
        """expr ::= 'case' expr 'of' [ OBJECTID ':' TYPEID '=>' expr ';' ]+ 'esac'"""
        token = self.expect(TokenType.CASE, "esperava 'case'")
        alvo = self.parse_expression()
        self.expect(TokenType.OF, "esperava 'of' depois da expressao do 'case'")

        ramos: list[CaseBranch] = []
        while not self.check(TokenType.ESAC) and not self.at_end():
            nome = self.expect(TokenType.OBJECTID,
                               "esperava o nome da variavel do ramo do 'case'")
            self.expect(TokenType.COLON, "esperava ':' no ramo do 'case'")
            tipo = self.expect(TokenType.TYPEID, "esperava o tipo do ramo do 'case'")
            self.expect(TokenType.DARROW, "esperava '=>' no ramo do 'case'")
            corpo = self.parse_expression()
            self.expect(TokenType.SEMI, "todo ramo do 'case' termina com ';'")
            ramos.append(CaseBranch(nome.lexeme, tipo.lexeme, corpo, nome.line))

        self.expect(TokenType.ESAC, "esperava 'esac' para fechar o 'case'")
        if not ramos:
            self.error(token, "um 'case' precisa de pelo menos um ramo")
        return Case(alvo, ramos, token.line)
