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

## Como rodar o jogo

**1. Instale as dependências** (só na primeira vez)

- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt install build-essential pkg-config libgtk2.0-dev libsdl2-dev python3
  ```
- **Windows:** instale o [MSYS2](https://www.msys2.org/) e o Python. Depois, abra o terminal
  **MSYS2 UCRT64** e rode:
  ```bash
  pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-gtk2 mingw-w64-ucrt-x86_64-SDL2 mingw-w64-ucrt-x86_64-pkgconf
  ```

No Windows, use o terminal **MSYS2 UCRT64** em todos os passos seguintes. Em outro terminal, como o
Git Bash, acrescente `C:\msys64\ucrt64\bin` ao `PATH` para os programas acharem as bibliotecas.

**2. Entre na pasta do projeto**

```bash
cd guitar-hero-icmc
```

**3. Compile os programas** (só na primeira vez ou depois de mudar o código em C/C++; feche o simulador antes)

```bash
./build.sh
```

**4. Gere e monte o jogo** (só depois de mudar músicas, telas, sprites ou o `jogo.asm`)

```bash
python tools/gera_jogo.py
```

**5. Abra o simulador**

```bash
./Simulador/sim cpuram.mif charmap.mif
```

No Windows, o programa se chama `sim.exe`:

```bash
./Simulador/sim.exe cpuram.mif charmap.mif
```

**6. Jogue**

1. Aperte **Home** na janela do simulador para iniciar a execução automática.
2. No menu, escolha a velocidade com `1` a `9` e troque de música com `M`.
3. Aperte `ESPAÇO` para começar.
4. Use `D` `F` `J` `K` quando a nota estiver sobre o alvo.

Para conferir se está tudo funcionando, rode os testes:

```bash
python tools/testa_tudo.py
```

## Como jogar

| Tecla | Ação |
|---|---|
| `1` … `9` (no menu) | escolhe a velocidade |
| `M` (no menu) | troca a música |
| `ESPAÇO` | começa a música / joga de novo |
| `D` `F` `J` `K` | acerta a nota da pista verde, vermelha, amarela, azul |

- **No alvo, com folga de 1 linha:** 10 pontos (`PERFEITO!`) e uma faísca
- **A 2 linhas do alvo:** 5 pontos (`QUASE`) e uma faísca
- **A cada 10 acertos seguidos** o multiplicador sobe, até **x4**
- **Deixar a nota passar** zera o combo (`ERROU!`)
- **Apertar sem nota por perto** preenche o alvo da pista e zera o combo

A música toca sozinha, e cada nota soa no instante em que chega ao alvo. No fim aparecem pontos,
acertos, combo máximo, precisão e um conceito (S, A, B, C, D).

## Modificação na arquitetura: instrução `SNDN`

A instrução original `SOUND Rx, Ry, Rz` **trava a CPU** até a nota terminar; num jogo de ritmo, as notas
param de cair enquanto a música toca. A nova **`SNDN Rx, Ry, Rz`** recebe os mesmos operandos
(frequência em Hz, duração em ms, forma de onda), mas só inicia a nota e devolve o controle na hora.

| | |
|---|---|
| **Opcode** | `110110` (54), livre, vizinho de `SOUND` (`110100`) e `INCHAR` (`110101`) |
| **Formato** | `110110 \| Rx \| Ry \| Rz \| 0`, uma palavra, igual ao `SOUND` |
| **Semântica** | interrompe a nota que estiver tocando e começa a nova (monofônico) |
| **Resultado** | música inteira: CPU travada **24 960 ms** com `SOUND` e **0 ms** com `SNDN` |

Implementada no simulador (`Simulador/`) e no montador (`Montador/`): veja
[docs/nova_instrucao.md](docs/nova_instrucao.md).

**Outras melhorias no simulador:** clock fixo de 5 MHz (o jogo tem a mesma velocidade em qualquer
computador e a janela redesenha sem trancos), áudio funcionando no Windows, volume menor, sem estalos
e com ~12 ms de latência.

## Simple Simulator (requisito 2)

[`SimpleSimulator/simple_simulator.c`](SimpleSimulator/simple_simulator.c) é o processador ICMC
**ciclo a ciclo** em C, a partir do template da disciplina (estados `FETCH → DECODE → EXECUTE`,
muxes `M1`–`M6`, ULA e sinais de controle), com todas as instruções completadas. Os testes
`testes/simples/TesteCPU.asm` e `TesteExtra.asm` rodam no `python tools/testa_tudo.py`.

## Músicas

As músicas do menu e a ordem delas ficam em **`tools/musicas/lista.txt`**, um arquivo por linha.

- **Escrever uma partitura:** formato em [docs/formato_partitura.md](docs/formato_partitura.md)
  (inclui um prompt pronto para pedir a transcrição a um modelo de IA).
- **Converter uma tablatura** em texto (padrão Cifra Club):
  ```bash
  python tools/tab_para_jogo.py minha_tab.txt -o tools/musicas/minha_tab.txt --nome "MINHA TAB"
  ```
  O ritmo é deduzido do espaçamento da tab; use `--max-tempos 1.5` para encurtar pausas longas e
  `--frames-por-unidade 6` para deixar a música mais lenta.
- **Colocar no jogo:** acrescente o nome do arquivo em `tools/musicas/lista.txt` e rode
  `python tools/gera_jogo.py`.
- **Conferir:** `python tools/gera_musica.py --validar` aponta notas fora da faixa ou impossíveis de jogar.

> Músicas comerciais são protegidas por direito autoral. Se o repositório for público, prefira obras
> em domínio público (como a Ode à Alegria) ou composições próprias.

## Testes

```bash
python tools/testa_tudo.py
```

Confere as partituras, o conversor de tablatura, o jogo inteiro (um "robô" joga cada música do menu
no simulador sem janela e o teste confere pontos, janelas de acerto, efeitos visuais e reinício) e o
Simple Simulator. Leva cerca de 10 segundos.

## Estrutura do repositório

```
jogo.asm                 o jogo (Assembly do Processador ICMC, comentado linha a linha)
cpuram.mif, charmap.mif  jogo montado e caracteres com os sprites do jogo
build.sh                 compila os programas em C/C++
Simulador/               simulador gráfico (GTK2 + SDL2) com SNDN, clock fixo e áudio corrigido
Montador/                montador com a instrução SNDN
SimpleSimulator/         processador ciclo a ciclo em C (requisito 2)
docs/                    documentação técnica (PDF), nova instrução e formato de partitura
tools/
  gera_jogo.py           regenera tudo e monta o jogo (usa os três geradores abaixo)
  gera_charmap.py        sprites -> charmap.mif
  gera_telas.py          tools/telas/*.txt -> telas do jogo.asm
  gera_musica.py         tools/musicas/*.txt (lista.txt) -> músicas do jogo.asm
  tab_para_jogo.py       tablatura em texto -> partitura do jogo
  gera_doc.py            docs/documentacao_tecnica.md -> PDF
  testa_tudo.py          roda todos os testes (testa_jogo.py, testa_tab.py, Simple Simulator)
  headless/              simulador sem janela usado pelos testes (mesmo Model.cpp)
  versao_sound.py, mede_sincronia.py   comparação SOUND x SNDN e medição da sincronia
testes/                  programas de teste (som, clock, áudio, Simple Simulator)
```

A documentação técnica completa (dados, tempo, cada subrotina, ferramentas e testes) está em
[docs/documentacao_tecnica.pdf](docs/documentacao_tecnica.pdf). Para regenerá-la depois de mudar o
texto em `docs/documentacao_tecnica.md`: `python tools/gera_doc.py`.
