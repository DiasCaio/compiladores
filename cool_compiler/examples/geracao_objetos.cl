-- Geracao de codigo: objetos, atributos com inicializadores, heranca e os
-- tres tipos de dispatch (dinamico, implicito e estatico).
--
-- Rode com:
--   python -m cool_compiler.main --fase executar cool_compiler/examples/geracao_objetos.cl

class Contador {
    valor : Int <- 10;
    passo : Int <- valor / 5;      -- le um atributo ja inicializado: 2

    incrementar() : SELF_TYPE {
        {
            valor <- valor + passo;
            self;
        }
    };

    -- Metodo e atributo podem ter o mesmo nome em COOL.
    valor() : Int { valor };

    -- Um metodo chamado init NAO colide com a funcao Contador_init que o
    -- compilador gera: os metodos viram @Contador.init, com ponto.
    init(v : Int) : SELF_TYPE {
        {
            valor <- v;
            self;
        }
    };
};

class Animal {
    nome : String <- "animal";
    patas : Int <- 4;

    batizar(n : String) : SELF_TYPE {
        {
            nome <- n;
            self;
        }
    };

    som() : String { "..." };

    -- som() aqui e um dispatch IMPLICITO (self.som()) e DINAMICO: num
    -- Cachorro, roda o som() de Cachorro.
    apresentar() : String { nome.concat(" faz ").concat(som()) };
};

class Cachorro inherits Animal {
    -- Os atributos do pai sao inicializados antes: patas ja vale 4.
    truques : Int <- patas + 1;

    som() : String { "au au" };
    truques() : Int { truques };
};

class Passaro inherits Animal {
    som() : String { "piu" };
    patas() : Int { patas };
    duas_patas() : SELF_TYPE {
        {
            patas <- 2;
            self;
        }
    };
};

class Main inherits IO {
    animal : Animal;               -- sem inicializador: void

    linha(s : String) : SELF_TYPE { out_string(s).out_string("\n") };
    numero(n : Int) : SELF_TYPE { out_int(n).out_string("\n") };

    main() : Object {
        let c : Contador <- new Contador, outro : Contador <- new Contador in
            {
                numero(c.valor());                              -- 10
                numero(c.incrementar().incrementar().valor());  -- 14
                numero(outro.valor());                          -- 10: cada objeto tem os seus atributos
                numero((new Contador).init(100).valor());       -- 100

                if isvoid animal then linha("animal ainda e void") else linha("?") fi;

                animal <- new Cachorro.batizar("Rex");
                linha(animal.apresentar());     -- Rex faz au au: o tipo estatico e Animal, o real e Cachorro
                linha(animal@Animal.som());     -- ...: o dispatch estatico forca a versao de Animal
                linha(animal.som());            -- au au

                animal <- new Passaro;
                linha(animal.apresentar());     -- animal faz piu

                numero(new Cachorro.truques());              -- 5
                numero((new Passaro).duas_patas().patas());  -- 2
            }
    };
};
