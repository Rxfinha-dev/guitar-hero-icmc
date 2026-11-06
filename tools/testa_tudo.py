"""Roda todos os testes do projeto (depois de ./build.sh e python tools/gera_jogo.py):

    1. partituras do menu         python tools/gera_musica.py --validar
    2. conversor de tablatura     python tools/testa_tab.py
    3. jogo inteiro (headless)    python tools/testa_jogo.py
    4. Simple Simulator           TesteCPU.asm e TesteExtra.asm

Uso (na raiz do projeto): python tools/testa_tudo.py
"""

import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = ".exe" if os.name == "nt" else ""
PY = sys.executable


def etapa(nome, comando, cwd=RAIZ, entrada=None):
    """Executa uma etapa dos testes e mostra a saida dela."""
    print(f"\n===== {nome} =====", flush=True)
    r = subprocess.run(comando, cwd=cwd, input=entrada, capture_output=True, text=True)
    print(r.stdout[-4000:], end="")
    if r.returncode != 0:
        print(r.stderr[-2000:])
    return r


def simple_simulator(programa, esperado):
    """Monta o programa e confere a ultima linha impressa pelo Simple Simulator."""
    with tempfile.TemporaryDirectory() as pasta:
        mif = os.path.join(pasta, "cpuram.mif")          # o simulador le cpuram.mif da pasta atual
        subprocess.run([os.path.join(RAIZ, "Montador", "montador" + EXE),
                        os.path.join(RAIZ, "testes", "simples", programa), mif],
                       capture_output=True, check=True)
        r = subprocess.run([os.path.join(RAIZ, "SimpleSimulator", "simples" + EXE)], cwd=pasta,
                           input="q\n", capture_output=True, text=True, timeout=60)
    saida = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    ok = saida == esperado
    print(f"[{'OK   ' if ok else 'FALHA'}] {programa}: '{saida}' (esperado '{esperado}')")
    return ok


def main():
    resultados = {
        "partituras": etapa("1. partituras do menu", [PY, "tools/gera_musica.py", "--validar"]).returncode == 0,
        "tablatura": etapa("2. conversor de tablatura", [PY, "tools/testa_tab.py"]).returncode == 0,
        "jogo": etapa("3. jogo (harness headless)", [PY, "tools/testa_jogo.py"]).returncode == 0,
    }
    print("\n===== 4. Simple Simulator =====")
    resultados["simple simulator"] = (simple_simulator("TesteCPU.asm", "ABCDEFGHIJKLMNOP")
                                      & simple_simulator("TesteExtra.asm", "abcdefghij"))

    print("\n===== resumo =====")
    for nome, ok in resultados.items():
        print(f"[{'OK   ' if ok else 'FALHA'}] {nome}")
    sys.exit(0 if all(resultados.values()) else 1)


if __name__ == "__main__":
    if not os.path.exists(os.path.join(RAIZ, "Montador", "montador" + EXE)):
        sys.exit("binarios nao encontrados: rode ./build.sh antes")
    main()
