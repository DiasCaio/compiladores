"""Etapa 24: runtime, parte 2 — os métodos de Object, IO e String.

As classes básicas não têm nó na AST: a fase semântica conhece só as
ASSINATURAS delas (etapa 14). Os corpos são escritos aqui, direto em Bril.

Eles seguem a mesma convenção dos métodos do usuário, @Classe.metodo(heap,
self, args...). Assim um despachante chama IO.out_string ou Main.out_string
do mesmo jeito, sem saber qual dos dois foi escrito em Python e qual veio do
programa COOL.
"""

from ..semantico.etapa14_tipos_basicos import BOOL, INT, IO, OBJECT, STRING
from .etapa21_bril import BOOL as BRIL_BOOL
from .etapa21_bril import HEAP, INT as BRIL_INT, PTR_INT, FunctionBuilder
from .etapa22_layout import (
    COMPRIMENTO, PRIMEIRO_CHAR, TAG, TAMANHO, VALOR_EMBALADO, Layout,
    funcao_metodo, funcao_novo, tipo_bril,
)
from .etapa23_runtime import SegmentoDeDados


class RuntimeClassesBasicas:
    """Corpos dos métodos das classes básicas, igualdade e new dinâmico."""

    def __init__(self, layout: Layout, dados: SegmentoDeDados):
        self.layout = layout
        self.dados = dados

    def funcoes(self) -> list[FunctionBuilder]:
        return [
            self.abort(), self.type_name(), self.copy(),
            self.out_string(), self.out_int(), self.in_string(), self.in_int(),
            self.length(), self.concat(), self.substr(), self.nova_string(),
            self.igual(), self.strings_iguais(), self.novo_por_tag(),
        ]

    # ---- 0. Atalhos -------------------------------------------------------

    def _metodo(self, classe: str, nome: str) -> FunctionBuilder:
        """Cabeçalho tirado da assinatura da etapa 14: não há como divergir."""
        assinatura = self.layout.ambiente.classes[classe].methods[nome]
        parametros = [(HEAP, PTR_INT), ("self", BRIL_INT)]
        parametros += [(param, tipo_bril(tipo)) for param, tipo in assinatura.params]
        return FunctionBuilder(funcao_metodo(classe, nome), parametros,
                               tipo_bril(assinatura.return_type))

    def _int(self, f: FunctionBuilder, valor: int) -> str:
        return f.const(valor, BRIL_INT)

    def _tag(self, f: FunctionBuilder, classe: str) -> str:
        return self._int(f, self.layout.classes[classe].tag)

    # ---- 1. Object ----------------------------------------------------------

    def abort(self) -> FunctionBuilder:
        """Encerra o programa, dizendo de qual classe veio a chamada."""
        f = self._metodo(OBJECT, "abort")
        nome = f.call(funcao_metodo(OBJECT, "type_name"), HEAP, "self", tipo=BRIL_INT)
        prefixo = self._int(f, self.dados.endereco("abort() chamado em um objeto da classe "))
        mensagem = f.call(funcao_metodo(STRING, "concat"), HEAP, prefixo, nome, tipo=BRIL_INT)
        f.call("rt_erro", HEAP, mensagem, self._int(f, 0))
        f.ret("self")                                      # nunca chega aqui
        return f

    def type_name(self) -> FunctionBuilder:
        """A tag indexa a tabela de nomes do segmento de dados: nada de if."""
        f = self._metodo(OBJECT, "type_name")
        tag = f.ler("self", TAG)
        posicao = f.op("add", tag, self._int(f, self.dados.tabela_de_nomes))
        f.ret(f.ler(posicao))
        return f

    def copy(self) -> FunctionBuilder:
        """Cópia rasa: o tamanho no cabeçalho diz quantas posições copiar.

        Serve igual para objetos, Strings e Int/Bool empacotados.
        """
        f = self._metodo(OBJECT, "copy")
        tamanho = f.ler("self", TAMANHO)
        novo = f.call("rt_alocar", HEAP, tamanho, tipo=BRIL_INT)
        f.call("rt_copiar_slots", HEAP, "self", novo, tamanho)
        f.ret(novo)
        return f

    # ---- 2. IO --------------------------------------------------------------
    # out_* devolvem self (tipo SELF_TYPE): é o que permite encadear chamadas.

    def out_string(self) -> FunctionBuilder:
        f = self._metodo(IO, "out_string")
        f.call("rt_imprimir_string", HEAP, "x")
        f.ret("self")
        return f

    def out_int(self) -> FunctionBuilder:
        f = self._metodo(IO, "out_int")
        f.call("rt_imprimir_int", HEAP, "x")
        f.ret("self")
        return f

    def in_string(self) -> FunctionBuilder:
        """A Bril não lê entrada (o stdin do brili é o próprio programa): devolve ""."""
        f = self._metodo(IO, "in_string")
        f.ret(self._int(f, self.dados.endereco("")))
        return f

    def in_int(self) -> FunctionBuilder:
        """Mesma limitação de in_string: devolve 0."""
        f = self._metodo(IO, "in_int")
        f.ret(self._int(f, 0))
        return f

    # ---- 3. String ----------------------------------------------------------

    def length(self) -> FunctionBuilder:
        f = self._metodo(STRING, "length")
        f.ret(f.ler("self", COMPRIMENTO))
        return f

    def nova_string(self) -> FunctionBuilder:
        """@rt_nova_string(heap, n): aloca uma String de n caracteres.

        Escreve só o cabeçalho; quem chama preenche os caracteres em seguida,
        antes de qualquer leitura.
        """
        f = FunctionBuilder("rt_nova_string", [(HEAP, PTR_INT), ("n", BRIL_INT)], BRIL_INT)
        tamanho = f.op("add", "n", self._int(f, PRIMEIRO_CHAR))
        nova = f.call("rt_alocar", HEAP, tamanho, tipo=BRIL_INT)
        f.escrever(nova, TAG, self._tag(f, STRING))
        f.escrever(nova, TAMANHO, tamanho)
        f.escrever(nova, COMPRIMENTO, "n")
        f.ret(nova)
        return f

    def concat(self) -> FunctionBuilder:
        """self + s: uma String nova com os caracteres dos dois, nessa ordem."""
        f = self._metodo(STRING, "concat")
        n1, n2 = f.ler("self", COMPRIMENTO), f.ler("s", COMPRIMENTO)
        nova = f.call("rt_nova_string", HEAP, f.op("add", n1, n2), tipo=BRIL_INT)
        destino = f.endereco(nova, PRIMEIRO_CHAR)
        f.call("rt_copiar_slots", HEAP, f.endereco("self", PRIMEIRO_CHAR), destino, n1)
        f.call("rt_copiar_slots", HEAP, f.endereco("s", PRIMEIRO_CHAR),
               f.op("add", destino, n1), n2)
        f.ret(nova)
        return f

    def substr(self) -> FunctionBuilder:
        """Os l caracteres a partir da posição i; fora dos limites é erro."""
        f = self._metodo(STRING, "substr")
        zero = self._int(f, 0)
        comprimento = f.ler("self", COMPRIMENTO)
        invalido = f.op("or",
                        f.op("or", f.op("lt", "i", zero, tipo=BRIL_BOOL),
                             f.op("lt", "l", zero, tipo=BRIL_BOOL), tipo=BRIL_BOOL),
                        f.op("gt", f.op("add", "i", "l"), comprimento, tipo=BRIL_BOOL),
                        tipo=BRIL_BOOL)
        f.se(invalido, lambda: f.call(
            "rt_erro", HEAP, self._int(f, self.dados.endereco("substr fora dos limites")),
            zero))
        nova = f.call("rt_nova_string", HEAP, "l", tipo=BRIL_INT)
        origem = f.op("add", f.endereco("self", PRIMEIRO_CHAR), "i")
        f.call("rt_copiar_slots", HEAP, origem, f.endereco(nova, PRIMEIRO_CHAR), "l")
        f.ret(nova)
        return f

    # ---- 4. Igualdade -------------------------------------------------------

    def igual(self) -> FunctionBuilder:
        """@rt_igual(heap, a, b): o `=` entre dois endereços.

            mesmo endereço                -> true  (inclui void = void)
            só um dos lados void          -> false
            tags diferentes               -> false
            Int, Bool: mesmo valor; String: mesmos caracteres
            qualquer outra classe         -> false (objetos distintos)
        """
        f = FunctionBuilder("rt_igual", [(HEAP, PTR_INT), ("a", BRIL_INT), ("b", BRIL_INT)],
                            BRIL_BOOL)
        verdade, falso, zero = f.const(True, BRIL_BOOL), f.const(False, BRIL_BOOL), self._int(f, 0)
        f.se(f.op("eq", "a", "b", tipo=BRIL_BOOL), lambda: f.ret(verdade))
        algum_void = f.op("or", f.op("eq", "a", zero, tipo=BRIL_BOOL),
                          f.op("eq", "b", zero, tipo=BRIL_BOOL), tipo=BRIL_BOOL)
        f.se(algum_void, lambda: f.ret(falso))

        tag = f.ler("a", TAG)
        tags_diferentes = f.op("not", f.op("eq", tag, f.ler("b", TAG), tipo=BRIL_BOOL),
                               tipo=BRIL_BOOL)
        f.se(tags_diferentes, lambda: f.ret(falso))

        embalado = f.op("or", f.op("eq", tag, self._tag(f, INT), tipo=BRIL_BOOL),
                        f.op("eq", tag, self._tag(f, BOOL), tipo=BRIL_BOOL), tipo=BRIL_BOOL)
        f.se(embalado, lambda: f.ret(f.op("eq", f.ler("a", VALOR_EMBALADO),
                                          f.ler("b", VALOR_EMBALADO), tipo=BRIL_BOOL)))
        f.se(f.op("eq", tag, self._tag(f, STRING), tipo=BRIL_BOOL),
             lambda: f.ret(f.call("rt_strings_iguais", HEAP, "a", "b", tipo=BRIL_BOOL)))
        f.ret(falso)
        return f

    def strings_iguais(self) -> FunctionBuilder:
        """@rt_strings_iguais(heap, a, b): mesmo comprimento e mesmos caracteres."""
        f = FunctionBuilder("rt_strings_iguais",
                            [(HEAP, PTR_INT), ("a", BRIL_INT), ("b", BRIL_INT)], BRIL_BOOL)
        falso = f.const(False, BRIL_BOOL)
        comprimento = f.ler("a", COMPRIMENTO)
        f.se(f.op("not", f.op("eq", comprimento, f.ler("b", COMPRIMENTO), tipo=BRIL_BOOL),
                  tipo=BRIL_BOOL),
             lambda: f.ret(falso))

        def comparar(i: str) -> None:
            posicao = f.op("add", i, self._int(f, PRIMEIRO_CHAR))
            igual = f.op("eq", f.ler(f.op("add", "a", posicao)),
                         f.ler(f.op("add", "b", posicao)), tipo=BRIL_BOOL)
            f.se(f.op("not", igual, tipo=BRIL_BOOL), lambda: f.ret(falso))

        f.laco_contado(comprimento, comparar)
        f.ret(f.const(True, BRIL_BOOL))
        return f

    # ---- 5. new SELF_TYPE ---------------------------------------------------

    def novo_por_tag(self) -> FunctionBuilder:
        """@rt_novo_por_tag(heap, tag): o `new` cuja classe só se sabe rodando.

        Sem ponteiros de função, a única saída é uma cadeia de comparações,
        uma por classe que pode ser instanciada.
        """
        f = FunctionBuilder("rt_novo_por_tag", [(HEAP, PTR_INT), ("tag", BRIL_INT)], BRIL_INT)
        for classe in self.layout.por_tag():
            if classe.nome in (INT, BOOL, STRING):         # new Int etc. são constantes
                continue
            mesma = f.op("eq", "tag", self._int(f, classe.tag), tipo=BRIL_BOOL)
            f.se(mesma, lambda nome=classe.nome: f.ret(
                f.call(funcao_novo(nome), HEAP, tipo=BRIL_INT)))
        f.ret(self._int(f, 0))                             # inalcançável
        return f
