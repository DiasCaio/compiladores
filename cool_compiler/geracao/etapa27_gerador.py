"""Etapa 27: o programa Bril inteiro, e generate(), a API da fase.

Para cada classe do usuário saem três tipos de função:

    @Cachorro_novo(heap): int         aloca, escreve tag, tamanho e padrões, chama _init
    @Cachorro_init(heap, self)        _init do pai, depois os inicializadores próprios
    @Cachorro.som(heap, self): int    um por método escrito na classe

Depois vêm os despachantes (um por família de método), o runtime das etapas
23 e 24 e, por último, @rt_iniciar_heap com o segmento de dados.
"""

from ..semantico.etapa14_tipos_basicos import IO, MAIN, MAIN_METHOD, OBJECT, STRING
from ..semantico.etapa15_tabela_de_classes import ClassInfo
from ..semantico.etapa20_verificador import SemanticResult
from ..sintatico.etapa6_ast import Attribute, Method, Program
from .etapa21_bril import HEAP, INT as BRIL_INT, PTR_INT, FunctionBuilder, programa_json
from .etapa22_layout import (
    TAG, TAMANHO, Layout, LayoutDeClasse, funcao_despachante, funcao_init,
    funcao_metodo, funcao_novo, tipo_bril,
)
from .etapa23_runtime import TAMANHO_HEAP_PADRAO, RuntimeMemoria, SegmentoDeDados
from .etapa24_runtime_classes_basicas import RuntimeClassesBasicas
from .etapa26_gerador_chamadas import GeradorDeChamadas


