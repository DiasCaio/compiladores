import sys
from pathlib import Path

from etapa1_tokens import Token, TokenType
from etapa2_lexer_rules import MASTER_PATTERN, classify_identifier
from etapa3_string_scanner import scan_string
from etapa4_comment_scanner import scan_comment

EXAMPLES_DIR = Path(__file__).parent / "examples"


def tokenize(source: str):
    """Percorre o código-fonte de COOL inteiro e devolve a lista de
    Tokens reconhecidos, terminada por um Token de tipo EOF.
    """
    tokens = []
    pos = 0
    line = 1
    n = len(source)

    while pos < n:
        # MASTER_PATTERN sempre casa alguma coisa aqui: a última regra da
        # lista (MISMATCH) casa com qualquer caractere restante, então
        # nunca sobra posição sem candidato.
        m = MASTER_PATTERN.match(source, pos)

        kind = m.lastgroup #Qual regra que o texto casou (exemplo: "PLUS", "IDENTIFIER" etc.)

        text = m.group() #Texto que casou com a regra (exemplo: "+", "foo" etc.)

        if kind in ("WHITESPACE", "LINE_COMMENT"):
            pos = m.end()
            continue

        if kind == "NEWLINE":
            line += 1
            pos = m.end()
            continue

        if kind == "COMMENT_CLOSE_STRAY":
            tokens.append(Token(TokenType.ERROR, text, line, "Unmatched *)"))
            pos = m.end()
            continue

        if kind == "STRING_OPEN":
            token, pos, line = scan_string(source, m.end(), line) #m.end() é a posição logo após a aspa de abertura da string
            # que é onde o scan_string deve começar a analisar
            tokens.append(token)
            continue

        if kind == "COMMENT_OPEN":
            token, pos, line = scan_comment(source, m.end(), line)
            if token is not None:
                tokens.append(token)
            continue

        if kind == "IDENTIFIER":
            token_type = classify_identifier(text)
            if token_type == TokenType.BOOL_CONST:
                value = text.lower() == "true"
            else:
                value = None
            tokens.append(Token(token_type, text, line, value))
            pos = m.end()
            continue

        if kind == "INT_CONST":
            tokens.append(Token(TokenType.INT_CONST, text, line, int(text)))
            pos = m.end()
            continue

        if kind == "MISMATCH":
            tokens.append(Token(TokenType.ERROR, text, line, f"invalid character {text!r}"))
            pos = m.end()
            continue

        # Qualquer outro grupo é um operador/pontuação de 1 ou 2 caracteres,
        # e o nome do grupo em TOKEN_SPECS foi escolhido para ser IGUAL ao
        # nome do TokenType correspondente (ex.: "PLUS" -> TokenType.PLUS).
        tokens.append(Token(TokenType[kind], text, line))
        pos = m.end()

    tokens.append(Token(TokenType.EOF, "", line))
    return tokens


def escolher_arquivo_exemplo() -> Path:
    """Lista os arquivos .cl da pasta examples/ e deixa o usuário
    escolher um deles digitando o número correspondente.
    """
    arquivos = sorted(EXAMPLES_DIR.glob("*.cl"))
    if not arquivos:
        print(f"Nenhum arquivo .cl encontrado em {EXAMPLES_DIR}")
        sys.exit(1)

    print("Arquivos disponíveis em examples/:")
    for indice, caminho in enumerate(arquivos, start=1):
        print(f"  {indice}. {caminho.name}")

    escolha = input("Digite o número do arquivo: ")
    return arquivos[int(escolha) - 1]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        caminho = Path(sys.argv[1])
    else:
        caminho = escolher_arquivo_exemplo()

    codigo = caminho.read_text(encoding="utf-8")

    for token in tokenize(codigo):
        print(token)
