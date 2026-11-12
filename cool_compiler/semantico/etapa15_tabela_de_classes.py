"""Etapa 15 (passada 1): tabela de classes e grafo de herança.

Recusa classe duplicada, pai inválido e herança circular.
Conserto: pai inválido ou ciclo -> a classe passa a herdar de Object.
"""

from dataclasses import dataclass, field
from typing import Optional

from ..sintatico.etapa6_ast import ClassDef, Program
from .etapa13_erros_semanticos import ErrorReporter
from .etapa14_tipos_basicos import (
    CLASSES_BASICAS, MAIN, NAO_HERDAVEIS, OBJECT, SELF_TYPE,
)


# --------------------------------------------------------------------------
# 1. O que se guarda sobre cada classe
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class MethodSignature:
    """Assinatura de um método, sem o corpo: basta para checar uma chamada."""

    name: str
    params: list[tuple[str, str]]   # [(nome, tipo), ...] na ordem
    return_type: str
    defined_in: str                 # classe onde o método foi escrito
    line: int                       # 0 nas classes básicas


@dataclass
class ClassInfo:
    """Tudo que se sabe de uma classe (mutável: é preenchida aos poucos)."""

    name: str
    parent: Optional[str]           # None só em Object
    node: Optional[ClassDef]        # nó da AST; None nas classes básicas
    line: int                       # 0 nas classes básicas
    attributes: dict[str, str] = field(default_factory=dict)            # nome -> tipo
    methods: dict[str, MethodSignature] = field(default_factory=dict)   # nome -> assinatura


# --------------------------------------------------------------------------
# 2. A tabela
# --------------------------------------------------------------------------

class ClassTable:
    """Registra as classes e valida o grafo de herança."""

    def __init__(self, programa: Program, relator: ErrorReporter):
        self.relator = relator
        self.classes: dict[str, ClassInfo] = {}    # nome -> ClassInfo

        self._registrar_classes_basicas()          # 1. Object, IO, Int, String, Bool
        for classe in programa.classes:            # 2. classes do arquivo
            self._registrar_classe(classe)
        self._validar_pais()                       # 3. só depois de TODAS registradas
        self._quebrar_ciclos()                     # 4. só depois de todo pai existir
        self._exigir_main()                        # 5. existe classe Main?

    # ---- Registro -------------------------------------------------------

    def _registrar_classes_basicas(self) -> None:
        """Converte a tabela da etapa 14 em ClassInfo."""
        for nome, (pai, metodos) in CLASSES_BASICAS.items():
            info = ClassInfo(nome, pai, node=None, line=0)
            for nome_metodo, parametros, retorno in metodos:
                info.methods[nome_metodo] = MethodSignature(
                    nome_metodo, parametros, retorno, defined_in=nome, line=0,
                )
            self.classes[nome] = info

    def _registrar_classe(self, classe: ClassDef) -> None:
        """Registra uma classe do usuário; se recusada, fica fora da tabela."""
        if classe.name == SELF_TYPE:
            self.relator.report(classe.line,
                                "SELF_TYPE nao pode ser usado como nome de classe")
            return
        if classe.name in CLASSES_BASICAS:
            self.relator.report(classe.line,
                                f"a classe basica {classe.name} nao pode ser redefinida")
            return
        if classe.name in self.classes:            # duplicada: fica a primeira
            anterior = self.classes[classe.name]
            self.relator.report(
                classe.line,
                f"a classe {classe.name} ja foi definida na linha {anterior.line}",
            )
            return

        pai = classe.parent if classe.parent is not None else OBJECT   # sem inherits -> Object
        self.classes[classe.name] = ClassInfo(classe.name, pai, classe, classe.line)

    # ---- Validação do grafo ---------------------------------------------

    def _validar_pais(self) -> None:
        """Cada classe herda de alguém que existe e pode ser herdado?"""
        for info in self.classes.values():
            if info.node is None:                  # básica: pai já está certo
                continue

            if info.parent in NAO_HERDAVEIS:       # ex.: inherits Int
                self.relator.report(
                    info.line,
                    f"a classe {info.name} nao pode herdar de {info.parent}",
                )
                info.parent = OBJECT               # conserto
            elif info.parent not in self.classes:  # pai não existe
                self.relator.report(
                    info.line,
                    f"a classe {info.name} herda de {info.parent}, que nao foi definida",
                )
                info.parent = OBJECT               # conserto

    def _quebrar_ciclos(self) -> None:
        """Sobe de pai em pai; se uma classe se repetir, achou um ciclo.

            C -> A -> B -> A      A repetiu: ciclo = [A, B]  (C só leva até ele)
        """
        for nome in self.classes:
            caminho: list[str] = []
            atual: Optional[str] = nome
            while atual is not None and atual not in caminho:   # sobe até Object ou repetir
                caminho.append(atual)
                atual = self.classes[atual].parent

            if atual is None:
                continue                           # chegou em Object: sem ciclo

            ciclo = caminho[caminho.index(atual):]          # do 1º repetido em diante
            desenho = " -> ".join(ciclo + [atual])          # "A -> B -> A"
            self.relator.report(self.classes[ciclo[0]].line,
                                f"heranca circular: {desenho}")

            for membro in ciclo:                            # conserto: desfaz o ciclo,
                self.classes[membro].parent = OBJECT        # que é reportado uma vez só

    def _exigir_main(self) -> None:
        if MAIN not in self.classes:
            self.relator.report(
                None,                              # sem linha: é algo que falta
                "o programa nao tem uma classe Main; e por ela que a execucao comeca",
            )

    # ---- Consultas (o grafo já é uma árvore: nenhum laço gira para sempre) ----

    def ancestors(self, nome: str) -> list[str]:
        """A classe e seus ancestrais: ancestors("Cachorro") -> [Cachorro, Animal, Object]"""
        caminho: list[str] = []
        atual: Optional[str] = nome
        while atual is not None:
            caminho.append(atual)
            atual = self.classes[atual].parent
        return caminho

    def inheritance_order(self) -> list[ClassInfo]:
        """Todas as classes, cada pai ANTES dos filhos (busca em largura)."""
        filhos: dict[str, list[str]] = {nome: [] for nome in self.classes}
        for info in self.classes.values():
            if info.parent is not None:
                filhos[info.parent].append(info.name)       # pai -> [filhos]

        ordem: list[ClassInfo] = []
        fila = [OBJECT]                                     # começa pela raiz
        while fila:
            atual = fila.pop(0)                             # tira o primeiro da fila
            ordem.append(self.classes[atual])
            fila.extend(filhos[atual])                      # filhos vão para o fim da fila
        return ordem
