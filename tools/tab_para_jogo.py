"""Converte uma tablatura em texto (padrao do Cifra Club e similares) para o formato
de partitura do Guitar Hero ICMC (docs/formato_partitura.md).

Entrada: um .txt com a tablatura colada como aparece no site, por exemplo

    Intro
    e|-----0-----|-----3-----|
    B|---1---1---|---0---0---|
    G|-2-------2-|-0-------0-|
    D|-----------|-----------|
    A|-3---------|-----------|
    E|-----------|-3---------|

Linhas que nao sao tablatura (titulo, cifras, letra, "Parte 1 de 3") sao
ignoradas, e os blocos de tablatura sao lidos em sequencia.

Uso:
    python tools/tab_para_jogo.py minha_tab.txt -o tools/musicas/minha_tab.txt --nome "MINHA TAB"

Opcoes uteis:
    --afinacao "D2 A2 D3 G3 B3 E4"   afinacao da corda mais grave para a mais aguda
                                     (sem esta opcao: padrao, ajustada pelos nomes
                                     das cordas escritos na tab, ex.: Drop D)
    --capo N                         capotraste na casa N
    --acordes 2                      em acordes, cai tambem a nota mais grave
                                     (padrao: so' a mais aguda, que e' a melodia)
    --frames-por-unidade N           frames do espacamento mais comum entre notas
                                     (padrao 4; maior = musica mais lenta e facil)
    --max-tempos N                   duracao maxima de uma nota, em tempos (padrao 2):
                                     encurta os espacos grandes da tab, que viram
                                     silencios longos no jogo (0 = sem limite)
    --oitava N                       transpoe N oitavas (padrao: o necessario para
                                     caber na faixa do jogo, C3 a D8)
    --onda 0..3                      timbre (padrao 1, quadrada)

Como o ritmo e' deduzido: tablaturas em texto nao trazem ritmo exato, mas o
espacamento entre as notas costuma ser proporcional a ele. O espacamento mais
comum vira a "unidade" (1 tempo na partitura gerada = --frames-por-unidade
frames) e os outros sao proporcionais. Confira sempre ouvindo no jogo.
"""

import argparse
import os
import re
import sys
import unicodedata
from collections import Counter
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gera_musica as gm   # noqa: E402  (midi, nome_midi, valida)

NOMES_CLASSE = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5, "F#": 6, "GB": 6,
                "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}

# Afinacoes padrao, da corda mais grave para a mais aguda, pelo numero de cordas
AFINACOES = {
    4: ["E1", "A1", "D2", "G2"],                     # baixo
    5: ["B0", "E1", "A1", "D2", "G2"],               # baixo de 5 cordas
    6: ["E2", "A2", "D3", "G3", "B3", "E4"],         # violao / guitarra
    7: ["B1", "E2", "A2", "D3", "G3", "B3", "E4"],   # guitarra de 7 cordas
}

MENOR_NOTA_JOGO = gm.MIDI_BASE + 1                   # C3
MAIOR_NOTA_JOGO = gm.MIDI_BASE + gm.MAX_INDICE       # D8
DISTANCIA_MINIMA = 3                                  # frames entre notas na mesma pista

RE_LINHA = re.compile(r"^\s*([A-Ga-g][#b]?)?\s*([|:])(.*)$")
CARACTERES_TAB = set("-|0123456789hpbr/\\~x()<>.*^vtPMsS ")


# ----------------------------------------------------------------------------
# Leitura da tablatura
# ----------------------------------------------------------------------------

