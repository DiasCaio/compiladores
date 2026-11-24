-- Erro de execucao: substr fora dos limites da String.
-- substr e um metodo da classe String, escrito no runtime: ele nao sabe a
-- linha de quem o chamou, por isso a mensagem sai sem linha.

class Main inherits IO {
    main() : Object {
        let s : String <- "abc" in
            {
                out_string(s.substr(1, 2)).out_string("\n");
                out_string(s.substr(1, 5)).out_string("\n");
            }
    };
};
