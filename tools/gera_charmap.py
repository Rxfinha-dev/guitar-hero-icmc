"""Gera o charmap.mif do jogo a partir do charmap original do Processador ICMC.

O charmap original deixa os caracteres de controle (codigos 0 a 31) em branco e
"livres para edicao". Este script desenha os sprites do jogo nesses codigos e
mantem todo o resto (letras, numeros, simbolos) exatamente como no original.

Uso:
    python tools/gera_charmap.py <charmap_original.mif> <charmap_saida.mif>

Cada sprite e' uma matriz 8x8: '#' = pixel aceso, '.' = apagado.
A cor NAO faz parte do sprite: ela e' escolhida no Assembly, somando
(indice_da_cor * 256) ao codigo do caractere antes do OUTCHAR.

ATENCAO: o codigo 4 nunca e' desenhado pelo simulador grafico (o View.cpp pula
blocos com sym == 32, e sym = codigo * 8), por isso ele nao e' usado.
"""

import sys

SPRITES = {
    # --- Nota (gema) que cai pela pista: 3 caracteres de largura -------------
    1: ("NOTA_ESQ", [
        "........",
        "...#####",
        "..######",
        ".#######",
        ".#######",
        "..######",
        "...#####",
        "........",
    ]),
    2: ("NOTA_MEIO", [
        "........",
        "########",
        "###..###",
        "##....##",
        "##....##",
        "###..###",
        "########",
        "........",
    ]),
    3: ("NOTA_DIR", [
        "........",
        "#####...",
        "######..",
        "#######.",
        "#######.",
        "######..",
        "#####...",
        "........",
    ]),
    # --- Divisoria vertical entre as pistas ----------------------------------
    5: ("PISTA", [
        "...##...",
        "...##...",
        "...##...",
        "........",
        "...##...",
        "...##...",
        "...##...",
        "........",
    ]),
    # --- Alvo na linha de acerto: mesmo formato da nota, mas vazado ----------
    6: ("ALVO_ESQ", [
        "........",
        "...#####",
        "..#.....",
        ".#......",
        ".#......",
        "..#.....",
        "...#####",
        "........",
    ]),
    7: ("ALVO_MEIO", [
        "........",
        "########",
        "........",
        "........",
        "........",
        "........",
        "########",
        "........",
    ]),
    8: ("ALVO_DIR", [
        "........",
        "#####...",
        ".....#..",
        "......#.",
        "......#.",
        ".....#..",
        "#####...",
        "........",
    ]),
    # --- Moldura de linha dupla ----------------------------------------------
    9: ("BORDA_V", [
        "..#..#..",
        "..#..#..",
        "..#..#..",
        "..#..#..",
        "..#..#..",
        "..#..#..",
        "..#..#..",
        "..#..#..",
    ]),
    10: ("BORDA_H", [
        "........",
        "........",
        "########",
        "........",
        "........",
        "########",
        "........",
        "........",
    ]),
    11: ("CANTO_SUP_ESQ", [
        "........",
        "........",
        "..######",
        "..#.....",
        "..#.....",
        "..#..###",
        "..#..#..",
        "..#..#..",
    ]),
    12: ("CANTO_SUP_DIR", [
        "........",
        "........",
        "######..",
        ".....#..",
        ".....#..",
        "###..#..",
        "..#..#..",
        "..#..#..",
    ]),
    13: ("CANTO_INF_ESQ", [
        "..#..#..",
        "..#..#..",
        "..#..###",
        "..#.....",
        "..#.....",
        "..######",
        "........",
        "........",
    ]),
    14: ("CANTO_INF_DIR", [
        "..#..#..",
        "..#..#..",
        "###..#..",
        ".....#..",
        ".....#..",
        "######..",
        "........",
        "........",
    ]),
    # --- Decoracao ------------------------------------------------------------
    15: ("BLOCO", ["########"] * 8),
    16: ("NOTA_MUSICAL", [
        "....#...",
        "....##..",
        "....#.#.",
        "....#..#",
        "....#...",
        ".####...",
        "#####...",
        ".###....",
    ]),
    17: ("FAISCA", [
        "...#....",
        ".#.#.#..",
        "..###...",
        "#######.",
        "..###...",
        ".#.#.#..",
        "...#....",
        "........",
    ]),
}

LINHA_LIVRES = "[0..255]"


def valida():
    for codigo, (nome, linhas) in SPRITES.items():
        if codigo == 4 or not 1 <= codigo <= 31:
            raise ValueError(f"sprite {nome}: codigo {codigo} invalido (use 1..31, exceto 4)")
        if len(linhas) != 8 or any(len(l) != 8 or set(l) - {"#", "."} for l in linhas):
            raise ValueError(f"sprite {nome}: precisa ser 8x8 com '#' e '.'")


def bloco_caracteres_controle():
    """Gera as 256 linhas (32 caracteres x 8 linhas) dos codigos 0..31."""
    saida = ["-- CARACTERES DE CONTROLE - SPRITES DO JOGO (gerado por tools/gera_charmap.py)"]
    livres_inicio = None
    for codigo in range(32):
        if codigo in SPRITES:
            if livres_inicio is not None:
                saida.append(f"\t[{livres_inicio * 8}..{codigo * 8 - 1}]  :   00000000;")
                livres_inicio = None
            nome, linhas = SPRITES[codigo]
            saida.append(f"-- {codigo} {nome}")
            for i, linha in enumerate(linhas):
                bits = linha.replace("#", "1").replace(".", "0")
                saida.append(f"\t{codigo * 8 + i}  :   {bits};")
        elif livres_inicio is None:
            livres_inicio = codigo
    if livres_inicio is not None:
        saida.append(f"\t[{livres_inicio * 8}..255]  :   00000000;")
    return saida


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    valida()
    with open(sys.argv[1], encoding="latin-1", newline="") as f:
        texto = f.read()
    # O load_charmap do simulador usa fseek(-1) em modo texto: no Windows isso
    # so' funciona com quebras CRLF. Preserva a quebra de linha do original.
    quebra = "\r\n" if "\r\n" in texto else "\n"
    linhas = texto.splitlines()

    idx = next(i for i, l in enumerate(linhas) if l.strip().startswith(LINHA_LIVRES))
    # remove tambem o comentario "-- CARACTERES DE CONTROLE ..." logo acima
    inicio = idx - 1 if linhas[idx - 1].startswith("--") else idx
    novas = linhas[:inicio] + bloco_caracteres_controle() + linhas[idx + 1:]

    with open(sys.argv[2], "w", encoding="latin-1", newline="") as f:
        f.write(quebra.join(novas) + quebra)
    print(f"charmap gerado: {sys.argv[2]} ({len(SPRITES)} sprites)")


if __name__ == "__main__":
    main()
