"""Análise semântica de COOL (etapas 13 a 20): o programa FAZ SENTIDO?

Três passadas pela árvore, cada uma prepara a seguinte:
    1. CLASSES      quem existe e quem herda de quem     etapas 15 e 16
    2. FEATURES     atributos e assinaturas de métodos   etapa 17
    3. EXPRESSÕES   o tipo de cada expressão             etapas 18 a 20

Nunca aborta: anota o erro e segue (etapa 13).
"""
