# Guitar Hero ICMC

Jogo de ritmo no estilo Guitar Hero escrito em **Assembly do Processador ICMC**, com uma
**instrução nova (`SNDN`)** adicionada ao processador para que a música toque sem travar o jogo.

Trabalho da disciplina **SSC0511 – Organização de Computadores Digitais** (ICMC-USP),
Prof. Eduardo do Valle Simões.

```
+--------------------------------------+
|         s GUITAR HERO ICMC s         |
|--------------------------------------|
|          :(=):   :   :   :           |
| MUSICA   :   :   :   :   : PONTOS    |
| ODE A    :   :   :   :   :  01000    |
| ALEGRIA  :   :   :   :   :           |
| BEETHOVEN:   :   :   :   : COMBO     |
|          :   :   :   :   :  040      |
|          :   :(=):   :   :           |
| TECLAS   :   :   :   :   : MULT      |
| D F J K  :   :   :   :   :  X4       |
|          :   :   :   :   :           |
| ACERTE AS:   :   :   :   : ACERTOS   |
| AS NOTAS :   :   :   :   :  040      |
| NO ALVO  :   :   :(=):   :           |
|          :   :   :   :   : ERROS     |
|          :   :   :   :   :  000      |
|          :   :   :   :(=):           |
| VELOC. 9 :   :   :   :   :           |
|          :   :   :   :   :           |
|          :   :   :(=):   :           |
|          :   :   :   :   :           |
|          :   :   :   :   :           |
|          :   :   :   :   :           |
|          :[_]:[*]:[_]:[_]:           |   <- alvos (com uma faisca de acerto)
|          : D : F : J : K :           |   <- teclas
|          :   PERFEITO!   :           |
|          :   :   :   :   :           |
+--------------------------------------+
```
*(tela real capturada em texto pelo harness de testes no meio de uma partida: `(=)` é uma nota,
`[_]` um alvo e `:` a divisória das pistas. No simulador eles são sprites coloridos.)*

## Vídeo

> **TODO:** link do vídeo explicando o projeto (YouTube/Drive).

## Como jogar

| Tecla | Ação |
|---|---|
| `1` … `9` (no menu) | escolhe a velocidade |
| `ESPAÇO` | começa a música / joga de novo |
| `D` `F` `J` `K` | acerta a nota da pista verde, vermelha, amarela, azul |

As notas descem pelas 4 pistas. Aperte a tecla da pista quando a nota estiver sobre o alvo:

- **No alvo:** 10 pontos (`PERFEITO!`)
- **Uma linha antes ou depois:** 5 pontos (`QUASE`)
- **A cada 10 acertos seguidos** o multiplicador sobe, até **x4**
- **Deixar a nota passar, ou apertar sem nota,** zera o combo

A música (*Ode à Alegria*, de Beethoven) toca sozinha: cada nota soa exatamente quando chega ao alvo.
No fim aparecem pontos, acertos, combo máximo, precisão e um conceito (S, A, B, C, D).

## Como montar e rodar

