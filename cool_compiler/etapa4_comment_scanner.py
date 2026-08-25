from etapa1_tokens import Token, TokenType


def scan_comment(source: str, start: int, line: int):
    """Escaneia o interior de um comentário de bloco de COOL.

    `start` deve apontar para a posição logo APÓS o '(*' de abertura
    (quem chama esta função já viu e consumiu esses dois caracteres).
    `line` é a linha onde esse '(*' de abertura foi encontrado.

    Devolve uma tupla (token, novo_indice, nova_linha):
      - token: None se o comentário fechou corretamente (nada deve virar
        token, igual um espaço em branco); ou um Token de tipo ERROR se
        o comentário nunca fechou.
      - novo_indice / nova_linha: de onde o escaneamento normal deve
        retomar depois deste comentário.
    """
    comment_start = start - 2   # inclui o '(*' de abertura, para o lexema de erro
    comment_line = line          # linha onde o comentário começou, para a mensagem
    depth = 1                     # já estamos dentro de um nível
    i = start
    n = len(source)

    while True:
        #erro caso o o texto acabe antes de fecharmos o comentário
        if i >= n:
            lexeme = source[comment_start:i]
            return Token(TokenType.ERROR, lexeme, comment_line, "EOF in comment"), i, line

        #Verificação de abrimos um novo bloco de comentário (contamos o aninhamento)
        if source[i:i + 2] == "(*":
            depth += 1
            i += 2
            continue

        #Verificamos se fechamos um bloco de comentário (diminuímos o aninhamento e, se virar 0, acabou o comentário)
        if source[i:i + 2] == "*)":
            depth -= 1
            i += 2
            if depth == 0:
                return None, i, line
            continue

        #contagem de linhas do comentário
        if source[i] == "\n":
            line += 1

        i += 1
