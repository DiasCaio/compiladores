-- Erro de execucao: nenhum ramo do case aceita a classe do valor.
-- A mensagem diz a classe REAL do valor, lida da tag em tempo de execucao.

class Main inherits IO {
    descrever(x : Object) : String {
        case x of
            s : String => "uma String";
            i : IO => "um IO";
        esac
    };

    main() : Object {
        {
            out_string(descrever("oi")).out_string("\n");
            out_string(descrever(self)).out_string("\n");
            out_string(descrever(42)).out_string("\n");
        }
    };
};