class GeradorDePrograma(GeradorDeChamadas):
    """Monta todas as funções; as expressões ficam com as etapas 25 e 26."""

    def __init__(self, programa: Program, semantico: SemanticResult, tamanho_heap: int):
        layout = Layout(semantico.ambiente)
        super().__init__(layout, SegmentoDeDados(layout), semantico.types)
        self.programa = programa
        self.tamanho_heap = tamanho_heap

    def gerar_programa(self) -> dict:
        funcoes = [self.gerar_main()]

        for classe in self.programa.classes:               # na ordem do arquivo
            info = self.ambiente.classes[classe.name]
            funcoes += [self.gerar_novo(self.layout.classes[info.name]), self.gerar_init(info)]
            funcoes += [self.gerar_metodo(info, feature) for feature in classe.features
                        if isinstance(feature, Method)]

        for nome in (OBJECT, IO):                           # new Object, new IO
            funcoes.append(self.gerar_novo(self.layout.classes[nome]))

        for (raiz, metodo), definidores in self.layout.familias.items():
            if not self.layout.despacho_e_estatico(raiz):   # String: sempre direto
                funcoes.append(self.gerar_despachante(raiz, metodo, definidores))

        funcoes += RuntimeMemoria(self.layout, self.dados, self.tamanho_heap).funcoes()
        funcoes += RuntimeClassesBasicas(self.layout, self.dados).funcoes()
        funcoes.append(self.dados.funcao_iniciar())         # por último: já sabe todas as strings
        return programa_json(funcoes)

    # ----------------------------------------------------------------------
    # 1. @main: o ponto de entrada da Bril
    # ----------------------------------------------------------------------

    def gerar_main(self) -> FunctionBuilder:
        """Cria o heap, roda (new Main).main() e devolve a memória.

        O brili recusa terminar com memória sem free, e o heap é o único bloco
        que o programa pede à Bril; por isso um único free no fim basta.
        """
        f = self.f = FunctionBuilder("main", [], None)
        f.alloc(f.const(self.tamanho_heap, BRIL_INT), dest=HEAP)
        f.call("rt_iniciar_heap", HEAP)
        objeto = f.call(funcao_novo(MAIN), HEAP, tipo=BRIL_INT)
        assinatura = self.ambiente.lookup_method(MAIN, MAIN_METHOD)
        f.call(self.layout.implementacao(MAIN, MAIN_METHOD), HEAP, objeto,
               tipo=tipo_bril(assinatura.return_type))
        f.free(HEAP)
        return f

    # ----------------------------------------------------------------------
    # 2. Criação de objetos: _novo e _init
    # ----------------------------------------------------------------------

    def gerar_novo(self, classe: LayoutDeClasse) -> FunctionBuilder:
        """Os padrões vêm ANTES de qualquer inicializador, como manda o manual:
        um inicializador que leia um atributo ainda não inicializado enxerga 0,
        false, "" ou void, nunca lixo (e a Bril nem deixaria ler lixo)."""
        f = self.f = FunctionBuilder(funcao_novo(classe.nome), [(HEAP, PTR_INT)], BRIL_INT)
        tamanho = f.const(classe.tamanho, BRIL_INT)
        objeto = f.call("rt_alocar", HEAP, tamanho, tipo=BRIL_INT)
        f.escrever(objeto, TAG, f.const(classe.tag, BRIL_INT))
        f.escrever(objeto, TAMANHO, tamanho)
        for nome, tipo in classe.atributos:
            f.escrever(objeto, classe.offset(nome), self._padrao_no_slot(tipo))
        if self.ambiente.classes[classe.nome].node is not None:     # só classes do usuário
            f.call(funcao_init(classe.nome), HEAP, objeto)
        f.ret(objeto)
        return f

    def _padrao_no_slot(self, tipo: str) -> str:
        """Valor padrão já no formato do heap (Bool false é 0)."""
        if tipo == STRING:
            return self.f.const(self.dados.endereco(""), BRIL_INT)
        return self.f.const(0, BRIL_INT)                    # Int, Bool e void

    def gerar_init(self, info: ClassInfo) -> FunctionBuilder:
        f = self.f = FunctionBuilder(funcao_init(info.name),
                                     [(HEAP, PTR_INT), ("self", BRIL_INT)], None)
        self.comecar_classe(info.name)                      # self é desta classe

        pai = self.ambiente.classes[info.parent]
        if pai.node is not None:                            # Object e IO não têm _init
            f.call(funcao_init(pai.name), HEAP, "self")

        layout = self.layout.classes[info.name]
        for feature in info.node.features:
            if isinstance(feature, Attribute) and feature.init is not None:
                valor = self.converter(self.gerar(feature.init),
                                       self.tipo_de(feature.init), feature.type_name)
                f.escrever("self", layout.offset(feature.name),
                           self.para_slot(valor, feature.type_name))
        f.ret()
        return f

    # ----------------------------------------------------------------------
    # 3. Métodos
    # ----------------------------------------------------------------------

    def gerar_metodo(self, info: ClassInfo, metodo: Method) -> FunctionBuilder:
        assinatura = info.methods[metodo.name]
        self.comecar_classe(info.name)

        with self.escopo():                                 # parâmetros sobre atributos
            parametros = [(HEAP, PTR_INT), ("self", BRIL_INT)]
            for formal in metodo.formals:
                nome_bril = self.declarar(formal.name, formal.type_name)
                parametros.append((nome_bril, tipo_bril(formal.type_name)))

            f = self.f = FunctionBuilder(funcao_metodo(info.name, metodo.name), parametros,
                                         tipo_bril(assinatura.return_type))
            valor = self.gerar(metodo.body)
            f.ret(self.converter(valor, self.tipo_de(metodo.body), assinatura.return_type))
        return f

    # ----------------------------------------------------------------------
    # 4. Despachantes: o "ponteiro de função" que a Bril não tem
    # ----------------------------------------------------------------------

    def gerar_despachante(self, raiz: str, metodo: str,
                          definidores: list[LayoutDeClasse]) -> FunctionBuilder:
        """@despachar_Animal.som(heap, self): lê a tag e chama a versão certa.

        `definidores` são as classes que escrevem a própria versão, da mais
        funda para a mais rasa. A primeira cuja faixa contém a tag vence. A
        última é sempre a raiz, cuja faixa cobre a família inteira: ela é o
        caso que sobra e não precisa de teste.
        """
        assinatura = self.ambiente.lookup_method(raiz, metodo)
        retorno = tipo_bril(assinatura.return_type)
        argumentos = [f"arg{posicao}" for posicao in range(1, len(assinatura.params) + 1)]
        parametros = [(HEAP, PTR_INT), ("self", BRIL_INT)]
        parametros += [(nome, tipo_bril(tipo))
                       for nome, (_, tipo) in zip(argumentos, assinatura.params)]

        f = self.f = FunctionBuilder(funcao_despachante(raiz, metodo), parametros, retorno)
        *mais_fundos, ultimo = definidores
        assert ultimo.nome == raiz

        tag = f.ler("self", TAG) if mais_fundos else ""     # sem sobrescrita: nada a testar
        for classe in mais_fundos:
            chamar = lambda nome=classe.nome: f.ret(f.call(
                funcao_metodo(nome, metodo), HEAP, "self", *argumentos, tipo=retorno))
            f.se(self._tag_na_faixa(tag, classe.nome), chamar)
        f.ret(f.call(funcao_metodo(raiz, metodo), HEAP, "self", *argumentos, tipo=retorno))
        return f


# --------------------------------------------------------------------------
# 5. API pública da fase
# --------------------------------------------------------------------------

def generate(programa: Program, semantico: SemanticResult,
             tamanho_heap: int = TAMANHO_HEAP_PADRAO,
             avisos: list[str] | None = None) -> dict:
    """Traduz um programa SEM erros para Bril em JSON (um dict pronto para json.dumps).

    `avisos`, se for uma lista, recebe as mensagens sobre o que a Bril não
    consegue fazer (hoje: ler entrada com in_int/in_string).
    """
    gerador = GeradorDePrograma(programa, semantico, tamanho_heap)
    resultado = gerador.gerar_programa()
    if avisos is not None:
        avisos.extend(gerador.avisos)
    return resultado
