-- Geracao de codigo: case, empacotamento (boxing) de Int e Bool, e a escolha
-- do ramo do ancestral mais proximo.
--
-- Rode com:
--   python -m cool_compiler.main --fase executar cool_compiler/examples/geracao_case.cl

class Animal { som() : String { "..." }; };
class Cachorro inherits Animal { som() : String { "au au" }; };
class Filhote inherits Cachorro { som() : String { "ai ai" }; };
class Gato inherits Animal { som() : String { "miau" }; };

class Main inherits IO {

    linha(s : String) : SELF_TYPE { out_string(s).out_string("\n") };

    -- Vence o ramo do ancestral MAIS PROXIMO da classe real, qualquer que
    -- seja a ordem em que os ramos foram escritos: Object vem primeiro aqui,
    -- mas so e escolhido quando nenhum outro serve.
    classificar(x : Object) : String {
        case x of
            o : Object => "um Object qualquer";
            a : Animal => "um Animal que faz ".concat(a.som());
            c : Cachorro => "um Cachorro que faz ".concat(c.som());
            n : Int => "o Int ".concat(if n < 0 then "negativo" else "nao negativo" fi);
            s : String => "a String \"".concat(s).concat("\"");
            b : Bool => if b then "o Bool true" else "o Bool false" fi;
        esac
    };

    main() : Object {
        {
            linha(classificar(new Animal));      -- um Animal que faz ...
            linha(classificar(new Cachorro));    -- um Cachorro que faz au au
            linha(classificar(new Filhote));     -- um Cachorro que faz ai ai
            linha(classificar(new Gato));        -- um Animal que faz miau
            linha(classificar(42));              -- o Int nao negativo: 42 foi empacotado
            linha(classificar(~3));              -- o Int negativo
            linha(classificar("oi"));            -- a String "oi"
            linha(classificar(true));            -- o Bool true
            linha(classificar(new IO));          -- um Object qualquer
            linha(classificar(self));            -- um Object qualquer: Main herda de IO

            -- Um case de Int: o ramo recebe o valor desempacotado e o resultado
            -- (Int nos dois ramos) volta a ser um Int comum.
            out_int(case 5 of i : Int => i + 1; o : Object => 0; esac).out_string("\n");  -- 6

            -- Um Int guardado numa variavel Object continua sendo um Int.
            let o : Object <- 7 in
                out_int(case o of i : Int => i * 2; x : Object => 0; esac).out_string("\n");  -- 14
        }
    };
};