**Dependências:**
- **Linux (Debian/Ubuntu):** `sudo apt install build-essential pkg-config libgtk2.0-dev libsdl2-dev python3`
- **Windows:** [MSYS2](https://www.msys2.org/) UCRT64 com
  `pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-gtk2 mingw-w64-ucrt-x86_64-SDL2 mingw-w64-ucrt-x86_64-pkgconf`

```bash
./build.sh                                  # montador + simulador + Simple Simulator + harness de testes
./Montador/montador jogo.asm cpuram.mif     # monta o jogo
./Simulador/sim cpuram.mif charmap.mif      # roda (no Windows: .exe)
```

No simulador, aperte **Home** para executar em modo automático e depois use as teclas do jogo.

**Velocidade:** o simulador executa o mais rápido que o computador permite, então o ritmo
depende da máquina. Se as notas descerem rápido ou devagar demais, escolha outro nível (1 a 9) no menu.
O nível 5 foi calibrado para cerca de 20 milhões de instruções por segundo. Para medir a sua
máquina, rode `testes/calibra.asm`: após *N* segundos, velocidade ≈ (número da linha 0) × 20040 / *N*.

## Modificação na arquitetura: instrução `SNDN`

**O problema.** A instrução `SOUND Rx, Ry, Rz` do Processador ICMC **bloqueia a CPU** até a nota terminar
(`Sound.cpp` chama `beeper.wait()` e ainda reinicializa o SDL a cada nota). Num jogo de ritmo isso é fatal:
enquanto a música toca, as notas param de cair e o teclado não é lido.

**A solução.** A nova instrução **`SNDN Rx, Ry, Rz`** (*sound, non-blocking*) recebe os mesmos operandos,
mas apenas inicia a nota e devolve o controle à CPU no ciclo seguinte.

| | |
|---|---|
| **Sintaxe** | `SNDN Rx, Ry, Rz` (Rx = frequência em Hz, Ry = duração em ms, Rz = forma de onda 0–3) |
| **Opcode** | `110110` (54), um opcode livre da família de E/S, vizinho de `SOUND` (`110100`) e `INCHAR` (`110101`) |
| **Formato** | `110110 \| Rx(3) \| Ry(3) \| Rz(3) \| 0`, uma palavra, igual ao `SOUND` |
| **Semântica** | síntese monofônica: interrompe a nota que estiver tocando e começa a nova |

**Resultado medido** (música inteira no nível 5, com `tools/versao_sound.py` + harness):

| Versão | CPU travada pelo som |
|---|---|
| `SOUND` (original) | **24 960 ms**, a música inteira |
| `SNDN` (nova) | **0 ms** |

Os detalhes (motivação, decisões de projeto e cada arquivo alterado) estão em
[docs/nova_instrucao.md](docs/nova_instrucao.md).

## Simple Simulator (requisito 2)

[`SimpleSimulator/simple_simulator.c`](SimpleSimulator/simple_simulator.c) é o processador ICMC implementado
**ciclo a ciclo** em C, a partir do template do professor: estados `FETCH → DECODE → EXECUTE → EXECUTE2`,
muxes `M1`–`M6`, ULA e sinais de controle (`LoadPC`, `IncSP`, `RW`…). Todas as instruções foram completadas.

```bash
cd testes/simples && ../../Montador/montador TesteCPU.asm cpuram.mif && ../../SimpleSimulator/simples
# saída esperada: ABCDEFGHIJKLMNOP   (uma letra por instrução testada)
```

`testes/simples/TesteExtra.asm` cobre o que o `TesteCPU` não cobre e o jogo usa (`MOD`, `PUSH FR`/`POP FR`,
`MOV SP`, chamadas aninhadas, `jle`/`jeg`/`jel`). Saída esperada: `abcdefghij`, idêntica ao simulador gráfico.

## Estrutura do repositório

```
jogo.asm                 o jogo (Assembly do Processador ICMC, comentado linha a linha)
cpuram.mif               jogo montado
charmap.mif              charmap com os sprites do jogo (códigos 1..17)
build.sh                 compila tudo
Simulador/               simulador gráfico (GTK2 + SDL2) com a instrução SNDN
Montador/                montador com a instrução SNDN
SimpleSimulator/         processador ciclo a ciclo em C (requisito 2)
docs/nova_instrucao.md   documentação da modificação de arquitetura
tools/
  telas/*.txt            desenhos das telas (jogo, menu, fim de jogo)
  musicas/*.txt          partituras
  gera_telas.py          desenhos -> strings do jogo.asm
  gera_musica.py         partitura -> mapa de notas + tabela de frequências no jogo.asm
  gera_charmap.py        sprites -> charmap.mif
  versao_sound.py        gera a versão "antes" (com SOUND) para comparação
  testa_jogo.py          testes automáticos do jogo
  headless/              simulador sem janela, para testes (usa o mesmo Model.cpp)
testes/                  programas de teste e calibração
```

### Arquitetura do jogo

- **Tela:** 40 × 30. As notas nascem na linha 3, descem 1 linha por frame e o alvo fica na linha 25.
  A janela de acerto vai da linha 24 à 26.
- **Mapa da música:** uma palavra de 16 bits por frame. Bits 3–0: pistas que recebem nota.
  Bits 9–4: índice da nota em `freqs`. Bits 13–10: duração em frames. `65535` marca o fim.
- **Sincronia:** uma nota leva 22 frames da linha 3 ao alvo, então a melodia lê o mapa com 22 frames
  de atraso. O som sai no instante em que a nota passa pelo alvo.
- **Notas ativas:** 16 slots em vetores paralelos (`notaY`, `notaPista`).
- **Laço do jogo:** `MoveNotas → SpawnNotas → TocaMelodia (SNDN) → AtualizaEfeitos → AtualizaHUD → Delay`.
  O `Delay` lê o teclado a cada 5 instruções, então nenhuma tecla se perde.
- **Cenário:** os desenhos usam letras minúsculas como "códigos de sprite" (`p` = divisória,
  `e f g` = alvo verde…), traduzidas pela tabela `traduz`. As notas são apagadas
  **redesenhando o cenário por baixo**, assim a pista e o alvo nunca somem.

## Como criar novas músicas

1. Escreva a partitura em `tools/musicas/minha_musica.txt` (veja o formato em `ode_alegria.txt`:
   `NOTA DURAÇÃO`, acordes com `+`, pausas com `-`).
2. `python tools/gera_musica.py jogo.asm tools/musicas/minha_musica.txt`
3. Monte de novo o `cpuram.mif`. Se o número de notas mudar, atualize `TOTAL_NOTAS` e os valores esperados em `tools/testa_jogo.py`.

Para alterar telas ou sprites: edite `tools/telas/*.txt` ou `tools/gera_charmap.py` e rode
`python tools/gera_telas.py jogo.asm tools/telas/jogo.txt tools/telas/menu.txt tools/telas/fim.txt` ou
`python tools/gera_charmap.py <charmap original> charmap.mif`.

## Testes

```bash
python tools/testa_jogo.py
```

Os testes jogam a música inteira no harness headless, com um "robô" que lê a tela e aperta as teclas.
Cada cenário confere o resultado final:

| Cenário | Resultado esperado |
|---|---|
| acerta tudo no alvo | 63/63, 1920 pontos, conceito S |
| acerta tudo uma linha antes | 63/63, 960 pontos (`QUASE`) |
| aperta fora da janela | 0 acertos, conceito D |
| ninguém joga | 0 acertos, conceito D |
| reinício | `ESPAÇO` volta ao menu e a nova partida começa zerada |

Os testes também conferem as 62 notas da melodia tocadas via `SNDN`, com 0 ms de CPU travada.

## Autores

> **TODO:** nome e número USP de cada integrante do grupo.
