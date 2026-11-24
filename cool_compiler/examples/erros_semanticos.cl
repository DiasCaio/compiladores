-- Erros semanticos DELIBERADOS, isolados entre codigo valido.
--
-- Este arquivo e para a fase semantica o que erros_sintaticos.cl e para a
-- fase sintatica. So que aqui a GRAMATICA esta perfeita: o parser monta a
-- arvore inteira sem reclamar de nada. Os problemas so aparecem quando se
-- pergunta se o programa FAZ SENTIDO.
--
-- A analise semantica nao aborta no primeiro erro: ela anota o erro e segue,
-- e uma unica execucao reporta todos os problemas abaixo.

-- ERRO 1: Int nao pode ser herdada.
class Numero inherits Int {
};

-- ERRO 2: a classe-mae nao existe.
class Orfa inherits ClasseQueNaoExiste {
};

-- ERRO 3: heranca circular. A herda de B, e B herda de A.
class A inherits B {
};

class B inherits A {
};

class Animal {
    nome : String <- "animal";
    som() : String { "..." };
    idade(anos : Int) : Int { anos };
};

class Cachorro inherits Animal {

    -- ERRO 4: um atributo herdado nao pode ser declarado de novo.
    nome : String <- "rex";

    -- ERRO 5: a sobrescrita precisa manter a assinatura do pai, e o som() de
    -- Animal devolve String.
    som() : Int { 1 };

    valido : Int <- 10;
};

class Main inherits IO {

    contador : Int <- 0;

    main() : Object {
        {
            -- ERRO 6: variavel que nunca foi declarada.
            nao_existe <- 1;

            -- ERRO 7: o valor nao combina com o tipo declarado de contador.
            contador2 <- "dez";

            -- ERRO 8: a condicao de um if precisa ser Bool.
            if contador then 1 else 2 fi;

            -- ERRO 9: Animal nao tem metodo voar.
            (new Animal).voar();

            -- ERRO 10: idade recebe um argumento, nao dois.
            (new Animal).idade(1, 2);

            -- ERRO 11: o '+' exige Int dos dois lados.
            contador + "um";

            -- ERRO 12: o '=' nao compara Int com String.
            contador = "zero";

            -- ERRO 13: nao se atribui um valor a self.
            self <- new Main;

            -- Codigo valido no meio dos erros: deve receber o tipo normalmente
            -- na arvore, provando que a analise seguiu em frente.
            out_int(contador + 1);
        }
    };

    -- ERRO 14: o corpo e uma String, mas o metodo promete devolver Int.
    retorno_errado() : Int { "nao sou um Int" };
};
