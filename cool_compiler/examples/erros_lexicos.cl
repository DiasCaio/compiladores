-- Este arquivo contem erros lexicos DE PROPOSITO, para testar os tokens ERROR.
-- Cada erro fica isolado, cercado de codigo valido, para provar que o lexer
-- se recupera e continua escaneando o resto do arquivo normalmente.

class ErrosLexicos {
    a : Int <- 1 & 2;      -- '&' nao existe em COOL -> ERROR de caractere invalido

    b : Int <- 3;
};

*)                          -- fechamento de comentario sem abertura -> ERROR

class MaisErros {
    d : String <- "esqueci de fechar;

    e : Int <- 5;
};
