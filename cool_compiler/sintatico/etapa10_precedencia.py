"""Tabela de precedência e associatividade dos operadores binários.

Este arquivo é para o parser o que o etapa2_lexer_rules.py é para o lexer: a
TABELA que dirige o trabalho, separada do laço que a consome. Mudar a
precedência de um operador aqui muda o formato da árvore, sem tocar no parser.

A precedência oficial de COOL, do MAIS FRACO para o MAIS FORTE:

    <-              associativo à direita
    not             prefixo
    <= < =          NÃO associativo
    + -             associativo à esquerda
    * /             associativo à esquerda
    isvoid          prefixo
    ~               prefixo
    @               pós-fixo
    .               pós-fixo

Só os quatro níveis do meio (os operadores binários de verdade) cabem numa
tabela; os prefixos e os pós-fixos viram funções próprias na etapa 11, porque
a forma deles é outra.

Equivale às declarações %right / %left / %nonassoc que um arquivo de bison
usaria — a diferença é que lá elas resolvem conflitos de uma gramática ambígua,
e aqui elas dirigem diretamente o algoritmo.
"""

from dataclasses import dataclass
from enum import Enum, auto

from ..lexico.etapa1_tokens import TokenType


class Assoc(Enum):
    """Como agrupar operadores de mesma precedência lado a lado."""

    LEFT = auto()       # a - b - c  vira  (a - b) - c
    NON_ASSOC = auto()  # a < b < c  é ERRO em COOL, nem uma leitura nem outra


@dataclass(frozen=True)
class BinaryInfo:
    """O que o parser precisa saber sobre um operador binário.

    O campo `operator` guarda o símbolo que vai para o nó BinaryOp. Poderíamos
    usar o lexema do token, mas tê-lo aqui deixa a tabela ser a única fonte de
    verdade: o parser não precisa olhar o texto que o usuário digitou.
    """

    operator: str
    precedence: int
    assoc: Assoc


# Precedência maior = liga mais forte = fica MAIS FUNDO na árvore.
BINARY_OPERATORS: dict[TokenType, BinaryInfo] = {
    TokenType.LE:     BinaryInfo("<=", 1, Assoc.NON_ASSOC),
    TokenType.LT:     BinaryInfo("<",  1, Assoc.NON_ASSOC),
    TokenType.EQ:     BinaryInfo("=",  1, Assoc.NON_ASSOC),
    TokenType.PLUS:   BinaryInfo("+",  2, Assoc.LEFT),
    TokenType.MINUS:  BinaryInfo("-",  2, Assoc.LEFT),
    TokenType.TIMES:  BinaryInfo("*",  3, Assoc.LEFT),
    TokenType.DIVIDE: BinaryInfo("/",  3, Assoc.LEFT),
}

# Piso inicial de precedência: quem chama parse_binary de fora começa daqui,
# aceitando qualquer operador da tabela.
MIN_PRECEDENCE = 1

# Os comparadores, para detectar o encadeamento proibido a < b < c.
COMPARISON_TOKENS = {TokenType.LE, TokenType.LT, TokenType.EQ}
