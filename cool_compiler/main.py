"""Ponto de entrada único do compilador.

Concentra aqui tudo que é interface com o usuário (argumentos, menu de
examples/, impressão), para que os módulos das etapas continuem sendo
bibliotecas puras. Antes da reorganização em pacotes, este papel era do bloco
`if __name__ == "__main__"` de etapa5_lexer.py — que servia só ao lexer.

Uso, sempre a partir da raiz do repositório:

    python -m cool_compiler.main                             menu de examples/
    python -m cool_compiler.main arquivo.cl                  AST com os tipos
    python -m cool_compiler.main --fase sintatico arquivo.cl AST sem os tipos
    python -m cool_compiler.main --fase lexico arquivo.cl    imprime os tokens
    python -m cool_compiler.main --fase ambas  arquivo.cl    tokens e AST
    python -m cool_compiler.main --expr "1 + 2 * 3"          expressao solta
    python -m cool_compiler.main --ascii arquivo.cl          arvore sem Unicode

Geração de código (alvo: Bril, executada pelo brili):

    python -m cool_compiler.main --fase bril arquivo.cl          programa Bril em JSON
    python -m cool_compiler.main --fase bril-texto arquivo.cl    o mesmo, em texto
    python -m cool_compiler.main --fase executar arquivo.cl      compila e roda no brili
    python -m cool_compiler.main --fase executar --bruto x.cl    saída sem decodificar
    python -m cool_compiler.main --fase bril -o x.json x.cl      salva o JSON em x.json

Também dá para clicar direto no botão de "play" do editor (Run Python File),
sem usar -m. O bloco logo abaixo é o que torna isso possível: veja o
comentário ali para o porquê.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

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

from .geracao.etapa21_bril import formatar_json, formatar_texto
from .geracao.etapa27_gerador import generate
from .geracao.etapa28_executor import BriliNaoEncontrado, executar
from .lexico.etapa5_lexer import tokenize
from .semantico.etapa20_verificador import analyze
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
# 2. As fases
# --------------------------------------------------------------------------

def executar_lexico(codigo: str) -> int:
    """Imprime um Token por linha, no formato do lexer de referência."""
    for token in tokenize(codigo):
        print(token)
    return 0


def listar_erros(erros: list, descricao: str) -> None:
    """Imprime o total e as primeiras mensagens de uma lista de erros.

    Compartilhada pelas fases sintática e semântica: o teto
    MAX_ERROS_EXIBIDOS vale para as duas, pelo mesmo motivo.
    """
    print()
    total = len(erros)
    print(f"{total} erro(s) {descricao}:")
    for erro in erros[:MAX_ERROS_EXIBIDOS]:
        print(f"  {erro}")
    if total > MAX_ERROS_EXIBIDOS:
        print(f"  ... e mais {total - MAX_ERROS_EXIBIDOS}")


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
        listar_erros(resultado.syntax_errors, "sintatico(s)")

    return 1 if resultado.has_errors else 0


def executar_semantico(resultado: ParseResult, nome: str, ascii_only: bool) -> int:
    """Roda a fase semântica sobre a árvore do parser e imprime a árvore com tipos.

    A fase semântica só roda sobre uma árvore SEM erros. A política de nunca
    abortar vale DENTRO de cada fase; entre uma fase e outra, rodar a semântica
    sobre uma árvore com buracos (ErrorExpr, features descartadas) geraria
    erros falsos, como "variavel nao declarada" para uma declaração que o
    parser teve que jogar fora. Nesse caso mostramos o relatório sintático e
    explicamos por que a fase seguinte não rodou.
    """
    if resultado.has_errors:
        codigo_saida = relatar(resultado, nome, ascii_only)
        print()
        print("A analise semantica nao foi executada: ela precisa de uma arvore sem erros.")
        return codigo_saida

    semantico = analyze(resultado.program, nome)
    print(format_ast(resultado.program, ascii_only, semantico.types))

    if semantico.errors:
        listar_erros(semantico.errors, "semantico(s)")

    return 1 if semantico.has_errors else 0


def gerar_bril(resultado: ParseResult, nome: str, ascii_only: bool) -> Optional[dict]:
    """Roda a semântica e, só se não houver NENHUM erro, a geração de código.

    Mesma política de executar_semantico: a geração confia que cada nome
    existe e cada tipo foi anotado, então um programa com qualquer erro
    léxico, sintático ou semântico para aqui, com o relatório da fase que
    falhou. Os avisos da geração (hoje: uso de entrada) vão para o stderr,
    para não sujar o JSON que sai no stdout.
    """
    nao_executada = "A geracao de codigo nao foi executada: ela precisa de um programa sem erros."
    if resultado.has_errors:
        relatar(resultado, nome, ascii_only)
        print()
        print(nao_executada)
        return None

    semantico = analyze(resultado.program, nome)
    if semantico.errors:
        listar_erros(semantico.errors, "semantico(s)")
        print()
        print(nao_executada)
        return None

    avisos: list[str] = []
    programa = generate(resultado.program, semantico, avisos=avisos)
    for aviso in avisos:
        print(f"aviso: {nome}: {aviso}", file=sys.stderr)
    return programa


def executar_geracao(resultado: ParseResult, nome: str,
                     argumentos: argparse.Namespace) -> int:
    """As três fases de geração: bril (JSON), bril-texto e executar."""
    programa = gerar_bril(resultado, nome, argumentos.ascii)
    if programa is None:
        return 1

    if argumentos.saida is not None:
        Path(argumentos.saida).write_text(formatar_json(programa) + "\n", encoding="utf-8")
        print(f"Programa Bril salvo em {argumentos.saida}", file=sys.stderr)

    if argumentos.fase == "bril":
        if argumentos.saida is None:           # com -o, o JSON já foi para o arquivo
            print(formatar_json(programa))
        return 0

    if argumentos.fase == "bril-texto":
        print(formatar_texto(programa))
        return 0

    try:
        execucao = executar(programa)
    except BriliNaoEncontrado as erro:
        print(erro, file=sys.stderr)
        return 1

    if argumentos.bruto:                       # um código de caractere por linha
        sys.stdout.write(execucao.bruto)
        sys.stdout.flush()
        sys.stderr.write(execucao.stderr)
        return execucao.codigo

    sys.stdout.write(execucao.saida)
    sys.stdout.flush()
    rodape = execucao.rodape()
    if rodape is not None:
        if execucao.saida and not execucao.saida.endswith("\n"):
            print()
        print(rodape, file=sys.stderr)
    return execucao.codigo


# --------------------------------------------------------------------------
# 3. Linha de comando
# --------------------------------------------------------------------------

def construir_parser_de_argumentos() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cool_compiler.main",
        description="Compilador didático de COOL: análise léxica, sintática e "
                    "semântica, e geração de código para Bril.",
    )
    parser.add_argument(
        "arquivo",
        nargs="?",
        help="programa .cl a analisar; sem ele, abre o menu de examples/",
    )
    # O padrão é a fase mais avançada que existe: cada fase já roda as
    # anteriores, então "semantico" mostra tudo o que o compilador sabe fazer.
    # "ambas" continua significando léxico + sintático, como antes.
    # As fases de geração NÃO viram o padrão: mudar o padrão mudaria a saída
    # de quem já roda o compilador sem --fase.
    parser.add_argument(
        "--fase",
        choices=("lexico", "sintatico", "semantico", "ambas",
                 "bril", "bril-texto", "executar"),
        default="semantico",
        help="qual fase executar (padrão: semantico; 'ambas' = tokens e AST; "
             "bril = JSON, bril-texto = texto, executar = roda no brili)",
    )
    parser.add_argument(
        "--bruto",
        action="store_true",
        help="com --fase executar: mostra a saída do brili sem decodificar "
             "(um código de caractere por linha)",
    )
    parser.add_argument(
        "-o",
        dest="saida",
        metavar="ARQUIVO.json",
        help="com as fases de geração: salva o programa Bril gerado neste arquivo",
    )
    parser.add_argument(
        "--expr",
        metavar="EXPRESSAO",
        help="analisa uma expressão solta em vez de um arquivo (só até a fase "
             "sintática: fora de uma classe não há contexto para os tipos)",
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

    resultado = parse(codigo, caminho.name)

    if argumentos.fase == "semantico":
        sys.exit(executar_semantico(resultado, caminho.name, argumentos.ascii))

    if argumentos.fase in ("bril", "bril-texto", "executar"):
        sys.exit(executar_geracao(resultado, caminho.name, argumentos))

    sys.exit(relatar(resultado, caminho.name, argumentos.ascii))


if __name__ == "__main__":
    main()
