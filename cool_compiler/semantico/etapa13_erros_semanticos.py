"""Etapa 13: o erro semântico e o caderno que acumula os erros da fase.

Não é exceção: o erro é só anotado, e a análise continua.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SemanticError:
    """Um erro: arquivo, linha e mensagem."""

    filename: str
    line: Optional[int]   # None só no erro "falta a classe Main"
    message: str

    def __str__(self) -> str:
        # Mesmo formato das outras fases -> arquivo:linha: erro semantico: detalhe
        if self.line is None:
            return f"{self.filename}: erro semantico: {self.message}"
        return f"{self.filename}:{self.line}: erro semantico: {self.message}"


class ErrorReporter:
    """Caderno de erros compartilhado por todas as etapas da fase."""

    def __init__(self, filename: str):
        self.filename = filename
        self.errors: list[SemanticError] = []

    def report(self, line: Optional[int], message: str) -> None:
        """Anota o erro e volta; quem chamou segue normalmente."""
        self.errors.append(SemanticError(self.filename, line, message))
