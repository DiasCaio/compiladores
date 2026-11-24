"""Demonstração guiada: escolhe um programa COOL e mostra o compilador trabalhando.

Uso, a partir da raiz do repositório:

    python -m cool_compiler.demo                  menu com os exemplos
    python -m cool_compiler.demo arquivo.cl       vai direto para um arquivo
    python -m cool_compiler.demo --direto         sem pausas entre as fases
    python -m cool_compiler.demo --sem-cor        sem cores
    python -m cool_compiler.demo --salvar         grava o Bril em bril_gerado/
    python -m cool_compiler.demo --salvar --pasta X   grava o Bril em X/

Sem --salvar, o programa Bril só existe na memória: vai do gerador direto
para o brili pelo stdin, sem passar pelo disco. Com --salvar, cada exemplo
compilado deixa dois arquivos na pasta: nome.json (o que o brili lê) e
nome.bril (o mesmo programa em texto, para ler no editor).

O main.py é a ferramenta de linha de comando: uma fase por vez, saída fácil
de redirecionar. Este arquivo é a vitrine: roda TODAS as fases em sequência,
explica cada uma e resume o que ela produziu. Ele não compila nada sozinho;
só chama as etapas e mostra o resultado.
"""

import argparse
import os
import re
import sys
import textwrap
import time
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):                  # mesmo truque do main.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "cool_compiler"

from .geracao.etapa21_bril import formatar_json, formatar_texto
from .geracao.etapa27_gerador import generate
from .geracao.etapa28_executor import BriliNaoEncontrado, executar
from .lexico.etapa1_tokens import TokenType
from .lexico.etapa5_lexer import tokenize
from .semantico.etapa14_tipos_basicos import IO, OBJECT
from .semantico.etapa20_verificador import SemanticResult, analyze
from .sintatico.etapa6_ast import Attribute, Method, Program
from .sintatico.etapa7_ast_printer import configurar_saida_utf8
from .sintatico.etapa12_parser import ParseResult, parse

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"
LARGURA = 76
TOTAL_DE_FASES = 6
MAX_LINHAS_BRIL = 60           # do texto Bril mostrado na fase 5
MAX_LINHAS_SAIDA = 40          # da saída do programa mostrada na fase 6


# --------------------------------------------------------------------------
# 1. Cores e pequenos auxiliares de impressão
# --------------------------------------------------------------------------
# Sequências ANSI: "\033[32m" liga o verde, "\033[0m" volta ao normal.

ESTILOS = {"titulo": "1;36", "ok": "1;32", "erro": "1;31", "aviso": "33",
           "fraco": "90", "forte": "1"}
_usar_cor = True


def cor(texto: str, estilo: str) -> str:
    return f"\033[{ESTILOS[estilo]}m{texto}\033[0m" if _usar_cor else texto


def preparar_terminal(sem_cor: bool) -> None:
    global _usar_cor
    configurar_saida_utf8()
    _usar_cor = not sem_cor and sys.stdout.isatty() and "NO_COLOR" not in os.environ
    if _usar_cor and os.name == "nt":
        os.system("")          # liga as sequências ANSI no console do Windows


def paragrafo(texto: str) -> None:
    for linha in textwrap.wrap(texto, LARGURA - 2):
        print("  " + linha)
    print()


def milhar(numero: int) -> str:
    return f"{numero:,}".replace(",", ".")


def titulo_da_fase(numero: int, nome: str, explicacao: str) -> None:
    print()
    print(cor("━" * LARGURA, "titulo"))
    print(cor(f" FASE {numero}/{TOTAL_DE_FASES}  ·  {nome}", "titulo"))
    print(cor("━" * LARGURA, "titulo"))
    paragrafo(explicacao)


class Pausa:
    """Espera o Enter entre uma fase e outra; 'd' desliga as pausas seguintes."""

    def __init__(self, ativa: bool):
        self.ativa = ativa

    def __call__(self) -> None:
        if not self.ativa:
            return
        try:
            resposta = input(cor("\n  [Enter] próxima fase   [d + Enter] direto até o fim ",
                                 "fraco"))
        except EOFError:
            resposta = "d"
        if resposta.strip().lower() == "d":
            self.ativa = False


