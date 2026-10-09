"""Converte uma partitura em texto (tools/musicas/*.txt) no mapa de notas do jogo.

Formato da partitura (uma nota por linha, comentarios com '#'):

    # comentario: linha comecando com '#', ou '#' depois de um espaco
    slots_por_tempo 6          # quantos frames do jogo dura 1 tempo (seminima)
    pistas G3=0 C4=0 D4=1 ...  # (opcional) pista de cada altura; senao e' automatico
    E4 1                        # nota e duracao em tempos (1 = seminima, 0.5 = colcheia)
    D4 1.5                      # pontuada
    - 1                         # pausa
    C4+G4 2                     # acorde: duas notas caem juntas (a 1a e' a que toca)

Cada frame do jogo corresponde a uma palavra de 16 bits no vetor `musica`:

    bits  3-0  : mascara das pistas que recebem nota neste frame (bit0 = D ... bit3 = K)
    bits  9-4  : indice da nota na tabela `freqs` (0 = nao toca nada)
    bits 13-10 : duracao da nota, em frames (maximo 15)
    65535      : fim da musica

O script substitui, no jogo.asm, o bloco entre '; >>> MUSICA' e '; <<< MUSICA'.

Uso:
    python tools/gera_musica.py jogo.asm tools/musicas/ode_alegria.txt
"""

import re
import sys

NOMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MIDI_BASE = 47          # indice 1 da tabela = MIDI 48 = C3
MAX_INDICE = 63         # 6 bits
FIM = 65535


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


def le_partitura(caminho):
    slots_por_tempo, mapa, eventos = 4, {}, []
    with open(caminho, encoding="utf-8") as f:
        for num, linha in enumerate(f, 1):
            # '#' so' e' comentario no inicio da linha ou depois de espaco ("F#3" e' sustenido)
            linha = "" if linha.lstrip().startswith("#") else re.sub(r"\s#.*$", "", linha).strip()
            if not linha:
                continue
            partes = linha.split()
            if partes[0] == "slots_por_tempo":
                slots_por_tempo = int(partes[1])
            elif partes[0] == "pistas":
                for item in partes[1:]:
                    nota, pista = item.split("=")
                    mapa[midi(nota)] = int(pista)
            else:
                if len(partes) != 2:
                    raise SystemExit(f"{caminho}:{num}: esperado 'NOTA DURACAO'")
                notas = [] if partes[0] == "-" else [midi(n) for n in partes[0].split("+")]
                eventos.append((notas, float(partes[1]), num))
    return slots_por_tempo, mapa, eventos


def pistas_automaticas(eventos):
    alturas = sorted({n for notas, _, _ in eventos for n in notas})
    return {n: i * 4 // len(alturas) for i, n in enumerate(alturas)}


def gera(caminho):
    slots_por_tempo, mapa, eventos = le_partitura(caminho)
    if not mapa:
        mapa = pistas_automaticas(eventos)
    musica, usadas, total_notas = [], set(), 0
    for notas, tempos, num in eventos:
        slots = round(tempos * slots_por_tempo)
        if slots < 1 or abs(slots - tempos * slots_por_tempo) > 1e-9:
            raise SystemExit(f"{caminho}:{num}: duracao {tempos} nao vira um numero inteiro de frames")
        palavra = 0
        if notas:
            mascara = 0
            for n in notas:
                if n not in mapa:
                    raise SystemExit(f"{caminho}:{num}: nota {nome_midi(n)} sem pista definida")
                mascara |= 1 << mapa[n]
            indice = notas[0] - MIDI_BASE
            if not 1 <= indice <= MAX_INDICE:
                raise SystemExit(f"{caminho}:{num}: nota {nome_midi(notas[0])} fora da faixa C3..D8")
            usadas.add(notas[0])
            total_notas += bin(mascara).count("1")
            palavra = mascara | (indice << 4) | (min(slots, 15) << 10)
        musica.append(palavra)
        musica.extend([0] * (slots - 1))
    return musica, usadas, total_notas, slots_por_tempo


def bloco_asm(musica, origem):
    linhas = [f"; >>> MUSICA  (gerado por tools/gera_musica.py a partir de {origem} - nao edite a mao)",
              f"musica : var #{len(musica) + 1}        ; 1 palavra por frame + marcador de fim"]
    for i, palavra in enumerate(musica):
        if palavra:
            pistas = "".join("DFJK"[p] for p in range(4) if palavra & (1 << p))
            nota = nome_midi(((palavra >> 4) & 63) + MIDI_BASE)
            linhas.append(f"static musica + #{i}, #{palavra}\t\t; pistas {pistas:<4} nota {nota:<4} {palavra >> 10} frames")
    linhas.append(f"static musica + #{len(musica)}, #{FIM}\t\t; fim da musica")
    linhas.append("")
    linhas.append("; freqs[i] = frequencia em Hz da nota de indice i (indice 1 = C3, sobe de semitom em semitom)")
    linhas.append(f"freqs : var #{MAX_INDICE + 1}")
    for i in range(1, MAX_INDICE + 1):
        n = i + MIDI_BASE
        linhas.append(f"static freqs + #{i}, #{freq_hz(n)}\t\t; {nome_midi(n)}")
    linhas.append("; <<< MUSICA")
    return "\n".join(linhas)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    caminho_asm, caminho_musica = sys.argv[1], sys.argv[2]
    musica, usadas, total_notas, spt = gera(caminho_musica)
    with open(caminho_asm, encoding="utf-8") as f:
        asm = f.read()
    inicio, fim = "; >>> MUSICA", "; <<< MUSICA"
    if inicio not in asm or fim not in asm:
        raise SystemExit("jogo.asm nao tem os marcadores '; >>> MUSICA' / '; <<< MUSICA'")
    novo = asm.split(inicio)[0] + bloco_asm(musica, caminho_musica.replace("\\", "/")) + asm.split(fim, 1)[1]
    with open(caminho_asm, "w", encoding="utf-8", newline="\n") as f:
        f.write(novo)
    print(f"{caminho_musica}: {len(musica)} frames ({len(musica) / spt:.0f} tempos), "
          f"{total_notas} notas para acertar, alturas usadas: {', '.join(nome_midi(n) for n in sorted(usadas))}")


if __name__ == "__main__":
    main()
