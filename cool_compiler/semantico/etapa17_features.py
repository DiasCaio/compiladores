"""Etapa 17 (passada 2): os atributos e as assinaturas de métodos de cada classe.

Só declarações; os corpos ficam para a passada 3.
"""

from typing import Optional

from ..sintatico.etapa6_ast import Attribute, Method, Program
from .etapa13_erros_semanticos import ErrorReporter
from .etapa14_tipos_basicos import MAIN, MAIN_METHOD, SELF, TIPO_ERRO
from .etapa15_tabela_de_classes import ClassInfo, MethodSignature
from .etapa16_relacao_de_tipos import TypeSystem


class FeatureTable(TypeSystem):
    """Tudo que se sabe do programa: classes, herança e o que cada classe declara."""

    def __init__(self, programa: Program, relator: ErrorReporter):
        super().__init__(programa, relator)        # passada 1 (etapas 15 e 16)

        for info in self.inheritance_order():      # passada 2: pais antes dos filhos. A ideia é ver se o filho está sobrescrevendo algo
            if info.node is not None:              # básicas já vêm prontas da etapa 14
                self._coletar_features(info)

        self._exigir_metodo_main()

    # ----------------------------------------------------------------------
    # 1. Coleta
    # ----------------------------------------------------------------------

    def _coletar_features(self, info: ClassInfo) -> None:
        for feature in info.node.features:
            match feature:
                case Attribute():                  # feature é um Attribute?
                    self._coletar_atributo(info, feature)
                case Method():                     # feature é um Method?
                    self._coletar_metodo(info, feature)

    def _coletar_atributo(self, info: ClassInfo, atributo: Attribute) -> None:
        tipo = self.check_declared_type(           # o do atributo tipo existe?
            atributo.type_name, atributo.line, allow_self_type=True,
            descricao=f"do atributo '{atributo.name}'",
        )

        if atributo.name == SELF:
            self.relator.report(atributo.line,
                                "'self' nao pode ser o nome de um atributo")
            return

        if atributo.name in info.attributes:       # atributo repetido na mesma classe
            self.relator.report(
                atributo.line,
                f"o atributo '{atributo.name}' foi definido mais de uma vez "
                f"na classe {info.name}",
            )
            return

        dono = self._classe_que_define_atributo(info.parent, atributo.name)
        if dono is not None:                       # já existe num ancestral: proibido em COOL
            self.relator.report(
                atributo.line,
                f"o atributo '{atributo.name}' ja existe na classe ancestral "
                f"{dono}; atributos herdados nao podem ser redefinidos",
            )
            return

        info.attributes[atributo.name] = tipo      # aceito

    def _coletar_metodo(self, info: ClassInfo, metodo: Method) -> None:
        # 1) Monta a assinatura, validando cada parâmetro
        parametros: list[tuple[str, str]] = []
        vistos: set[str] = set()
        for formal in metodo.formals: #percorre todos os parâmetros do método
            if formal.name == SELF: #Self não pode ser parâmetro
                self.relator.report(formal.line,
                                    "'self' nao pode ser o nome de um parametro")
            elif formal.name in vistos:            # parâmetro repetido
                self.relator.report(
                    formal.line,
                    f"o parametro '{formal.name}' aparece mais de uma vez "
                    f"no metodo '{metodo.name}'",
                )
            vistos.add(formal.name)

            tipo = self.check_declared_type(           # checagem do tipo do parâmetro
                formal.type_name, formal.line, allow_self_type=False,
                descricao=f"do parametro '{formal.name}'",
            )
            parametros.append((formal.name, tipo))

        retorno = self.check_declared_type(            # Checagem do tipo do retorno do método
            metodo.return_type, metodo.line, allow_self_type=True,
            descricao=f"de retorno do metodo '{metodo.name}'",
        )

        assinatura = MethodSignature(metodo.name, parametros, retorno, #monta a assinatura do método
                                     defined_in=info.name, line=metodo.line)

        # 2) Decide se o método entra na tabela
        if metodo.name in info.methods:            # método repetido na mesma classe: recusa
            anterior = info.methods[metodo.name]
            self.relator.report(
                metodo.line,
                f"o metodo '{metodo.name}' ja foi definido na classe {info.name} "
                f"(linha {anterior.line})",
            )
            return

        herdado = self.lookup_method(info.parent, metodo.name) #existe um método com o mesmo nome em uma classe ancestral? Se sim, confere se a assinatura é compatível
        if herdado is not None:                    # é sobrescrita: confere a assinatura
            self._checar_sobrescrita(assinatura, herdado)

        info.methods[metodo.name] = assinatura     # entra mesmo com sobrescrita errada

    def _checar_sobrescrita(self, nova: MethodSignature,
                            herdada: MethodSignature) -> None:
        """A sobrescrita precisa ter EXATAMENTE a assinatura do pai."""
        inicio = (f"o metodo '{nova.name}' sobrescreve o de {herdada.defined_in}, "
                  f"mas")

        if len(nova.params) != len(herdada.params):     # 1) quantidade de parâmetros
            self.relator.report(
                nova.line,
                f"{inicio} recebe {len(nova.params)} parametro(s) "
                f"em vez de {len(herdada.params)}",
            )
        else:                                           # 2) tipo de cada parâmetro, em pares
            for (nome, tipo_novo), (_, tipo_herdado) in zip(nova.params, herdada.params):
                if TIPO_ERRO in (tipo_novo, tipo_herdado):
                    continue                            # já deu erro antes
                if tipo_novo != tipo_herdado:
                    self.relator.report(
                        nova.line,
                        f"{inicio} o parametro '{nome}' tem tipo {tipo_novo} "
                        f"em vez de {tipo_herdado}",
                    )

        if (TIPO_ERRO not in (nova.return_type, herdada.return_type)   # 3) tipo de retorno
                and nova.return_type != herdada.return_type):
            self.relator.report(
                nova.line,
                f"{inicio} devolve {nova.return_type} em vez de {herdada.return_type}",
            )

    def _exigir_metodo_main(self) -> None:
        info = self.classes.get(MAIN)
        if info is None:
            return                                 # falta de Main já reportada na etapa 15

        assinatura = self.lookup_method(MAIN, MAIN_METHOD)
        if assinatura is None:
            self.relator.report(info.line,
                                "a classe Main precisa ter um metodo main()")
        elif assinatura.params:
            self.relator.report(assinatura.line,
                                "o metodo main da classe Main nao pode receber parametros")

    # ----------------------------------------------------------------------
    # 2. Consultas (sobem a herança: a classe tem o que declara + o que herdou)
    # ----------------------------------------------------------------------

    #As funções de consulta buscam na classe ou em seus ancestrais, de baixo para cima, o que se deseja. Se não encontrar, retorna None ou vazio.

    def lookup_method(self, classe: str, nome: str) -> Optional[MethodSignature]:
        """Assinatura de `nome` vista por `classe`, ou None."""
        for ancestral in self.ancestors(classe):   # de baixo para cima
            assinatura = self.classes[ancestral].methods.get(nome)
            if assinatura is not None:
                return assinatura                  # 1º achado: a sobrescrita vence o original
        return None

    def all_attributes(self, classe: str) -> dict[str, str]:
        """Atributos próprios + herdados: nome -> tipo."""
        todos: dict[str, str] = {}
        for ancestral in self.ancestors(classe):
            todos.update(self.classes[ancestral].attributes)
        return todos

    def _classe_que_define_atributo(self, classe: str, nome: str) -> Optional[str]:
        """Em qual classe, de `classe` para cima, o atributo `nome` foi declarado."""
        for ancestral in self.ancestors(classe):
            if nome in self.classes[ancestral].attributes:
                return ancestral
        return None