# --------------------------------------------------------------------------
# 2. O menu
# --------------------------------------------------------------------------

def descricao(caminho: Path) -> str:
    """A primeira frase do comentário que abre o arquivo, se houver."""
    em_bloco = False
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        texto = linha.strip()
        if not texto:
            continue
        if texto.startswith("(*"):
            em_bloco, texto = True, texto[2:]
        elif texto.startswith("--"):
            texto = texto[2:]
        elif not em_bloco:
            return ""                          # o arquivo começa direto no código
        if "*)" in texto:
            em_bloco, texto = False, texto.split("*)")[0]
        texto = texto.strip(" *")
        if texto:
            return texto if len(texto) <= 55 else texto[:54] + "…"
    return ""


def escolher_arquivo() -> Optional[Path]:
    """Mostra os exemplos agrupados por pasta; devolve None para sair."""
    arquivos = sorted(EXAMPLES_DIR.rglob("*.cl"),
                      key=lambda p: (p.parent != EXAMPLES_DIR, p.as_posix()))
    print()
    print(cor("━" * LARGURA, "titulo"))
    print(cor("  Compilador COOL → Bril  ·  demonstração guiada", "titulo"))
    print(cor("━" * LARGURA, "titulo"))

    pasta_atual = None
    for indice, caminho in enumerate(arquivos, start=1):
        if caminho.parent != pasta_atual:
            pasta_atual = caminho.parent
            print("\n  " + cor(pasta_atual.relative_to(EXAMPLES_DIR.parent).as_posix() + "/",
                               "forte"))
        print(f"  {indice:>3}. {caminho.name:<32}{cor(descricao(caminho), 'fraco')}")

    while True:
        try:
            escolha = input("\n  Número do exemplo, caminho de um .cl ou [s] para sair: ").strip()
        except EOFError:
            return None
        if escolha.lower() in ("s", "sair"):
            return None
        if not escolha:                        # Enter sem querer: pergunta de novo
            continue
        if escolha.isdigit() and 1 <= int(escolha) <= len(arquivos):
            return arquivos[int(escolha) - 1]
        caminho = Path(escolha.strip('"'))
        if caminho.is_file():
            return caminho
        print(cor("  Não encontrei esse exemplo nem esse arquivo. Tente de novo.", "erro"))


# --------------------------------------------------------------------------
# 3. As seis fases
# --------------------------------------------------------------------------

def fase_fonte(codigo: str) -> None:
    titulo_da_fase(1, "Código-fonte", "O ponto de partida é um arquivo de texto "
                   "comum. Para o compilador, por enquanto, ele é só uma longa "
                   "sequência de caracteres.")
    for numero, linha in enumerate(codigo.splitlines(), start=1):
        print(cor(f"  {numero:>4} │ ", "fraco") + linha)


def fase_lexica(codigo: str) -> None:
    titulo_da_fase(2, "Análise léxica", "O lexer agrupa os caracteres em tokens, "
                   "as 'palavras' da linguagem: palavras-chave, identificadores, "
                   "números, strings e símbolos. Espaços e comentários são "
                   "descartados aqui.")
    tokens = [t for t in tokenize(codigo) if t.type is not TokenType.EOF]
    erros = [t for t in tokens if t.type is TokenType.ERROR]
    print(f"  {cor(milhar(len(tokens)), 'forte')} tokens reconhecidos. Os primeiros:\n")
    print(cor(f"  {'linha':>5}   {'tipo':<12} lexema", "fraco"))
    for token in tokens[:14]:
        print(f"  {token.line:>5}   {token.type.name:<12} {token.lexeme!r}")
    if len(tokens) > 14:
        print(cor(f"  {'…':>5}   (todos: python -m cool_compiler.main --fase lexico ARQUIVO)",
                  "fraco"))
    for token in erros:
        print(cor(f"  linha {token.line}: {token.value} -> {token.lexeme!r}", "erro"))


