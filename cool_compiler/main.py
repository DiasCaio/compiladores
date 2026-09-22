"""Ponto de entrada único do compilador.

Concentra aqui tudo que é interface com o usuário (argumentos, menu de
examples/, impressão), para que os módulos das etapas continuem sendo
bibliotecas puras. Antes da reorganização em pacotes, este papel era do bloco
`if __name__ == "__main__"` de etapa5_lexer.py — que servia só ao lexer.

Uso, sempre a partir da raiz do repositório:

    python -m cool_compiler.main                          menu de examples/
    python -m cool_compiler.main arquivo.cl               imprime a AST
    python -m cool_compiler.main --fase lexico arquivo.cl imprime os tokens
    python -m cool_compiler.main --fase ambas  arquivo.cl as duas coisas
    python -m cool_compiler.main --expr "1 + 2 * 3"       expressao solta
    python -m cool_compiler.main --ascii arquivo.cl       arvore sem Unicode

Também dá para clicar direto no botão de "play" do editor (Run Python File),
sem usar -m. O bloco logo abaixo é o que torna isso possível: veja o
comentário ali para o porquê.
"""

import argparse
import sys
from pathlib import Path

# Rodando com `python -m cool_compiler.main`, o Python já sabe que este
# arquivo faz parte do pacote cool_compiler, e os imports relativos abaixo
# (from .lexico import ...) funcionam sem ajuda.
#
# Mas clicar no botão de "play" do editor executa `python main.py` direto,
# como um script solto. Nesse caso o Python NÃO sabe que main.py é parte de um
# pacote — __package__ vem vazio — e o import relativo quebraria com
# "attempted relative import with no known parent package".
#
# Este bloco cobre esse segundo caso: se __package__ estiver vazio, inserimos
# a pasta MÃE de cool_compiler/ (isto é, a raiz do repositório) no sys.path e
# declaramos manualmente qual é o pacote. É o mesmo efeito de ter rodado com
# -m, só que decidido em tempo de execução.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "cool_compiler"

from .lexico.etapa5_lexer import tokenize
from .sintatico.etapa7_ast_printer import configurar_saida_utf8, format_ast
from .sintatico.etapa8_erros_sintaticos import MAX_ERROS_EXIBIDOS
from .sintatico.etapa12_parser import ParseResult, parse, parse_expression

# main.py fica ao lado de examples/, então o caminho sai natural. O .resolve()
# existe porque __file__ pode vir relativo dependendo de como o Python foi
# invocado. (Em etapa5_lexer.py esta constante funcionava pelo mesmo motivo;
# ela se mudou para cá junto com o menu.)
EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"


# --------------------------------------------------------------------------
# 1. Escolha do arquivo
# --------------------------------------------------------------------------

def escolher_arquivo_exemplo() -> Path:
    """Lista os arquivos .cl da pasta examples/ e deixa o usuário
    escolher um deles digitando o número correspondente.
    """
    arquivos = sorted(EXAMPLES_DIR.glob("*.cl"))
    if not arquivos:
        print(f"Nenhum arquivo .cl encontrado em {EXAMPLES_DIR}")
        sys.exit(1)

    print("Arquivos disponíveis em examples/:")
    for indice, caminho in enumerate(arquivos, start=1):
        print(f"  {indice}. {caminho.name}")

    print("\n")
    escolha = input("Digite o número do arquivo: ")
    print('\n')
    return arquivos[int(escolha) - 1]


def resolver_caminho(texto: str) -> Path:
    """Aceita um caminho qualquer ou só o nome de um exemplo.

    Assim `--expr` à parte, tanto `cool_compiler/examples/contador.cl` quanto
    `contador.cl` funcionam, de qualquer diretório.
    """
    caminho = Path(texto)
    if caminho.exists():
        return caminho

    alternativo = EXAMPLES_DIR / texto
    if alternativo.exists():
        return alternativo

    print(f"Arquivo não encontrado: {texto}")
    sys.exit(1)


# --------------------------------------------------------------------------
# 2. As duas fases
# --------------------------------------------------------------------------

def executar_lexico(codigo: str) -> int:
    """Imprime um Token por linha, no formato do lexer de referência."""
    for token in tokenize(codigo):
        print(token)
    return 0


def relatar(resultado: ParseResult, nome: str, ascii_only: bool) -> int:
    """Imprime os erros das duas fases e a árvore. Devolve o código de saída.

    Os erros léxicos saem primeiro, num bloco próprio: eles vêm de uma fase
    anterior e não são culpa da gramática. Mesmo havendo erro léxico, a árvore
    do que sobrou continua sendo impressa — é a política de nunca abortar,
    valendo também para a apresentação.
    """
    if resultado.lexical_errors:
        print("Erros lexicos encontrados (a analise sintatica seguiu mesmo assim):")
        for token in resultado.lexical_errors:
            print(f"  {nome}:{token.line}: {token.value} -> {token.lexeme!r}")
        print()

    if resultado.program is not None:
        print(format_ast(resultado.program, ascii_only))

    if resultado.syntax_errors:
        print()
        total = len(resultado.syntax_errors)
        print(f"{total} erro(s) sintatico(s):")
        for erro in resultado.syntax_errors[:MAX_ERROS_EXIBIDOS]:
            print(f"  {erro}")
        if total > MAX_ERROS_EXIBIDOS:
            print(f"  ... e mais {total - MAX_ERROS_EXIBIDOS}")

    return 1 if resultado.has_errors else 0


# --------------------------------------------------------------------------
# 3. Linha de comando
# --------------------------------------------------------------------------

def construir_parser_de_argumentos() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cool_compiler.main",
        description="Compilador didático de COOL: análise léxica e sintática.",
    )
    parser.add_argument(
        "arquivo",
        nargs="?",
        help="programa .cl a analisar; sem ele, abre o menu de examples/",
    )
    parser.add_argument(
        "--fase",
        choices=("lexico", "sintatico", "ambas"),
        default="sintatico",
        help="qual fase executar (padrão: sintatico)",
    )
    parser.add_argument(
        "--expr",
        metavar="EXPRESSAO",
        help="analisa uma expressão solta em vez de um arquivo",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="desenha a árvore com |-- em vez dos caracteres de box-drawing",
    )
    return parser


def main() -> None:
    # Antes de qualquer print: sem isto, redirecionar a saída para um arquivo
    # quebraria no cp1252 ao imprimir os conectores da árvore.
    configurar_saida_utf8()

    argumentos = construir_parser_de_argumentos().parse_args()

    # Modo depuração: uma expressão solta, sem classe em volta.
    if argumentos.expr is not None:
        resultado = parse_expression(argumentos.expr)
        sys.exit(relatar(resultado, "<expressao>", argumentos.ascii))

    if argumentos.arquivo is None:
        caminho = escolher_arquivo_exemplo()
    else:
        caminho = resolver_caminho(argumentos.arquivo)

    codigo = caminho.read_text(encoding="utf-8")

    if argumentos.fase == "lexico":
        sys.exit(executar_lexico(codigo))

    if argumentos.fase == "ambas":
        print("=== Tokens ===")
        executar_lexico(codigo)
        print()
        print("=== AST ===")

    sys.exit(relatar(parse(codigo, caminho.name), caminho.name, argumentos.ascii))


if __name__ == "__main__":
    main()
