"""Testes automaticos do Guitar Hero ICMC, rodando o jogo no harness headless.

Cada cenario joga a musica inteira no nivel de velocidade 9 (o mais rapido, para
o teste terminar logo) e confere a caixa de FIM DE JOGO na tela final.

Uso (na raiz do projeto, depois de ./build.sh e de montar o cpuram.mif):
    python tools/testa_jogo.py
"""

import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(RAIZ, "tools", "headless", "headless" + (".exe" if os.name == "nt" else ""))
CICLOS = "230000000"
INICIO = ["--key", "300000:9", "--key", "350000: "]   # nivel 9 no menu e depois ESPACO
TOTAL_NOTAS = 63


def roda(*args):
    r = subprocess.run([HARNESS, "cpuram.mif", "charmap.mif", *args], cwd=RAIZ,
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise AssertionError(f"harness terminou com codigo {r.returncode}:\n{r.stderr}")
    return r.stdout


def ultima_tela(saida):
    return saida.rsplit("---- tela no ciclo", 1)[1]


def resultado(saida):
    tela = ultima_tela(saida)
    def num(rotulo, padrao=r"(\d+)"):
        m = re.search(rotulo + r"\s+" + padrao, tela)
        if not m:
            raise AssertionError(f"'{rotulo}' nao encontrado na tela final:\n{tela}")
        return m.groups()
    return {
        "pontos": int(num("PONTOS")[0]),
        "acertos": int(num("ACERTOS", r"(\d+)/")[0]),
        "total": int(num("ACERTOS", r"\d+/(\d+)")[0]),
        "combo_max": int(num("COMBO MAX")[0]),
        "precisao": int(num("PRECISAO", r"(\d+)%")[0]),
        "conceito": num("CONCEITO", r"([SABCD])")[0],
    }


def som(saida):
    m = re.search(r"som: (\d+) notas \((\d+) bloqueantes / SOUND, (\d+) nao-bloqueantes / SNDN\); "
                  r"CPU travada por (\d+) ms", saida)
    return tuple(int(g) for g in m.groups())


CENARIOS = [
    ("robo acerta tudo no alvo", ["--autoplay"],
     dict(pontos=1920, acertos=63, total=63, combo_max=63, precisao=100, conceito="S")),
    ("robo acerta tudo uma linha antes (QUASE)", ["--autoplay-linha", "24"],
     dict(pontos=960, acertos=63, total=63, combo_max=63, precisao=100, conceito="S")),
    # Linha 22: mesmo que a tecla so' seja lida no frame seguinte, a nota estara' na
    # linha 23, ainda fora da janela de acerto (24..26).
    ("robo aperta cedo demais (fora da janela)", ["--autoplay-linha", "22"],
     dict(pontos=0, acertos=0, total=63, combo_max=0, precisao=0, conceito="D")),
    ("ninguem joga", [],
     dict(pontos=0, acertos=0, total=63, combo_max=0, precisao=0, conceito="D")),
]


def main():
    falhas = 0
    for nome, extra, esperado in CENARIOS:
        saida = roda(*INICIO, *extra, "--cycles", CICLOS)
        obtido = resultado(saida)
        diferencas = {k: (obtido[k], v) for k, v in esperado.items() if obtido[k] != v}
        notas, bloqueantes, sndn, travado = som(saida)
        if (notas, bloqueantes, sndn, travado) != (62, 0, 62, 0):
            diferencas["som"] = ((notas, bloqueantes, sndn, travado), (62, 0, 62, 0))
        status = "OK   " if not diferencas else "FALHA"
        falhas += bool(diferencas)
        print(f"[{status}] {nome}: {obtido['acertos']}/{obtido['total']} acertos, "
              f"{obtido['pontos']} pontos, conceito {obtido['conceito']}")
        for k, (o, e) in diferencas.items():
            print(f"         {k}: obtido {o}, esperado {e}")

    # Reinicio: depois do fim de jogo, ESPACO volta ao menu e ESPACO de novo comeca
    # uma partida nova com o placar zerado.
    # (8 milhoes de ciclos depois do 2o ESPACO = ~17 frames: nenhuma nota chegou ao alvo ainda)
    saida = roda(*INICIO, "--autoplay", "--key", "230000000: ", "--key", "231000000: ",
                 "--cycles", "239000000")
    tela = ultima_tela(saida)
    linha_placar = next((l for l in tela.splitlines() if "ODE A" in l), "")
    ok = "00000" in linha_placar and "FIM DE JOGO" not in tela
    falhas += not ok
    print(f"[{'OK   ' if ok else 'FALHA'}] reinicio: ESPACO no fim volta ao menu e a nova partida comeca zerada")
    if not ok:
        print(tela)

    print("\nTodos os testes passaram." if not falhas else f"\n{falhas} teste(s) falharam.")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
