"""Gera a versao "antes" do jogo, que usa a instrucao SOUND original (bloqueante)
no lugar da SNDN. Serve para demonstrar, lado a lado, o problema que a nova
instrucao resolve: com SOUND, a tela e o teclado congelam a cada nota.

Uso (na raiz do projeto):
    python tools/versao_sound.py
    Montador/montador testes/jogo_sound.asm testes/jogo_sound.mif
    Simulador/sim testes/jogo_sound.mif charmap.mif
"""

import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(RAIZ, "jogo.asm"), encoding="utf-8") as f:
    asm = f.read()

novo, trocas = re.subn(r"^(\s*)sndn(\s)", r"\1sound\2", asm, flags=re.MULTILINE)
if trocas != 1:
    raise SystemExit(f"esperava trocar 1 instrucao SNDN, troquei {trocas}")

cabecalho = ("; VERSAO 'ANTES' - gerada por tools/versao_sound.py\n"
             "; Igual ao jogo.asm, mas a melodia usa a instrucao SOUND original (bloqueante).\n\n")
destino = os.path.join(RAIZ, "testes", "jogo_sound.asm")
with open(destino, "w", encoding="utf-8", newline="\n") as f:
    f.write(cabecalho + novo)
print(f"gerado {os.path.relpath(destino, RAIZ)} (SNDN -> SOUND)")
