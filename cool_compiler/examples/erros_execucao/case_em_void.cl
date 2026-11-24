-- Erro de execucao: case sobre um valor void.

class Main inherits IO {
    main() : Object {
        let nada : Object in
            {
                out_string("antes do case\n");
                case nada of
                    o : Object => out_string("nunca chega aqui\n");
                esac;
            }
    };
};
