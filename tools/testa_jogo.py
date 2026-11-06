"""Testes automaticos do Guitar Hero ICMC, rodando o jogo no harness headless.

Cada cenario joga a musica inteira no nivel de velocidade 9 (o mais rapido, para
o teste terminar logo) e confere a caixa de FIM DE JOGO na tela final.

Uso (na raiz do projeto, depois de ./build.sh e python tools/gera_jogo.py):
    python tools/testa_jogo.py
"""

import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(RAIZ, "tools", "headless", "headless" + (".exe" if os.name == "nt" else ""))
# Nivel 9 = frames de 22 ms = ~115 mil instrucoes (clock de 5 MHz). A Ode tem 384
# frames: a partida acaba por volta de 48 milhoes de ciclos.
CICLOS = "80000000"
INICIO = ["--key", "300000:9", "--key", "350000: "]   # nivel 9 no menu e depois ESPACO


MSYS2_BIN = r"C:\msys64\ucrt64\bin"


def ambiente():
    """Variaveis de ambiente para rodar o harness."""
    # No Windows o harness precisa das DLLs do MSYS2 (GTK/glib). Outras copias no
    # PATH (ex.: a do Git) sao incompativeis e o Windows aborta com 0xC0000139.
    env = os.environ.copy()
    if os.name == "nt" and os.path.isdir(MSYS2_BIN):
        env["PATH"] = MSYS2_BIN + os.pathsep + env.get("PATH", "")
    return env


def roda(*args):
    """Executa o jogo no harness headless e devolve o que ele imprimiu."""
    r = subprocess.run([HARNESS, "cpuram.mif", "charmap.mif", *args], cwd=RAIZ,
                       capture_output=True, text=True, timeout=600, env=ambiente())
    if r.returncode != 0:
        raise AssertionError(f"harness terminou com codigo {r.returncode}:\n{r.stderr}")
    return r.stdout


def ultima_tela(saida):
    """Devolve a ultima tela impressa pelo harness."""
    return saida.rsplit("---- tela no ciclo", 1)[1]


def resultado(saida):
    """Le os numeros da caixa de FIM DE JOGO na ultima tela."""
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


def musicas_do_jogo():
    """Le do jogo.asm as musicas geradas: [(indice, nome, frames), ...] na ordem do menu."""
    with open(os.path.join(RAIZ, "jogo.asm"), encoding="utf-8") as f:
        asm = f.read()
    nomes = re.findall(r'^nomeMusica(\d+) : string "(.*)"', asm, re.M)
    tamanhos = dict(re.findall(r"^musica(\d+) : var #(\d+)", asm, re.M))
    return [(int(i), nome.strip(), int(tamanhos[i])) for i, nome in nomes]


def som(saida):
    """Le o resumo de som do harness: (notas, SOUND, SNDN, ms de CPU travada)."""
    m = re.search(r"som: (\d+) notas \((\d+) bloqueantes / SOUND, (\d+) nao-bloqueantes / SNDN\); "
                  r"CPU travada por (\d+) ms", saida)
    return tuple(int(g) for g in m.groups())


PERFEITO_TUDO = dict(pontos=1920, acertos=63, total=63, combo_max=63, precisao=100, conceito="S")
QUASE_TUDO = dict(pontos=960, acertos=63, total=63, combo_max=63, precisao=100, conceito="S")

