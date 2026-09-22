-- Exercita as construcoes fechadas: if, while e bloco.
--
-- Repare na diferenca entre os DOIS usos de chaves:
--   - as chaves do corpo de um metodo delimitam UMA expressao e nao levam ';'
--   - as chaves de um BLOCO levam ';' depois de CADA expressao, inclusive a ultima
-- Por isso um metodo com varios comandos escreve as chaves duas vezes.

class ControleDeFluxo inherits IO {

    x : Int <- 0;

    -- Em COOL o 'else' e obrigatorio: o if e uma expressao e precisa ter
    -- valor nos dois caminhos.
    maximo(a : Int, b : Int) : Int {
        if a < b then b else a fi
    };

    -- if dentro de if: o 'fi' de cada um marca onde ele termina.
    sinal(n : Int) : Int {
        if n < 0 then
            ~1
        else
            if n = 0 then 0 else 1 fi
        fi
    };

    -- while com um BLOCO no corpo. As chaves de fora sao do corpo do metodo,
    -- as de dentro sao o bloco.
    contar_ate(limite : Int) : Object {
        {
            x <- 0;
            while x < limite loop
                {
                    out_int(x);
                    x <- x + 1;
                }
            pool;
        }
    };

    -- Bloco dentro de bloco: o valor de um bloco e o da ultima expressao.
    blocos_aninhados() : Int {
        {
            x <- 1;
            {
                x <- x + 1;
                x;
            };
        }
    };
};
