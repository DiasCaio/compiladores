"""Etapa 26: tradução das expressões, parte 2 — new, dispatch e case.

São as expressões que dependem da classe REAL de um objeto, que só se sabe
rodando. A Bril não tem ponteiro de função nem tabela de métodos, então a
classe real é lida da tag (posição 0 do objeto) e decidida com comparações:

    dispatch dinâmico   x.som()        @despachar_Animal.som (etapa 27) testa a tag
    dispatch estático   x@Animal.som() chamada direta a @Animal.som
    case                case x of ...  testa a tag contra a faixa de cada ramo
"""

from ..semantico.etapa14_tipos_basicos import (
    BOOL, INT, IO, OBJECT, SELF_TYPE, STRING,
)
from ..semantico.etapa15_tabela_de_classes import MethodSignature
from ..sintatico.etapa6_ast import Case, Dispatch, Expr, New, StaticDispatch
from .etapa21_bril import BOOL as BRIL_BOOL
from .etapa21_bril import HEAP, INT as BRIL_INT
from .etapa22_layout import (
    TAG, eh_primitivo, funcao_despachante, funcao_metodo, funcao_novo, tipo_bril,
)
from .etapa25_gerador_expr import GeradorDeExpressoes

# Métodos de IO que, na Bril, não têm de onde ler (etapa 24)
METODOS_DE_ENTRADA = {"in_string", "in_int"}


