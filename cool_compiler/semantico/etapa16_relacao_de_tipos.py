"""Etapa 16: as duas perguntas sobre tipos, base de todo o verificador.

    conforms(A, B)   um A serve onde se espera um B?     Cachorro serve como Animal
    join(A, B)       menor tipo que descreve os dois?    join(Cachorro, Gato) = Animal
"""

from .etapa14_tipos_basicos import OBJECT, SELF_TYPE, TIPO_ERRO
from .etapa15_tabela_de_classes import ClassTable


class TypeSystem(ClassTable):
    """Acrescenta à tabela de classes as perguntas sobre tipos."""

    # ----------------------------------------------------------------------
    # 1. Conformidade
    # ----------------------------------------------------------------------

    def conforms(self, tipo: str, esperado: str, classe_atual: str) -> bool:
        """Um valor de `tipo` pode ser usado onde se espera `esperado`?"""
        if tipo == TIPO_ERRO or esperado == TIPO_ERRO:
            return True                            # coringa: nunca gera um 2º erro

        if esperado == SELF_TYPE:
            return tipo == SELF_TYPE               # só SELF_TYPE serve como SELF_TYPE

        if tipo == SELF_TYPE:
            tipo = classe_atual                    # SELF_TYPE de C é, no mínimo, um C

        return esperado in self.ancestors(tipo)    # `esperado` é ancestral de `tipo`?

    # ----------------------------------------------------------------------
    # 2. Join
    # ----------------------------------------------------------------------

    def join(self, a: str, b: str, classe_atual: str) -> str:
        """O ancestral comum mais próximo de `a` e `b`."""
        if a == TIPO_ERRO:
            return b                               # o lado com erro não informa nada
        if b == TIPO_ERRO:
            return a

        if a == SELF_TYPE and b == SELF_TYPE:
            return SELF_TYPE

        if a == SELF_TYPE:                         # só um é SELF_TYPE: vira a classe atual
            a = classe_atual
        if b == SELF_TYPE:
            b = classe_atual

        ancestrais_de_a = self.ancestors(a)        # [Cachorro, Animal, Object]
        for candidato in self.ancestors(b):        # [Gato, Animal, Object]
            if candidato in ancestrais_de_a:       # 1º em comum: Animal
                return candidato

        return OBJECT                              # inalcançável: Object está nas duas listas

    # ----------------------------------------------------------------------
    # 3. Tipos escritos pelo programador (x : Foo, new Foo, f() : Foo)
    # ----------------------------------------------------------------------

    def type_or_error(self, nome: str, allow_self_type: bool) -> str:
        """O tipo, se válido; senão TIPO_ERRO. NÃO reporta (evita erro repetido)."""
        if nome == SELF_TYPE:
            return SELF_TYPE if allow_self_type else TIPO_ERRO   # só vale em alguns lugares
        if nome in self.classes:
            return nome
        return TIPO_ERRO                                          # classe inexistente

    def check_declared_type(self, nome: str, linha: int, allow_self_type: bool,
                            descricao: str) -> str:
        """Igual a type_or_error, mas REPORTA o erro."""
        tipo = self.type_or_error(nome, allow_self_type)
        if tipo == TIPO_ERRO:
            if nome == SELF_TYPE:
                self.relator.report(
                    linha, f"SELF_TYPE nao pode ser usado como tipo {descricao}")
            else:
                self.relator.report(
                    linha, f"o tipo {nome} {descricao} nao foi definido")
        return tipo
