"""Parser completo: programa, classes, features, e a API pública da fase.

As expressões ficaram na etapa 11. Aqui entram as DECLARAÇÕES, que são a parte
fácil da gramática: não têm ambiguidade nem recursão à esquerda, cada função
lê uma sequência fixa de peças.

    program ::= [ class ';' ]+
    class   ::= 'class' TYPEID [ 'inherits' TYPEID ] '{' [ feature ';' ]* '}'
    feature ::= OBJECTID '(' [ formal (',' formal)* ] ')' ':' TYPEID '{' expr '}'
              | OBJECTID ':' TYPEID [ '<-' expr ]
    formal  ::= OBJECTID ':' TYPEID

É também aqui que ficam as duas fronteiras de recuperação de mais alto nível
(por classe e por feature) e a função parse(), que é o que o resto do
compilador chama.
"""

from dataclasses import dataclass
from typing import Optional

from ..lexico.etapa1_tokens import Token, TokenType
from ..lexico.etapa5_lexer import tokenize
from .etapa6_ast import (
    Attribute, ClassDef, ErrorExpr, Expr, Feature, Formal, Method, Program,
)
from .etapa8_erros_sintaticos import (
    SYNC_CLASS, SYNC_EXPR, SYNC_FEATURE, ParseError,
)
from .etapa11_parser_expr import ExpressionParser


class Parser(ExpressionParser):
    """Camada das declarações, montada sobre o parser de expressões."""

    # ----------------------------------------------------------------------
    # 1. Programa
    # ----------------------------------------------------------------------

    def parse_program(self) -> Program:
        """program ::= [ class ';' ]+

        Fronteira de recuperação mais externa: se uma classe inteira estiver
        irrecuperável, descartamos até o próximo `class` e seguimos. Assim um
        erro na primeira classe não esconde os erros das outras.
        """
        linha = self.peek().line
        classes: list[ClassDef] = []

        while not self.at_end():
            try:
                classes.append(self.parse_class())
            except ParseError:
                self.synchronize(SYNC_CLASS)
                # Não consumimos o `class`: ele é o começo da próxima volta.
                # O laço progride porque parse_class obrigatoriamente consome
                # esse token no primeiro expect.

        if not classes:
            self.error(self.peek(), "um programa COOL precisa de pelo menos uma classe")
        return Program(classes, linha)

    # ----------------------------------------------------------------------
    # 2. Classe
    # ----------------------------------------------------------------------

    def parse_class(self) -> ClassDef:
        token = self.expect(TokenType.CLASS, "esperava a palavra-chave 'class'")
        nome = self.expect(TokenType.TYPEID,
                           "esperava o nome da classe (comecando com maiuscula)")

        pai: Optional[str] = None
        if self.match(TokenType.INHERITS):
            pai = self.expect(
                TokenType.TYPEID,
                "esperava o nome da classe-mae depois de 'inherits'",
            ).lexeme

        self.expect(TokenType.LBRACE, "esperava '{' para abrir o corpo da classe")

        features: list[Feature] = []
        while not self.check(TokenType.RBRACE) and not self.at_end():
            try:
                feature = self.parse_feature()
            except ParseError:
                # Fronteira de recuperação por feature: uma feature quebrada
                # não derruba a classe inteira.
                self.synchronize(SYNC_FEATURE)
                if self.match(TokenType.SEMI):
                    continue
                if self.check(TokenType.CLASS):
                    # Perdemos o '}' desta classe. Deixamos o `class` para
                    # parse_program e saímos, em vez de engolir a classe
                    # seguinte dentro desta.
                    return ClassDef(nome.lexeme, pai, features, token.line)
                continue

            features.append(feature)
            try:
                self.expect(TokenType.SEMI, "toda feature termina com ';'")
            except ParseError:
                # Caso especial que vale tratar à parte: a feature saiu
                # INTEIRA e só faltou o ';'. Já estamos numa fronteira de
                # feature, então descartar tokens aqui só faria perder a
                # feature seguinte, que não tem culpa nenhuma. Reportamos e
                # seguimos o laço.
                pass

        self.expect(TokenType.RBRACE, "esperava '}' para fechar o corpo da classe")
        self.expect(TokenType.SEMI, "toda classe termina com ';'")
        return ClassDef(nome.lexeme, pai, features, token.line)

    # ----------------------------------------------------------------------
    # 3. Features
    # ----------------------------------------------------------------------

    def parse_feature(self) -> Feature:
        """Método ou atributo — as duas alternativas começam com OBJECTID.

        FATORAÇÃO À ESQUERDA outra vez: consumimos o identificador, que é comum
        às duas, e decidimos pelo token seguinte ('(' é método, ':' é atributo).
        Sem isso, precisaríamos de lookahead de 2.
        """
        nome = self.expect(TokenType.OBJECTID,
                           "esperava o nome de um atributo ou metodo")

        if self.check(TokenType.LPAREN):
            return self._parse_metodo(nome)
        return self._parse_atributo(nome)

    def _parse_metodo(self, nome: Token) -> Method:
        self.expect(TokenType.LPAREN, "esperava '(' na declaracao do metodo")

        formais: list[Formal] = []
        if not self.check(TokenType.RPAREN):
            formais.append(self.parse_formal())
            while self.match(TokenType.COMMA):
                formais.append(self.parse_formal())

        self.expect(TokenType.RPAREN, "esperava ')' para fechar a lista de parametros")
        self.expect(TokenType.COLON, "esperava ':' antes do tipo de retorno")
        retorno = self.expect(TokenType.TYPEID, "esperava o tipo de retorno do metodo")

        self.expect(TokenType.LBRACE, "esperava '{' para abrir o corpo do metodo")
        # ARMADILHA CLÁSSICA: estas chaves NÃO são o bloco `{ expr; expr; }`.
        # São chaves de delimitação, com UMA expressão e SEM ';'. Por isso
        # chamamos parse_expression e nunca parse_block. Um corpo que de fato
        # tenha vários comandos escreve as chaves duas vezes:
        # `{ { a; b; } }` — as de fora delimitam, as de dentro são o bloco.
        #
        # Fronteira de recuperação: o corpo é delimitado por chaves, então um
        # erro aqui dentro pode ser CONTIDO por elas. Sem isto, o '}' do corpo
        # seria confundido com o '}' da classe e o resto da classe se perderia.
        try:
            corpo: Expr = self.parse_expression()
        except ParseError:
            corpo = ErrorExpr("corpo de metodo invalido", self.peek().line)
            self.synchronize(SYNC_EXPR)

        self.expect(TokenType.RBRACE, "esperava '}' para fechar o corpo do metodo")

        return Method(nome.lexeme, formais, retorno.lexeme, corpo, nome.line)

    def _parse_atributo(self, nome: Token) -> Attribute:
        self.expect(TokenType.COLON, "esperava ':' depois do nome do atributo")
        tipo = self.expect(TokenType.TYPEID, "esperava o tipo do atributo")

        inicial: Optional[Expr] = None
        if self.match(TokenType.ASSIGN):
            inicial = self.parse_expression()

        return Attribute(nome.lexeme, tipo.lexeme, inicial, nome.line)

    def parse_formal(self) -> Formal:
        nome = self.expect(TokenType.OBJECTID, "esperava o nome do parametro")
        self.expect(TokenType.COLON, "esperava ':' depois do nome do parametro")
        tipo = self.expect(TokenType.TYPEID, "esperava o tipo do parametro")
        return Formal(nome.lexeme, tipo.lexeme, nome.line)


