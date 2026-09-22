-- Exercita a tabela de precedencia e a associatividade dos operadores.
--
-- Este arquivo testa o FORMATO da arvore, nao os tipos: a verificacao de tipos
-- e assunto da fase semantica, que ainda nao existe. Para conferir, olhe quem
-- ficou MAIS FUNDO no desenho: quem esta mais fundo foi agrupado primeiro, ou
-- seja, liga mais forte.

class Precedencia inherits IO {

    a : Int <- 1;
    b : Int <- 2;
    c : Int <- 3;

    -- * e / ligam mais forte que + e -   ->  1 + (2 * 3) - (4 / 2)
    aritmetica() : Int { 1 + 2 * 3 - 4 / 2 };

    -- - e associativo a esquerda         ->  (1 - 2) - 3
    associatividade_esquerda() : Int { 1 - 2 - 3 };

    -- a comparacao e mais fraca que a aritmetica  ->  (1 + 2) < (3 * 4)
    comparacao() : Bool { 1 + 2 < 3 * 4 };

    -- not e mais fraco que a comparacao  ->  not (a < b)
    negacao_booleana() : Bool { not a < b };

    -- ~ e mais forte que *               ->  (~a) * b
    negacao_aritmetica() : Int { ~a * b };

    -- isvoid e mais forte que =          ->  (isvoid a) = false
    vazio() : Bool { isvoid a = false };

    -- <- e o operador MAIS FRACO         ->  a <- (b + c)
    atribuicao() : Int { a <- b + c };

    -- <- e associativo a direita         ->  a <- (b <- c)
    atribuicao_encadeada() : Int { a <- b <- c };

    -- os parenteses mudam o agrupamento  ->  (1 + 2) * 3
    parenteses() : Int { (1 + 2) * 3 };

    -- . liga mais forte que +            ->  a + (self.aritmetica())
    dispatch_e_soma() : Int { a + self.aritmetica() };

    -- @ escolhe a versao de um ancestral ->  (self@Precedencia).aritmetica()
    dispatch_estatico() : Int { self@Precedencia.aritmetica() };
};
