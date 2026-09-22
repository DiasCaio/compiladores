"""Impressão da AST como árvore desenhada.

Uma AST só é útil para estudar se der para OLHAR para ela. Este módulo desenha
a árvore com os caracteres de box-drawing do Unicode, no mesmo estilo do
comando `tree`:

    Assign x (linha 4)
    └── BinaryOp < (linha 4)
        ├── esquerda: BinaryOp + (linha 4)
        │   ├── esquerda: IntConst 1 (linha 4)
        │   └── direita: BinaryOp * (linha 4)
        │       ├── esquerda: IntConst 2 (linha 4)
        │       └── direita: IntConst 3 (linha 4)
        └── direita: IntConst 4 (linha 4)

A leitura de precedência sai direto do desenho: quem está mais fundo na árvore
foi agrupado primeiro, logo tem precedência mais forte.

O módulo é dividido em três partes que não se misturam:

  - `_rotular`  diz como se ESCREVE um nó numa linha;
  - `_filhos`   diz quais são os filhos de um nó e como se chama cada papel;
  - `_desenhar` cuida só dos conectores, sem saber nada sobre COOL.

Separar assim significa que acrescentar um nó novo à AST custa duas entradas de
`match`, e nunca mexer no desenho.
"""

import sys

from .etapa6_ast import (
    Assign, Attribute, BinaryOp, Block, BoolConst, Case, CaseBranch, ClassDef,
    Dispatch, ErrorExpr, Formal, If, IntConst, IsVoid, Let, Method, Neg, New,
    Node, Not, ObjectId, Program, StaticDispatch, StringConst, While,
)

# --------------------------------------------------------------------------
# 1. Conectores
# --------------------------------------------------------------------------
# "ramo" é usado num filho do meio, "ultimo" no último filho. Abaixo de um
# filho do meio o tronco precisa continuar descendo ("tronco"); abaixo do
# último ele acabou, e a coluna vira espaço em branco ("vazio").
#
# Os quatro têm a MESMA largura (4 colunas), senão as colunas desalinham nos
# níveis mais fundos.

CONECTORES_UNICODE = {
    "ramo": "├── ",   # ├──
    "ultimo": "└── ", # └──
    "tronco": "│   ",           # │
    "vazio": "    ",
}

# Escape hatch para terminal antigo, ou para colar a árvore num lugar que não
# aceite Unicode. Ligado pela flag --ascii de main.py.
CONECTORES_ASCII = {
    "ramo": "|-- ",
    "ultimo": "`-- ",
    "tronco": "|   ",
    "vazio": "    ",
}


# --------------------------------------------------------------------------
# 2. API pública
# --------------------------------------------------------------------------

def format_ast(no: Node, ascii_only: bool = False) -> str:
    """Devolve a árvore desenhada como uma string única.

    Devolver string em vez de imprimir direto deixa a função testável e
    componível: dá para comparar com um esperado, ou embutir num relatório.
    """
    conectores = CONECTORES_ASCII if ascii_only else CONECTORES_UNICODE
    linhas: list[str] = []
    # A raiz não tem conector nem prefixo: ela é a única linha na coluna zero.
    _desenhar(no, prefixo="", conector="", rotulo=None,
              conectores=conectores, linhas=linhas)
    return "\n".join(linhas)


def print_ast(no: Node, ascii_only: bool = False) -> None:
    print(format_ast(no, ascii_only))


def configurar_saida_utf8() -> None:
    """Garante que os caracteres de box-drawing cheguem à saída.

    No Windows, quando a saída vai para um CONSOLE de verdade, o Python usa
    WriteConsoleW (UTF-16) e o ├── sai sem problema. Mas quando a saída é
    REDIRECIONADA para arquivo ou cano (`... > arvore.txt`), o Python cai na
    codificação de locale — cp1252 por aqui — e o │ levanta UnicodeEncodeError.

    Uma linha resolve os dois casos. O errors="replace" é só um cinto de
    segurança: mesmo que a reconfiguração falhe em algum ambiente exótico, o
    programa imprime um caractere substituto em vez de morrer.
    """
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------
# 3. O desenho (genérico: não sabe nada sobre COOL)
# --------------------------------------------------------------------------

