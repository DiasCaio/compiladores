"""Etapa 21: construtor de Bril, o "montador" das etapas seguintes.

Uma função Bril é uma lista de instruções em JSON. Escrever esses dicionários
à mão em cada etapa seria repetitivo e fácil de errar, então esta etapa
oferece um FunctionBuilder: cada método emite UMA instrução e devolve o nome
da variável que recebeu o resultado.

    f = FunctionBuilder("dobro", [("x", INT)], INT)
    dois = f.const(2, INT)              t1: int = const 2;
    r = f.op("mul", "x", dois)          t2: int = mul x t1;
    f.ret(r)                            ret t2;

No fim há o formatador de TEXTO, no mesmo formato do bril2txt, para que o
programa gerado possa ser lido (e reconvertido com bril2json).
"""

import json
from typing import Callable, Optional, Union

# --------------------------------------------------------------------------
# 1. Tipos da Bril
# --------------------------------------------------------------------------
# Usamos só três: int (64 bits), bool e ponteiro para int. No JSON o ponteiro
# se escreve {"ptr": "int"}; no texto, ptr<int>.

BrilTipo = Union[str, dict]

INT = "int"
BOOL = "bool"
PTR_INT = {"ptr": "int"}

# O heap é o primeiro argumento de toda função gerada, sempre com este nome
HEAP = "heap"


# --------------------------------------------------------------------------
# 2. Construtor de uma função
# --------------------------------------------------------------------------

class FunctionBuilder:
    """Acumula as instruções de uma função Bril."""

    def __init__(self, nome: str, parametros: list[tuple[str, BrilTipo]],
                 tipo_retorno: Optional[BrilTipo]):
        self.nome = nome                       # sem o @
        self.parametros = parametros           # [(nome, tipo), ...]
        self.tipo_retorno = tipo_retorno       # None: função sem retorno
        self.instrucoes: list[dict] = []
        self._temporarios = 0
        self._rotulos = 0

    # ---- 1. Nomes novos ---------------------------------------------------
    # Temporários e rótulos são numerados por função: t1, t2, ... e
    # senao.1, fim.2, ... O número garante que nunca se repetem.

    def temp(self) -> str:
        self._temporarios += 1
        return f"t{self._temporarios}"

    def rotulo(self, prefixo: str) -> str:
        self._rotulos += 1
        return f"{prefixo}.{self._rotulos}"

    # ---- 2. Instruções que produzem valor --------------------------------
    # `dest` é opcional: sem ele, nasce um temporário novo. Com ele, a
    # instrução escreve numa variável que já existe (um let, um laço).

    def const(self, valor: Union[int, bool], tipo: BrilTipo,
              dest: Optional[str] = None) -> str:
        dest = dest or self.temp()
        self._emitir({"op": "const", "dest": dest, "type": tipo, "value": valor})
        return dest

    def op(self, opcode: str, *args: str, tipo: BrilTipo = INT,
           dest: Optional[str] = None) -> str:
        """add, sub, mul, div, eq, lt, le, gt, ge, not, and, or, id."""
        dest = dest or self.temp()
        self._emitir({"op": opcode, "dest": dest, "type": tipo, "args": list(args)})
        return dest

    def id(self, origem: str, tipo: BrilTipo, dest: Optional[str] = None) -> str:
        """Copia uma variável: dest = id origem."""
        return self.op("id", origem, tipo=tipo, dest=dest)

    def call(self, funcao: str, *args: str, tipo: Optional[BrilTipo] = None,
             dest: Optional[str] = None) -> Optional[str]:
        """Com `tipo`, a chamada produz valor; sem ele, é só efeito."""
        instrucao = {"op": "call", "funcs": [funcao], "args": list(args)}
        if tipo is None:
            self._emitir(instrucao)
            return None
        dest = dest or self.temp()
        self._emitir({**instrucao, "dest": dest, "type": tipo})
        return dest

    # ---- 3. Controle de fluxo --------------------------------------------

    def label(self, rotulo: str) -> None:
        self.instrucoes.append({"label": rotulo})

    def jmp(self, rotulo: str) -> None:
        self._emitir({"op": "jmp", "labels": [rotulo]})

    def br(self, condicao: str, se_verdade: str, se_falso: str) -> None:
        self._emitir({"op": "br", "args": [condicao], "labels": [se_verdade, se_falso]})

    def ret(self, valor: Optional[str] = None) -> None:
        self._emitir({"op": "ret", "args": [valor] if valor else []})

    def print(self, *args: str) -> None:
        self._emitir({"op": "print", "args": list(args)})

    # ---- 4. Memória (extensão memory da Bril) ----------------------------

    def alloc(self, quantidade: str, dest: Optional[str] = None) -> str:
        dest = dest or self.temp()
        self._emitir({"op": "alloc", "dest": dest, "type": PTR_INT,
                      "args": [quantidade]})
        return dest

    def free(self, ponteiro: str) -> None:
        self._emitir({"op": "free", "args": [ponteiro]})

    def ptradd(self, ponteiro: str, deslocamento: str,
               dest: Optional[str] = None) -> str:
        dest = dest or self.temp()
        self._emitir({"op": "ptradd", "dest": dest, "type": PTR_INT,
                      "args": [ponteiro, deslocamento]})
        return dest

    def load(self, ponteiro: str) -> str:
        dest = self.temp()
        self._emitir({"op": "load", "dest": dest, "type": INT, "args": [ponteiro]})
        return dest

    def store(self, ponteiro: str, valor: str) -> None:
        self._emitir({"op": "store", "args": [ponteiro, valor]})

    # ---- 5. Atalhos sobre o heap ------------------------------------------
    # Todo objeto mora no vetor `heap`, e um "endereço" é um ÍNDICE nele. Ler
    # o campo k de um objeto é, então, sempre a mesma receita de três passos:
    #     posição = endereço + k     p = ptradd heap posição     load p

    def endereco(self, base: str, deslocamento: int) -> str:
        """Variável com base + deslocamento (sem instrução se for 0)."""
        if deslocamento == 0:
            return base
        return self.op("add", base, self.const(deslocamento, INT))

    def ler(self, base: str, deslocamento: int = 0) -> str:
        """heap[base + deslocamento]"""
        posicao = self.endereco(base, deslocamento)
        return self.load(self.ptradd(HEAP, posicao))

    def escrever(self, base: str, deslocamento: int, valor: str) -> None:
        """heap[base + deslocamento] = valor"""
        posicao = self.endereco(base, deslocamento)
        self.store(self.ptradd(HEAP, posicao), valor)

    # ---- 6. Estruturas prontas -------------------------------------------

    def laco_contado(self, limite: str, corpo: Callable[[str], None]) -> None:
        """for (i = 0; i < limite; i++) corpo(i)

        O runtime percorre caracteres e campos o tempo todo; montar o laço
        num lugar só evita repetir os mesmos rótulos em cada função.
        """
        i = self.const(0, INT)
        um = self.const(1, INT)
        teste, miolo, fim = (self.rotulo("laco"), self.rotulo("corpo"),
                             self.rotulo("fim_laco"))
        self.label(teste)
        self.br(self.op("lt", i, limite, tipo=BOOL), miolo, fim)
        self.label(miolo)
        corpo(i)
        self.op("add", i, um, dest=i)
        self.jmp(teste)
        self.label(fim)

    def se(self, condicao: str, corpo: Callable[[], None]) -> None:
        """if (condicao) corpo(), sem else: o caminho falso pula o corpo."""
        entao, segue = self.rotulo("entao"), self.rotulo("segue")
        self.br(condicao, entao, segue)
        self.label(entao)
        corpo()
        self.label(segue)

    # ---- 7. Saída ---------------------------------------------------------

    def _emitir(self, instrucao: dict) -> None:
        self.instrucoes.append(instrucao)

    def to_json(self) -> dict:
        funcao: dict = {"name": self.nome}
        if self.parametros:
            funcao["args"] = [{"name": nome, "type": tipo}
                              for nome, tipo in self.parametros]
        if self.tipo_retorno is not None:
            funcao["type"] = self.tipo_retorno
        funcao["instrs"] = self.instrucoes
        return funcao


