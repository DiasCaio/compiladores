from .etapa1_tokens import Token, TokenType

MAX_STRING_LENGTH = 1024


#a chave representa o caractere que vem depois da barra invertida e o valor é o caractere que vai ser inserido na string final
#A ideia é que vamos chamar os scapes depois de vermos uma barra invertida, 
#então vamos olhar para o próximo caractere e ver se ele é um dos casos especiais que a gente quer tratar
ESCAPES = {
    "n": "\n",
    "t": "\t",
    "b": "\b",
    "f": "\f",
    '"': '"',
    "\\": "\\", #duas barras representam uma barra invertida literal, a primeira barra é o escape da segunda
    #por exemplo, se tentarmos printar ("\") dará erro. Para efetivamente exibir a barra, precisamos colocar \\
} 


def scan_string(source: str, start: int, line: int):
    """Escaneia o conteúdo de uma constante de string de COOL.

    `start` deve apontar para a posição logo APÓS a aspas de abertura
    (quem chama esta função já viu e consumiu o '"' inicial). `line` é a
    linha onde essa aspas de abertura foi encontrada.

    Devolve uma tupla (token, novo_indice, nova_linha):
      - token: um Token de tipo STR_CONST (sucesso) ou ERROR (falha).
      - novo_indice: posição no texto de onde o escaneamento normal deve
        retomar depois desta string.
      - nova_linha: número de linha atualizado (uma string pode conter
        continuações de linha via '\\' seguido de quebra de linha real).
    """
    token_start = start - 1   # inclui a aspas de abertura no lexema final. Só para a mensagem ficar igual ao texto original
    chars = []                 # conteúdo já decodificado da string
    error = None                # guarda o PRIMEIRO erro encontrado, se houver
    i = start                   #indice que vai andando pelo texto
    n = len(source)
    string_line = line          # linha onde a string começou, para o token final

    while True:
        if i >= n:
            lexeme = source[token_start:i]
            #verificamos se o texto acabou sem uma string fechada, nesse caso retornamos um token de erro
            token = Token(TokenType.ERROR, lexeme, string_line, "EOF in string constant")
            return token, i, line

        
        c = source[i]

        #obviamente vamos subindo o valor de i no loop, então essa condição verifica se achamos a aspas de fechamento da string
        if c == '"':
            i += 1 #avançamos para depois da aspas de fechamento, para que o scan continue a partir do fim da string analisada
            lexeme = source[token_start:i]
            if error is not None:
                return Token(TokenType.ERROR, lexeme, string_line, error), i, line
            if len(chars) > MAX_STRING_LENGTH:
                return Token(TokenType.ERROR, lexeme, string_line, "String constant too long"), i, line
            valor = "".join(chars) #junto todos os caracteres da string (que vieram em lista) em um único valor
            return Token(TokenType.STR_CONST, lexeme, string_line, valor), i, line

        #caso em que pulamos de linha antes de fechar a string (o programador aperta enter antes de fechar a string)
        if c == "\n":
            lexeme = source[token_start:i]
            mensagem = error or "Unterminated string constant"
            return Token(TokenType.ERROR, lexeme, string_line, mensagem), i, line

        #caracter nulo não é permitido dentro de uma string, mas vamos continuar a analisar o resto da string para poder reportar outros erros também
        if c == "\0":
            if error is None:
                error = "String contains null character"
            i += 1
            continue

        #Se vermos uma contra barra, precisamos entender o que ela significa, olhando pro próximo caractere
        if c == "\\":
            #se a barra invertida for o último caractere do texto, então não tem como continuar a analisar a string, então reportamos erro de EOF
            if i + 1 >= n:
                lexeme = source[token_start:i + 1]
                return Token(TokenType.ERROR, lexeme, string_line, "EOF in string constant"), i + 1, line

            proximo = source[i + 1]
            #quebra de linha real (não a sequência de escape \n) é permitida dentro de uma string, então vamos incrementar o contador de linha
            if proximo == "\n":
                chars.append("\n")
                line += 1

            #mesmo tratamento para o caractere nulo, que não é permitido dentro de uma string
            elif proximo == "\0":
                if error is None:
                    error = "String contains null character"
            else:
                chars.append(ESCAPES.get(proximo, proximo)) #tentando buscar nos nossos scapes qual o caso do próximo caractere. Se não for nenhum dos casos, 
                #então vamos colocar o próprio caractere literal na string final (segundo argumento da função get)
                #isso vem da regra "barra invertida é ignorada para qualquer caractere não-especial" vinda do COOL
            
            i += 2 #avançamos a barra + o caractere que vem após ela
            continue

        chars.append(c)
        i += 1
