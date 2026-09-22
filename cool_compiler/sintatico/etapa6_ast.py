"""
Arquivo que define a árvore da linguagem. Aqui temos a definição de todos os tipos de nós 
que o parser pode produzir, ou seja, a estrutura de dados que representa o programa COOL na 
memória. Cada nó é uma instância de uma classe, e cada classe corresponde a um tipo de 
construção da linguagem (como classes, métodos, expressões, etc.).
"""

from dataclasses import dataclass
from typing import Optional


# --------------------------------------------------------------------------
# 1. Classes base
# --------------------------------------------------------------------------
# Repare que as classes base estão vazias, e isso é de propósito.
#
# Se colocássemos aqui só o atributo "line", ele não viraria um campo de
# verdade: um campo de dataclass só existe em classes decoradas com
# @dataclass, e Node, Expr e Feature não são. O atributo ficaria solto, sem
# fazer parte da construção do nó.
#
# E se decorássemos essas bases com @dataclass para "line" ser reconhecido,
# ele passaria a ser herdado como o PRIMEIRO parâmetro de todo nó que viesse
# depois — ficaria BinaryOp(12, "+", esq, dir), com a linha na frente do que
# interessa, em vez de podermos deixá-la por último como fazemos abaixo.

class Node:
    """Base de todo nó da árvore."""


class Expr(Node):
    """Base das expressões: tudo que produz um valor.

    Em COOL quase tudo é expressão, inclusive if e while (que em muitas
    linguagens seriam comandos). Por isso Expr cobre tanta coisa aqui.
    """


class Feature(Node):
    """Base dos membros de uma classe: um método ou um atributo."""


# --------------------------------------------------------------------------
# 2. Estrutura do programa
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Program(Node):
    """A raiz da árvore: um programa COOL é uma lista de classes."""

    classes: list["ClassDef"]
    line: int


@dataclass(frozen=True)
class ClassDef(Node):
    """class Nome [inherits Pai] { features }

    O campo parent é None quando o inherits foi omitido. Não preenchemos com
    "Object" aqui de propósito: o parser registra o que estava ESCRITO, e a
    regra "quem não herda de ninguém herda de Object" é da fase semântica.
    """

    name: str
    parent: Optional[str]
    features: list[Feature]
    line: int


@dataclass(frozen=True)
class Method(Feature):
    """nome(formais) : TipoDeRetorno { corpo }"""

    name: str
    formals: list["Formal"]
    return_type: str
    body: Expr
    line: int


@dataclass(frozen=True)
class Attribute(Feature):
    """nome : Tipo [<- valor_inicial]"""

    name: str
    type_name: str
    init: Optional[Expr]
    line: int


@dataclass(frozen=True)
class Formal(Node):
    """Um parâmetro na declaração de um método: nome : Tipo."""

    name: str
    type_name: str
    line: int


# --------------------------------------------------------------------------
# 3. Nomes e atribuição
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Assign(Expr):
    """nome <- valor.

    Em COOL a atribuição é EXPRESSÃO: tem valor (o do lado direito), e é por
    isso que x <- y <- 1 faz sentido.
    """

    name: str
    value: Expr
    line: int


@dataclass(frozen=True)
class ObjectId(Expr):
    """Um identificador usado como valor: uma variável, um parâmetro, self."""

    name: str
    line: int


# --------------------------------------------------------------------------
# 4. Chamadas de método (dispatch)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Dispatch(Expr):
    """alvo.metodo(args), ou metodo(args) quando target é None.

    target=None marca o DISPATCH IMPLÍCITO: f(1) em vez de self.f(1).
    Poderíamos ter inventado um ObjectId("self") no lugar, mas aí a árvore
    afirmaria que o programador escreveu um self que ele não escreveu.
    Guardar None preserva o que estava no código; a fase semântica resolve.
    """

    target: Optional[Expr]
    method: str
    args: list[Expr]
    line: int


@dataclass(frozen=True)
class StaticDispatch(Expr):
    """alvo@Tipo.metodo(args).

    Serve para chamar a versão do método de uma classe ANCESTRAL, pulando a
    sobrescrita: é o equivalente em COOL do super.metodo() de outras
    linguagens, só que podendo nomear qualquer ancestral, não só o pai.
    """

    target: Expr
    type_name: str
    method: str
    args: list[Expr]
    line: int


