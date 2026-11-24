"""Testes da geração de código: compila, roda no brili e confere a saída.

Uso, a partir da raiz do repositório:

    python -m cool_compiler.testar_geracao

Para cada .cl de examples/ (subpastas incluídas):

    1. EXECUÇÃO   com .esperado: o que o programa mostra tem que ser igual ao
                  arquivo. Sem .esperado: basta rodar até o fim sem erro.
    2. TEXTO      se o bril2json estiver instalado, o texto gerado pela fase
                  bril-texto, convertido de volta, tem que dar o mesmo JSON.

Exemplos que não passam da análise semântica (os de erros de propósito)
aparecem como PULADO: não há o que gerar para eles.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):                  # mesmo truque do main.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "cool_compiler"

from .geracao.etapa21_bril import formatar_texto
from .geracao.etapa27_gerador import generate
from .geracao.etapa28_executor import (
    PASTAS_BRIL_TXT, BriliNaoEncontrado, executar, procurar_executavel,
)
from .semantico.etapa20_verificador import analyze
from .sintatico.etapa7_ast_printer import configurar_saida_utf8
from .sintatico.etapa12_parser import parse

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"
TEMPO_MAXIMO = 120                             # segundos por programa


def compilar(caminho: Path) -> Optional[dict]:
    """O programa Bril, ou None se o .cl tiver qualquer erro."""
    resultado = parse(caminho.read_text(encoding="utf-8"), caminho.name)
    if resultado.has_errors:
        return None
    semantico = analyze(resultado.program, caminho.name)
    if semantico.has_errors:
        return None
    return generate(resultado.program, semantico)


def testar_execucao(caminho: Path, programa: dict) -> Optional[str]:
    """None se passou; senão, a explicação da falha."""
    execucao = executar(programa, timeout=TEMPO_MAXIMO)
    esperado_path = caminho.with_suffix(".esperado")

    if not esperado_path.exists():
        if execucao.codigo != 0:
            return f"deveria rodar sem erro, mas: {execucao.rodape()}"
        return None

    esperado = esperado_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    obtido = execucao.transcricao()
    if obtido != esperado:
        return f"saida diferente\n--- esperado ---\n{esperado}--- obtido ---\n{obtido}"
    return None


def _normalizar(programa: dict) -> dict:
    """Listas vazias de args/funcs/labels são o mesmo que não ter a chave."""
    for funcao in programa["functions"]:
        funcao.setdefault("args", [])
        for instr in funcao["instrs"]:
            for chave in ("args", "funcs", "labels"):
                if chave in instr and not instr[chave]:
                    del instr[chave]
    return programa


def testar_texto(programa: dict, bril2json: str) -> Optional[str]:
    """Texto -> bril2json -> JSON: tem que voltar ao programa original."""
    processo = subprocess.run([bril2json], input=formatar_texto(programa),
                              capture_output=True, text=True, encoding="utf-8")
    if processo.returncode != 0:
        return f"bril2json recusou o texto: {processo.stderr.strip()[-300:]}"
    original = _normalizar(json.loads(json.dumps(programa)))
    if _normalizar(json.loads(processo.stdout)) != original:
        return "o texto nao reconverte para o mesmo JSON"
    return None


def main() -> int:
    configurar_saida_utf8()
    bril2json = procurar_executavel("bril2json", PASTAS_BRIL_TXT)
    if bril2json is None:
        print("(bril2json nao encontrado: o teste do formato texto sera pulado)\n")

    falhas = 0
    aprovados = 0
    for caminho in sorted(EXAMPLES_DIR.rglob("*.cl")):
        nome = caminho.relative_to(EXAMPLES_DIR).as_posix()
        programa = compilar(caminho)
        if programa is None:
            print(f"PULADO  {nome}  (tem erros de compilacao de proposito)")
            continue

        try:
            problema = testar_execucao(caminho, programa)
        except BriliNaoEncontrado as erro:
            print(erro)
            return 1
        if problema is None and bril2json is not None:
            problema = testar_texto(programa, bril2json)

        if problema is None:
            aprovados += 1
            print(f"OK      {nome}")
        else:
            falhas += 1
            print(f"FALHA   {nome}: {problema}")

    print(f"\n{aprovados} ok, {falhas} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
