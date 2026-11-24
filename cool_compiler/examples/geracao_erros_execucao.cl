-- Geracao de codigo: um erro de execucao.
--
-- O programa percorre uma lista ligada de 3 nos, mas o laco anda 4 vezes. Na
-- 4a volta, `lista` e void e `lista.valor()` e um dispatch em void: o
-- programa imprime o que deu tempo de imprimir e para com a mensagem de erro
-- e a linha do dispatch. O brili termina com codigo de saida 2.
--
-- Rode com:
--   python -m cool_compiler.main --fase executar cool_compiler/examples/geracao_erros_execucao.cl
--
-- Ha um exemplo para cada tipo de erro de execucao em examples/erros_execucao/.

class No {
    valor : Int;
    proximo : No;                  -- void no ultimo no

    iniciar(v : Int, p : No) : No {
        {
            valor <- v;
            proximo <- p;
            self;
        }
    };

    valor() : Int { valor };
    proximo() : No { proximo };
};

class Main inherits IO {
    main() : Object {
        let fim : No,
            lista : No <- (new No).iniciar(1, (new No).iniciar(2, (new No).iniciar(3, fim))),
            i : Int <- 0
        in
            while i < 4 loop
                {
                    out_int(lista.valor()).out_string("\n");
                    lista <- lista.proximo();
                    i <- i + 1;
                }
            pool
    };
};
