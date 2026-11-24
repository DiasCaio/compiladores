"""Etapa 22: como cada valor de COOL fica guardado na memória da Bril.

Só dados, nenhuma instrução: esta etapa responde perguntas como "qual é a tag
de Cachorro?", "em que posição do objeto fica o atributo nome?" e "quais
classes têm a sua própria versão de som()?". As etapas seguintes consultam
estas respostas na hora de emitir código.
"""

from dataclasses import dataclass

from ..semantico.etapa14_tipos_basicos import BOOL, INT, OBJECT, STRING
from ..semantico.etapa17_features import FeatureTable
from .etapa21_bril import BOOL as BRIL_BOOL
from .etapa21_bril import INT as BRIL_INT
from .etapa21_bril import BrilTipo

# --------------------------------------------------------------------------
# 1. Representação dos valores
# --------------------------------------------------------------------------
# Int e Bool viram os tipos nativos da Bril (int e bool) e passam direto de
# variável para variável. Todo o resto (objetos, String, IO, Object) é um
# int que guarda um ENDEREÇO no heap. O endereço 0 nunca é usado: é o void.

PRIMITIVOS = {INT, BOOL}
VOID = 0


def eh_primitivo(tipo_cool: str) -> bool:
    return tipo_cool in PRIMITIVOS


def tipo_bril(tipo_cool: str) -> BrilTipo:
    """Int -> int, Bool -> bool, qualquer outro (inclusive SELF_TYPE) -> int."""
    return BRIL_BOOL if tipo_cool == BOOL else BRIL_INT


# --------------------------------------------------------------------------
# 2. Formato dos blocos no heap
# --------------------------------------------------------------------------
#   heap[0]                         próximo índice livre (o alocador bump)
#   objeto:      [tag, tamanho, atributo1, atributo2, ...]
#   String:      [tag, tamanho, comprimento, c0, c1, ...]   (códigos dos caracteres)
#   Int/Bool:    [tag, tamanho, valor]                       (empacotados)
# `tamanho` conta o bloco inteiro, cabeçalho incluído: é o que copy() usa.

PROXIMO_LIVRE = 0
TAG = 0
TAMANHO = 1
CABECALHO = 2                 # tag + tamanho
VALOR_EMBALADO = 2            # onde fica o valor de um Int/Bool empacotado
COMPRIMENTO = 2               # onde fica o comprimento de uma String
PRIMEIRO_CHAR = 3             # onde começam os caracteres de uma String


# --------------------------------------------------------------------------
# 3. Nomes das funções geradas
# --------------------------------------------------------------------------
# Métodos usam ponto (Main.main): a Bril aceita '.' em nomes e COOL não, então
# nenhum método colide com outro nem com _novo/_init, mesmo que o usuário
# escreva um método chamado init. Classes começam com maiúscula, então rt_ e
# despachar_ também nunca colidem com nada que venha do programa.

def funcao_metodo(classe: str, metodo: str) -> str:
    return f"{classe}.{metodo}"


def funcao_novo(classe: str) -> str:
    return f"{classe}_novo"


def funcao_init(classe: str) -> str:
    return f"{classe}_init"


def funcao_despachante(raiz: str, metodo: str) -> str:
    return f"despachar_{raiz}.{metodo}"


# --------------------------------------------------------------------------
# 4. O layout de uma classe
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class LayoutDeClasse:
    """Tag, faixa de tags dos descendentes e posição de cada atributo.

    As tags são numeradas em PRÉ-ORDEM na árvore de herança, então os
    descendentes de uma classe ocupam as tags logo depois dela:

        Object 0 ─┬─ IO 1 ── Main 2
                  ├─ Int 3,  String 4,  Bool 5
                  └─ Animal 6 ─┬─ Cachorro 7     Animal: faixa [6, 8]
                               └─ Gato 8         "x é um Animal?" vira
                                                 6 <= tag(x) <= 8
    """

    nome: str
    tag: int
    ultima_tag: int                       # maior tag entre os descendentes
    profundidade: int                     # Object = 0
    atributos: tuple[tuple[str, str], ...]   # (nome, tipo), do pai para o filho

    @property
    def tamanho(self) -> int:
        return CABECALHO + len(self.atributos)

    def offset(self, atributo: str) -> int:
        """Posição do atributo dentro do objeto (depois do cabeçalho)."""
        for posicao, (nome, _) in enumerate(self.atributos):
            if nome == atributo:
                return CABECALHO + posicao
        raise KeyError(atributo)


