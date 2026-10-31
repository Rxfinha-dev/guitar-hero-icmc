"""Converte as partituras em texto (tools/musicas/*.txt) nos mapas de notas do jogo.

Varias musicas podem ser geradas de uma vez; a ordem dos arquivos e' a ordem em
que elas aparecem no menu (tecla M troca a musica).

Formato da partitura (uma nota por linha):

    # comentario: linha comecando com '#', ou '#' depois de um espaco
    nome ODE A ALEGRIA          # nome no menu (ate' 20 caracteres)
    painel ODE A|ALEGRIA|BEETHOVEN   # 3 linhas do painel do jogo (ate' 9 cada)
    onda 2                      # 0 seno, 1 quadrada, 2 triangular, 3 dente de serra
    slots_por_tempo 6           # quantos frames do jogo dura 1 tempo (seminima)
    pistas G3=0 C4=0 D4=1 ...   # (opcional) pista de cada altura; senao e' automatico
    E4 1                        # nota e duracao em tempos (1 = seminima, 0.5 = colcheia)
    D4 1.5                      # pontuada
    - 1                         # pausa
    C4+G4 2                     # acorde: duas notas caem juntas (a 1a e' a que toca)

Cada frame do jogo corresponde a uma palavra de 16 bits no mapa da musica:

    bits  3-0  : mascara das pistas que recebem nota neste frame (bit0 = D ... bit3 = K)
    bits  9-4  : indice da nota na tabela `freqs` (0 = nao toca nada)
    bits 13-10 : duracao da nota, em frames (maximo 15)
    65535      : fim da musica

O script substitui, no jogo.asm, o bloco entre '; >>> MUSICA' e '; <<< MUSICA'.

Uso:
    python tools/gera_musica.py jogo.asm tools/musicas/ode_alegria.txt [outra.txt ...]
    python tools/gera_musica.py --validar tools/musicas/minha_musica.txt [outra.txt ...]
        (so' confere as partituras e a jogabilidade, sem alterar o jogo.asm)

Especificacao completa do formato: docs/formato_partitura.md
"""

import re
import sys
from fractions import Fraction

NOMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MIDI_BASE = 47          # indice 1 da tabela = MIDI 48 = C3
MAX_INDICE = 63         # 6 bits
FIM = 65535
LARG_NOME, LARG_PAINEL = 20, 9


