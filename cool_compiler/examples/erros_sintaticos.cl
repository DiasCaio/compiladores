-- Erros sintaticos DELIBERADOS, isolados entre codigo valido.
--
-- Este arquivo e para a fase sintatica o que erros_lexicos.cl e para a fase
-- lexica: prova que o parser NAO aborta no primeiro erro. Ele registra o erro,
-- descarta tokens ate um ponto seguro (';', '}' ou 'class') e continua, para
-- que uma unica execucao reporte varios problemas.
--
-- Cada erro esta cercado de codigo valido de proposito: se a recuperacao
-- funciona, o codigo valido aparece na arvore mesmo assim.

class ErrosSintaticos {

    valido_antes : Int <- 1;

    -- ERRO 1: falta o ';' no fim da feature.
    sem_ponto_e_virgula : Int <- 2

    valido_no_meio : Int <- 3;

    -- ERRO 2: o 'if' ficou sem o 'fi' que o fecha.
    if_sem_fi() : Int {
        if valido_antes < 10 then 1 else 2
    };

    -- ERRO 3: falta o ')' que fecha a lista de argumentos.
    parentese_faltando() : Object {
        abs(valido_antes
    };

    -- ERRO 4: comparadores encadeados. Em COOL '<' e NAO associativo, entao
    -- a < b < c nao tem leitura definida.
    comparacao_encadeada() : Bool {
        valido_antes < valido_no_meio < 10
    };

    -- ERRO 5: o 'let' ficou sem o 'in'.
    let_sem_in() : Int {
        let x : Int <- 1 x + 1
    };

    valido_depois : Int <- 4;
};

-- A classe seguinte e inteira valida: se ela aparecer na arvore, a recuperacao
-- sobreviveu a todos os erros acima.
class DepoisDosErros inherits IO {
    ok() : String { "cheguei ate aqui" };
};
