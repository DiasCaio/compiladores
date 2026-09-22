"""Análise sintática de COOL (etapas 6 a 12): da lista de Tokens até a AST.

O lexer respondeu "que palavras existem neste arquivo?". O parser responde
"essas palavras formam um programa, e com que estrutura?".


TÉCNICA: DESCIDA RECURSIVA ESCRITA À MÃO
----------------------------------------
Uma função por regra da gramática, chamando umas às outras na mesma forma em
que as regras se referenciam. O material clássico de COOL usa um gerador
LALR(1) (bison), que constrói tabelas a partir de uma gramática declarativa.
As duas abordagens chegam à mesma árvore; a diferença está em o que cada uma
resolve de graça:

  - o gerador aceita a gramática quase como está no manual, inclusive
    recursiva à esquerda e ambígua, e resolve os conflitos com declarações
    de precedência;
  - a descida recursiva exige que a gramática seja reescrita antes, mas em
    troca o algoritmo fica visível: dá para ler o parser de cima a baixo.

Como o objetivo aqui é estudar, escolhemos ver o algoritmo.


PRECEDÊNCIA (etapa 10)
----------------------
Do MAIS FRACO para o MAIS FORTE, como manda o manual de COOL:

    <-              associativo à direita     parse_expression
    not             prefixo                   parse_not
    <= < =          NÃO associativo           parse_binary (nível 1)
    + -             associativo à esquerda    parse_binary (nível 2)
    * /             associativo à esquerda    parse_binary (nível 3)
    isvoid          prefixo                   parse_unary
    ~               prefixo                   parse_unary
    @               pós-fixo                  parse_dispatch_chain
    .               pós-fixo                  parse_dispatch_chain

Os quatro níveis binários cabem numa tabela e são lidos por uma função só
(precedence climbing), em vez de uma função por nível.


RECURSÃO À ESQUERDA
-------------------
A gramática do manual é recursiva à esquerda em `expr op expr` e em
`expr.metodo(...)`. Uma função que começa chamando a si mesma sem consumir
nada entra em laço infinito, então as duas viraram ITERAÇÃO: um while que
reconstrói o nó a cada volta. Isso resolve dois problemas de uma vez, porque
reconstruir o nó a cada volta também fixa a associatividade à esquerda.


O DANGLING-LET
--------------
No bison, `let x : Int in x + 1` gera um conflito shift/reduce: ao chegar no
'+', dá para fechar o let (deixando o corpo ser só `x`) ou estendê-lo. O
conflito é resolvido à mão, com uma declaração que escolhe estender.

Aqui esse conflito NÃO EXISTE. O corpo do let é lido por parse_expression, que
é o nível mais fraco da cascata e consome tudo que conseguir, parando só num
token que nenhuma regra de expressão aceita. Ser guloso É a regra "o let se
estende o máximo possível" — ganhamos de graça o que o bison precisa declarar.


LOOKAHEAD
---------
Três pontos da gramática não se decidem com o token atual, e cada um usa uma
das duas técnicas disponíveis:

  1. `x <- 1` (atribuição) vs `x` (variável) — a decisão precede o consumo,
     porque se não for atribuição o identificador tem que continuar disponível
     para o nível de baixo. Resolvido com LOOKAHEAD DE 2 (check_ahead).
  2. `f(1)` (dispatch implícito) vs `f` (variável) — resolvido por FATORAÇÃO
     À ESQUERDA: consome o identificador, que é comum às duas alternativas, e
     só então olha o que veio.
  3. método vs atributo numa feature — mesma fatoração à esquerda.

A fatoração à esquerda é o que um gerador LALR(1) faz implicitamente por só
decidir na hora de reduzir.


TRATAMENTO DE ERRO
------------------
Nenhuma das duas fases aborta. O lexer emite Token(ERROR, ...) e continua
escaneando; o parser acumula os erros numa lista, marca os buracos com nós
ErrorExpr e se recupera por MODO PÂNICO, descartando tokens até um ponto de
sincronização (';', '}', 'class' e os terminadores das construções fechadas).
Depois de um erro, os seguintes são suprimidos até a próxima sincronização,
senão um único ';' esquecido geraria dezenas de mensagens em cascata.

Os Tokens ERROR do lexer são separados ANTES da análise sintática e reportados
num bloco próprio; o parser analisa o resto do fluxo. Um erro léxico não é um
erro sintático, e repeti-lo como tal não acrescentaria informação.

As fronteiras de recuperação são quatro, sempre em construções delimitadas:
por classe (parse_program), por feature (parse_class), por corpo de método
(_parse_metodo) e por expressão de um bloco (parse_block).


LIMITAÇÕES CONHECIDAS
---------------------
  - As mensagens citam apenas a LINHA, não a coluna, porque o Token guarda só
    `line`. Acrescentar `column` custaria guardar o índice de início de linha
    em tokenize() e passá-lo a cada Token — umas seis linhas, fora do escopo
    desta etapa.
  - Mensagens de erro léxico estão em inglês, para coincidirem com as do
    compilador de referência; as de erro sintático estão em português.
  - `a < not b` é REJEITADO aqui, embora o bison da referência aceite (por
    shift). É consequência de `not` ficar acima das comparações na cascata.
    Fica documentado em vez de contornado: contorná-lo embaralharia a
    precedência do `not`, que é o que a cascata existe para deixar explícita.
  - Não há verificação de tipos, de escopo nem de herança: isso é a fase
    semântica, que ainda não existe. Um arquivo pode passar por aqui sem erro
    e ainda assim não ser um programa COOL válido.
"""