def fase_sintatica(codigo: str, nome: str) -> Optional[ParseResult]:
    titulo_da_fase(3, "Análise sintática", "O parser confere se os tokens formam "
                   "frases válidas da gramática de COOL e monta a árvore sintática "
                   "(AST). Abaixo, o esqueleto dela: classes, atributos e métodos.")
    resultado = parse(codigo, nome)
    if resultado.program is not None:
        for classe in resultado.program.classes:
            heranca = f" inherits {classe.parent}" if classe.parent else ""
            print(f"  {cor('class', 'forte')} {classe.name}{heranca}")
            for feature in classe.features:
                if isinstance(feature, Method):
                    formais = ", ".join(f"{f.name} : {f.type_name}" for f in feature.formals)
                    print(f"      {feature.name}({formais}) : {feature.return_type}")
                elif isinstance(feature, Attribute):
                    print(cor(f"      {feature.name} : {feature.type_name}   (atributo)",
                              "fraco"))
    print(cor("\n  (a árvore completa: python -m cool_compiler.main --fase sintatico ARQUIVO)",
              "fraco"))

    if not resultado.has_errors:
        print(cor("\n  ✓ Nenhum erro léxico nem sintático.", "ok"))
        return resultado
    for token in resultado.lexical_errors:
        print(cor(f"  erro léxico, linha {token.line}: {token.value}", "erro"))
    for erro in resultado.syntax_errors:
        print(cor(f"  {erro}", "erro"))
    print()
    paragrafo("O programa tem erros, então o compilador para aqui: as fases "
              "seguintes precisam de uma árvore completa.")
    return None


def imprimir_hierarquia(programa: Program) -> None:
    """A árvore de herança, com Object na raiz (a base das tags da etapa 22)."""
    usuario = {classe.name for classe in programa.classes}
    filhos: dict[str, list[str]] = {}
    for classe in programa.classes:
        filhos.setdefault(classe.parent or OBJECT, []).append(classe.name)
    if IO in filhos:
        filhos.setdefault(OBJECT, []).insert(0, IO)

    def desenhar(nome: str, prefixo: str, ultimo: bool, raiz: bool) -> None:
        rotulo = nome if nome in usuario else cor(f"{nome} (básica)", "fraco")
        conector = "" if raiz else ("└── " if ultimo else "├── ")
        print(f"      {prefixo}{conector}{rotulo}")
        abaixo = filhos.get(nome, [])
        prefixo_filhos = "" if raiz else prefixo + ("    " if ultimo else "│   ")
        for posicao, filho in enumerate(abaixo):
            desenhar(filho, prefixo_filhos, posicao == len(abaixo) - 1, False)

    desenhar(OBJECT, "", True, True)


def fase_semantica(resultado: ParseResult, nome: str) -> Optional[SemanticResult]:
    titulo_da_fase(4, "Análise semântica", "Aqui o compilador confere o SENTIDO do "
                   "programa: se cada classe existe, se a herança não tem ciclos, se "
                   "cada nome foi declarado e se os tipos batem. Cada expressão da "
                   "árvore ganha um tipo.")
    semantico = analyze(resultado.program, nome)
    if not semantico.has_errors:
        print("  Hierarquia de classes:\n")
        imprimir_hierarquia(resultado.program)
        print(cor(f"\n  ✓ Nenhum erro semântico; {milhar(len(semantico.types))} "
                  "expressões receberam um tipo.", "ok"))
        print(cor("  (a árvore com os tipos: python -m cool_compiler.main ARQUIVO)", "fraco"))
        return semantico
    for erro in semantico.errors:
        print(cor(f"  {erro}", "erro"))
    print()
    paragrafo(f"{len(semantico.errors)} erro(s) semântico(s). Gerar código para um "
              "programa sem sentido não faz sentido: o compilador para aqui.")
    return None


