"""Converte os desenhos de tela (tools/telas/*.txt) em diretivas `string` do jogo.asm.

Cada arquivo de tela tem um cabecalho com o prefixo dos rotulos e a largura:

    # prefixo telaL
    # largura 40
    <linhas do desenho, todas com exatamente `largura` caracteres>

O script substitui, dentro do jogo.asm, o bloco entre os marcadores

    ; >>> TELA <prefixo>
    ; <<< TELA <prefixo>

por uma linha `<prefixo>NN : string "..."` para cada linha do desenho.

Convencao dos desenhos: TEXTO EM MAIUSCULAS e' impresso como texto; letras
minusculas sao "codigos de sprite", traduzidos no Assembly pela tabela `traduz`
(ex.: 'p' = divisoria da pista, 'e' 'f' 'g' = alvo verde). Veja a legenda no
cabecalho do jogo.asm.

Uso (na raiz do projeto):
    python tools/gera_telas.py                      (as 3 telas: jogo, menu e fim)
    python tools/gera_telas.py jogo.asm tools/telas/jogo.txt ...
"""

import re
import sys


def le_tela(caminho):
    """Le um desenho de tools/telas e confere os caracteres e a largura das linhas."""
    prefixo, largura, linhas = None, None, []
    with open(caminho, encoding="utf-8") as f:
        for n, linha in enumerate(f.read().splitlines(), 1):
            if linha.startswith("#"):
                m = re.match(r"#\s*(prefixo|largura)\s+(\S+)", linha)
                if m and m.group(1) == "prefixo":
                    prefixo = m.group(2)
                elif m:
                    largura = int(m.group(2))
                continue
            if '"' in linha or "\\" in linha:
                raise SystemExit(f"{caminho}:{n}: aspas e barra invertida nao sao permitidas")
            if any(ord(c) > 126 or ord(c) < 32 for c in linha):
                raise SystemExit(f"{caminho}:{n}: use somente caracteres ASCII imprimiveis")
            linhas.append((n, linha))
    if prefixo is None or largura is None:
        raise SystemExit(f"{caminho}: cabecalho precisa de '# prefixo' e '# largura'")
    erros = [f"{caminho}:{n}: tem {len(l)} caracteres, esperado {largura}"
             for n, l in linhas if len(l) != largura]
    if erros:
        raise SystemExit("\n".join(erros))
    return prefixo, [l for _, l in linhas]


def injeta(asm, prefixo, linhas, origem):
    """Troca, no jogo.asm, o bloco da tela entre os marcadores >>> e <<<."""
    inicio = f"; >>> TELA {prefixo}"
    fim = f"; <<< TELA {prefixo}"
    if inicio not in asm or fim not in asm:
        raise SystemExit(f"jogo.asm nao tem os marcadores '{inicio}' / '{fim}'")
    bloco = [inicio + f"  (gerado por tools/gera_telas.py a partir de {origem} - nao edite a mao)"]
    bloco += [f'{prefixo}{i:02d} : string "{l}"' for i, l in enumerate(linhas)]
    bloco.append(fim)
    antes = asm.split(inicio)[0]
    depois = asm.split(fim, 1)[1]
    return antes + "\n".join(bloco) + depois


TELAS = ["tools/telas/jogo.txt", "tools/telas/menu.txt", "tools/telas/fim.txt"]


def main():
    caminho_asm = sys.argv[1] if len(sys.argv) > 1 else "jogo.asm"
    telas = sys.argv[2:] or TELAS
    with open(caminho_asm, encoding="utf-8") as f:
        asm = f.read()
    for caminho in telas:
        prefixo, linhas = le_tela(caminho)
        asm = injeta(asm, prefixo, linhas, caminho.replace("\\", "/"))
        print(f"{caminho}: {len(linhas)} linhas -> rotulos {prefixo}00..{prefixo}{len(linhas) - 1:02d}")
    with open(caminho_asm, "w", encoding="utf-8", newline="\n") as f:
        f.write(asm)


if __name__ == "__main__":
    main()