CENARIOS = [
    ("robo acerta tudo no alvo (linha 25)", ["--autoplay"], PERFEITO_TUDO),
    ("robo acerta 1 linha antes (24): ainda PERFEITO", ["--autoplay-linha", "24"], PERFEITO_TUDO),
    ("robo acerta 1 linha depois (26): ainda PERFEITO", ["--autoplay-linha", "26"], PERFEITO_TUDO),
    ("robo acerta 2 linhas antes (23): QUASE", ["--autoplay-linha", "23"], QUASE_TUDO),
    ("robo acerta 2 linhas depois (27): QUASE", ["--autoplay-linha", "27"], QUASE_TUDO),
    # Linha 21: mesmo que a tecla so' seja lida no frame seguinte, a nota estara' na
    # linha 22, ainda fora da janela de acerto (23..27).
    ("robo aperta cedo demais (fora da janela)", ["--autoplay-linha", "21"],
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

    # Demais musicas do menu (tecla M): o robo tem que acertar todas as notas de cada
    # uma, quantas forem. Assim o teste vale para qualquer partitura nova.
    for indice, nome, frames in musicas_do_jogo()[1:]:
        teclas = ["--key", "300000:9"]
        for k in range(indice):
            teclas += ["--key", f"{310000 + k * 10000}:m"]
        ciclos = str((frames + 40) * 130000)            # ~115 mil instrucoes por frame no nivel 9
        saida = roda(*teclas, "--key", "400000: ", "--autoplay", "--cycles", ciclos)
        r2 = resultado(saida)
        notas, bloqueantes, sndn, travado = som(saida)
        ok = r2["acertos"] == r2["total"] > 0 and r2["conceito"] == "S" and bloqueantes == 0 and sndn > 0
        falhas += not ok
        print(f"[{'OK   ' if ok else 'FALHA'}] musica {indice + 1} '{nome}' (tecla M x{indice}): "
              f"{r2['acertos']}/{r2['total']} acertos, {r2['pontos']} pontos, conceito {r2['conceito']}, "
              f"{sndn} notas via SNDN")

    # Tecla sem nota: o alvo da pista fica preenchido (sprites 18-20, "{O}" no harness),
    # sem faisca, e conta um erro. A 1a nota so' chega ao alvo no frame 22, entao uma
    # tecla logo no inicio da partida nunca acerta nada.
    # (1o print depois do inicio do frame seguinte, quando o placar e' redesenhado,
    #  mas antes de vencerem os 3 frames do preenchimento)
    saida = roda("--key", "300000:9", "--key", "350000: ", "--key", "600000:f",
                 "--dump", "760000", "--dump", "1500000", "--cycles", "1500001", "--quiet")
    telas = saida.split("---- tela no ciclo ")[1:]
    alvos_logo = telas[0].splitlines()[26]          # linha 25 da tela (1a linha e' o cabecalho)
    alvos_depois = telas[1].splitlines()[26]
    erros_hud = telas[0].splitlines()[18]           # linha 17: valor de ERROS
    ok = ("[_]:{O}:[_]" in alvos_logo and "*" not in alvos_logo and "001" in erros_hud
          and "[_]:[_]:[_]:[_]" in alvos_depois)
    falhas += not ok
    print(f"[{'OK   ' if ok else 'FALHA'}] tecla sem nota: alvo preenchido, sem faisca, 1 erro, e depois volta ao normal")
    if not ok:
        print(alvos_logo, erros_hud, alvos_depois, sep="\n")

    # Animacao em meia linha: na metade de cada frame a nota aparece partida em duas
    # linhas ("/=\" em cima e "\=/" logo abaixo, na mesma coluna); no resto, inteira.
    dumps = [a for t in range(400000, 3400000, 10000) for a in ("--dump", str(t))]
    saida = roda("--key", "300000:9", "--key", "350000: ", *dumps, "--cycles", "3400001", "--quiet")
    meia = inteira = False
    for tela in saida.split("---- tela no ciclo ")[1:]:
        linhas = tela.splitlines()[1:]
        inteira |= any("(=)" in l for l in linhas)
        for a, b in zip(linhas, linhas[1:]):
            col = a.find("/=\\")
            if col >= 0 and b[col:col + 3] == "\\=/":
                meia = True
    ok = meia and inteira
    falhas += not ok
    print(f"[{'OK   ' if ok else 'FALHA'}] animacao: nota inteira e em meia linha "
          f"(inteira={inteira}, meia linha={meia})")

    # Reinicio: depois do fim de jogo, ESPACO volta ao menu e ESPACO de novo comeca
    # uma partida nova com o placar zerado.
    # (1 milhao de ciclos depois do 2o ESPACO = ~8 frames: nenhuma nota chegou ao alvo ainda)
    saida = roda(*INICIO, "--autoplay", "--key", "70000000: ", "--key", "71000000: ",
                 "--cycles", "72000000")
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