def categoria(funcao: str, classes_do_usuario: set[str]) -> str:
    if funcao == "main":
        return "ponto de entrada (@main)"
    if funcao.startswith("despachar_"):
        return "despachantes (escolhem o método pela classe real)"
    if funcao.endswith(("_novo", "_init")):
        return "criação de objetos (_novo e _init)"
    if "." in funcao and funcao.split(".")[0] in classes_do_usuario:
        return "métodos escritos no seu programa"
    return "runtime (rt_..., Object, IO e String)"


def salvar_bril(programa: dict, nome: str, pasta: Path) -> None:
    """Grava o programa em nome.json e nome.bril dentro de `pasta`."""
    pasta.mkdir(parents=True, exist_ok=True)
    base = Path(nome).stem
    json_path, texto_path = pasta / f"{base}.json", pasta / f"{base}.bril"
    json_path.write_text(formatar_json(programa) + "\n", encoding="utf-8")
    texto_path.write_text(formatar_texto(programa) + "\n", encoding="utf-8")
    print(cor("\n  ✓ Programa Bril salvo:", "ok"))
    print(f"      {json_path}   (JSON, o que o brili lê)")
    print(f"      {texto_path}   (texto, para ler no editor)")
    print(cor(f"    Para rodar à mão: Get-Content {json_path} | brili", "fraco"))


def fase_geracao(resultado: ParseResult, semantico: SemanticResult, nome: str,
                 pasta_saida: Optional[Path]) -> dict:
    titulo_da_fase(5, "Geração de código", "A árvore com os tipos é traduzida para "
                   "Bril, uma linguagem intermediária de instruções simples (const, "
                   "add, call, load, store, print...). O resultado é um programa Bril "
                   "completo, em JSON. Repare: até aqui, NADA do programa foi executado.")
    avisos: list[str] = []
    programa = generate(resultado.program, semantico, avisos=avisos)
    funcoes = programa["functions"]
    usuario = {classe.name for classe in resultado.program.classes}

    grupos: dict[str, list[str]] = {}
    for funcao in funcoes:
        grupos.setdefault(categoria(funcao["name"], usuario), []).append(funcao["name"])
    instrucoes = sum(1 for f in funcoes for i in f["instrs"] if "op" in i)
    print(f"  {cor(str(len(funcoes)), 'forte')} funções Bril, "
          f"{cor(milhar(instrucoes), 'forte')} instruções:\n")
    for grupo, nomes in grupos.items():
        print(f"    {len(nomes):>3}  {grupo}")

    do_usuario = [f for f in funcoes if f["name"] == "main"
                  or categoria(f["name"], usuario).startswith("métodos")]
    texto = formatar_texto({"functions": do_usuario}).splitlines()
    print(f"\n  O código Bril do seu programa (@main e os métodos):\n")
    for linha in texto[:MAX_LINHAS_BRIL]:
        print(cor("    │ ", "fraco") + linha)
    if len(texto) > MAX_LINHAS_BRIL:
        print(cor(f"    │ … mais {len(texto) - MAX_LINHAS_BRIL} linhas", "fraco"))
    print(cor("\n  (tudo: python -m cool_compiler.main --fase bril-texto ARQUIVO;"
              " o JSON: --fase bril -o x.json)", "fraco"))
    for aviso in avisos:
        print(cor(f"  aviso: {aviso}", "aviso"))
    if pasta_saida is not None:
        salvar_bril(programa, nome, pasta_saida)
    return programa