# --------------------------------------------------------------------------
# 5. O layout do programa inteiro
# --------------------------------------------------------------------------

class Layout:
    """Calcula tags, faixas, atributos e famílias de métodos de todas as classes."""

    def __init__(self, ambiente: FeatureTable):
        self.ambiente = ambiente
        self.classes: dict[str, LayoutDeClasse] = {}

        self._filhos: dict[str, list[str]] = {nome: [] for nome in ambiente.classes}
        for info in ambiente.inheritance_order():          # pais antes dos filhos
            if info.parent is not None:
                self._filhos[info.parent].append(info.name)

        self._numerar(OBJECT, proxima_tag=0, profundidade=0)
        self.familias = self._montar_familias()

    # ---- 1. Tags em pré-ordem --------------------------------------------

    def _numerar(self, nome: str, proxima_tag: int, profundidade: int) -> int:
        """Numera `nome` e seus descendentes; devolve a próxima tag livre."""
        tag = proxima_tag
        proxima_tag += 1
        for filho in self._filhos[nome]:                   # filhos logo depois do pai
            proxima_tag = self._numerar(filho, proxima_tag, profundidade + 1)

        self.classes[nome] = LayoutDeClasse(
            nome, tag, ultima_tag=proxima_tag - 1, profundidade=profundidade,
            atributos=self._atributos_pai_para_filho(nome),
        )
        return proxima_tag

    def _atributos_pai_para_filho(self, nome: str) -> tuple[tuple[str, str], ...]:
        """all_attributes() vem do FILHO para o pai; o objeto precisa do contrário.

        Com os atributos do pai primeiro, um atributo herdado fica na MESMA
        posição no pai e em todos os filhos. É isso que permite a um método de
        Animal ler `nome` sem saber se self é um Cachorro ou um Gato.
        """
        atributos: list[tuple[str, str]] = []
        for ancestral in reversed(self.ambiente.ancestors(nome)):   # Object primeiro
            atributos += self.ambiente.classes[ancestral].attributes.items()
        return tuple(atributos)

    def por_tag(self) -> list[LayoutDeClasse]:
        return sorted(self.classes.values(), key=lambda classe: classe.tag)

    # ---- 2. Famílias de métodos ------------------------------------------
    # Uma família é um nome de método mais a classe RAIZ que o introduziu:
    # som() de Animal, sobrescrito em Cachorro e Filhote, é a família
    # (Animal, som). Como a sobrescrita em COOL mantém a assinatura, todos os
    # membros da família recebem e devolvem os mesmos tipos.

    def raiz_da_familia(self, classe: str, metodo: str) -> str:
        """O ancestral mais alto de `classe` que declara `metodo`."""
        declaram = [ancestral for ancestral in self.ambiente.ancestors(classe)
                    if metodo in self.ambiente.classes[ancestral].methods]
        return declaram[-1]                                # o último é o mais alto

    def _montar_familias(self) -> dict[tuple[str, str], list[LayoutDeClasse]]:
        """(raiz, método) -> classes que escrevem uma versão própria, da mais
        funda para a mais rasa. Testar nessa ordem garante que a versão mais
        específica vence, como no case."""
        familias: dict[tuple[str, str], list[LayoutDeClasse]] = {}
        for info in self.ambiente.classes.values():
            for metodo in info.methods:                    # só os declarados nela
                chave = (self.raiz_da_familia(info.name, metodo), metodo)
                familias.setdefault(chave, []).append(self.classes[info.name])

        for definidores in familias.values():
            definidores.sort(key=lambda classe: -classe.profundidade)
        return familias

    def implementacao(self, classe: str, metodo: str) -> str:
        """A função que roda quando `metodo` é chamado num objeto de `classe`."""
        assinatura = self.ambiente.lookup_method(classe, metodo)
        return funcao_metodo(assinatura.defined_in, metodo)

    def despacho_e_estatico(self, tipo: str) -> bool:
        """Int, Bool e String não têm subclasses: a classe real é a estática."""
        return tipo in (INT, BOOL, STRING)
