"""Testes do conversor de tablatura (tools/tab_para_jogo.py).

Usa tablaturas de exemplo escritas para o teste (riffs originais) e confere,
nota por nota, as alturas e as duracoes geradas.

Uso (na raiz do projeto): python tools/testa_tab.py
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gera_musica as gm      # noqa: E402
import tab_para_jogo as tab   # noqa: E402

# Afinacao padrao (e = E4, B = B3, G = G3, A = A2). Texto, cifras e "Parte 1 de 2"
# devem ser ignorados. Compasso 1: A3 = C3, G2 = A3, B1 = C4, e0 = E4, uma a cada
# 2 colunas. Compasso 2: e12 = E5, G7 com bend ate 9 = D4, B5 hammer-on 7 = E4, F#4,
# e uma nota abafada (x). Bloco 2: acorde e0 + B1 + G0 = E4, C4, G3.
TAB_PADRAO = """
Minha Tab de Teste
Tom: Am   Parte 1 de 2

Intro       Am        C
e|-------0---|--12------------|
B|-----1-----|------5h7--x----|
G|---2-------|----7b9---------|
D|-----------|----------------|
A|-3---------|----------------|
E|-----------|----------------|

Refrao
e|-0---------|
B|-1---------|
G|-0---------|
D|-----------|
A|-----------|
E|-----------|
"""

# Drop D: a corda mais grave escrita como "D" vira D2 (e nao E2)
TAB_DROP_D = """
e|---------|
B|---------|
G|---------|
D|---------|
A|---------|
D|-0---2---|
"""


def args(**k):
    base = dict(entrada="teste.txt", nome="TESTE", afinacao=None, capo=0, acordes=1,
                frames_por_unidade=4, oitava=None, onda=1)
    base.update(k)
    return argparse.Namespace(**base)


def notas_da_saida(partitura):
    """[(notas sem a pista fixada, duracao), ...] do corpo da partitura gerada."""
    diretivas = ("nome", "painel", "onda", "slots_por_tempo", "pistas")
    resultado = []
    for linha in partitura.splitlines():
        if not linha or linha.startswith("#") or linha.split()[0] in diretivas:
            continue
        notas, dur = linha.split()
        resultado.append(("+".join(n.split("@")[0] for n in notas.split("+")), dur))
    return resultado


def confere(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"[{'OK   ' if ok else 'FALHA'}] {nome}")
    if not ok:
        print(f"         obtido:   {obtido}\n         esperado: {esperado}")
    return ok


def main():
    falhas = 0

    saida, _ = tab.converte(TAB_PADRAO, args(oitava=0))
    obtido = notas_da_saida(saida)
    alturas = [n for n, _ in obtido]
    falhas += not confere("texto, cifras e titulos ignorados; 9 notas lidas", len(alturas), 9)
    falhas += not confere("casas -> notas na afinacao padrao (A3=C3, G2=A3, B1=C4, e0=E4, e12=E5)",
                          alturas[:5], ["C3", "A3", "C4", "E4", "E5"])
    falhas += not confere("bend: so' a casa antes do 'b' vira nota (G7b9 -> D4)", alturas[5], "D4")
    falhas += not confere("hammer-on: as duas casas viram notas (B5h7 -> E4, F#4); x ignorado",
                          alturas[6:8], ["E4", "F#4"])
    falhas += not confere("acorde: fica a nota mais aguda (e0 B1 G0 -> E4)", alturas[8], "E4")
    falhas += not confere("ritmo: 2 colunas = 1 tempo; a barra de compasso nao conta (6 colunas = 3)",
                          [d for _, d in obtido[:5]], ["1", "1", "1", "3", "1"])

    saida2, _ = tab.converte(TAB_PADRAO, args(oitava=0, acordes=2))
    falhas += not confere("--acordes 2: acorde vira melodia + nota mais grave (E4+G3)",
                          notas_da_saida(saida2)[-1][0], "E4+G3")

    saida3, _ = tab.converte(TAB_DROP_D, args())
    falhas += not confere("Drop D: corda 'D' = D2; transposta 1 oitava para caber no jogo (D3, E3)",
                          [n for n, _ in notas_da_saida(saida3)], ["D3", "E3"])

    saida4, _ = tab.converte(TAB_PADRAO, args(oitava=0, capo=2))
    falhas += not confere("capotraste na casa 2 sobe tudo 2 semitons (C3 -> D3)",
                          notas_da_saida(saida4)[0][0], "D3")

    saida5, _ = tab.converte(TAB_PADRAO, args())
    falhas += not confere("transposicao automatica: nota mais grave fica em C3 ou acima",
                          notas_da_saida(saida5)[0][0], "C3")

    # a partitura gerada passa no gerador do jogo
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".tab_teste.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(saida2)
    try:
        info = gm.le_partitura(caminho)
        gm.gera_mapa(caminho, info)
        falhas += not confere("partitura gerada e' aceita pelo gerador do jogo", True, True)
    except SystemExit as e:
        falhas += not confere(f"partitura gerada e' aceita pelo gerador do jogo ({e})", False, True)
    finally:
        os.remove(caminho)

    print("\nTodos os testes passaram." if not falhas else f"\n{falhas} teste(s) falharam.")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
