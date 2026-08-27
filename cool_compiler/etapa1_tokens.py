from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional

#Herda de Enum para criar uma lista fechada de tokens
#Usando Enum apenas para prevenção de erros silenciosos, assim se eu comparar "Class" com "class", o Python vai reclamar que não são do mesmo tipo
class TokenType(Enum):
    #Todos os tipos de token que o léxico de COOL pode produzir.

    # --- Palavras-chave (case-insensitive) ---
    CLASS = auto()
    ELSE = auto()
    FI = auto()
    IF = auto()
    IN = auto()
    INHERITS = auto()
    ISVOID = auto()
    LET = auto()
    LOOP = auto()
    POOL = auto()
    THEN = auto()
    WHILE = auto()
    CASE = auto()
    ESAC = auto()
    NEW = auto()
    OF = auto()
    NOT = auto()

    # --- Constantes ---
    BOOL_CONST = auto()   # true / false (regra de caixa própria)
    INT_CONST = auto()    # sequência de dígitos
    STR_CONST = auto()    # "..."

    # --- Identificadores ---
    TYPEID = auto()       # começa com maiúscula
    OBJECTID = auto()     # começa com minúscula

    # --- Operadores de dois caracteres ---
    ASSIGN = auto()         # <-
    DARROW = auto()         # =>
    LE = auto()              # <=

    # --- Operadores e pontuação de um caractere ---
    PLUS = auto()
    MINUS = auto()
    TIMES = auto()
    DIVIDE = auto()
    TILDE = auto()
    LT = auto()
    EQ = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    COLON = auto()
    SEMI = auto()
    COMMA = auto()
    DOT = auto()
    AT = auto()

    # --- Controle ---
    ERROR = auto()   # caractere/construção léxica inválida
    EOF = auto()     # fim de entrada


#dataclass serve apenas para agilizar a construção da classe
#Com ele não precisamos gerar o construtor na mão, por exemplo
#o frozen só bloqueia a sobrescrição de algum atributo
@dataclass(frozen=True)
class Token:
    """Um token reconhecido pelo lexer.

    Reúne num único objeto o que, no flex, ficava espalhado em duas
    variáveis globais (`yytext`, o texto casado, e `yylval`, o valor
    semântico) mais o tipo de token que era devolvido via `return`.
    """

    type: TokenType
    lexeme: str
    line: int
    value: Optional[Any] = None
    #Value guarda o conteúdo já processado do token, por exemplo, o valor numérico de um INT_CONST ou o valor booleano de um BOOL_CONST. 
    #Para tokens que não têm valor semântico, value é None.
    #Então em strings com \n, ele exibe o valor real da string, com a quebra de linha 


    def __repr__(self) -> str:
        if self.value is not None:
            return f"#{self.line} {self.type.name} {self.value!r}"
        return f"#{self.line} {self.type.name} {self.lexeme!r}"
    #!r serve pra mostrar o valor real do objeto, por exemplo, se for uma string com \n, 
    #ele exibe o valor real da string, com \n exposto. Fiz isso apenas para a visualização do token, 
    #não para o valor semântico, que continua sendo o valor real da string.
