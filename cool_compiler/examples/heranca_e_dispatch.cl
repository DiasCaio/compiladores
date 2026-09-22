-- Exercita heranca e as tres formas de chamar um metodo em COOL.
--
--   alvo.metodo(args)        dispatch comum: usa a versao mais especifica
--   alvo@Tipo.metodo(args)   dispatch estatico: forca a versao de um ANCESTRAL
--   metodo(args)             dispatch implicito: o alvo e o self, subentendido
--
-- Na arvore, o dispatch implicito aparece marcado como "(implicito)", e nao
-- tem filho "alvo": guardamos o que estava escrito, sem inventar um self.

class Animal {

    nome : String <- "animal";

    -- SELF_TYPE como tipo de retorno: "devolve um objeto do MESMO tipo de
    -- quem recebeu a chamada", nao necessariamente um Animal.
    batizar(novo : String) : SELF_TYPE {
        {
            nome <- novo;
            self;
        }
    };

    som() : String { "algum som" };

    -- Dispatch IMPLICITO: som() em vez de self.som().
    descrever() : String { som() };
};

class Cachorro inherits Animal {

    -- Sobrescreve o metodo do pai.
    som() : String { "au au" };

    -- Dispatch ESTATICO: pula a sobrescrita acima e chama a versao de Animal.
    -- E o equivalente em COOL do super.som() de outras linguagens.
    som_do_ancestral() : String { self@Animal.som() };
};

class Filhote inherits Cachorro {

    som() : String { "ai ai" };

    -- Da para nomear qualquer ancestral, nao so o pai imediato.
    som_do_avo() : String { self@Animal.som() };
};

class Main inherits IO {

    main() : Object {
        {
            -- new Tipo cria a instancia.
            out_string(new Cachorro.som());

            -- Dispatch ENCADEADO: cada chamada recebe o resultado da anterior.
            -- Na arvore isso sai aninhado a esquerda, que e a ordem de avaliacao.
            out_string(new Filhote.batizar("Rex").descrever());

            -- Os parenteses aqui so agrupam; eles nao viram no na arvore.
            out_string((new Cachorro).som_do_ancestral());
        }
    };
};
