"""Etapa 25: tradução das expressões, parte 1 — variáveis, operadores e fluxo.

Mesma organização da etapa 19: um `match` escolhe a regra pelo tipo do nó, e
cada regra é uma função. Lá cada regra devolvia o TIPO da expressão; aqui
devolve o NOME da variável Bril que guarda o VALOR dela.

    1 + 2 * 3        t1: int = const 1;
                     t2: int = const 2;
                     t3: int = const 3;
                     t4: int = mul t2 t3;
                     t5: int = add t1 t4;      <- gerar() devolve "t5"

Os filhos são gerados antes do pai e da esquerda para a direita, que é a
ordem de avaliação do manual de COOL. new, dispatch e case ficam na etapa 26.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional

from ..semantico.etapa14_tipos_basicos import BOOL, INT, OBJECT, SELF, SELF_TYPE, STRING
from ..sintatico.etapa6_ast import (
    Assign, BinaryOp, Block, BoolConst, Case, Dispatch, Expr, If, IntConst,
    IsVoid, Let, Neg, New, Not, ObjectId, StaticDispatch, StringConst, While,
)
from .etapa21_bril import BOOL as BRIL_BOOL
from .etapa21_bril import HEAP, INT as BRIL_INT, FunctionBuilder
from .etapa22_layout import Layout, eh_primitivo, tipo_bril
from .etapa23_runtime import SegmentoDeDados

# Operadores que viram uma instrução Bril só: COOL -> (opcode, tipo do resultado)
OPERADORES_DIRETOS = {
    "+": ("add", BRIL_INT),
    "-": ("sub", BRIL_INT),
    "*": ("mul", BRIL_INT),
    "/": ("div", BRIL_INT),
    "<": ("lt", BRIL_BOOL),
    "<=": ("le", BRIL_BOOL),
}


@dataclass(frozen=True)
class Variavel:
    """Um nome de COOL visível agora: ou uma variável Bril, ou um atributo de self."""

    tipo: str                          # tipo COOL declarado
    nome_bril: Optional[str] = None    # variável local (let, case, parâmetro)
    offset: Optional[int] = None       # atributo: posição dentro de self


class GeradorDeExpressoes:
    """Emite, na função atual, as instruções de cada expressão."""

    def __init__(self, layout: Layout, dados: SegmentoDeDados, tipos: dict[int, str]):
        self.layout = layout
        self.ambiente = layout.ambiente
        self.dados = dados
        self.tipos = tipos                 # id(nó) -> tipo, vindo da etapa 19
        self.f: FunctionBuilder = None     # função sendo montada
        self.classe_atual = OBJECT
        self.escopos: list[dict[str, Variavel]] = []
        self._renomeadas = 0

    # ----------------------------------------------------------------------
    # 1. Contexto: classe atual, escopos e renomeação
    # ----------------------------------------------------------------------

    def comecar_classe(self, classe: str) -> None:
        """Atributos (próprios e herdados) formam o escopo mais externo."""
        self.classe_atual = classe
        layout = self.layout.classes[classe]
        self.escopos = [{nome: Variavel(tipo, offset=layout.offset(nome))
                         for nome, tipo in layout.atributos}]

    @contextmanager
    def escopo(self) -> Iterator[None]:
        self.escopos.append({})
        try:
            yield
        finally:
            self.escopos.pop()

    def declarar(self, nome: str, tipo: str) -> str:
        """Cria a variável Bril de um nome de COOL, com um número único.

        Em `let x : Int <- 1 in let x : String in ...` os dois x precisam ser
        variáveis Bril diferentes (x.1 e x.2), senão o de dentro apagaria o de
        fora. O ponto não existe em nomes de COOL nem nos temporários t<n>,
        então o nome renomeado nunca colide com nada.
        """
        self._renomeadas += 1
        nome_bril = f"{nome}.{self._renomeadas}"
        self.escopos[-1][nome] = Variavel(tipo, nome_bril=nome_bril)
        return nome_bril

    def buscar(self, nome: str) -> Variavel:
        for escopo in reversed(self.escopos):          # do mais interno para fora
            if nome in escopo:
                return escopo[nome]
        raise KeyError(nome)                           # a fase semântica garante que existe

    # ----------------------------------------------------------------------
    # 2. Tipos e conversões
    # ----------------------------------------------------------------------

    def tipo_de(self, expr: Expr) -> str:
        """O tipo estático anotado pela etapa 19, com SELF_TYPE resolvido."""
        tipo = self.tipos[id(expr)]
        return self.classe_atual if tipo == SELF_TYPE else tipo

    def converter(self, valor: str, origem: str, destino: str) -> str:
        """Leva um valor do tipo `origem` para um lugar que espera `destino`.

        O ÚNICO ponto que empacota (box) e desempacota (unbox):
            Int  -> Object     5 vira o objeto [tag_Int, 3, 5]
            Object -> Int      só no ramo `n : Int` de um case
            demais casos       o valor passa como está
        """
        if eh_primitivo(origem) == eh_primitivo(destino):
            return valor
        if eh_primitivo(origem):
            return self.f.call(f"rt_box_{origem.lower()}", HEAP, valor, tipo=BRIL_INT)
        return self.f.call(f"rt_unbox_{destino.lower()}", HEAP, valor,
                           tipo=tipo_bril(destino))

    def valor_padrao(self, tipo: str) -> str:
        """Int 0, Bool false, String "" e void (0) para todo o resto."""
        if tipo == BOOL:
            return self.f.const(False, BRIL_BOOL)
        if tipo == STRING:
            return self.f.const(self.dados.endereco(""), BRIL_INT)
        return self.f.const(0, BRIL_INT)

    # O heap só guarda int: um Bool vai como 0/1 e volta comparando com 1.

    def para_slot(self, valor: str, tipo: str) -> str:
        if tipo == BOOL:
            return self.f.call("rt_bool_para_int", HEAP, valor, tipo=BRIL_INT)
        return valor

    def de_slot(self, valor: str, tipo: str) -> str:
        if tipo == BOOL:
            return self.f.op("eq", valor, self.f.const(1, BRIL_INT), tipo=BRIL_BOOL)
        return valor

    # ----------------------------------------------------------------------
    # 3. Despacho: escolhe a regra pelo tipo do nó
    # ----------------------------------------------------------------------

    def gerar(self, expr: Expr) -> str:
        match expr:
            case IntConst():
                return self.f.const(expr.value, BRIL_INT)
            case BoolConst():
                return self.f.const(expr.value, BRIL_BOOL)
            case StringConst():
                return self.f.const(self.dados.endereco(expr.value), BRIL_INT)
            case ObjectId():
                return self.gerar_object_id(expr)
            case Assign():
                return self.gerar_assign(expr)
            case If():
                return self.gerar_if(expr)
            case While():
                return self.gerar_while(expr)
            case Block():
                return self.gerar_block(expr)
            case Let():
                return self.gerar_let(expr)
            case IsVoid():
                return self.gerar_isvoid(expr)
            case Not():
                return self.f.op("not", self.gerar(expr.operand), tipo=BRIL_BOOL)
            case Neg():                                # ~x é 0 - x
                operando = self.gerar(expr.operand)
                return self.f.op("sub", self.f.const(0, BRIL_INT), operando)
            case BinaryOp():
                return self.gerar_binary(expr)
            case New():                                # etapa 26
                return self.gerar_new(expr)
            case Dispatch():                           # etapa 26
                return self.gerar_dispatch(expr)
            case StaticDispatch():                     # etapa 26
                return self.gerar_static_dispatch(expr)
            case Case():                               # etapa 26
                return self.gerar_case(expr)
        raise ValueError(f"expressao sem traducao: {type(expr).__name__}")

    # ----------------------------------------------------------------------
    # 4. Nomes e atribuição
    # ----------------------------------------------------------------------

    def gerar_object_id(self, expr: ObjectId) -> str:
        if expr.name == SELF:
            return "self"                          # parâmetro de toda função de método
        variavel = self.buscar(expr.name)
        if variavel.offset is None:
            # Copia para um temporário: em `x + (x <- 5)`, o x da esquerda tem
            # que valer o que valia ANTES da atribuição da direita.
            return self.f.id(variavel.nome_bril, tipo_bril(variavel.tipo))
        return self.de_slot(self.f.ler("self", variavel.offset), variavel.tipo)

    def gerar_assign(self, expr: Assign) -> str:
        valor = self.gerar(expr.value)
        variavel = self.buscar(expr.name)
        guardado = self.converter(valor, self.tipo_de(expr.value), variavel.tipo)
        if variavel.offset is None:
            self.f.id(guardado, tipo_bril(variavel.tipo), dest=variavel.nome_bril)
        else:
            self.f.escrever("self", variavel.offset, self.para_slot(guardado, variavel.tipo))
        return valor                               # a atribuição vale o valor atribuído

    # ----------------------------------------------------------------------
    # 5. Controle de fluxo
    # ----------------------------------------------------------------------

    def gerar_if(self, expr: If) -> str:
        """Os dois ramos escrevem na MESMA variável, lida depois do fim."""
        tipo = self.tipo_de(expr)
        resultado = self.f.temp()
        entao, senao, fim = (self.f.rotulo("entao"), self.f.rotulo("senao"),
                             self.f.rotulo("fim_if"))

        self.f.br(self.gerar(expr.condition), entao, senao)
        for rotulo, ramo in ((entao, expr.then_branch), (senao, expr.else_branch)):
            self.f.label(rotulo)
            valor = self.converter(self.gerar(ramo), self.tipo_de(ramo), tipo)
            self.f.id(valor, tipo_bril(tipo), dest=resultado)
            self.f.jmp(fim)
        self.f.label(fim)
        return resultado

    def gerar_while(self, expr: While) -> str:
        teste, corpo, fim = (self.f.rotulo("while"), self.f.rotulo("loop"),
                             self.f.rotulo("pool"))
        self.f.label(teste)
        self.f.br(self.gerar(expr.condition), corpo, fim)
        self.f.label(corpo)
        self.gerar(expr.body)                      # o valor do corpo é descartado
        self.f.jmp(teste)
        self.f.label(fim)
        return self.f.const(0, BRIL_INT)           # while vale void

    def gerar_block(self, expr: Block) -> str:
        valor = ""
        for interna in expr.expressions:
            valor = self.gerar(interna)
        return valor                               # vale a última

    def gerar_let(self, expr: Let) -> str:
        # O inicializador é gerado ANTES de x existir: em `let x <- x + 1`,
        # o x da direita ainda é o de fora (mesma regra da etapa 19).
        if expr.init is not None:
            valor = self.converter(self.gerar(expr.init), self.tipo_de(expr.init),
                                   expr.type_name)
        else:
            valor = self.valor_padrao(expr.type_name)

        with self.escopo():
            nome = self.declarar(expr.name, expr.type_name)
            self.f.id(valor, tipo_bril(expr.type_name), dest=nome)
            return self.gerar(expr.body)

    # ----------------------------------------------------------------------
    # 6. Operadores
    # ----------------------------------------------------------------------

    def gerar_isvoid(self, expr: IsVoid) -> str:
        valor = self.gerar(expr.operand)           # gerado mesmo assim: pode ter efeitos
        if eh_primitivo(self.tipo_de(expr.operand)):
            return self.f.const(False, BRIL_BOOL)  # um Int ou Bool nunca é void
        return self.f.op("eq", valor, self.f.const(0, BRIL_INT), tipo=BRIL_BOOL)

    def gerar_binary(self, expr: BinaryOp) -> str:
        esquerda = self.gerar(expr.left)
        direita = self.gerar(expr.right)

        if expr.operator == "=":
            return self._igualdade(esquerda, direita, self.tipo_de(expr.left))

        if expr.operator == "/":                   # a nossa mensagem, não a do brili
            self.f.call("rt_checar_divisor", HEAP, direita,
                        self.f.const(expr.line, BRIL_INT))
        opcode, tipo = OPERADORES_DIRETOS[expr.operator]
        return self.f.op(opcode, esquerda, direita, tipo=tipo)

    def _igualdade(self, a: str, b: str, tipo: str) -> str:
        """A etapa 19 garante: se um lado é Int, String ou Bool, o outro também."""
        if tipo == INT:
            return self.f.op("eq", a, b, tipo=BRIL_BOOL)
        if tipo == BOOL:                           # o eq da Bril só compara int:
            ambos = self.f.op("and", a, b, tipo=BRIL_BOOL)          # a = b  é
            algum = self.f.op("or", a, b, tipo=BRIL_BOOL)           # (a e b) ou
            nenhum = self.f.op("not", algum, tipo=BRIL_BOOL)        # (nem a nem b)
            return self.f.op("or", ambos, nenhum, tipo=BRIL_BOOL)
        return self.f.call("rt_igual", HEAP, a, b, tipo=BRIL_BOOL)  # endereços
