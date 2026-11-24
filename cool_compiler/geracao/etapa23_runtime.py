"""Etapa 23: runtime, parte 1 — memória, saída, erros e empacotamento.

A Bril não tem malloc, printf nem exceções. Tudo isso precisa ser escrito em
Bril e anexado a cada programa gerado: é o RUNTIME, o mesmo papel do
trap.handler que acompanha o código MIPS do compilador COOL de referência.

As funções do runtime são montadas aqui em Python, com o FunctionBuilder da
etapa 21, e todas começam com rt_ para não se confundirem com código do
usuário.
"""

from ..semantico.etapa14_tipos_basicos import BOOL, INT, STRING
from .etapa21_bril import BOOL as BRIL_BOOL
from .etapa21_bril import HEAP, INT as BRIL_INT, PTR_INT, FunctionBuilder
from .etapa22_layout import (
    COMPRIMENTO, PRIMEIRO_CHAR, TAG, TAMANHO, VALOR_EMBALADO, Layout,
)

# Tamanho do único bloco que o @main pede à Bril. Cada posição é um int.
TAMANHO_HEAP_PADRAO = 1_000_000

# O print da Bril sempre quebra a linha, então cada caractere sai como o seu
# CÓDIGO, um por linha, e o executor (etapa 28) converte de volta com chr().
# Um -1 nunca é código de caractere: ele avisa que daqui em diante vem a
# mensagem de um erro de execução, e não mais a saída normal.
SENTINELA_ERRO = -1


# --------------------------------------------------------------------------
# 1. Segmento de dados: as strings conhecidas em tempo de compilação
# --------------------------------------------------------------------------

class SegmentoDeDados:
    """Grava no começo do heap tudo o que já se sabe antes de rodar.

        heap[0]           próximo índice livre (onde o alocador continua)
        heap[1 .. N]      tabela de nomes: heap[1 + tag] = endereço do nome
        heap[N+1 ..]      strings: nomes das classes, literais e mensagens

    Strings em COOL são imutáveis, então um literal pode ser gravado UMA vez e
    compartilhado: no código, "abc" vira apenas `const <endereço>`. É a mesma
    ideia da seção .data de um programa em assembly.
    """

    def __init__(self, layout: Layout):
        self.tag_string = layout.classes[STRING].tag
        self.tabela_de_nomes = 1
        self._proximo = self.tabela_de_nomes + len(layout.classes)
        self._strings: dict[str, int] = {}                 # texto -> endereço
        self._nomes = [self.endereco(classe.nome) for classe in layout.por_tag()]

    def endereco(self, texto: str) -> int:
        """Endereço da string `texto`, reservando espaço na primeira vez."""
        if texto not in self._strings:
            self._strings[texto] = self._proximo
            self._proximo += PRIMEIRO_CHAR + len(texto)
        return self._strings[texto]

    def funcao_iniciar(self) -> FunctionBuilder:
        """@rt_iniciar_heap: escreve o segmento inteiro, posição por posição.

        Gerada por ÚLTIMO, quando todos os literais do programa já pediram
        o seu endereço.
        """
        valores = [self._proximo] + self._nomes            # heap[0] e a tabela
        for texto in self._strings:                        # em ordem de endereço
            valores += [self.tag_string, PRIMEIRO_CHAR + len(texto), len(texto)]
            valores += [ord(caractere) for caractere in texto]

        f = FunctionBuilder("rt_iniciar_heap", [(HEAP, PTR_INT)], None)
        um = f.const(1, BRIL_INT)
        f.id(HEAP, PTR_INT, dest="p")
        for posicao, valor in enumerate(valores):
            f.const(valor, BRIL_INT, dest="v")
            f.store("p", "v")
            if posicao < len(valores) - 1:
                f.ptradd("p", um, dest="p")
        f.ret()
        return f


# --------------------------------------------------------------------------
# 2. As funções do runtime
# --------------------------------------------------------------------------

