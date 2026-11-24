"""Geração de código de COOL para Bril (etapas 21 a 28): o programa RODA.

A análise semântica respondeu "o programa faz sentido?". A geração responde
"que instruções uma máquina executa para fazer o que o programa diz?". A
máquina aqui é o interpretador `brili`, que executa Bril (Big Red
Intermediate Language) escrita em JSON.

    21  construtor de Bril        instruções, temporários, rótulos, JSON e texto
    22  layout                    tags, faixas, offsets e famílias de métodos
    23  runtime: memória          heap, erros, empacotamento, segmento de dados
    24  runtime: classes básicas  Object, IO e String escritos direto em Bril
    25  expressões (1)            variáveis, operadores e controle de fluxo
    26  expressões (2)            new, dispatch e case
    27  gerador                   classes, despachantes, @main e generate()
    28  executor                  roda o brili e decodifica a saída
"""
