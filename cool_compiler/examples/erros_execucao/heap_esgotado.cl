-- Erro de execucao: heap esgotado.
-- Nao ha coleta de lixo: toda String criada continua ocupando o heap. Aqui a
-- String dobra de tamanho a cada volta ate o heap (1.000.000 de posicoes)
-- acabar. Leva alguns segundos no brili.

class Main inherits IO {
    main() : Object {
        let s : String <- "x" in
            while true loop
                {
                    out_int(s.length()).out_string("\n");
                    s <- s.concat(s);
                }
            pool
    };
};
