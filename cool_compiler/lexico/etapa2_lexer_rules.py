import re

from .etapa1_tokens import TokenType

# --------------------------------------------------------------------------
# 1. Tabela de palavras-chave "normais" (case-insensitive).
#    Todas as chaves ficam em minúsculo de propósito: antes de consultar
#    essa tabela, vamos sempre converter o texto lido para minúsculo.
# --------------------------------------------------------------------------
KEYWORDS = {
    "class": TokenType.CLASS,
    "else": TokenType.ELSE,
    "fi": TokenType.FI,
    "if": TokenType.IF,
    "in": TokenType.IN,
    "inherits": TokenType.INHERITS,
    "isvoid": TokenType.ISVOID,
    "let": TokenType.LET,
    "loop": TokenType.LOOP,
    "pool": TokenType.POOL,
    "then": TokenType.THEN,
    "while": TokenType.WHILE,
    "case": TokenType.CASE,
    "esac": TokenType.ESAC,
    "new": TokenType.NEW,
    "of": TokenType.OF,
    "not": TokenType.NOT,
}


def classify_identifier(lexeme: str) -> TokenType:
    """Recebe um texto que já bate com o formato geral de identificador
    (letra seguida de letras/dígitos/underscore) e decide a categoria
    exata: palavra-chave, booleano, TYPEID ou OBJECTID.
    """
    lower = lexeme.lower()

    if lower in KEYWORDS:
        return KEYWORDS[lower]

    #verificamos se o lexema é "true" ou "false" e se o texto original começa com letra minúscula
    if lower in ("true", "false") and lexeme[0].islower():
        return TokenType.BOOL_CONST

    #pela regra, se começa com maiúscula identifica um tipo (como uma classe), senão é um identificador de objeto (variável, parâmetro, etc.)
    if lexeme[0].isupper():
        return TokenType.TYPEID

    return TokenType.OBJECTID


# --------------------------------------------------------------------------
# 2. Especificação dos tokens do "modo normal", em ORDEM DE PRIORIDADE.
#    A ordem desta lista importa: quando dois padrões poderiam casar no
#    mesmo ponto do texto, o primeiro da lista é que vence.
#    Exemplo seria o line comment vs minus
# --------------------------------------------------------------------------
TOKEN_SPECS = [
    ("WHITESPACE",          r"[ \t\r\f\v]+"),
    ("NEWLINE",              r"\n"),
    ("LINE_COMMENT",         r"--[^\n]*"),
    ("COMMENT_OPEN",         r"\(\*"),
    ("COMMENT_CLOSE_STRAY",  r"\*\)"),
    ("STRING_OPEN",          r"\""),
    ("IDENTIFIER",           r"[A-Za-z][A-Za-z0-9_]*"),
    ("INT_CONST",            r"[0-9]+"),
    ("ASSIGN",               r"<-"),
    ("DARROW",               r"=>"),
    ("LE",                   r"<="),
    ("LT",                   r"<"),
    ("PLUS",                 r"\+"),
    ("MINUS",                r"-"),
    ("TIMES",                r"\*"),
    ("DIVIDE",               r"/"),
    ("TILDE",                r"~"),
    ("EQ",                   r"="),
    ("LPAREN",               r"\("),
    ("RPAREN",               r"\)"),
    ("LBRACE",               r"\{"),
    ("RBRACE",               r"\}"),
    ("COLON",                r":"),
    ("SEMI",                 r";"),
    ("COMMA",                r","),
    ("DOT",                  r"\."),
    ("AT",                   r"@"),
    ("MISMATCH",             r"."),
]


#faz o casamento de todos os regex de Token_Specs
#a ideia é que quando a gente passe os tokens recebidos, a gente consiga identificar qual regex casou com o texto, 
# e assim saber qual é o tipo do token
MASTER_PATTERN = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECS)
)