class GeradorDeChamadas(GeradorDeExpressoes):
    """Acrescenta new, os três tipos de dispatch e o case."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.avisos: list[str] = []        # usos de in_int/in_string

    # ----------------------------------------------------------------------
    # 1. new
    # ----------------------------------------------------------------------

    def gerar_new(self, expr: New) -> str:
        if expr.type_name == SELF_TYPE:
            # A classe de self só se sabe rodando: a tag dele escolhe o _novo
            tag = self.f.ler("self", TAG)
            return self.f.call("rt_novo_por_tag", HEAP, tag, tipo=BRIL_INT)
        if expr.type_name in (INT, BOOL, STRING):
            return self.valor_padrao(expr.type_name)   # new Int é 0, new String é ""
        return self.f.call(funcao_novo(expr.type_name), HEAP, tipo=BRIL_INT)

    # ----------------------------------------------------------------------
    # 2. Dispatch
    # ----------------------------------------------------------------------
    # Ordem do manual de COOL: primeiro os argumentos, da esquerda para a
    # direita; só depois a expressão antes do ponto; e por fim o teste de void.

    def gerar_dispatch(self, expr: Dispatch) -> str:
        """alvo.metodo(args), ou metodo(args), que é self.metodo(args)."""
        classe = (self.classe_atual if expr.target is None
                  else self.tipo_de(expr.target))
        assinatura = self.ambiente.lookup_method(classe, expr.method)
        argumentos = self._gerar_argumentos(expr.args, assinatura)

        if expr.target is None:                    # self nunca é void: sem teste
            return self._chamar_despachante("self", classe, expr.method,
                                             argumentos, assinatura, expr.line)

        alvo = self.gerar(expr.target)
        if self.layout.despacho_e_estatico(classe):
            # Int, Bool e String não têm subclasses: já se sabe qual método roda
            return self._chamar_direto(alvo, classe, classe, expr.method,
                                       argumentos, assinatura, expr.line)

        self._checar_void(alvo, "dispatch em void", expr.line)
        return self._chamar_despachante(alvo, classe, expr.method,
                                        argumentos, assinatura, expr.line)

    def gerar_static_dispatch(self, expr: StaticDispatch) -> str:
        """alvo@Tipo.metodo(args): a versão de Tipo, sem olhar a classe real."""
        assinatura = self.ambiente.lookup_method(expr.type_name, expr.method)
        argumentos = self._gerar_argumentos(expr.args, assinatura)
        alvo = self.gerar(expr.target)
        return self._chamar_direto(alvo, self.tipo_de(expr.target), expr.type_name,
                                   expr.method, argumentos, assinatura, expr.line)

    def _gerar_argumentos(self, args: list[Expr],
                          assinatura: MethodSignature) -> list[str]:
        """Gera cada argumento e já o converte para o tipo do parâmetro."""
        valores = []
        for arg, (_, tipo_param) in zip(args, assinatura.params):
            valores.append(self.converter(self.gerar(arg), self.tipo_de(arg), tipo_param))
        return valores

    def _chamar_despachante(self, alvo: str, classe: str, metodo: str,
                            argumentos: list[str], assinatura: MethodSignature,
                            linha: int) -> str:
        raiz = self.layout.raiz_da_familia(classe, metodo)
        if raiz == IO and metodo in METODOS_DE_ENTRADA:
            self._avisar_entrada(metodo, linha)
        return self.f.call(funcao_despachante(raiz, metodo), HEAP, alvo, *argumentos,
                           tipo=tipo_bril(assinatura.return_type))

    def _chamar_direto(self, alvo: str, tipo_alvo: str, classe: str, metodo: str,
                       argumentos: list[str], assinatura: MethodSignature,
                       linha: int) -> str:
        """Chama a implementação que `classe` enxerga, sem despachante."""
        if eh_primitivo(tipo_alvo):
            if metodo == "copy":
                return alvo                        # Int e Bool são valores: a cópia é ele mesmo
            # abort e type_name são de Object e esperam um objeto com tag
            alvo = self.converter(alvo, tipo_alvo, OBJECT)
        else:
            self._checar_void(alvo, "dispatch em void", linha)

        funcao = self.layout.implementacao(classe, metodo)
        if funcao in (funcao_metodo(IO, m) for m in METODOS_DE_ENTRADA):
            self._avisar_entrada(metodo, linha)
        return self.f.call(funcao, HEAP, alvo, *argumentos,
                           tipo=tipo_bril(assinatura.return_type))

    def _checar_void(self, valor: str, mensagem: str, linha: int) -> None:
        self.f.call("rt_checar_void", HEAP, valor,
                    self.f.const(self.dados.endereco(mensagem), BRIL_INT),
                    self.f.const(linha, BRIL_INT))

    def _avisar_entrada(self, metodo: str, linha: int) -> None:
        padrao = '""' if metodo == "in_string" else "0"
        self.avisos.append(f"linha {linha}: {metodo}() nao le entrada na Bril; "
                           f"sempre devolve {padrao}")

    # ----------------------------------------------------------------------
    # 3. case
    # ----------------------------------------------------------------------

    def gerar_case(self, expr: Case) -> str:
        """Escolhe o ramo do ancestral MAIS PRÓXIMO da classe real.

        Os ramos são testados do mais fundo na herança para o mais raso: se x
        é um Cachorro e há ramos para Animal e Cachorro, o de Cachorro é
        testado primeiro e vence. Cada teste é "tag dentro da faixa da classe"
        (etapa 22), que já cobre todas as subclasses dela.
        """
        valor = self.gerar(expr.expression)
        objeto = self.converter(valor, self.tipo_de(expr.expression), OBJECT)
        self._checar_void(objeto, "case em void", expr.line)
        tag = self.f.ler(objeto, TAG)

        tipo = self.tipo_de(expr)
        resultado = self.f.temp()
        fim = self.f.rotulo("esac")
        ramos = sorted(expr.branches,
                       key=lambda ramo: -self.layout.classes[ramo.type_name].profundidade)

        for ramo in ramos:
            escolhido, proximo = self.f.rotulo("ramo"), self.f.rotulo("proximo")
            self.f.br(self._tag_na_faixa(tag, ramo.type_name), escolhido, proximo)
            self.f.label(escolhido)
            with self.escopo():
                nome = self.declarar(ramo.name, ramo.type_name)
                # O ramo `n : Int` recebe o valor desempacotado, não o objeto
                self.f.id(self.converter(objeto, OBJECT, ramo.type_name),
                          tipo_bril(ramo.type_name), dest=nome)
                corpo = self.gerar(ramo.body)
                self.f.id(self.converter(corpo, self.tipo_de(ramo.body), tipo),
                          tipo_bril(tipo), dest=resultado)
            self.f.jmp(fim)
            self.f.label(proximo)

        self._erro_sem_ramo(objeto, expr.line)
        self.f.jmp(fim)
        self.f.label(fim)
        return resultado

    def _tag_na_faixa(self, tag: str, classe: str) -> str:
        """tag_da_classe <= tag <= ultima_tag_dos_descendentes"""
        faixa = self.layout.classes[classe]
        acima = self.f.op("ge", tag, self.f.const(faixa.tag, BRIL_INT), tipo=BRIL_BOOL)
        abaixo = self.f.op("le", tag, self.f.const(faixa.ultima_tag, BRIL_INT),
                           tipo=BRIL_BOOL)
        return self.f.op("and", acima, abaixo, tipo=BRIL_BOOL)

    def _erro_sem_ramo(self, objeto: str, linha: int) -> None:
        """Nenhum ramo aceitou: a mensagem diz a classe real do valor."""
        nome = self.f.call(funcao_metodo(OBJECT, "type_name"), HEAP, objeto, tipo=BRIL_INT)
        prefixo = self.f.const(self.dados.endereco("case sem ramo para a classe "), BRIL_INT)
        mensagem = self.f.call(funcao_metodo(STRING, "concat"), HEAP, prefixo, nome,
                               tipo=BRIL_INT)
        self.f.call("rt_erro", HEAP, mensagem, self.f.const(linha, BRIL_INT))
