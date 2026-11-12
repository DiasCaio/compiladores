-- Programa VALIDO que exercita as regras de tipo da fase semantica.
--
-- Rode com a fase semantica (o padrao) e confira, na arvore, o [tipo: ...]
-- que cada expressao recebeu. Os comentarios abaixo dizem o que esperar.

class Animal {

    nome : String <- "animal";

    -- SELF_TYPE no retorno: quem chamar num Cachorro recebe um Cachorro de
    -- volta, e nao um Animal.
    batizar(novo : String) : SELF_TYPE {
        {
            nome <- novo;
            self;            -- self tem tipo SELF_TYPE
        }
    };

    som() : String { "..." };
};

class Cachorro inherits Animal {

    -- Mesma assinatura do pai: sobrescrita valida.
    som() : String { "au au" };

    abanar() : String { "abanando o rabo" };
};

class Gato inherits Animal {
    som() : String { "miau" };
};

class Main inherits IO {

    -- JOIN: os ramos tem tipos diferentes (Cachorro e Gato). O if inteiro
    -- recebe o ancestral comum mais proximo dos dois: Animal.
    escolher(b : Bool) : Animal {
        if b then new Cachorro else new Gato fi
    };

    -- Gracas ao SELF_TYPE de batizar, (new Cachorro).batizar("Rex") tem tipo
    -- Cachorro, e nao Animal. Por isso o abanar() logo depois e aceito.
    batizar_e_abanar() : String {
        (new Cachorro).batizar("Rex").abanar()
    };

    -- O tipo de um case e o join dos corpos dos ramos: aqui todos sao String.
    descrever(a : Animal) : String {
        case a of
            c : Cachorro => "um cachorro";
            g : Gato => "um gato";
            o : Object => "outra coisa";
        esac
    };

    -- ESCOPO: dentro do let, x e a String declarada nele e esconde o
    -- parametro. Fora do let, x volta a ser o parametro Int.
    esconder(x : Int) : Int {
        {
            let x : String <- "texto" in x.length();
            x + 1;
        }
    };

    -- Um while vale sempre Object, qualquer que seja o corpo.
    contar() : Object {
        let i : Int <- 0 in
            while i < 3 loop i <- i + 1 pool
    };

    main() : Object {
        {
            -- out_string devolve SELF_TYPE, o proprio objeto: por isso as
            -- chamadas podem ser encadeadas.
            out_string(escolher(true).som()).out_string("\n");
            out_string(batizar_e_abanar()).out_string("\n");
            out_string(descrever(new Gato)).out_string("\n");
            out_int(esconder(41)).out_string("\n");
        }
    };
};