def programa_json(funcoes: list[FunctionBuilder]) -> dict:
    """O programa Bril completo: {"functions": [...]}"""
    return {"functions": [funcao.to_json() for funcao in funcoes]}


# --------------------------------------------------------------------------
# 3. Formatadores: JSON legível e texto (o mesmo formato do bril2txt)
# --------------------------------------------------------------------------
# O JSON é o formato oficial, mas ninguém lê JSON com prazer. O texto
# reproduz as regras do bril2txt: "dest: tipo = op @funcs args .rotulos;".

def _tipo_texto(tipo: BrilTipo) -> str:
    if isinstance(tipo, dict):                    # {"ptr": "int"} -> ptr<int>
        chave, valor = next(iter(tipo.items()))
        return f"{chave}<{_tipo_texto(valor)}>"
    return tipo


def _instrucao_texto(instr: dict) -> str:
    if instr["op"] == "const":
        valor = str(instr["value"]).lower()      # True -> true
        return f"{instr['dest']}: {_tipo_texto(instr['type'])} = const {valor}"

    partes = [instr["op"]]
    partes += [f"@{funcao}" for funcao in instr.get("funcs", [])]
    partes += instr.get("args", [])
    partes += [f".{rotulo}" for rotulo in instr.get("labels", [])]
    lado_direito = " ".join(partes)

    if "dest" in instr:
        return f"{instr['dest']}: {_tipo_texto(instr['type'])} = {lado_direito}"
    return lado_direito


def formatar_json(programa: dict) -> str:
    """JSON válido, mas com UMA instrução por linha.

    O json.dumps com indent espalharia cada instrução por quatro ou cinco
    linhas; assim o arquivo continua legível e o brili lê do mesmo jeito.
    """
    funcoes = programa["functions"]
    linhas = ['{"functions": [']
    for posicao, funcao in enumerate(funcoes):
        cabecalho = json.dumps({chave: valor for chave, valor in funcao.items()
                                if chave != "instrs"})
        linhas.append(f'  {cabecalho[:-1]}, "instrs": [')        # tira o } final
        instrucoes = funcao["instrs"]
        for indice, instr in enumerate(instrucoes):
            virgula = "," if indice < len(instrucoes) - 1 else ""
            linhas.append(f"    {json.dumps(instr)}{virgula}")
        linhas.append("  ]}" + ("," if posicao < len(funcoes) - 1 else ""))
    linhas.append("]}")
    return "\n".join(linhas)


def formatar_texto(programa: dict) -> str:
    linhas: list[str] = []
    for funcao in programa["functions"]:
        args = funcao.get("args", [])
        parametros = ("(" + ", ".join(f"{a['name']}: {_tipo_texto(a['type'])}"
                                      for a in args) + ")") if args else ""
        retorno = f": {_tipo_texto(funcao['type'])}" if "type" in funcao else ""
        linhas.append(f"@{funcao['name']}{parametros}{retorno} {{")
        for instr in funcao["instrs"]:
            if "label" in instr:
                linhas.append(f".{instr['label']}:")
            else:
                linhas.append(f"  {_instrucao_texto(instr)};")
        linhas.append("}")
    return "\n".join(linhas)
