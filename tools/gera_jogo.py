"""Regenera e monta o jogo com um comando so':

    1. sprites       -> charmap.mif            (tools/gera_charmap.py)
    2. telas         -> jogo.asm               (tools/gera_telas.py,  tools/telas/*.txt)
    3. musicas       -> jogo.asm               (tools/gera_musica.py, tools/musicas/lista.txt)
    4. montador      -> cpuram.mif

Uso (na raiz do projeto, depois de ./build.sh):
    python tools/gera_jogo.py
"""

import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTADOR = os.path.join(RAIZ, "Montador", "montador" + (".exe" if os.name == "nt" else ""))


def roda(descricao, comando):
    """Executa uma etapa e encerra o script se ela falhar."""
    print(f">> {descricao}")
    r = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:], sep="\n")
        sys.exit(f"falhou: {descricao}")
    return r.stdout


def main():
    if not os.path.exists(MONTADOR):
        sys.exit("montador nao encontrado: rode ./build.sh antes")
    py = sys.executable
    roda("sprites (charmap.mif)", [py, "tools/gera_charmap.py"])
    roda("telas", [py, "tools/gera_telas.py"])
    print(roda("musicas (tools/musicas/lista.txt)", [py, "tools/gera_musica.py"]), end="")
    saida = roda("montando jogo.asm -> cpuram.mif", [MONTADOR, "jogo.asm", "cpuram.mif"])
    if "Concluido" not in saida:
        print(saida[-3000:])
        sys.exit("o montador nao concluiu")
    print("OK: cpuram.mif pronto. Para jogar: ./Simulador/sim cpuram.mif charmap.mif")


if __name__ == "__main__":
    main()