def midi(nome):
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", nome)
    if not m:
        raise ValueError(f"nota invalida: {nome!r} (use ex.: C4, F#3, Bb4)")
    semitom = NOMES[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + semitom


def nome_midi(n):
    return ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][n % 12] + str(n // 12 - 1)


def freq_hz(n):
    return round(440 * 2 ** ((n - 69) / 12))


def texto_tela(caminho, num, texto, largura):
    texto = texto.upper()
    if len(texto) > largura:
        raise SystemExit(f"{caminho}:{num}: '{texto}' passa de {largura} caracteres")
    if '"' in texto or "\\" in texto or any(not 32 <= ord(c) <= 126 for c in texto):
        raise SystemExit(f"{caminho}:{num}: use so' letras, numeros e simbolos simples em '{texto}'")
    return texto.ljust(largura)


def le_partitura(caminho):
    info = {"nome": None, "painel": None, "onda": 2, "slots_por_tempo": 4, "mapa": {}, "eventos": []}
    with open(caminho, encoding="utf-8") as f:
        for num, linha in enumerate(f, 1):
            linha = "" if linha.lstrip().startswith("#") else re.sub(r"\s#.*$", "", linha).strip()
            if not linha:
                continue
            chave, _, resto = linha.partition(" ")
            resto = resto.strip()
            if chave == "nome":
                info["nome"] = texto_tela(caminho, num, resto, LARG_NOME)
            elif chave == "painel":
                partes = resto.split("|")
                if len(partes) > 3:
                    raise SystemExit(f"{caminho}:{num}: o painel tem no maximo 3 linhas")
                info["painel"] = [texto_tela(caminho, num, p.strip(), LARG_PAINEL)
                                  for p in partes + [""] * (3 - len(partes))]
            elif chave == "onda":
                info["onda"] = int(resto)
                if not 0 <= info["onda"] <= 3:
                    raise SystemExit(f"{caminho}:{num}: onda deve ser 0, 1, 2 ou 3")
            elif chave == "slots_por_tempo":
                info["slots_por_tempo"] = int(resto)
            elif chave == "pistas":
                for item in resto.split():
                    nota, pista = item.split("=")
                    info["mapa"][midi(nota)] = int(pista)
            else:
                partes = linha.split()
                if len(partes) != 2:
                    raise SystemExit(f"{caminho}:{num}: esperado 'NOTA DURACAO'")
                notas = [] if partes[0] == "-" else [le_nota(caminho, num, n) for n in partes[0].split("+")]
                try:
                    tempos = Fraction(partes[1])        # aceita 1, 0.5, 1.5 e fracoes como 1/3
                except ValueError:
                    raise SystemExit(f"{caminho}:{num}: duracao invalida '{partes[1]}' (use ex.: 1, 0.5, 1/3)")
                if tempos <= 0:
                    raise SystemExit(f"{caminho}:{num}: a duracao precisa ser maior que zero")
                info["eventos"].append((notas, tempos, num))
    if info["nome"] is None:
        raise SystemExit(f"{caminho}: falta a linha 'nome ...'")
    if info["painel"] is None:
        info["painel"] = [texto_tela(caminho, 0, p, LARG_PAINEL) for p in (info["nome"].strip()[:9], "", "")]
    if not info["eventos"]:
        raise SystemExit(f"{caminho}: a partitura nao tem nenhuma nota")
    return info


def le_nota(caminho, num, texto):
    """'E4' -> (64, None); 'E4@2' -> (64, 2): pista fixada so' para esta nota."""
    nome, _, pista = texto.partition("@")
    try:
        n = midi(nome)
    except ValueError as e:
        raise SystemExit(f"{caminho}:{num}: {e}")
    if pista == "":
        return n, None
    if not pista.isdigit() or not 0 <= int(pista) <= 3:
        raise SystemExit(f"{caminho}:{num}: pista invalida em '{texto}' (use @0, @1, @2 ou @3)")
    return n, int(pista)


def pistas_automaticas(eventos):
    alturas = sorted({n for notas, _, _ in eventos for n, _ in notas})
    return {n: i * 4 // len(alturas) for i, n in enumerate(alturas)}


def gera_mapa(caminho, info):
    mapa = info["mapa"] or pistas_automaticas(info["eventos"])
    spt = info["slots_por_tempo"]
    musica, usadas, total_notas = [], set(), 0
    for notas, tempos, num in info["eventos"]:
        frames = tempos * spt
        if frames.denominator != 1:
            raise SystemExit(f"{caminho}:{num}: duracao {tempos} x slots_por_tempo {spt} = {float(frames):g} frames, "
                             f"precisa ser inteiro (aumente slots_por_tempo; tercinas pedem multiplo de 3)")
        slots = int(frames)
        palavra = 0
        if notas:
            mascara = 0
            for n, fixa in notas:
                if fixa is not None:
                    pista = fixa
                elif n in mapa:
                    pista = mapa[n]
                else:
                    raise SystemExit(f"{caminho}:{num}: nota {nome_midi(n)} sem pista definida na linha 'pistas' "
                                     f"(ou use {nome_midi(n)}@PISTA)")
                if not 0 <= pista <= 3:
                    raise SystemExit(f"{caminho}:{num}: pista de {nome_midi(n)} deve ser 0..3")
                if mascara & (1 << pista):
                    raise SystemExit(f"{caminho}:{num}: duas notas juntas na mesma pista {pista}")
                mascara |= 1 << pista
            primeira = notas[0][0]
            indice = primeira - MIDI_BASE
            if not 1 <= indice <= MAX_INDICE:
                raise SystemExit(f"{caminho}:{num}: nota {nome_midi(primeira)} fora da faixa C3..D8 "
                                 f"(transponha uma oitava)")
            usadas.add(primeira)
            total_notas += bin(mascara).count("1")
            palavra = mascara | (indice << 4) | (min(slots, 15) << 10)
        musica.append(palavra)
        musica.extend([0] * (slots - 1))
    return musica, usadas, total_notas


def bloco_asm(musicas):
    n = len(musicas)
    L = [f"; >>> MUSICA  (gerado por tools/gera_musica.py - nao edite a mao)",
         f"; Musicas, na ordem do menu: " + ", ".join(m["nome"].strip() for m in musicas),
         f"numMusicas : var #1",
         f"static numMusicas + #0, #{n}",
         f"tabMusicas : var #{n}           ; endereco do mapa de cada musica",
         *[f"static tabMusicas + #{i}, #musica{i}" for i in range(n)],
         f"tabOndas : var #{n}             ; forma de onda de cada musica",
         *[f"static tabOndas + #{i}, #{m['onda']}" for i, m in enumerate(musicas)],
         f"tabNomes : var #{n}             ; nome no menu (20 caracteres)",
         *[f"static tabNomes + #{i}, #nomeMusica{i}" for i in range(n)],
         f"tabPainel : var #{n}            ; 3 linhas do painel (9 caracteres + \\0 cada = 10 palavras)",
         *[f"static tabPainel + #{i}, #painel{i}L0" for i in range(n)],
         ""]
    for i, m in enumerate(musicas):
        L.append(f"; ---- musica {i}: {m['nome'].strip()} (tools/musicas/{m['arquivo']}) ----")
        L.append(f'nomeMusica{i} : string "{m["nome"]}"')
        for k, linha in enumerate(m["painel"]):
            L.append(f'painel{i}L{k} : string "{linha}"')
        L.append(f"musica{i} : var #{len(m['mapa']) + 1}        ; 1 palavra por frame + marcador de fim")
        for f_, palavra in enumerate(m["mapa"]):
            if palavra:
                pistas = "".join("DFJK"[p] for p in range(4) if palavra & (1 << p))
                nota = nome_midi(((palavra >> 4) & 63) + MIDI_BASE)
                L.append(f"static musica{i} + #{f_}, #{palavra}\t\t; pistas {pistas:<4} nota {nota:<4} {palavra >> 10} frames")
        L.append(f"static musica{i} + #{len(m['mapa'])}, #{FIM}\t\t; fim da musica")
        L.append("")
    L.append("; freqs[i] = frequencia em Hz da nota de indice i (indice 1 = C3, sobe de semitom em semitom)")
    L.append(f"freqs : var #{MAX_INDICE + 1}")
    for i in range(1, MAX_INDICE + 1):
        L.append(f"static freqs + #{i}, #{freq_hz(i + MIDI_BASE)}\t\t; {nome_midi(i + MIDI_BASE)}")
    L.append("; <<< MUSICA")
    return "\n".join(L)


MS_POR_FRAME_PADRAO = 65   # nivel de velocidade 5 do jogo


def valida(caminho):
    """Confere uma partitura e avisa sobre trechos dificeis ou impossiveis de jogar."""
    info = le_partitura(caminho)
    mapa, usadas, total = gera_mapa(caminho, info)
    erros, avisos = [], []
    ultimo = [None] * 4                       # ultimo frame com nota em cada pista
    for frame, palavra in enumerate(mapa):
        if not palavra:
            continue
        pistas = [p for p in range(4) if palavra & (1 << p)]
        if len(pistas) >= 3:
            avisos.append(f"frame {frame}: {len(pistas)} notas juntas (acordes de 3+ notas sao muito dificeis)")
        for p in pistas:
            if ultimo[p] is not None:
                distancia = frame - ultimo[p]
                if distancia < 2:
                    erros.append(f"frame {frame}: pista {'DFJK'[p]} com notas a {distancia} frame de distancia "
                                 f"(ficam grudadas na tela; aumente slots_por_tempo ou troque a pista)")
                elif distancia < 3:
                    avisos.append(f"frame {frame}: pista {'DFJK'[p]} com notas a {distancia} frames (muito rapido)")
            ultimo[p] = frame
    for notas, tempos, num in info["eventos"]:
        if notas and round(tempos * info["slots_por_tempo"]) > 15:
            avisos.append(f"linha {num}: nota longa demais; o som dura no maximo 15 frames (a pausa continua normal)")
    segundos = len(mapa) * MS_POR_FRAME_PADRAO / 1000
    print(f"{caminho}: '{info['nome'].strip()}' - {total} notas, {len(mapa)} frames "
          f"(~{segundos:.0f} s no nivel 5), alturas: {', '.join(nome_midi(n) for n in sorted(usadas))}")
    for a in avisos[:20]:
        print(f"  AVISO: {a}")
    if len(avisos) > 20:
        print(f"  ... mais {len(avisos) - 20} avisos")
    for e in erros[:20]:
        print(f"  ERRO:  {e}")
    if len(erros) > 20:
        print(f"  ... mais {len(erros) - 20} erros")
    print("  OK: pronta para o jogo" if not erros else f"  {len(erros)} erro(s): corrija antes de usar")
    return not erros


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--validar":
        resultados = [valida(c) for c in sys.argv[2:]]
        sys.exit(0 if all(resultados) else 1)
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    caminho_asm, partituras = sys.argv[1], sys.argv[2:]
    musicas = []
    for caminho in partituras:
        info = le_partitura(caminho)
        mapa, usadas, total = gera_mapa(caminho, info)
        info.update(mapa=mapa, arquivo=caminho.replace("\\", "/").rsplit("/", 1)[-1])
        musicas.append(info)
        print(f"{caminho}: '{info['nome'].strip()}', {len(mapa)} frames, {total} notas para acertar, "
              f"alturas: {', '.join(nome_midi(n) for n in sorted(usadas))}")
    with open(caminho_asm, encoding="utf-8") as f:
        asm = f.read()
    inicio, fim = "; >>> MUSICA", "; <<< MUSICA"
    if inicio not in asm or fim not in asm:
        raise SystemExit("jogo.asm nao tem os marcadores '; >>> MUSICA' / '; <<< MUSICA'")
    novo = asm.split(inicio)[0] + bloco_asm(musicas) + asm.split(fim, 1)[1]
    with open(caminho_asm, "w", encoding="utf-8", newline="\n") as f:
        f.write(novo)


if __name__ == "__main__":
    main()