def _desenhar(no: Node, prefixo: str, conector: str, rotulo: str | None,
              conectores: dict[str, str], linhas: list[str]) -> None:
    """Escreve a linha de `no` e desce recursivamente nos filhos.

    `prefixo` é a coluna de troncos herdada dos ancestrais, e `rotulo` nomeia o
    papel deste nó dentro do pai (condicao, entao, alvo, arg[0]...). O rótulo
    vai INLINE depois do conector: como o desenho já mostra a estrutura, gastar
    uma linha só para o rótulo seria ruído.
    """
    cabeca = f"{rotulo}: " if rotulo else ""
    linhas.append(prefixo + conector + cabeca + _rotular(no))

    filhos = _filhos(no)
    # Prefixo dos filhos: o que já vinha, mais a coluna deste nível. Sob o
    # último filho o tronco acabou (vira espaço); sob os outros, ele continua.
    if conector == conectores["ultimo"] or conector == "":
        prefixo_filhos = prefixo + (conectores["vazio"] if conector else "")
    else:
        prefixo_filhos = prefixo + conectores["tronco"]

    for indice, (rotulo_filho, filho) in enumerate(filhos):
        ultimo = indice == len(filhos) - 1
        _desenhar(
            filho,
            prefixo_filhos,
            conectores["ultimo"] if ultimo else conectores["ramo"],
            rotulo_filho,
            conectores,
            linhas,
        )


# --------------------------------------------------------------------------
# 4. Como se escreve cada nó numa linha
# --------------------------------------------------------------------------
# Regra: o que é escalar (nome, tipo, operador, valor literal) cabe na MESMA
# linha do nó. O que é expressão vira filho e ganha linha própria.

def _rotular(no: Node) -> str:
    """Devolve a descrição de uma linha só para `no`, sem os filhos."""
    match no:
        case Program(_, line):
            return f"Program (linha {line})"
        case ClassDef(name, parent, _, line):
            # Imprimimos "Object" quando não há inherits para lembrar a regra,
            # mas a AST continua guardando None: isto é só a apresentação.
            return f"Class {name} : {parent or 'Object'} (linha {line})"
        case Method(name, formals, return_type, _, line):
            parametros = ", ".join(f"{f.name} : {f.type_name}" for f in formals)
            return f"Method {name}({parametros}) : {return_type} (linha {line})"
        case Attribute(name, type_name, _, line):
            return f"Attribute {name} : {type_name} (linha {line})"
        case Formal(name, type_name, line):
            return f"Formal {name} : {type_name} (linha {line})"
        case Assign(name, _, line):
            return f"Assign {name} (linha {line})"
        case ObjectId(name, line):
            return f"ObjectId {name} (linha {line})"
        case Dispatch(target, method, _, line):
            # Dispatch implícito aparece marcado, para não confundir com
            # um dispatch comum cujo alvo simplesmente não foi impresso.
            marca = "" if target is not None else " (implicito)"
            return f"Dispatch .{method}{marca} (linha {line})"
        case StaticDispatch(_, type_name, method, _, line):
            return f"StaticDispatch @{type_name}.{method} (linha {line})"
        case If(_, _, _, line):
            return f"If (linha {line})"
        case While(_, _, line):
            return f"While (linha {line})"
        case Block(_, line):
            return f"Block (linha {line})"
        case Let(name, type_name, _, _, line):
            return f"Let {name} : {type_name} (linha {line})"
        case Case(_, _, line):
            return f"Case (linha {line})"
        case CaseBranch(name, type_name, _, line):
            return f"Branch {name} : {type_name} (linha {line})"
        case New(type_name, line):
            return f"New {type_name} (linha {line})"
        case IsVoid(_, line):
            return f"IsVoid (linha {line})"
        case Not(_, line):
            return f"Not (linha {line})"
        case Neg(_, line):
            return f"Neg ~ (linha {line})"
        case BinaryOp(operator, _, _, line):
            return f"BinaryOp {operator} (linha {line})"
        # !r nos literais pelo mesmo motivo do Token.__repr__: uma string com
        # \n dentro sairia quebrando o desenho da árvore se fosse impressa crua.
        case IntConst(value, line):
            return f"IntConst {value!r} (linha {line})"
        case StringConst(value, line):
            return f"StringConst {value!r} (linha {line})"
        case BoolConst(value, line):
            return f"BoolConst {value!r} (linha {line})"
        case ErrorExpr(message, line):
            return f"ErrorExpr {message!r} (linha {line})"
    return f"<no desconhecido: {type(no).__name__}>"


