(*
   Exemplo simples de programa em COOL: um contador que comeca em 0,
   e incrementado tres vezes e depois mostra o valor.
   Saida esperada: "Valor atual: 3".
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
            out_string("Valor atual: ").out_int(valor).out_string("\n");  -- imprime o valor
            self;
        }
    };
};

class Main {
    main() : Object {
        (new Contador).incrementa().incrementa().incrementa().mostra()
    };
};