class RuntimeMemoria:
    """Alocação, saída por códigos, erros e empacotamento de Int/Bool."""

    def __init__(self, layout: Layout, dados: SegmentoDeDados, tamanho_heap: int):
        self.layout = layout
        self.dados = dados
        self.tamanho_heap = tamanho_heap

    def funcoes(self) -> list[FunctionBuilder]:
        return [
            self.alocar(), self.copiar_slots(),
            self.imprimir_string(), self.imprimir_int(), self.imprimir_digitos(),
            self.erro(), self.checar_void(), self.checar_divisor(),
            self.bool_para_int(),
            self.box(INT), self.box(BOOL), self.unbox(INT), self.unbox(BOOL),
        ]

    def _mensagem(self, f: FunctionBuilder, texto: str) -> str:
        return f.const(self.dados.endereco(texto), BRIL_INT)

    # ---- 1. Memória -------------------------------------------------------

    def alocar(self) -> FunctionBuilder:
        """@rt_alocar(heap, n): alocador bump, sem coleta de lixo.

        heap[0] diz onde começa a parte livre; alocar n posições é só
        devolver esse índice e avançá-lo n casas. Nada é liberado.
        """
        f = FunctionBuilder("rt_alocar", [(HEAP, PTR_INT), ("n", BRIL_INT)], BRIL_INT)
        livre = f.load(HEAP)                               # heap[PROXIMO_LIVRE], o 0
        novo_livre = f.op("add", livre, "n")
        limite = f.const(self.tamanho_heap, BRIL_INT)
        f.se(f.op("gt", novo_livre, limite, tipo=BRIL_BOOL),
             lambda: f.call("rt_erro", HEAP, self._mensagem(f, "heap esgotado"),
                            f.const(0, BRIL_INT)))
        f.store(HEAP, novo_livre)                          # heap[0] = novo_livre
        f.ret(livre)
        return f

    def copiar_slots(self) -> FunctionBuilder:
        """@rt_copiar_slots(heap, origem, destino, n): copia n posições."""
        f = FunctionBuilder("rt_copiar_slots", [(HEAP, PTR_INT), ("origem", BRIL_INT),
                                                ("destino", BRIL_INT), ("n", BRIL_INT)], None)

        def copiar_uma(i: str) -> None:
            valor = f.ler(f.op("add", "origem", i))
            f.escrever(f.op("add", "destino", i), 0, valor)

        f.laco_contado("n", copiar_uma)
        f.ret()
        return f

    # ---- 2. Saída: um código de caractere por print ----------------------

    def imprimir_string(self) -> FunctionBuilder:
        """@rt_imprimir_string(heap, s): um print por caractere de s."""
        f = FunctionBuilder("rt_imprimir_string", [(HEAP, PTR_INT), ("s", BRIL_INT)], None)
        comprimento = f.ler("s", COMPRIMENTO)
        inicio = f.endereco("s", PRIMEIRO_CHAR)
        f.laco_contado(comprimento, lambda i: f.print(f.ler(f.op("add", inicio, i))))
        f.ret()
        return f

    def imprimir_int(self) -> FunctionBuilder:
        """@rt_imprimir_int(heap, n): o sinal, se houver, e depois os dígitos."""
        f = FunctionBuilder("rt_imprimir_int", [(HEAP, PTR_INT), ("n", BRIL_INT)], None)
        zero = f.const(0, BRIL_INT)

        def negativo() -> None:
            f.print(f.const(ord("-"), BRIL_INT))
            f.op("sub", zero, "n", dest="n")               # n = -n

        f.se(f.op("lt", "n", zero, tipo=BRIL_BOOL), negativo)
        f.call("rt_imprimir_digitos", HEAP, "n")
        f.ret()
        return f

    def imprimir_digitos(self) -> FunctionBuilder:
        """@rt_imprimir_digitos(heap, n), n >= 0, recursiva.

        A divisão por 10 entrega os dígitos do FIM para o começo; imprimir
        primeiro o resto da recursão (n / 10) e só depois o último dígito
        coloca tudo na ordem certa, sem precisar de um vetor auxiliar.
        """
        f = FunctionBuilder("rt_imprimir_digitos", [(HEAP, PTR_INT), ("n", BRIL_INT)], None)
        dez = f.const(10, BRIL_INT)
        quociente = f.op("div", "n", dez)
        f.se(f.op("ge", "n", dez, tipo=BRIL_BOOL),
             lambda: f.call("rt_imprimir_digitos", HEAP, quociente))
        digito = f.op("sub", "n", f.op("mul", quociente, dez))   # n % 10
        f.print(f.op("add", digito, f.const(ord("0"), BRIL_INT)))
        f.ret()
        return f

    # ---- 3. Erros de execução --------------------------------------------

    def erro(self) -> FunctionBuilder:
        """@rt_erro(heap, mensagem, linha): imprime e ENCERRA o programa.

        A Bril não tem exit, então o término é forçado com uma divisão por
        zero: o brili para na hora com código de saída 2. A mensagem sai
        antes, pelo mesmo protocolo de códigos, logo depois do sentinela -1.
        """
        f = FunctionBuilder("rt_erro", [(HEAP, PTR_INT), ("mensagem", BRIL_INT),
                                        ("linha", BRIL_INT)], None)
        f.print(f.const(SENTINELA_ERRO, BRIL_INT))
        f.call("rt_imprimir_string", HEAP, "mensagem")

        def com_linha() -> None:                           # linha 0 = desconhecida
            f.call("rt_imprimir_string", HEAP, self._mensagem(f, " (linha "))
            f.call("rt_imprimir_int", HEAP, "linha")
            f.call("rt_imprimir_string", HEAP, self._mensagem(f, ")"))

        f.se(f.op("gt", "linha", f.const(0, BRIL_INT), tipo=BRIL_BOOL), com_linha)
        f.op("div", f.const(1, BRIL_INT), f.const(0, BRIL_INT))   # fim forçado
        f.ret()
        return f

    def checar_void(self) -> FunctionBuilder:
        """@rt_checar_void(heap, valor, mensagem, linha): erro se valor for void."""
        f = FunctionBuilder("rt_checar_void", [(HEAP, PTR_INT), ("valor", BRIL_INT),
                                               ("mensagem", BRIL_INT), ("linha", BRIL_INT)],
                            None)
        e_void = f.op("eq", "valor", f.const(0, BRIL_INT), tipo=BRIL_BOOL)
        f.se(e_void, lambda: f.call("rt_erro", HEAP, "mensagem", "linha"))
        f.ret()
        return f

    def checar_divisor(self) -> FunctionBuilder:
        """@rt_checar_divisor(heap, d, linha): chamada antes de todo `/` do COOL.

        Sem ela o brili também pararia, mas com a mensagem dele; assim o
        erro sai no nosso formato e com a linha do programa COOL.
        """
        f = FunctionBuilder("rt_checar_divisor", [(HEAP, PTR_INT), ("d", BRIL_INT),
                                                  ("linha", BRIL_INT)], None)
        f.call("rt_checar_void", HEAP, "d", self._mensagem(f, "divisao por zero"), "linha")
        f.ret()
        return f

    # ---- 4. Empacotamento (boxing) de Int e Bool -------------------------
    # Um Int que vai para uma variável Object precisa virar objeto, para ter
    # tag (o case e o type_name dependem dela). O heap só guarda int, então
    # um Bool é guardado como 0 ou 1.

    def bool_para_int(self) -> FunctionBuilder:
        """@rt_bool_para_int(heap, b): a Bril não converte bool em int sozinha."""
        f = FunctionBuilder("rt_bool_para_int", [(HEAP, PTR_INT), ("b", BRIL_BOOL)],
                            BRIL_INT)
        verdade, falso = f.rotulo("verdade"), f.rotulo("falso")
        f.br("b", verdade, falso)
        f.label(verdade)
        f.ret(f.const(1, BRIL_INT))
        f.label(falso)
        f.ret(f.const(0, BRIL_INT))
        return f

    def box(self, tipo: str) -> FunctionBuilder:
        """@rt_box_int / @rt_box_bool: cria o objeto [tag, 3, valor]."""
        f = FunctionBuilder(f"rt_box_{tipo.lower()}",
                            [(HEAP, PTR_INT), ("v", BRIL_BOOL if tipo == BOOL else BRIL_INT)],
                            BRIL_INT)
        valor = f.call("rt_bool_para_int", HEAP, "v", tipo=BRIL_INT) if tipo == BOOL else "v"
        tamanho = f.const(VALOR_EMBALADO + 1, BRIL_INT)
        objeto = f.call("rt_alocar", HEAP, tamanho, tipo=BRIL_INT)
        f.escrever(objeto, TAG, f.const(self.layout.classes[tipo].tag, BRIL_INT))
        f.escrever(objeto, TAMANHO, tamanho)
        f.escrever(objeto, VALOR_EMBALADO, valor)
        f.ret(objeto)
        return f

    def unbox(self, tipo: str) -> FunctionBuilder:
        """@rt_unbox_int / @rt_unbox_bool: lê o valor de volta do objeto."""
        f = FunctionBuilder(f"rt_unbox_{tipo.lower()}", [(HEAP, PTR_INT), ("objeto", BRIL_INT)],
                            BRIL_BOOL if tipo == BOOL else BRIL_INT)
        valor = f.ler("objeto", VALOR_EMBALADO)
        if tipo == BOOL:
            valor = f.op("eq", valor, f.const(1, BRIL_INT), tipo=BRIL_BOOL)
        f.ret(valor)
        return f
