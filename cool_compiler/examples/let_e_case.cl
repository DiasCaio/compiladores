-- Exercita let e case.
--
-- O ponto mais interessante esta na regra do let: "o corpo de um let se
-- estende o MAXIMO possivel". Em um gerador LALR isso e um conflito
-- shift/reduce que precisa ser resolvido a mao; em descida recursiva sai de
-- graca, porque o corpo e lido por uma chamada que consome tudo que conseguir.
-- Confira na arvore quem ficou DENTRO do corpo do let.

class LetECase inherits IO {

    -- O '+ 1' esta DENTRO do corpo do let, nao depois dele.
    let_guloso() : Int {
        let x : Int <- 1 in x + 1
    };

    -- Aqui o '* 2' tambem esta dentro do let: 1 + (let x in (x * 2)).
    -- Para somar antes seriam necessarios parenteses.
    let_dentro_de_expressao() : Int {
        1 + let x : Int in x * 2
    };

    -- Varios bindings de uma vez. Na arvore eles viram Let ANINHADOS, um por
    -- binding: e assim que o escopo de cada um fica sendo o corpo do seu Let.
    let_multiplo() : Int {
        let a : Int <- 1, b : Int <- 2, c : Int in a + b
    };

    -- let dentro de let, escrito a mao.
    let_aninhado() : Int {
        let externo : Int <- 1 in
            let interno : Int <- externo + 1 in
                externo + interno
    };

    -- case escolhe o ramo pelo tipo do valor em tempo de execucao.
    -- Cada ramo termina com ';', inclusive o ultimo.
    descrever(item : Object) : String {
        case item of
            n : Int => "e um inteiro";
            s : String => "e uma string";
            b : Bool => "e um booleano";
            o : Object => "e outra coisa";
        esac
    };

    -- case dentro de um ramo de case.
    case_aninhado(item : Object) : String {
        case item of
            n : Int =>
                case item of
                    m : Int => "inteiro por dentro e por fora";
                    o : Object => "nunca chega aqui";
                esac;
            o : Object => "nao e inteiro";
        esac
    };

    -- let cujo corpo e um case.
    let_com_case(item : Object) : String {
        let rotulo : String <- "?" in
            case item of
                n : Int => "inteiro";
                o : Object => rotulo;
            esac
    };
};
