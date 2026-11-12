"""Etapa 19 (passada 3): o tipo de cada expressão, uma função por regra de tipo.

O tipo é calculado de baixo para cima: primeiro os filhos, depois o próprio nó.
"""

from typing import Optional

from ..sintatico.etapa6_ast import (
    Assign, BinaryOp, Block, BoolConst, Case, Dispatch, ErrorExpr, Expr, If,
    IntConst, IsVoid, Let, Neg, New, Not, ObjectId, StaticDispatch,
    StringConst, While,
)
from .etapa13_erros_semanticos import ErrorReporter
from .etapa14_tipos_basicos import (
    BOOL, INT, OBJECT, SELF, SELF_TYPE, STRING, TIPO_ERRO,
    TIPOS_COMPARADOS_POR_VALOR, TIPOS_DOS_OPERADORES,
)
from .etapa17_features import FeatureTable
from .etapa18_escopos import SymbolTable


class ExpressionChecker:
    """Verifica os tipos das expressões, consultando a FeatureTable."""

    def __init__(self, ambiente: FeatureTable, relator: ErrorReporter):
        self.ambiente = ambiente            # o que se sabe do programa (etapas 15 a 17)
        self.relator = relator              # caderno de erros (etapa 13)
        self.escopos = SymbolTable()        # nomes visíveis agora (etapa 18)
        self.classe_atual = OBJECT          # classe sendo verificada: a "dona" do SELF_TYPE
        self.types: dict[int, str] = {}     # resultado: id do nó -> tipo

    # ----------------------------------------------------------------------
    # 1. Atalhos usados por todas as regras
    # ----------------------------------------------------------------------

    def error(self, linha: int, mensagem: str) -> None:
        self.relator.report(linha, mensagem)

    def _conforma(self, tipo: str, esperado: str) -> bool:
        return self.ambiente.conforms(tipo, esperado, self.classe_atual)

    def _join(self, a: str, b: str) -> str:
        return self.ambiente.join(a, b, self.classe_atual)

    def _exigir_compativel(self, tipo: str, esperado: str, linha: int,
                           o_que: str, com_o_que: str) -> None:
        """Erro se `tipo` não servir onde se espera `esperado` (subclasse serve)."""
        if not self._conforma(tipo, esperado):
            self.error(linha, f"{o_que} tem tipo {tipo}, que nao e compativel "
                              f"com {com_o_que}")

    def _exigir(self, tipo: str, esperado: str, linha: int, o_que: str) -> None:
        """Erro se `tipo` não for EXATAMENTE `esperado` (para Int e Bool)."""
        if tipo != esperado and tipo != TIPO_ERRO:
            self.error(linha, f"{o_que} precisa ser {esperado}, mas tem tipo {tipo}")

    # ----------------------------------------------------------------------
    # 2. Despacho: escolhe a regra pelo tipo do nó
    # ----------------------------------------------------------------------

    def check(self, expr: Expr) -> str:
        """Porta de entrada única: calcula o tipo, anota e devolve.

            check(a + b * 2)
             +-- check(a)          -> Int
             +-- check(b * 2)
             |     +-- check(b)    -> Int
             |     +-- check(2)    -> Int
             |     regra do *      -> Int
             regra do +            -> Int
        """
        tipo = self._aplicar_regra(expr)    # escolhe e aplica a regra do nó
        self.types[id(expr)] = tipo         # anota: vira o [tipo: ...] da árvore
        return tipo

    def _aplicar_regra(self, expr: Expr) -> str:
        match expr:                         # `case X():` = "expr é um X?" (como isinstance)
            case IntConst():
                return INT
            case StringConst():
                return STRING
            case BoolConst():
                return BOOL
            case ObjectId():
                return self.check_object_id(expr)
            case Assign():
                return self.check_assign(expr)
            case New():
                return self.check_new(expr)
            case Dispatch():
                return self.check_dispatch(expr)
            case StaticDispatch():
                return self.check_static_dispatch(expr)
            case If():
                return self.check_if(expr)
            case While():
                return self.check_while(expr)
            case Block():
                return self.check_block(expr)
            case Let():
                return self.check_let(expr)
            case Case():
                return self.check_case(expr)
            case IsVoid():
                return self.check_isvoid(expr)
            case Not():
                return self.check_not(expr)
            case Neg():
                return self.check_neg(expr)
            case BinaryOp():
                return self.check_binary(expr)
            case ErrorExpr():
                return TIPO_ERRO            # por segurança: a fase só roda sem erro sintático
        return TIPO_ERRO

    # ----------------------------------------------------------------------
    # 3. Nomes e atribuição
    # ----------------------------------------------------------------------

    def check_object_id(self, expr: ObjectId) -> str:
        if expr.name == SELF:
            return SELF_TYPE                       # self: "o tipo de quem executa"

        tipo = self.escopos.lookup(expr.name)      # procura na pilha de escopos
        if tipo is None:
            self.error(expr.line, f"a variavel '{expr.name}' nao foi declarada")
            return TIPO_ERRO                       # coringa: quem está em volta não reclama
        return tipo

    def check_assign(self, expr: Assign) -> str:
        tipo_valor = self.check(expr.value)        # 1) tipo do lado direito

        if expr.name == SELF:                      # 2) self não pode ser trocado
            self.error(expr.line, "nao e possivel atribuir um valor a 'self'")
            return tipo_valor

        tipo_declarado = self.escopos.lookup(expr.name)   # 3) tipo da variável
        if tipo_declarado is None:
            self.error(expr.line, f"a variavel '{expr.name}' nao foi declarada")
            return tipo_valor

        self._exigir_compativel(                   # 4) o valor serve na variável?
            tipo_valor, tipo_declarado, expr.line,
            f"o valor atribuido a '{expr.name}'",
            f"o tipo declarado {tipo_declarado}",
        )
        return tipo_valor                          # vale o tipo do VALOR, não o da variável

    def check_new(self, expr: New) -> str:
        if expr.type_name == SELF_TYPE:
            return SELF_TYPE                       # new SELF_TYPE: mesmo tipo de quem executa
        return self.ambiente.check_declared_type(  # a classe existe?
            expr.type_name, expr.line, allow_self_type=False, descricao="do 'new'",
        )

    # ----------------------------------------------------------------------
    # 4. Chamadas de método (dispatch)
    # ----------------------------------------------------------------------

    def check_dispatch(self, expr: Dispatch) -> str:
        """alvo.metodo(args), ou metodo(args), que é self.metodo(args)."""
        if expr.target is None:
            tipo_alvo = SELF_TYPE                  # sem alvo: é self
        else:
            tipo_alvo = self.check(expr.target)
        tipos_args = [self.check(arg) for arg in expr.args]

        if tipo_alvo == TIPO_ERRO:
            return TIPO_ERRO                       # alvo já deu erro: nem procura o método

        # Onde procurar o método: SELF_TYPE procura na classe atual
        classe_busca = self.classe_atual if tipo_alvo == SELF_TYPE else tipo_alvo
        return self._chamar(classe_busca, expr.method, tipos_args, tipo_alvo, expr.line)

    def check_static_dispatch(self, expr: StaticDispatch) -> str:
        """alvo@Tipo.metodo(args): usa a versão do método de Tipo (como um super)."""
        tipo_alvo = self.check(expr.target)
        tipos_args = [self.check(arg) for arg in expr.args]

        tipo_estatico = self.ambiente.check_declared_type(   # Tipo existe?
            expr.type_name, expr.line, allow_self_type=False,
            descricao="do dispatch estatico",
        )
        if TIPO_ERRO in (tipo_alvo, tipo_estatico):
            return TIPO_ERRO

        self._exigir_compativel(                   # Tipo precisa ser ancestral do alvo
            tipo_alvo, tipo_estatico, expr.line,
            "a expressao antes do '@'",
            f"o tipo {tipo_estatico} pedido no '@'",
        )
        return self._chamar(tipo_estatico, expr.method, tipos_args, tipo_alvo, expr.line)

    def _chamar(self, classe_busca: str, metodo: str, tipos_args: list[str],
                tipo_alvo: str, linha: int) -> str:
        """Comum aos dois dispatches: acha o método, confere os args e dá o tipo."""
        assinatura = self.ambiente.lookup_method(classe_busca, metodo)   # sobe a herança
        if assinatura is None:
            self.error(linha, f"a classe {classe_busca} nao tem um metodo "
                              f"chamado '{metodo}'")
            return TIPO_ERRO

        if len(tipos_args) != len(assinatura.params):      # quantidade de argumentos
            self.error(linha, f"o metodo '{metodo}' recebe "
                              f"{len(assinatura.params)} argumento(s), mas foi "
                              f"chamado com {len(tipos_args)}")
        else:                                              # cada argumento serve no parâmetro?
            for posicao, (tipo_arg, (nome_param, tipo_param)) in enumerate(
                    zip(tipos_args, assinatura.params), start=1):
                self._exigir_compativel(
                    tipo_arg, tipo_param, linha,
                    f"o argumento {posicao} da chamada a '{metodo}'",
                    f"o tipo {tipo_param} do parametro '{nome_param}'",
                )

        if assinatura.return_type == SELF_TYPE:
            return tipo_alvo                       # (new Cachorro).batizar("Rex") -> Cachorro
        return assinatura.return_type

    # ----------------------------------------------------------------------
    # 5. Controle de fluxo
    # ----------------------------------------------------------------------

    def check_if(self, expr: If) -> str:
        self._exigir(self.check(expr.condition), BOOL, expr.line,   # condição é Bool?
                     "a condicao do 'if'")
        tipo_entao = self.check(expr.then_branch)
        tipo_senao = self.check(expr.else_branch)
        return self._join(tipo_entao, tipo_senao)  # pode valer qualquer ramo: ancestral comum

    def check_while(self, expr: While) -> str:
        self._exigir(self.check(expr.condition), BOOL, expr.line,   # condição é Bool?
                     "a condicao do 'while'")
        self.check(expr.body)                      # verifica o corpo, descarta o tipo
        return OBJECT                              # while não produz valor útil

    def check_block(self, expr: Block) -> str:
        tipo = TIPO_ERRO
        for interna in expr.expressions:
            tipo = self.check(interna)
        return tipo                                # vale o tipo da última expressão

    def check_let(self, expr: Let) -> str:
        """let x : T <- inicial in corpo (um binding só: o parser desmembrou os demais)."""
        tipo_declarado = self.ambiente.check_declared_type(   # T existe?
            expr.type_name, expr.line, allow_self_type=True,
            descricao=f"da variavel '{expr.name}' do 'let'",
        )

        # Init checado ANTES de x existir: em `let x <- x + 1`, o x da direita é o de fora
        if expr.init is not None:
            self._exigir_compativel(
                self.check(expr.init), tipo_declarado, expr.line,
                f"a inicializacao de '{expr.name}'",
                f"o tipo declarado {tipo_declarado}",
            )

        if expr.name == SELF:
            self.error(expr.line, "'self' nao pode ser o nome de uma variavel do 'let'")

        with self.escopos.scope():                 # abre o escopo do let
            if expr.name != SELF:
                self.escopos.define(expr.name, tipo_declarado)   # x passa a existir
            return self.check(expr.body)           # o corpo enxerga x; ao sair, x some

    def check_case(self, expr: Case) -> str:
        """case e of x : T => corpo; ... esac. Vale o join de todos os ramos."""
        self.check(expr.expression)                # qualquer tipo serve

        tipos_vistos: set[str] = set()
        resultado: Optional[str] = None

        for ramo in expr.branches:
            tipo_ramo = self.ambiente.check_declared_type(   # T existe? (SELF_TYPE proibido)
                ramo.type_name, ramo.line, allow_self_type=False,
                descricao=f"do ramo '{ramo.name}' do 'case'",
            )

            if tipo_ramo in tipos_vistos:          # mesmo tipo em dois ramos: o 2º nunca roda
                self.error(ramo.line, f"o 'case' tem mais de um ramo para o "
                                      f"tipo {tipo_ramo}")
            elif tipo_ramo != TIPO_ERRO:
                tipos_vistos.add(tipo_ramo)

            if ramo.name == SELF:
                self.error(ramo.line, "'self' nao pode ser o nome da variavel "
                                      "de um ramo do 'case'")

            with self.escopos.scope():             # cada ramo tem seu próprio escopo
                if ramo.name != SELF:
                    self.escopos.define(ramo.name, tipo_ramo)
                tipo_corpo = self.check(ramo.body)

            # Acumula o join: o 1º ramo inicia, os seguintes vão juntando
            resultado = tipo_corpo if resultado is None else self._join(resultado, tipo_corpo)

        return resultado if resultado is not None else TIPO_ERRO

    # ----------------------------------------------------------------------
    # 6. Operadores (devolvem o tipo do resultado mesmo com operando errado)
    # ----------------------------------------------------------------------

    def check_isvoid(self, expr: IsVoid) -> str:
        self.check(expr.operand)                   # qualquer objeto pode ser void
        return BOOL

    def check_not(self, expr: Not) -> str:
        self._exigir(self.check(expr.operand), BOOL, expr.line,
                     "o operando do 'not'")
        return BOOL

    def check_neg(self, expr: Neg) -> str:
        self._exigir(self.check(expr.operand), INT, expr.line,
                     "o operando do '~'")
        return INT

    def check_binary(self, expr: BinaryOp) -> str:
        tipo_esquerda = self.check(expr.left)
        tipo_direita = self.check(expr.right)

        if expr.operator == "=":                   # "=" tem regra própria
            return self._check_igualdade(tipo_esquerda, tipo_direita, expr.line)

        exigido, resultado = TIPOS_DOS_OPERADORES[expr.operator]   # ex.: "<" -> (Int, Bool)
        self._exigir(tipo_esquerda, exigido, expr.line,
                     f"o lado esquerdo do '{expr.operator}'")
        self._exigir(tipo_direita, exigido, expr.line,
                     f"o lado direito do '{expr.operator}'")
        return resultado

    def _check_igualdade(self, esquerda: str, direita: str, linha: int) -> str:
        """a = b: livre para objetos; Int, String e Bool só com o mesmo tipo."""
        if TIPO_ERRO not in (esquerda, direita):
            envolve_valor = (esquerda in TIPOS_COMPARADOS_POR_VALOR      # algum lado é
                             or direita in TIPOS_COMPARADOS_POR_VALOR)   # Int, String ou Bool?
            if envolve_valor and esquerda != direita:
                self.error(linha, f"o '=' so compara Int, String e Bool com um "
                                  f"valor do mesmo tipo; aqui os lados tem tipos "
                                  f"{esquerda} e {direita}")
        return BOOL
