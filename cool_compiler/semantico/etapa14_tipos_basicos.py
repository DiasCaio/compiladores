"""Etapa 14: nomes especiais, classes básicas e tipos dos operadores.

Só dados, nenhuma lógica.
"""

# --------------------------------------------------------------------------
# 1. Nomes com significado especial
# --------------------------------------------------------------------------

OBJECT = "Object"
IO = "IO"
INT = "Int"
STRING = "String"
BOOL = "Bool"

MAIN = "Main"            # classe por onde a execução começa
MAIN_METHOD = "main"     # método por onde a execução começa

SELF = "self"            # o objeto executando agora: não pode ser declarado nem receber valor

# "O tipo de quem está executando": batizar() : SELF_TYPE chamado num Cachorro devolve Cachorro
SELF_TYPE = "SELF_TYPE"

# Coringa de uma expressão que já deu erro: combina com tudo, evita erro em cascata
TIPO_ERRO = "<erro>"     # os < > garantem que nunca colide com um nome de classe


# --------------------------------------------------------------------------
# 2. As classes básicas
# --------------------------------------------------------------------------
# classe: (pai, [(método, [(parâmetro, tipo)], retorno), ...])  -> só assinaturas, sem corpo

CLASSES_BASICAS = {
    OBJECT: (None, [                                             # raiz: sem pai
        ("abort",      [],                          OBJECT),
        ("type_name",  [],                          STRING),
        ("copy",       [],                          SELF_TYPE),
    ]),
    IO: (OBJECT, [
        ("out_string", [("x", STRING)],             SELF_TYPE),  # SELF_TYPE permite encadear:
        ("out_int",    [("x", INT)],                SELF_TYPE),  # out_string("a").out_int(1)
        ("in_string",  [],                          STRING),
        ("in_int",     [],                          INT),
    ]),
    INT: (OBJECT, []),
    STRING: (OBJECT, [
        ("length",     [],                          INT),
        ("concat",     [("s", STRING)],             STRING),
        ("substr",     [("i", INT), ("l", INT)],    STRING),
    ]),
    BOOL: (OBJECT, []),
}

# Ninguém pode herdar destas
NAO_HERDAVEIS = {INT, STRING, BOOL, SELF_TYPE}


# --------------------------------------------------------------------------
# 3. Operadores
# --------------------------------------------------------------------------
# operador -> (tipo exigido dos DOIS lados, tipo do resultado)

TIPOS_DOS_OPERADORES = {
    "+":  (INT, INT),
    "-":  (INT, INT),
    "*":  (INT, INT),
    "/":  (INT, INT),
    "<":  (INT, BOOL),
    "<=": (INT, BOOL),
}

# "=" aceita quaisquer objetos, mas se um lado for destes tipos, o outro tem que ser igual
TIPOS_COMPARADOS_POR_VALOR = {INT, STRING, BOOL}
