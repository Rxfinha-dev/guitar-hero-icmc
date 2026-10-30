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
| `M` (no menu) | troca a música |
| `ESPAÇO` | começa a música / joga de novo |
| `D` `F` `J` `K` | acerta a nota da pista verde, vermelha, amarela, azul |

As notas descem pelas 4 pistas. Aperte a tecla da pista quando a nota estiver sobre o alvo:

- **No alvo, com folga de 1 linha para cima ou para baixo:** 10 pontos (`PERFEITO!`) e uma faísca no alvo
- **A 2 linhas do alvo:** 5 pontos (`QUASE`) e uma faísca no alvo
- **A cada 10 acertos seguidos** o multiplicador sobe, até **x4**
- **Deixar a nota passar** zera o combo (`ERROU!`)
- **Apertar sem nota por perto:** o alvo da pista fica todo preenchido na cor dela e o combo zera
- **Duas notas da mesma pista na janela:** a tecla vale para a mais antiga (a mais baixa)

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

**Velocidade e sincronia:** o simulador roda com **clock fixo de 5 MHz** (`CLOCK_HZ` em
`Simulador/Mneumonicos.h`), como uma placa de verdade, em vez de "o mais rápido possível". Assim um
frame do jogo dura exatamente o que a tabela `tabMsFrame` diz (65 ms no nível 5), em qualquer computador,
e a música fica sincronizada com as notas: medido com `python tools/mede_sincronia.py`, cada nota termina
a menos de 0,5% do início da seguinte. A pausa do clock também deixa a janela redesenhar com
regularidade, por isso as notas descem sem trancos. Os níveis 1 a 9 do menu continuam escolhendo a
dificuldade. Para conferir o clock, rode `testes/calibra.asm`: devem sair ~250 blocos por segundo na linha 0.

**Áudio:** para conferir o som sem abrir o jogo, rode o teste de ouvido
(`g++ testes/teste_beep.cpp Simulador/Sound.cpp -ISimulador -o testes/teste_beep -lSDL2`).
Ele toca Dó-Ré-Mi com `SOUND` e a Ode à Alegria com `SNDN`. Se ficar mudo, o
`testes/diagnostico_audio.cpp` mostra o formato que a placa de som aceitou. O volume fica na constante
`AMPLITUDE` de `Simulador/Sound.h` (hoje 7000, um quarto do original). Cada nota entra e sai com uma
rampa de 5 ms para não estalar, e o áudio é gerado em blocos de ~12 ms para sair junto com a imagem.

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
  A janela de acerto vai da linha 23 à 27: 24–26 é perfeito e 23 ou 27 é quase. No nível 5 cada
  linha dura ~65 ms, então o "perfeito" aceita ~65 ms de erro para cada lado. As mensagens ficam
  na linha 28, abaixo da última linha por onde as notas passam.
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

O menu oferece todas as músicas passadas ao gerador, **na ordem dos arquivos** (tecla `M` troca).
Hoje são `ode_alegria.txt`, `arpejo_la_menor.txt` e `minha_musica.txt` (um modelo para você substituir).

1. Escreva a partitura em `tools/musicas/minha_musica.txt` (ou crie outro `.txt` no mesmo formato).
2. Gere e monte, listando **todas** as músicas que devem aparecer no menu (a que ficar de fora some do jogo):
   ```bash
   python tools/gera_musica.py jogo.asm tools/musicas/ode_alegria.txt tools/musicas/arpejo_la_menor.txt tools/musicas/minha_musica.txt
   ./Montador/montador jogo.asm cpuram.mif
   ```
3. Confira com `python tools/testa_jogo.py`. O teste joga cada música do menu e exige que o robô
   acerte todas as notas; se ele falhar, há notas próximas demais na mesma pista.

### Como transcrever uma música

> A especificação completa, para entregar a um transcritor ou colar num modelo de IA (com prompt
> pronto, regras de ritmo, tercinas, MIDI, tablatura e checklist), está em
> [docs/formato_partitura.md](docs/formato_partitura.md). Para conferir um arquivo transcrito:
> `python tools/gera_musica.py --validar tools/musicas/minha_musica.txt`.

**Resumo do formato:**
```
nome MINHA MUSICA          # nome no menu (até 20 caracteres)
painel MINHA|MUSICA|       # 3 linhas do painel lateral (até 9 caracteres cada)
onda 1                     # 0 seno, 1 quadrada (guitarra de videogame), 2 triangular, 3 dente de serra
slots_por_tempo 8          # frames por tempo (semínima)
pistas A3=0 C4=1 E4=2 G4=3 # pista (0=D, 1=F, 2=J, 3=K) de cada altura usada
E4 0.5                     # NOTA DURAÇÃO_EM_TEMPOS   (1 = semínima, 0.5 = colcheia, 0.25 = semicolcheia)
- 1                        # pausa
A3+E4 2                    # duas notas juntas (só a primeira soa)
```

**Passo a passo, partindo de uma tablatura de guitarra:**

1. **Converta cada número da tablatura em nota.** Cada corda solta tem uma nota na afinação padrão,
   da mais grave para a mais aguda:

   | Corda | 6ª (E grave) | 5ª | 4ª | 3ª | 2ª | 1ª (e aguda) |
   |---|---|---|---|---|---|---|
   | Solta | E2 | A2 | D3 | G3 | B3 | E4 |

   Cada casa sobe um semitom: C → C# → D → D# → E → F → F# → G → G# → A → A# → B → (C da oitava seguinte).
   Exemplo genérico: corda G (G3) na casa 5 → G#3, A3, A#3, B3, **C4**.
2. **Respeite a faixa do jogo, C3 a D8.** Notas mais graves que C3 (comuns nas cordas E e A)
   devem subir uma oitava inteira (+12 semitons, ex.: E2 → E3). O gerador avisa quando uma nota sai da faixa.
3. **Durações.** Anote o tempo de cada nota em relação à semínima (1). Em riffs rápidos de
   semicolcheias use `slots_por_tempo 8`: cada semicolcheia vira 2 frames. Se ficar difícil de jogar,
   aumente para 12 (o jogo fica mais lento e espaçado).
4. **Pistas.** Na linha `pistas`, distribua as alturas da mais grave (0) para a mais aguda (3), como no
   Guitar Hero. Evite a mesma pista em notas a menos de 3 frames de distância: ficam impossíveis de acertar.
5. **Teste:** gere, monte e jogue (veja os comandos acima).

> Músicas comerciais são protegidas por direito autoral. Uma transcrição feita por você para uso
> pessoal ou acadêmico é escolha sua, mas se o repositório for público prefira deixar esse `.txt` de fora
> (ou use músicas em domínio público, como a Ode à Alegria).

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
| acerta tudo na linha 25, 24 ou 26 | 63/63, 1920 pontos (`PERFEITO`), conceito S |
| acerta tudo na linha 23 ou 27 | 63/63, 960 pontos (`QUASE`) |
| aperta fora da janela | 0 acertos, conceito D |
| ninguém joga | 0 acertos, conceito D |
| cada música extra do menu | o robô acerta todas as notas |
| tecla sem nota | alvo preenchido, sem faísca, 1 erro, e depois o alvo volta ao normal |
| reinício | `ESPAÇO` volta ao menu e a nova partida começa zerada |

Os testes também conferem as notas da melodia tocadas via `SNDN`, com 0 ms de CPU travada.
