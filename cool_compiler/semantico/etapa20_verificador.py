"""Etapa 20: verifica classes, atributos e métodos, e expõe analyze(), a API da fase."""

from dataclasses import dataclass

from ..sintatico.etapa6_ast import Attribute, Method, Program
from .etapa13_erros_semanticos import ErrorReporter, SemanticError
from .etapa14_tipos_basicos import SELF
from .etapa15_tabela_de_classes import ClassInfo
from .etapa17_features import FeatureTable
from .etapa19_verificador_expr import ExpressionChecker


class TypeChecker(ExpressionChecker):
    """Declarações (classes, atributos, métodos) sobre o verificador de expressões."""

    # ----------------------------------------------------------------------
    # 1. Programa
    # ----------------------------------------------------------------------

    def check_program(self, programa: Program) -> None:
        for classe in programa.classes:
            info = self.ambiente.classes.get(classe.name)
            # Pula classe recusada na etapa 15 (ou a 2ª declaração de um nome repetido)
            if info is None or info.node is not classe:
                continue
            self.check_class(info)

    # ----------------------------------------------------------------------
    # 2. Classe
    # ----------------------------------------------------------------------

    def check_class(self, info: ClassInfo) -> None:
        self.classe_atual = info.name              # todo SELF_TYPE agora é desta classe

        with self.escopos.scope():                 # escopo da classe
            for nome, tipo in self.ambiente.all_attributes(info.name).items():
                self.escopos.define(nome, tipo)    # atributos próprios e herdados

            for feature in info.node.features:
                match feature:
                    case Attribute():
                        self.check_attribute(feature)
                    case Method():
                        self.check_method(feature)

    # ----------------------------------------------------------------------
    # 3. Features (type_or_error não reporta: a etapa 17 já reportou)
    # ----------------------------------------------------------------------

    def check_attribute(self, atributo: Attribute) -> None:
        if atributo.init is None or atributo.name == SELF:
            return                                 # nada a verificar

        tipo_declarado = self.ambiente.type_or_error(atributo.type_name,
                                                     allow_self_type=True)
        self._exigir_compativel(                   # a inicialização serve no tipo declarado?
            self.check(atributo.init), tipo_declarado, atributo.line,
            f"a inicializacao do atributo '{atributo.name}'",
            f"o tipo declarado {tipo_declarado}",
        )

    def check_method(self, metodo: Method) -> None:
        retorno = self.ambiente.type_or_error(metodo.return_type,
                                              allow_self_type=True)

        with self.escopos.scope():                 # escopo do método, acima do da classe
            for formal in metodo.formals:
                if formal.name != SELF:
                    tipo = self.ambiente.type_or_error(formal.type_name,
                                                       allow_self_type=False)
                    self.escopos.define(formal.name, tipo)   # esconde atributo de mesmo nome

            tipo_corpo = self.check(metodo.body)   # pilha: {parâmetros} sobre {atributos}

        self._exigir_compativel(                   # o corpo serve no tipo de retorno?
            tipo_corpo, retorno, metodo.line,
            f"o corpo do metodo '{metodo.name}'",
            f"o tipo de retorno declarado {retorno}",
        )


# --------------------------------------------------------------------------
# 4. API pública da fase
# --------------------------------------------------------------------------

@dataclass
class SemanticResult:
    """Saída da fase: os tipos anotados e os erros."""

    types: dict[int, str]          # id do nó -> tipo (o printer escreve [tipo: ...])
    errors: list[SemanticError]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def analyze(programa: Program, filename: str = "<entrada>") -> SemanticResult:
    """Ponto de entrada da fase, chamado pelo main.py."""
    relator = ErrorReporter(filename)              # caderno de erros compartilhado

    ambiente = FeatureTable(programa, relator)     # passadas 1 e 2: classes e features
    verificador = TypeChecker(ambiente, relator)
    verificador.check_program(programa)            # passada 3: expressões

    # Ordena por linha; o erro sem linha (falta Main) vai para o topo
    erros = sorted(relator.errors, key=lambda erro: erro.line or 0)
    return SemanticResult(verificador.types, erros)
