-- abort() encerra o programa na hora, dizendo de qual classe veio a chamada.

class Main inherits IO {
    main() : Object {
        {
            out_string("antes do abort\n");
            abort();
            out_string("nunca chega aqui\n");
        }
    };
};
