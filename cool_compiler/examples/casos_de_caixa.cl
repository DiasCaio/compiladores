-- Este arquivo testa as regras de maiusculas/minusculas do lexico de COOL.
-- Palavras-chave normais sao totalmente case-insensitive:
-- class / Class / CLASS / cLaSs sao sempre reconhecidas como o mesmo token CLASS.

class CasosDeCaixa {
    a : Bool <- true;      -- comeca minuscula -> BOOL_CONST
    b : Bool <- tRue;      -- comeca minuscula -> BOOL_CONST (letras seguintes podem variar)
    c : Bool <- False;     -- comeca MAIUSCULA -> NAO e booleano, vira TYPEID
    d : Bool <- TRUE;      -- comeca MAIUSCULA -> NAO e booleano, vira TYPEID

    ExemploDeTipo : Int <- 1;       -- identificador comecando com maiuscula -> TYPEID
    exemploDeVariavel : Int <- 2;   -- identificador comecando com minuscula -> OBJECTID
};

Class OutroJeitoDeEscrever inherits IO {
};

CLASS TerceiroJeito inherits IO {
};
