-- Geracao de codigo: SELF_TYPE (retornos e new SELF_TYPE), copy e type_name.
--
-- Rode com:
--   python -m cool_compiler.main --fase executar cool_compiler/examples/geracao_self_type.cl

class Ponto {
    x : Int;
    y : Int;

    mover(dx : Int, dy : Int) : SELF_TYPE {
        {
            x <- x + dx;
            y <- y + dy;
            self;
        }
    };

    x() : Int { x };

    -- new SELF_TYPE cria um objeto da classe REAL de self, que pode ser uma
    -- subclasse de Ponto. So se sabe qual rodando: o codigo le a tag de self.
    vazio_do_mesmo_tipo() : SELF_TYPE { new SELF_TYPE };

    -- type_name() tambem olha a classe real.
    descrever() : String { type_name() };
};

class PontoColorido inherits Ponto {
    cor : String <- "azul";

    cor() : String { cor };

    pintar(c : String) : SELF_TYPE {
        {
            cor <- c;
            self;
        }
    };
};

class Main inherits IO {

    linha(s : String) : SELF_TYPE { out_string(s).out_string("\n") };
    numero(n : Int) : SELF_TYPE { out_int(n).out_string("\n") };

    main() : Object {
        -- mover() devolve SELF_TYPE: chamado num PontoColorido, devolve um PontoColorido
        let p : PontoColorido <- new PontoColorido.mover(1, 2), q : PontoColorido in
            {
                linha(p.pintar("verde").cor());                 -- verde
                linha(p.descrever());                           -- PontoColorido
                linha(p.vazio_do_mesmo_tipo().descrever());     -- PontoColorido
                linha(p.vazio_do_mesmo_tipo().cor());           -- azul: objeto novo, com o inicializador
                linha(new Ponto.vazio_do_mesmo_tipo().descrever());  -- Ponto

                -- copy() e uma copia rasa: mexer na copia nao mexe no original
                q <- p.copy();
                q.mover(10, 10).pintar("vermelho");
                numero(p.x());                                  -- 1
                numero(q.x());                                  -- 11
                linha(p.cor());                                 -- verde
                linha(q.cor());                                 -- vermelho

                -- type_name nas classes basicas
                linha(5.type_name());                           -- Int
                linha(true.type_name());                        -- Bool
                linha("texto".type_name());                     -- String
                linha(self.type_name());                        -- Main
                linha((new Object).type_name());                -- Object
                let o : Object <- 7 in linha(o.type_name());    -- Int: o 7 empacotado tem a tag de Int

                numero(5.copy() + 1);                           -- 6
                linha("abc".copy().concat("!"));                -- abc!
            }
    };
};