# --------------------------------------------------------------------------
# 5. Quais são os filhos de cada nó
# --------------------------------------------------------------------------

def _filhos(no: Node) -> list[tuple[str | None, Node]]:
    """Devolve os filhos de `no` como pares (rótulo, nó).

    Rótulo None quer dizer "filho óbvio, não precisa de nome": o operando de um
    ~ ou de um not, ou um item de uma lista homogênea de classes. Papéis que se
    distinguem (condicao/entao/senao, alvo/argumentos) sempre levam rótulo,
    senão a árvore fica ambígua.
    """
    match no:
        case Program(classes, _):
            return [(None, c) for c in classes]
        case ClassDef(_, _, features, _):
            return [(None, f) for f in features]
        case Method(_, formals, _, body, _):
            # Os formais já apareceram na linha do método; repeti-los como
            # filhos só engordaria a árvore.
            return [("corpo", body)]
        case Attribute(_, _, init, _):
            return [] if init is None else [("inicializacao", init)]
        case Assign(_, value, _):
            return [("valor", value)]
        case Dispatch(target, _, args, _):
            filhos: list[tuple[str | None, Node]] = []
            if target is not None:
                filhos.append(("alvo", target))
            filhos += [(f"arg[{i}]", a) for i, a in enumerate(args)]
            return filhos
        case StaticDispatch(target, _, _, args, _):
            return [("alvo", target)] + [(f"arg[{i}]", a) for i, a in enumerate(args)]
        case If(condition, then_branch, else_branch, _):
            return [("condicao", condition), ("entao", then_branch), ("senao", else_branch)]
        case While(condition, body, _):
            return [("condicao", condition), ("corpo", body)]
        case Block(expressions, _):
            return [(f"expr[{i}]", e) for i, e in enumerate(expressions)]
        case Let(_, _, init, body, _):
            filhos = []
            if init is not None:
                filhos.append(("inicializacao", init))
            filhos.append(("corpo", body))
            return filhos
        case Case(expression, branches, _):
            return [("alvo", expression)] + [(f"ramo[{i}]", b) for i, b in enumerate(branches)]
        case CaseBranch(_, _, body, _):
            return [("corpo", body)]
        case IsVoid(operand, _) | Not(operand, _) | Neg(operand, _):
            return [(None, operand)]
        case BinaryOp(_, left, right, _):
            return [("esquerda", left), ("direita", right)]
    # Literais, ObjectId, New, Formal e ErrorExpr são folhas.
    return []


# --------------------------------------------------------------------------
# 6. Teste manual: monta uma AST na mão e desenha
# --------------------------------------------------------------------------
# Útil para conferir o formato do desenho ANTES de existir um parser: se a
# árvore sai torta aqui, o problema é do printer, não do parser.

if __name__ == "__main__":
    configurar_saida_utf8()

    # Equivalente a:  class Main { main() : Object { 1 + 2 * 3 } };
    arvore = Program(
        [
            ClassDef(
                "Main",
                None,
                [
                    Method(
                        "main",
                        [],
                        "Object",
                        BinaryOp(
                            "+",
                            IntConst(1, 2),
                            BinaryOp("*", IntConst(2, 2), IntConst(3, 2), 2),
                            2,
                        ),
                        2,
                    )
                ],
                1,
            )
        ],
        1,
    )

    print("--- box-drawing (padrao) ---")
    print_ast(arvore)
    print()
    print("--- ascii (--ascii) ---")
    print_ast(arvore, ascii_only=True)