# --------------------------------------------------------------------------
# 4. API pública da fase
# --------------------------------------------------------------------------

@dataclass
class ParseResult:
    """O que uma análise devolve: a árvore e os erros das DUAS fases.

    Não é frozen como os nós da AST: aqui não há razão para imutabilidade, isto
    é só um pacote de resultado.
    """

    program: Optional[Program]
    lexical_errors: list[Token]
    syntax_errors: list[ParseError]

    @property
    def has_errors(self) -> bool:
        return bool(self.lexical_errors or self.syntax_errors)


def parse(source: str, filename: str = "<entrada>") -> ParseResult:
    """Analisa um programa COOL inteiro: do texto até a AST.

    Os Tokens ERROR que o lexer injetou são SEPARADOS antes de parsear, em vez
    de entregues ao parser. A razão: um ERROR não pertence a nenhuma categoria
    sintática, então cada erro léxico viraria um erro sintático em cascata, sem
    informação nova — o usuário já foi avisado pelo lexer. Filtrando, uma única
    execução dá a lista completa de erros léxicos E a análise sintática do resto.

    A contrapartida, aceita: uma string não terminada some do fluxo, e o parser
    pode reclamar de um operando faltando logo adiante. O erro raiz já foi
    reportado, um nível abaixo.
    """
    todos = tokenize(source)
    lexical_errors = [t for t in todos if t.type is TokenType.ERROR]
    limpos = [t for t in todos if t.type is not TokenType.ERROR]

    parser = Parser(limpos, filename)
    programa = parser.parse_program()
    return ParseResult(programa, lexical_errors, parser.errors)


def parse_expression(source: str, filename: str = "<expressao>") -> ParseResult:
    """Analisa uma expressão solta, sem a classe em volta.

    Existe para a flag --expr: é o modo de depuração que permite conferir a
    precedência de um operador sem escrever um programa inteiro à volta dele.
    """
    todos = tokenize(source)
    lexical_errors = [t for t in todos if t.type is TokenType.ERROR]
    limpos = [t for t in todos if t.type is not TokenType.ERROR]

    parser = Parser(limpos, filename)
    try:
        arvore = parser.parse_expression()
    except ParseError:
        arvore = None
    else:
        if not parser.at_end():
            parser.error(parser.peek(), "sobrou texto depois do fim da expressao")

    # Reaproveitamos ParseResult, mas o campo `program` carrega uma Expr neste
    # caso: é um modo de depuração, não faz parte do fluxo normal do compilador.
    return ParseResult(arvore, lexical_errors, parser.errors)
