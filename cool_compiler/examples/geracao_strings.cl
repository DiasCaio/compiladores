-- Geracao de codigo: literais, out_string, length, concat, substr e o '='
-- entre Strings.
--
-- Rode com:
--   python -m cool_compiler.main --fase executar cool_compiler/examples/geracao_strings.cl

class Main inherits IO {

    linha(s : String) : SELF_TYPE { out_string(s).out_string("\n") };
    numero(n : Int) : SELF_TYPE { out_int(n).out_string("\n") };
    booleano(b : Bool) : SELF_TYPE { linha(if b then "true" else "false" fi) };

    -- Inverte uma String, um caractere de cada vez.
    inverter(s : String) : String {
        let resultado : String <- "", i : Int <- s.length() in
            {
                while 0 < i loop
                    {
                        i <- i - 1;
                        resultado <- resultado.concat(s.substr(i, 1));
                    }
                pool;
                resultado;
            }
    };

    main() : Object {
        let s : String <- "Hello", vazia : String in
            {
                linha(s);                                   -- Hello
                numero(s.length());                         -- 5
                numero(vazia.length());                     -- 0: String sem valor e ""
                linha(s.concat(", World").concat("!"));     -- Hello, World!
                linha(s.substr(1, 3));                      -- ell
                linha(s.substr(5, 0).concat("[vazio]"));    -- [vazio]: substr no fim, de tamanho 0
                linha(inverter("roma"));                    -- amor

                -- O '=' compara o CONTEUDO de Strings, nao o endereco.
                booleano(s = "Hello");                      -- true
                booleano(s = "hello");                      -- false
                booleano("Hel".concat("lo") = s);           -- true: objetos diferentes, mesmo texto
                booleano(vazia = "");                       -- true

                out_string("tab:\tfim\n");                  -- o \t vira uma tabulacao
                out_string("aspas: \"ok\"\n");
            }
    };
};
