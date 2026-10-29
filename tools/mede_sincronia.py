"""Mede a sincronia entre a musica e o tempo do jogo, no harness headless.

Joga a 1a musica no nivel de velocidade 5 e, para cada nota tocada pela SNDN,
compara a duracao pedida (ms) com o tempo real ate a nota seguinte, calculado
pelos ciclos com o clock fixo do simulador (5 MHz = 5000 instrucoes por ms).
Se as duas coisas batem, cada nota acaba exatamente quando a proxima comeca.

Uso (na raiz do projeto): python tools/mede_sincronia.py
"""

import os
import re
import subprocess

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(RAIZ, "tools", "headless", "headless" + (".exe" if os.name == "nt" else ""))
INSTRUCOES_POR_MS = 5000          # CLOCK_HZ = 5 MHz

env = os.environ.copy()
if os.name == "nt" and os.path.isdir(r"C:\msys64\ucrt64\bin"):
    env["PATH"] = r"C:\msys64\ucrt64\bin" + os.pathsep + env["PATH"]

# nivel padrao (5), ESPACO, musica inteira; mostra ate' 40 notas no log
saida = subprocess.run([HARNESS, "cpuram.mif", "charmap.mif", "--key", "350000: ", "--cycles", "60000000", "--quiet"],
                       cwd=RAIZ, capture_output=True, text=True, env=env).stdout
notas = [(int(c), int(d)) for c, d in re.findall(r"ciclo\s+(\d+)\s+SNDN\s+freq=\s*\d+ Hz dur=\s*(\d+) ms", saida)]

piores = 0
print(f"{'nota':>4} {'duracao pedida':>15} {'ate a proxima':>14} {'diferenca':>10}")
for i in range(len(notas) - 1):
    ciclo, dur = notas[i]
    real = (notas[i + 1][0] - ciclo) / INSTRUCOES_POR_MS
    dif = real - dur
    piores = max(piores, abs(dif) / dur)
    if i < 12:
        print(f"{i + 1:>4} {dur:>12} ms {real:>11.1f} ms {dif:>+8.1f} ms")
print(f"... {len(notas)} notas analisadas; maior diferenca: {piores * 100:.1f}% da duracao da nota")
