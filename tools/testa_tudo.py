"""Roda todos os testes do projeto (depois de ./build.sh e python tools/gera_jogo.py):

    1. partituras do menu         python tools/gera_musica.py --validar
    2. conversor de tablatura     python tools/testa_tab.py
    3. jogo inteiro (headless)    python tools/testa_jogo.py
    4. Simple Simulator           TesteCPU.asm, TesteExtra.asm e TesteSndn.asm

Uso (na raiz do projeto): python tools/testa_tudo.py
"""

import os
import re
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = ".exe" if os.name == "nt" else ""
PY = sys.executable

# Notas (frequencia, duracao, onda) que o testes/simples/TesteSndn.asm toca, na ordem
NOTAS_SNDN = [(262, 200, 1), (294, 150, 2), (262, 262, 262), (330, 100, 0), (349, 100, 3),
              (392, 390, 1), (440, 3, 0), (440, 2, 0), (440, 1, 0)]


def etapa(nome, comando, cwd=RAIZ, entrada=None):
    """Executa uma etapa dos testes e mostra a saida dela."""
    print(f"\n===== {nome} =====", flush=True)
    r = subprocess.run(comando, cwd=cwd, input=entrada, capture_output=True, text=True)
    print(r.stdout[-4000:], end="")
    if r.returncode != 0:
        print(r.stderr[-2000:])
    return r


def notas_do_grafico(mif):
    """Roda o programa no harness (mesmo Model.cpp do simulador grafico) e devolve as notas da SNDN."""
    r = subprocess.run([os.path.join(RAIZ, "tools", "headless", "headless" + EXE), mif,
                        os.path.join(RAIZ, "charmap.mif"), "--quiet"],
                       capture_output=True, text=True, timeout=60)
    return re.findall(r"SNDN\s+freq=\s*(\d+) Hz dur=\s*(\d+) ms onda=(\d+)", r.stdout)


def simple_simulator(programa, esperado, notas=()):
    """Monta o programa e confere a ultima linha impressa pelo Simple Simulator e as notas da SNDN."""
    with tempfile.TemporaryDirectory() as pasta:
        mif = os.path.join(pasta, "cpuram.mif")          # o simulador le cpuram.mif da pasta atual
        subprocess.run([os.path.join(RAIZ, "Montador", "montador" + EXE),
                        os.path.join(RAIZ, "testes", "simples", programa), mif],
                       capture_output=True, check=True)
        r = subprocess.run([os.path.join(RAIZ, "SimpleSimulator", "simples" + EXE)], cwd=pasta,
                           input="q\n", capture_output=True, text=True, timeout=60)
        grafico = notas_do_grafico(mif) if notas else []
    lidas = re.findall(r"\[SNDN\] freq=(\d+) dur=(\d+) onda=(\d+)", r.stdout)
    tela = re.sub(r"\[SNDN\][^\n]*\n", "", r.stdout).strip()
    saida = tela.splitlines()[-1] if tela else ""
    ok = saida == esperado
    print(f"[{'OK   ' if ok else 'FALHA'}] {programa}: '{saida}' (esperado '{esperado}')")
    esperadas = [tuple(str(campo) for campo in nota) for nota in notas]
    if lidas != esperadas:
        ok = False
        print(f"[FALHA] {programa}: notas {lidas} (esperado {esperadas})")
    if grafico != esperadas:
        ok = False
        print(f"[FALHA] {programa}: simulador grafico tocou {grafico} (esperado {esperadas})")
    if notas and ok:
        print(f"[OK   ] {programa}: {len(lidas)} notas da SNDN, iguais nos dois simuladores")
    return ok


def main():
    resultados = {
        "partituras": etapa("1. partituras do menu", [PY, "tools/gera_musica.py", "--validar"]).returncode == 0,
        "tablatura": etapa("2. conversor de tablatura", [PY, "tools/testa_tab.py"]).returncode == 0,
        "jogo": etapa("3. jogo (harness headless)", [PY, "tools/testa_jogo.py"]).returncode == 0,
    }
    print("\n===== 4. Simple Simulator =====")
    resultados["simple simulator"] = (simple_simulator("TesteCPU.asm", "ABCDEFGHIJKLMNOP")
                                      & simple_simulator("TesteExtra.asm", "abcdefghij")
                                      & simple_simulator("TesteSndn.asm", "abcdef", NOTAS_SNDN))

    print("\n===== resumo =====")
    for nome, ok in resultados.items():
        print(f"[{'OK   ' if ok else 'FALHA'}] {nome}")
    sys.exit(0 if all(resultados.values()) else 1)


if __name__ == "__main__":
    if not os.path.exists(os.path.join(RAIZ, "Montador", "montador" + EXE)):
        sys.exit("binarios nao encontrados: rode ./build.sh antes")
    main()