def linha_de_tab(linha):
    """Se a linha for uma corda de tablatura, devolve (nome da corda ou None, conteudo)."""
    linha = linha.replace("–", "-").replace("—", "-").rstrip()
    m = RE_LINHA.match(linha)
    if not m:
        return None
    nome, _, corpo = m.groups()
    if corpo.count("-") < 3:
        return None
    estranhos = sum(1 for c in corpo if c not in CARACTERES_TAB)
    if estranhos > max(1, len(corpo) // 10):
        return None
    return nome, corpo


def le_blocos(texto):
    """Agrupa linhas de tablatura consecutivas em blocos (sistemas)."""
    blocos, atual, avisos = [], [], []
    for num, linha in enumerate(texto.splitlines() + [""], 1):
        corda = linha_de_tab(linha)
        if corda:
            atual.append(corda)
            continue
        if atual:
            if len(atual) in AFINACOES:
                blocos.append(atual)
            else:
                avisos.append(f"linha {num - len(atual)}: bloco com {len(atual)} linhas ignorado "
                              f"(esperado 4 a 7 cordas)")
            atual = []
    return blocos, avisos


def midi_da_corda(nome, padrao):
    """Altura da corda solta a partir do nome escrito na tab (ex.: 'D' numa
    afinacao Drop D), na oitava mais proxima da corda padrao."""
    if not nome:
        return padrao
    classe = NOMES_CLASSE.get(nome[0].upper() + nome[1:].upper())
    if classe is None:
        return padrao
    candidatos = [classe + 12 * k for k in range(0, 10)]
    return min(candidatos, key=lambda n: abs(n - padrao))


def afinacao_do_bloco(bloco, afinacao_fixa):
    """Altura MIDI de cada linha do bloco (linha de cima = corda mais aguda)."""
    n = len(bloco)
    if afinacao_fixa:
        if len(afinacao_fixa) != n:
            raise SystemExit(f"--afinacao tem {len(afinacao_fixa)} cordas, mas a tab tem {n}")
        da_grave = afinacao_fixa
    else:
        padrao = [gm.midi(x) for x in AFINACOES[n]]
        # na tab, a linha de cima e' a corda mais aguda
        da_grave = [midi_da_corda(bloco[n - 1 - i][0], padrao[i]) for i in range(n)]
    return list(reversed(da_grave))


def colunas_sem_barras(bloco):
    """Larguras sem as barras de compasso: mapa coluna original -> coluna de tempo."""
    largura = max(len(corpo) for _, corpo in bloco)
    linhas = [corpo.ljust(largura, "-") for _, corpo in bloco]
    mapa, coluna = [], 0
    for j in range(largura):
        barra = sum(1 for l in linhas if l[j] == "|") >= len(linhas) - 1
        mapa.append(coluna)
        if not barra:
            coluna += 1
    return linhas, mapa, coluna


def eventos_do_bloco(linhas, afinacao, mapa, deslocamento, capo):
    """Notas do bloco: (coluna de tempo, altura MIDI, digitos da casa)."""
    eventos = []
    for corda, linha in enumerate(linhas):
        j = 0
        while j < len(linha):
            if linha[j].isdigit():
                k = j
                while k < len(linha) and linha[k].isdigit() and k - j < 2:
                    k += 1
                casa = int(linha[j:k])
                anterior = linha[j - 1] if j > 0 else ""
                if anterior not in "br":        # depois de b/r e' o alvo do bend, nao nota nova
                    eventos.append((deslocamento + mapa[j], afinacao[corda] + casa + capo, k - j))
                j = k
            else:
                j += 1
    return eventos


def agrupa_acordes(eventos):
    """Junta notas da mesma coluna (acordes). Casa de 2 digitos desalinha 1 coluna."""
    grupos = []
    for col, nota, digitos in sorted(eventos):
        if grupos:
            inicio, notas, tem_dois = grupos[-1]
            if col - inicio <= (1 if (tem_dois or digitos == 2) else 0):
                notas.append(nota)
                grupos[-1] = (inicio, notas, tem_dois or digitos == 2)
                continue
        grupos.append((col, [nota], digitos == 2))
    return [(col, sorted(set(notas), reverse=True)) for col, notas, _ in grupos]


# ----------------------------------------------------------------------------
# Ritmo, faixa e pistas
# ----------------------------------------------------------------------------

def duracoes_em_frames(colunas, frames_por_unidade, max_tempos):
    """Duracao de cada nota em frames, proporcional ao espacamento na tab.

    max_tempos limita a duracao de cada nota (0 = sem limite). Espacos grandes
    na tab quase nunca sao pausas de verdade: sao tracos no fim de um bloco
    somados aos do comeco do proximo, notas sustentadas escritas com traco ou
    folga entre partes. Sem o limite eles viram silencios longos no jogo.
    """
    lacunas = [b - a for a, b in zip(colunas, colunas[1:]) if b > a]
    contagem = Counter(lacunas)
    unidade = min(contagem, key=lambda g: (-contagem[g], g)) if contagem else 1
    teto = max(2, int(max_tempos * frames_por_unidade)) if max_tempos else None   # frames inteiros
    frames, encurtadas, frames_cortados = [], 0, 0
    for i, col in enumerate(colunas):
        lacuna = colunas[i + 1] - col if i + 1 < len(colunas) else 2 * unidade
        f = max(2, round(Fraction(lacuna, unidade) * frames_por_unidade))
        if teto and f > teto:
            encurtadas += 1
            frames_cortados += f - teto
            f = teto
        frames.append(f)
    return frames, unidade, encurtadas, frames_cortados


def transposicao(alturas, oitava):
    """Semitons a somar (oitavas inteiras) para as notas caberem na faixa do jogo."""
    if oitava is not None:
        return 12 * oitava
    menor, maior = min(alturas), max(alturas)
    desloc = 0
    while menor + desloc < MENOR_NOTA_JOGO:
        desloc += 12
    while maior + desloc > MAIOR_NOTA_JOGO and menor + desloc - 12 >= MENOR_NOTA_JOGO:
        desloc -= 12
    return desloc


def escolhe_pista(base, tempo, ultimo, evitar, subindo):
    """Pista mais proxima da ideal que esteja livre (sem nota nos ultimos frames)."""
    ordem = [base]
    for d in (1, 2, 3):
        for p in ((base + d, base - d) if subindo else (base - d, base + d)):
            if 0 <= p <= 3:
                ordem.append(p)
    ordem = [p for p in ordem if p != evitar]
    livres = [p for p in ordem if tempo - ultimo[p] >= DISTANCIA_MINIMA]
    if livres:
        return livres[0]
    return max(ordem, key=lambda p: tempo - ultimo[p])


def texto_duracao(frames, frames_por_unidade):
    """Escreve uma duracao em frames como tempos da partitura (ex.: 0.5, 1/3)."""
    d = Fraction(frames, frames_por_unidade)
    if d.denominator == 1:
        return str(d.numerator)
    if 10 ** 6 % d.denominator == 0:
        return f"{float(d):g}"
    return f"{d.numerator}/{d.denominator}"


def sem_acentos(texto):
    """Remove acentos: o charmap do jogo so' tem ASCII."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9 ]", " ", texto).upper().split()


def nome_e_painel(nome):
    """Monta o nome do menu e as 3 linhas do painel a partir do nome da musica."""
    palavras = sem_acentos(nome) or ["MINHA", "TAB"]
    nome_menu = " ".join(palavras)[:gm.LARG_NOME].strip()
    linhas, atual = [], ""
    for p in palavras:
        p = p[:gm.LARG_PAINEL]
        if atual and len(atual) + 1 + len(p) > gm.LARG_PAINEL:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    linhas.append(atual)
    return nome_menu, "|".join(linhas[:3])


# ----------------------------------------------------------------------------

def converte(texto, args):
    """Faz a conversao completa: do texto da tablatura ao texto da partitura."""
    blocos, avisos = le_blocos(texto)
    if not blocos:
        raise SystemExit("nenhuma tablatura encontrada (esperado linhas como 'e|---0---|')")

    afinacao_fixa = [gm.midi(n) for n in args.afinacao.split()] if args.afinacao else None
    eventos, deslocamento, afinacoes_usadas = [], 0, set()
    for bloco in blocos:
        afinacao = afinacao_do_bloco(bloco, afinacao_fixa)
        afinacoes_usadas.add(" ".join(gm.nome_midi(n) for n in reversed(afinacao)))
        linhas, mapa, largura = colunas_sem_barras(bloco)
        eventos += eventos_do_bloco(linhas, afinacao, mapa, deslocamento, args.capo)
        deslocamento += largura
    if not eventos:
        raise SystemExit("a tablatura nao tem nenhuma nota")

    grupos = agrupa_acordes(eventos)
    frames, unidade, encurtadas, frames_cortados = duracoes_em_frames(
        [c for c, _ in grupos], args.frames_por_unidade, args.max_tempos)

    # melodia = nota mais aguda; com --acordes 2, tambem a mais grave
    notas = [[g[0]] + ([g[-1]] if args.acordes == 2 and len(g) > 1 else []) for _, g in grupos]
    desloc = transposicao([n for ns in notas for n in ns], args.oitava)
    notas = [[n + desloc for n in ns] for ns in notas]
    if any(not MENOR_NOTA_JOGO <= n <= MAIOR_NOTA_JOGO for ns in notas for n in ns):
        raise SystemExit("a tablatura nao cabe na faixa do jogo (C3 a D8) nem transpondo por oitavas")

    # pista base: alturas distintas divididas em 4 faixas, da grave para a aguda
    alturas = sorted({n for ns in notas for n in ns})
    base = {n: i * 4 // len(alturas) for i, n in enumerate(alturas)}

    linhas_saida, ultimo, tempo, anterior, movidas = [], [-99] * 4, 0, None, 0
    for ns, fr in zip(notas, frames):
        partes, usada = [], None
        for k, n in enumerate(ns):
            subindo = anterior is None or n >= anterior
            pista = escolhe_pista(base[n], tempo, ultimo, usada, subindo)
            ultimo[pista] = tempo
            usada = pista
            if pista != base[n]:
                movidas += 1
                partes.append(f"{gm.nome_midi(n)}@{pista}")
            else:
                partes.append(gm.nome_midi(n))
        anterior = ns[0]
        linhas_saida.append(f"{'+'.join(partes)} {texto_duracao(fr, args.frames_por_unidade)}")
        tempo += fr

    nome_menu, painel = nome_e_painel(args.nome or os.path.splitext(os.path.basename(args.entrada))[0])
    cabecalho = [
        f"# Gerado por tools/tab_para_jogo.py a partir de {os.path.basename(args.entrada)}",
        f"# Afinacao: {', '.join(sorted(afinacoes_usadas))}" + (f" | capotraste na casa {args.capo}" if args.capo else ""),
        f"# Transposicao: {desloc // 12:+d} oitava(s) | unidade de ritmo: {unidade} coluna(s) da tab"
        f" = {args.frames_por_unidade} frames",
        f"# {len(blocos)} bloco(s) de tablatura, {len(grupos)} notas"
        + (f", {movidas} movida(s) de pista para nao ficarem grudadas" if movidas else ""),
        (f"# Pausas longas encurtadas: {encurtadas} nota(s) limitadas a {args.max_tempos} tempo(s), "
         f"{frames_cortados * 65 / 1000:.0f} s de silencio removidos (nivel 5)"
         if encurtadas else f"# Nenhuma nota passou de {args.max_tempos} tempo(s)" if args.max_tempos
         else "# Sem limite de duracao (--max-tempos 0)"),
        "# Confira ouvindo no jogo: o ritmo e' deduzido do espacamento da tab.",
        "",
        f"nome {nome_menu}",
        f"painel {painel}",
        f"onda {args.onda}",
        f"slots_por_tempo {args.frames_por_unidade}",
        "pistas " + " ".join(f"{gm.nome_midi(n)}={base[n]}" for n in alturas),
        "",
    ]
    return "\n".join(cabecalho + linhas_saida) + "\n", avisos


def main():
    p = argparse.ArgumentParser(description="Converte tablatura em texto para o formato do Guitar Hero ICMC.")
    p.add_argument("entrada", help="arquivo .txt com a tablatura")
    p.add_argument("-o", "--saida", help="arquivo de partitura a gerar (padrao: mostra na tela)")
    p.add_argument("--nome", help="nome da musica no menu (ate' 20 caracteres)")
    p.add_argument("--afinacao", help='alturas das cordas soltas, da mais grave para a mais aguda, ex.: "D2 A2 D3 G3 B3 E4"')
    p.add_argument("--capo", type=int, default=0, help="casa do capotraste")
    p.add_argument("--acordes", type=int, choices=(1, 2), default=1, help="notas por acorde (1 = so' a melodia)")
    p.add_argument("--frames-por-unidade", type=int, default=4, help="frames do espacamento mais comum (padrao 4)")
    p.add_argument("--max-tempos", type=Fraction, default=Fraction(2),
                   help="duracao maxima de uma nota em tempos; encurta pausas longas da tab "
                        "(padrao 2; 0 = sem limite; aceita 1.5 ou 3/2)")
    p.add_argument("--oitava", type=int, help="transposicao em oitavas (padrao: automatica)")
    p.add_argument("--onda", type=int, choices=(0, 1, 2, 3), default=1, help="timbre: 0 seno, 1 quadrada, 2 triangular, 3 serra")
    args = p.parse_args()

    with open(args.entrada, encoding="utf-8", errors="replace") as f:
        partitura, avisos = converte(f.read(), args)
    for a in avisos:
        print(f"AVISO: {a}", file=sys.stderr)

    if not args.saida:
        print(partitura, end="")
        return
    with open(args.saida, "w", encoding="utf-8", newline="\n") as f:
        f.write(partitura)
    print(f"partitura gerada: {args.saida}")
    ok = gm.valida(args.saida)
    if ok:
        print(f"Para colocar no jogo: acrescente '{os.path.basename(args.saida)}' em tools/musicas/lista.txt "
              f"e rode: python tools/gera_jogo.py")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
