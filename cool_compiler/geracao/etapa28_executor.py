"""Etapa 28: roda o programa gerado no brili e traduz a saída de volta para texto.

O print da Bril sempre termina a linha, então o programa gerado imprime cada
caractere como o seu CÓDIGO, um por linha (etapa 23). Esta etapa desfaz isso:

    saída bruta do brili     72  105  10  -1  100 ...
    texto decodificado       "Hi\n"        |  mensagem de erro: "d..."
                                           sentinela: daqui em diante é erro

O brili lê o programa pelo stdin, então o JSON é passado por ali.
"""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .etapa23_runtime import SENTINELA_ERRO

# Código de saída do brili quando a execução para por erro (inclusive o
# nosso fim forçado com divisão por zero)
CODIGO_ERRO_BRILI = 2


class BriliNaoEncontrado(Exception):
    """O brili não está instalado ou não está no PATH."""


# --------------------------------------------------------------------------
# 1. Onde está o brili
# --------------------------------------------------------------------------

# Um terminal aberto ANTES da instalação (no VS Code: qualquer terminal, até
# o VS Code inteiro ser reaberto) não enxerga o PATH novo. Por isso, além do
# PATH, os executáveis também são procurados onde os instaladores os põem.
_LOCAL = Path(os.environ.get("LOCALAPPDATA", Path.home()))
PASTAS_DENO = [Path.home() / ".deno" / "bin", _LOCAL / "Microsoft" / "WinGet" / "Links",
               *sorted((_LOCAL / "Microsoft" / "WinGet" / "Packages").glob("DenoLand.Deno*"))]
PASTAS_BRIL_TXT = [Path.home() / ".local" / "bin"]


def procurar_executavel(nome: str, pastas: list[Path]) -> Optional[str]:
    """O caminho de `nome`: primeiro no PATH, depois nas `pastas` dadas."""
    achado = shutil.which(nome)
    if achado:
        return achado
    for pasta in pastas:
        achado = shutil.which(nome, path=str(pasta))   # já testa .exe e .cmd
        if achado:
            return achado
    return None


def localizar_brili() -> str:
    """Procura o brili: variável BRILI, depois o PATH, depois ~/.deno/bin.

    No Windows o `deno install` cria DOIS arquivos: brili (script de shell,
    que o Windows não executa) e brili.cmd. Por isso o .cmd é procurado
    primeiro.
    """
    if os.environ.get("BRILI"):
        return os.environ["BRILI"]
    for nome in (("brili.cmd", "brili") if os.name == "nt" else ("brili",)):
        achado = procurar_executavel(nome, PASTAS_DENO)
        if achado:
            return achado
    raise BriliNaoEncontrado(
        "brili nao encontrado. Instale com `deno install -g brili.ts` na raiz do "
        "repositorio da Bril e coloque ~/.deno/bin no PATH (ou defina BRILI)."
    )


def ambiente_com_deno() -> dict[str, str]:
    """O ambiente do processo do brili, com a pasta do deno no PATH.

    O brili instalado pelo deno é só um script que chama `deno` PELO NOME;
    sem o deno no PATH ele falha com uma mensagem do sistema que nada diz
    sobre a causa. Achando o deno, a pasta dele entra no PATH do brili.
    """
    deno = procurar_executavel("deno", PASTAS_DENO)
    if deno is None:
        raise BriliNaoEncontrado(
            "o brili foi encontrado, mas o deno nao. Instale o Deno ou, se acabou "
            "de instalar, abra um terminal novo (no VS Code, reabra o VS Code inteiro)."
        )
    ambiente = dict(os.environ)
    ambiente["PATH"] = str(Path(deno).parent) + os.pathsep + ambiente.get("PATH", "")
    return ambiente


# --------------------------------------------------------------------------
# 2. O resultado de uma execução
# --------------------------------------------------------------------------

@dataclass
class ResultadoExecucao:
    codigo: int                 # código de saída do brili (0 ou 2)
    saida: str                  # texto que o programa COOL imprimiu
    erro: Optional[str]         # mensagem de erro de execução do programa, se houve
    bruto: str                  # stdout do brili, sem decodificar
    stderr: str                 # o que o brili escreveu no stderr

    @property
    def erro_interno(self) -> bool:
        """Falhou sem o sentinela: o erro é do brili, não do programa COOL."""
        return self.codigo != 0 and self.erro is None

    def rodape(self) -> Optional[str]:
        """A linha que explica como a execução terminou, se não terminou bem."""
        if self.erro is not None:
            return f"Erro de execucao: {self.erro}"
        if self.codigo != 0:
            return f"Erro do brili (codigo {self.codigo}): {self.stderr.strip()}"
        return None

    def transcricao(self) -> str:
        """Saída e rodapé juntos: o que os arquivos .esperado guardam."""
        texto = self.saida
        rodape = self.rodape()
        if rodape is not None:
            if texto and not texto.endswith("\n"):
                texto += "\n"
            texto += rodape + "\n"
        return texto


# --------------------------------------------------------------------------
# 3. Decodificação e execução
# --------------------------------------------------------------------------

def decodificar(bruto: str) -> tuple[str, Optional[str]]:
    """Linhas com códigos -> (texto normal, mensagem de erro ou None)."""
    saida: list[str] = []
    erro: Optional[list[str]] = None
    destino = saida
    for linha in bruto.splitlines():
        try:
            codigo = int(linha)
        except ValueError:                  # não veio do nosso protocolo: mantém
            destino.append(linha + "\n")
            continue
        if codigo == SENTINELA_ERRO:
            erro = destino = []
        else:
            destino.append(chr(codigo))
    return "".join(saida), ("".join(erro) if erro is not None else None)


def executar(programa: dict, timeout: Optional[float] = None,
             opcoes: tuple[str, ...] = ()) -> ResultadoExecucao:
    """Roda o programa Bril (o dict do generate) e devolve a saída decodificada.

    `opcoes` vão para a linha de comando do brili; "-p", por exemplo, faz ele
    escrever no stderr quantas instruções executou (total_dyn_inst: N).
    """
    # errors="replace": o stdout do brili é só ASCII (números), mas o stderr
    # pode trazer mensagens do Windows em outra codificação (cp850, por
    # exemplo); um caractere estranho é melhor que uma exceção
    processo = subprocess.run(
        [localizar_brili(), *opcoes],
        input=json.dumps(programa), env=ambiente_com_deno(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    saida, erro = decodificar(processo.stdout)
    return ResultadoExecucao(processo.returncode, saida, erro,
                             processo.stdout, processo.stderr)
