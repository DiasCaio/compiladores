-- Erro de execucao: divisao por zero.
-- O compilador testa o divisor antes de todo '/', para que a mensagem seja a
-- do programa (com a linha), e nao a do brili.

class Main inherits IO {
    media(soma : Int, quantidade : Int) : Int { soma / quantidade };

    main() : Object {
        {
            out_int(media(10, 2)).out_string("\n");
            out_int(media(10, 0)).out_string("\n");
            out_string("nunca chega aqui\n");
        }
    };
};
