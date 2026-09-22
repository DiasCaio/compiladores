"""Erro sintático e os conjuntos de sincronização da recuperação.

A filosofia é a mesma já adotada no lexer: NUNCA abortar. Um caractere inválido
não faz o lexer parar de escanear — ele vira Token(ERROR, ...) e a varredura
segue. Do mesmo jeito, um erro sintático não faz o parser parar: ele é
registrado, o parser descarta tokens até um ponto seguro e continua.

O motivo é prático. Um compilador que morre no primeiro erro obriga a compilar,
corrigir, compilar, corrigir, um erro por vez. Um que se recupera reporta
vários numa passada só.

A técnica de recuperação aqui é o MODO PÂNICO: ao errar, o parser descarta
tokens até encontrar um que sirva de ponto de retomada — algo que marque o fim
da construção que deu errado. Os conjuntos abaixo dizem quais tokens são esses.
"""

from ..lexico.etapa1_tokens import Token, TokenType


class ParseError(Exception):
    """Um erro sintático.

    Tem papel duplo, de propósito:

      1. É LEVANTADA, para desempilhar as chamadas recursivas de uma vez até a
         fronteira de recuperação mais próxima. Sem isso, cada nível do parser
         teria que devolver um código de erro e checá-lo, o que espalharia
         if de erro por todas as funções da gramática.
      2. É GUARDADA na lista de erros do parser, para o relatório final.

    E se formata sozinha em __str__, pelo mesmo motivo que Token tem __repr__:
    quem chama não deveria precisar saber montar a mensagem.
    """

    def __init__(self, token: Token, message: str, filename: str = "<entrada>"):
        self.token = token
        self.message = message
        self.filename = filename
        super().__init__(str(self))

    def __str__(self) -> str:
        # No EOF não existe lexema para mostrar: dizer "encontrei ''" seria
        # confuso, então nomeamos a situação.
        if self.token.type is TokenType.EOF:
            onde = "o fim do arquivo"
        else:
            onde = f"{self.token.lexeme!r} ({self.token.type.name})"
        return (
            f"{self.filename}:{self.token.line}: erro sintatico: "
            f"{self.message}; encontrei {onde}"
        )


# --------------------------------------------------------------------------
# Conjuntos de sincronização
# --------------------------------------------------------------------------
# Cada conjunto responde à pergunta "depois de errar AQUI, em que token dá para
# recomeçar?". A escolha é sempre a mesma ideia: parar em algo que marque uma
# FRONTEIRA, não no meio de uma construção.
#
# A espinha dorsal de COOL são três tokens:
#   ;      termina uma feature, um comando de bloco e um ramo de case
#   }      fecha uma classe, um corpo de método e um bloco
#   class  começa uma declaração nova, e é a retomada de último recurso
#
# EOF entra em todos porque é o que garante que a sincronização sempre para.

SYNC_CLASS = {
    TokenType.CLASS,
    TokenType.EOF,
}

SYNC_FEATURE = {
    TokenType.SEMI,
    TokenType.RBRACE,
    TokenType.CLASS,
    TokenType.EOF,
}

# Dentro de uma expressão há mais lugares seguros para parar: todo terminador
# de construção fechada serve. Parar num deles permite RETOMAR a construção em
# curso (o if, o while, o case) em vez de descartá-la inteira.
SYNC_EXPR = {
    TokenType.SEMI,
    TokenType.RBRACE,
    TokenType.RPAREN,
    TokenType.COMMA,
    TokenType.THEN,
    TokenType.ELSE,
    TokenType.FI,
    TokenType.LOOP,
    TokenType.POOL,
    TokenType.IN,
    TokenType.OF,
    TokenType.ESAC,
    TokenType.CLASS,
    TokenType.EOF,
}

# Teto de mensagens exibidas. Passando disso, a saída deixou de ajudar: quase
# certamente o arquivo tem um problema estrutural lá no começo.
MAX_ERROS_EXIBIDOS = 20