# --------------------------------------------------------------------------
# 5. Controle de fluxo
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class If(Expr):
    """if condicao then entao else senao fi.

    Não há else_branch opcional: em COOL o else é OBRIGATÓRIO. Faz sentido,
    já que o if é uma expressão e precisa ter valor nos dois casos.
    """

    condition: Expr
    then_branch: Expr
    else_branch: Expr
    line: int


@dataclass(frozen=True)
class While(Expr):
    """while condicao loop corpo pool. O valor de um while em COOL é sempre void."""

    condition: Expr
    body: Expr
    line: int


@dataclass(frozen=True)
class Block(Expr):
    """{ expr; expr; ... } — avalia todas em ordem; o valor é o da última."""

    expressions: list[Expr]
    line: int


@dataclass(frozen=True)
class Let(Expr):
    """let nome : Tipo [<- init] in corpo.

    Um let com vários bindings (let a : Int, b : Int in ...) NÃO vira um nó com
    lista: vira vários Let aninhados, um por binding. É açúcar sintático, e
    desmontá-lo aqui poupa a fase semântica de tratar o caso de lista, já que
    o escopo de cada binding é exatamente o corpo do Let que o carrega.
    """

    name: str
    type_name: str
    init: Optional[Expr]
    body: Expr
    line: int


@dataclass(frozen=True)
class Case(Expr):
    """case expressao of ramos esac — escolhe o ramo pelo tipo em tempo de execução."""

    expression: Expr
    branches: list["CaseBranch"]
    line: int


@dataclass(frozen=True)
class CaseBranch(Node):
    """nome : Tipo => corpo, um ramo de um case.

    Não é Expr: um ramo sozinho não é uma expressão válida, só existe dentro
    de um Case.
    """

    name: str
    type_name: str
    body: Expr
    line: int


# --------------------------------------------------------------------------
# 6. Operadores
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class New(Expr):
    """new Tipo."""

    type_name: str
    line: int


@dataclass(frozen=True)
class IsVoid(Expr):
    """isvoid expressao."""

    operand: Expr
    line: int


@dataclass(frozen=True)
class Not(Expr):
    """not expressao — negação BOOLEANA (Bool -> Bool)."""

    operand: Expr
    line: int


@dataclass(frozen=True)
class Neg(Expr):
    """~expressao — negação ARITMÉTICA (Int -> Int).

    Separado de Not porque são operadores diferentes com tipos diferentes,
    apesar de os dois serem prefixos de um operando só. No cool-tree de
    referência esses nós se chamam comp e neg.
    """

    operand: Expr
    line: int


@dataclass(frozen=True)
class BinaryOp(Expr):
    """esquerda <operador> direita, para + - * / < <= =.

    Um nó só para os sete operadores, com o símbolo guardado em operator, em
    vez de sete classes (Plus, Minus, ...). A tabela de precedência da etapa 10
    já carrega o símbolo canônico, o printer imprime direto, e a fase semântica
    resolve com um dicionário de tipos por operador.
    """

    operator: str
    left: Expr
    right: Expr
    line: int


# --------------------------------------------------------------------------
# 7. Literais
# --------------------------------------------------------------------------
# O campo value já vem processado pelo lexer (int, str decodificada, bool): é
# exatamente o campo value do Token.

@dataclass(frozen=True)
class IntConst(Expr):
    value: int
    line: int


@dataclass(frozen=True)
class StringConst(Expr):
    value: str
    line: int


@dataclass(frozen=True)
class BoolConst(Expr):
    value: bool
    line: int


# --------------------------------------------------------------------------
# 8. Recuperação de erro
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ErrorExpr(Expr):
    """Buraco deixado por um erro sintático do qual o parser se recuperou.

    O paralelo com o lexer é direto: lá um caractere inválido vira
    Token(ERROR, ...) e o scanning continua; aqui uma expressão inválida vira
    ErrorExpr e o parsing continua. Nos dois casos a saída permanece
    bem-formada, e uma única execução reporta vários erros.
    """

    message: str
    line: int
