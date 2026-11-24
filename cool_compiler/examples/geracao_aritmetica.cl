-- Geracao de codigo: aritmetica, comparacoes e controle de fluxo.
--
-- Rode com:
--   python -m cool_compiler.main --fase executar cool_compiler/examples/geracao_aritmetica.cl
-- A saida esperada esta em geracao_aritmetica.esperado.

class Main inherits IO {

    -- Imprime um Int e quebra a linha. Devolve SELF_TYPE, como out_int.
    linha(n : Int) : SELF_TYPE {
        out_int(n).out_string("\n")
    };

    booleano(b : Bool) : SELF_TYPE {
        out_string(if b then "true\n" else "false\n" fi)
    };

    -- Recursao: cada chamada e uma chamada de funcao Bril.
    fatorial(n : Int) : Int {
        if n <= 1 then 1 else n * fatorial(n - 1) fi
    };

    -- 1 + 2 + ... + n com while. total comeca em 0: e o padrao de Int.
    soma_ate(n : Int) : Int {
        let i : Int <- 1, total : Int in
            {
                while i <= n loop
                    {
                        total <- total + i;
                        i <- i + 1;
                    }
                pool;
                total;
            }
    };

    main() : Object {
        {
            linha(1 + 2 * 3);              -- 7: * antes de +
            linha((1 + 2) * 3);            -- 9
            linha(10 - 4 - 3);             -- 3: associativo a esquerda
            linha(17 / 5);                 -- 3: divisao inteira
            linha(~17 / 5);                -- -3: ~ liga mais forte; trunca em direcao ao zero
            linha(~(2 - 9));               -- 7
            linha(0 - 2147483647);         -- -2147483647: out_int com sinal
            linha(fatorial(10));           -- 3628800
            linha(soma_ate(100));          -- 5050

            booleano(3 < 4);               -- true
            booleano(4 <= 3);              -- false
            booleano(not (2 = 3));         -- true
            booleano(true = false);        -- false
            booleano(false = false);       -- true
            booleano(isvoid self);         -- false

            -- let sem inicializador: o padrao do tipo
            let x : Int, b : Bool, o : Object in
                {
                    linha(x);              -- 0
                    booleano(b);           -- false
                    booleano(isvoid o);    -- true: Object sem valor e void
                };

            -- O x de dentro esconde o de fora; ao sair do let, o de fora volta.
            let x : Int <- 1 in
                {
                    let x : Int <- x + 10 in linha(x);    -- 11
                    linha(x);                             -- 1
                };

            -- A atribuicao e expressao: vale o valor atribuido.
            let a : Int, b : Int in
                {
                    a <- b <- 5;
                    linha(a + b);          -- 10
                };

            -- O valor de um while e void.
            booleano(isvoid (while false loop 0 pool));   -- true
        }
    };
};