def fase_execucao(programa: dict) -> None:
    titulo_da_fase(6, "Execução no brili", "O JSON é entregue ao brili, o "
                   "interpretador da Bril: um programa à parte, rodado pelo Deno. "
                   "O compilador já terminou; quem trabalha agora é o brili.")
    no_terminal = sys.stdout.isatty()
    if no_terminal:                            # some assim que a execução termina
        print(cor("  executando…", "fraco"), end="\r", flush=True)
    inicio = time.perf_counter()
    try:
        execucao = executar(programa, opcoes=("-p",))
    except BriliNaoEncontrado as erro:
        print(cor(f"  {erro}", "erro"))
        return
    segundos = time.perf_counter() - inicio
    if no_terminal:
        print(" " * 20, end="\r")

    codigos = execucao.bruto.split()
    print("  O brili só imprime números: um código de caractere por linha.")
    print("  Os primeiros: " + cor(" ".join(codigos[:14]) + (" …" if len(codigos) > 14 else ""),
                                   "fraco"))
    exemplos = [c for c in codigos[:6] if c.isdigit()]
    if exemplos:
        print("  Traduzindo:   " + cor("   ".join(f"{c}→{chr(int(c))!r}" for c in exemplos),
                                       "fraco"))
    if "-1" in codigos:
        print("  O -1 é o sentinela: dali em diante vem a mensagem de um erro de execução.")

    linhas = execucao.saida.splitlines() or [""]
    print("\n  " + cor("┌─ saída do programa " + "─" * (LARGURA - 23), "ok"))
    for linha in linhas[:MAX_LINHAS_SAIDA]:
        print("  " + cor("│ ", "ok") + linha)
    if len(linhas) > MAX_LINHAS_SAIDA:
        print("  " + cor("│ ", "ok") + cor(f"… mais {milhar(len(linhas) - MAX_LINHAS_SAIDA)}"
                                         " linhas", "fraco"))
    print("  " + cor("└" + "─" * (LARGURA - 3), "ok"))

    rodape = execucao.rodape()
    if rodape is not None:
        print(cor(f"  {rodape.splitlines()[0]}", "erro"))
    contagem = re.search(r"total_dyn_inst: (\d+)", execucao.stderr)
    resumo = f"código de saída {execucao.codigo}"
    if contagem:
        resumo += f"  ·  {milhar(int(contagem.group(1)))} instruções Bril executadas"
    print(cor(f"  {resumo}  ·  {segundos:.1f} s", "fraco"))


# --------------------------------------------------------------------------
# 4. A demonstração completa e o laço do menu
# --------------------------------------------------------------------------

def demonstrar(caminho: Path, pausa: Pausa, pasta_saida: Optional[Path]) -> None:
    codigo = caminho.read_text(encoding="utf-8")
    print(cor(f"\n  Arquivo: {caminho}", "forte"))

    fase_fonte(codigo)
    pausa()
    fase_lexica(codigo)
    pausa()
    resultado = fase_sintatica(codigo, caminho.name)
    if resultado is None:
        return
    pausa()
    semantico = fase_semantica(resultado, caminho.name)
    if semantico is None:
        return
    pausa()
    programa = fase_geracao(resultado, semantico, caminho.name, pasta_saida)
    pausa()
    fase_execucao(programa)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m cool_compiler.demo",
                                     description="Demonstração guiada do compilador COOL.")
    parser.add_argument("arquivo", nargs="?", help="um .cl; sem ele, abre o menu")
    parser.add_argument("--direto", action="store_true", help="sem pausas entre as fases")
    parser.add_argument("--sem-cor", action="store_true", help="sem cores no terminal")
    parser.add_argument("--salvar", action="store_true",
                        help="grava nome.json e nome.bril de cada exemplo compilado")
    parser.add_argument("--pasta", default="bril_gerado",
                        help="com --salvar: onde gravar (padrão: bril_gerado/)")
    configurar_saida_utf8()                    # antes do --help, que tem acentos
    argumentos = parser.parse_args()
    preparar_terminal(argumentos.sem_cor)
    pasta_saida = Path(argumentos.pasta) if argumentos.salvar else None

    if argumentos.arquivo is not None:
        caminho = Path(argumentos.arquivo)
        if not caminho.is_file():
            caminho = EXAMPLES_DIR / argumentos.arquivo
        if not caminho.is_file():
            sys.exit(f"Arquivo não encontrado: {argumentos.arquivo}")
        demonstrar(caminho, Pausa(not argumentos.direto), pasta_saida)
        return

    while (caminho := escolher_arquivo()) is not None:
        demonstrar(caminho, Pausa(not argumentos.direto), pasta_saida)
        try:
            input(cor("\n  [Enter] voltar ao menu ", "fraco"))
        except EOFError:
            break


if __name__ == "__main__":
    main()
