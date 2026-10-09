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

Uso:
    python tools/gera_telas.py jogo.asm tools/telas/jogo.txt tools/telas/menu.txt ...
"""

import re
import sys


def le_tela(caminho):
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


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    caminho_asm = sys.argv[1]
    with open(caminho_asm, encoding="utf-8") as f:
        asm = f.read()
    for caminho in sys.argv[2:]:
        prefixo, linhas = le_tela(caminho)
        asm = injeta(asm, prefixo, linhas, caminho.replace("\\", "/"))
        print(f"{caminho}: {len(linhas)} linhas -> rotulos {prefixo}00..{prefixo}{len(linhas) - 1:02d}")
    with open(caminho_asm, "w", encoding="utf-8", newline="\n") as f:
        f.write(asm)


if __name__ == "__main__":
    main()
