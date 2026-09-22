"""Cursor: a leitura da lista de tokens, com um token de lookahead.

O parser de descida recursiva é escrito como um monte de funções pequenas, uma
por regra da gramática. Todas elas precisam das mesmas operações básicas:
espiar o token atual, consumi-lo, exigir que ele seja de um tipo específico.
Esta classe concentra essas operações, para que as funções da gramática falem
só de COOL.

É também aqui que mora a recuperação de erro (`synchronize` e o flag de
pânico), porque ela é mexida no cursor: recuperar-se de um erro é, no fundo,
avançar o cursor até um lugar seguro.

A cadeia de herança da fase é Cursor -> ExpressionParser -> Parser. Cada etapa
acrescenta uma camada sobre a anterior, na mesma progressão do léxico. Funciona
porque as dependências não têm ciclo: expressões nunca precisam conhecer classes
e features, só o contrário.
"""

from ..lexico.etapa1_tokens import Token, TokenType
from .etapa8_erros_sintaticos import ParseError


class Cursor:
    """Percorre a lista de tokens produzida por tokenize()."""

    def __init__(self, tokens: list[Token], filename: str = "<entrada>"):
        self.tokens = tokens
        self.filename = filename
        self.pos = 0
        # Erros acumulados: o parser nunca aborta, então esta lista é o
        # relatório final.
        self.errors: list[ParseError] = []
        # Enquanto True, erros novos são engolidos (ver o método error).
        self.panicking = False

    # ---- Leitura sem consumir ------------------------------------------

    def peek(self, adiante: int = 0) -> Token:
        """Devolve o token atual, ou o que está `adiante` posições à frente.

        Como tokenize() já materializou TODOS os tokens numa lista, espiar
        adiante é só indexação — não custa nada. Fosse o lexer um gerador,
        precisaríamos de um buffer.

        Passando do fim, devolve o último token, que é sempre o EOF. Assim
        nenhum chamador precisa checar limite antes de espiar.
        """
        indice = self.pos + adiante
        if indice >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[indice]

    def check(self, tipo: TokenType) -> bool:
        """O token atual é deste tipo?"""
        return self.peek().type is tipo

    def check_ahead(self, adiante: int, tipo: TokenType) -> bool:
        """O token `adiante` posições à frente é deste tipo?

        É o lookahead de 2 que resolve o único ponto da gramática de COOL onde
        a decisão precisa ser tomada ANTES de consumir: distinguir
        `x <- expr` (atribuição) de `x` (só uma variável). Ver etapa 11.
        """
        return self.peek(adiante).type is tipo

    def at_end(self) -> bool:
        return self.check(TokenType.EOF)

    # ---- Consumo --------------------------------------------------------

    def advance(self) -> Token:
        """Consome o token atual e o devolve.

        Tokens ERROR do lexer são pulados aqui como defesa em profundidade.
        Normalmente eles já foram filtrados por parse() (etapa 12) e nunca
        chegam até aqui; mas se alguém construir um Parser direto sobre a saída
        crua de tokenize(), o comportamento continua sensato em vez de gerar
        uma cascata de erros sintáticos sem sentido.
        """
        while (self.pos < len(self.tokens) - 1
               and self.tokens[self.pos].type is TokenType.ERROR):
            self.pos += 1
        token = self.tokens[self.pos]
        if not self.at_end():
            self.pos += 1
        return token

    def match(self, *tipos: TokenType) -> Token | None:
        """Consome o token atual se ele for de um dos tipos; senão devolve None.

        É o atalho para as partes OPCIONAIS da gramática (o `inherits` de uma
        classe, o `<- valor` de um atributo), onde não achar não é erro.
        """
        for tipo in tipos:
            if self.check(tipo):
                return self.advance()
        return None

    def expect(self, tipo: TokenType, message: str) -> Token:
        """Exige um token deste tipo; erra se não vier.

        É o método mais usado do parser: cada peça OBRIGATÓRIA da gramática
        (o `then` de um if, o `;` de uma feature) vira um expect com a mensagem
        que explica o que faltava.
        """
        if self.check(tipo):
            # Consumimos um token esperado, ou seja, houve PROGRESSO: se
            # estávamos em pânico, voltamos ao normal e erros novos voltam a
            # ser reportados.
            self.panicking = False
            return self.advance()
        raise self.error(self.peek(), message)

    # ---- Erro e recuperação ---------------------------------------------

    def error(self, token: Token, message: str) -> ParseError:
        """Registra um erro e DEVOLVE a exceção, sem levantá-la.

        Quem chama decide se levanta (`raise self.error(...)`, para desempilhar
        até a fronteira de recuperação) ou se só registra e segue (quando dá
        para continuar de onde está).

        A supressão por pânico é o que separa uma saída legível de quarenta
        mensagens inúteis: depois do primeiro erro, tudo que vem até a próxima
        sincronização é quase sempre cascata do mesmo problema.
        """
        erro = ParseError(token, message, self.filename)
        if not self.panicking:
            self.errors.append(erro)
            self.panicking = True
        return erro

    def synchronize(self, conjunto: set[TokenType]) -> None:
        """Modo pânico: descarta tokens até cair num ponto de retomada.

        NÃO consome o token de sincronização. Quem chamou é que sabe o que
        fazer com ele: consumir o `;` e seguir o laço, ou deixar o `class`
        para o nível de cima tratar.

        Garantia de que isto não gera laço infinito: o conjunto sempre contém
        EOF, e at_end() guarda todos os laços do parser. Além disso, em
        parse_program o único token de sincronização além de EOF é `class`,
        que parse_class obrigatoriamente consome no primeiro expect — então
        cada volta do laço externo consome pelo menos um token.
        """
        self.panicking = False
        while not self.at_end() and self.peek().type not in conjunto:
            self.advance()


# --------------------------------------------------------------------------
# Teste manual do cursor, antes de existir qualquer regra da gramática
# --------------------------------------------------------------------------

if __name__ == "__main__":
    from ..lexico.etapa5_lexer import tokenize

    cursor = Cursor(tokenize("class Main { }"), "exemplo.cl")

    print("Tokens consumidos um a um:")
    while not cursor.at_end():
        print(f"  {cursor.advance()}")

    print()
    print("Lookahead sobre uma atribuicao (x <- 1):")
    outro = Cursor(tokenize("x <- 1"), "exemplo.cl")
    print(f"  atual e OBJECTID?      {outro.check(TokenType.OBJECTID)}")
    print(f"  o proximo e ASSIGN?    {outro.check_ahead(1, TokenType.ASSIGN)}")

    print()
    print("Um expect que falha:")
    try:
        outro.expect(TokenType.CLASS, "esperava a palavra-chave 'class'")
    except ParseError as erro:
        print(f"  {erro}")
    print(f"  erros acumulados: {len(outro.errors)}")
