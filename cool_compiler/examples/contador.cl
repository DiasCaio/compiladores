(*
   Exemplo simples de programa em COOL,
   so para testar o lexer.
*)
class Contador inherits IO {
    valor : Int <- 0;

    incrementa() : SELF_TYPE {
        {
            valor <- valor + 1;
            self;
        }
    };

    mostra() : SELF_TYPE {
        {
            out_string("Valor atual\n");  -- imprime o valor
            self;
        }
    };
};

class Main {
    main() : Object {
        (new Contador).incrementa().mostra()
    };
};
