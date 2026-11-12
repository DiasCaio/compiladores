"""Etapa 18: pilha de escopos, quais nomes estão visíveis em cada ponto.

    class C { x : Int;  f(x : String) : Object { let x : Bool in x }; };

    pilha no último x:   {x: Bool}     <- topo: lookup acha aqui
                         {x: String}
                         {x: Int}
"""

from contextlib import contextmanager
from typing import Iterator, Optional


class SymbolTable:
    """Lista de dicionários nome -> tipo; o último é o topo (escopo mais interno)."""

    def __init__(self):
        self.escopos: list[dict[str, str]] = []

    @contextmanager
    def scope(self) -> Iterator[None]:
        """`with escopos.scope():` abre um escopo e o fecha ao sair do bloco."""
        self.escopos.append({})         # entra: empilha
        try:
            yield                       # roda o corpo do `with`
        finally:
            self.escopos.pop()          # sai: desempilha (mesmo saindo por return)

    def define(self, nome: str, tipo: str) -> None:
        """Declara `nome` no topo."""
        self.escopos[-1][nome] = tipo

    def lookup(self, nome: str) -> Optional[str]:
        """Tipo da declaração mais interna de `nome`, ou None."""
        for escopo in reversed(self.escopos):   # do topo para o fundo
            if nome in escopo:
                return escopo[nome]             # 1º achado = o mais interno
        return None
