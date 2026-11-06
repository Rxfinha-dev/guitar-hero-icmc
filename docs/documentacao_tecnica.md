# 1. Visão geral

O **Guitar Hero ICMC** é um jogo de ritmo escrito inteiramente em Assembly do Processador ICMC, o processador didático de 16 bits usado na disciplina SSC0511 (Organização de Computadores Digitais). Notas descem por quatro pistas e o jogador aperta a tecla da pista (D, F, J ou K) no instante em que a nota passa sobre o alvo. A música toca sozinha, sincronizada com as notas na tela.

Além do jogo, o projeto faz uma **modificação na arquitetura**: uma instrução nova, `SNDN` (som não bloqueante). Ela foi adicionada ao montador, ao Simple Simulator e ao simulador gráfico porque a instrução de som original (`SOUND`) congela a CPU enquanto a nota toca, o que inviabiliza um jogo de ritmo. O projeto também traz o **Simple Simulator**, uma implementação ciclo a ciclo do processador em C, além de ferramentas em Python que geram partes do código e testes automáticos.

Este documento descreve cada parte do projeto: o que faz, como funciona e por que foi feita assim. Os nomes de rótulos, variáveis e arquivos são os do código-fonte.

## 1.1 Componentes do repositório

| Caminho | Conteúdo |
|---|---|
| `jogo.asm` | o jogo, em Assembly do Processador ICMC: cerca de 1600 linhas escritas à mão, mais os blocos gerados (telas e músicas) |
| `cpuram.mif` | o jogo montado: imagem da memória de programa/dados (32768 palavras de 16 bits) |
| `charmap.mif` | o mapa de caracteres (fonte 8x8) com os sprites do jogo nos códigos 1 a 26 |
| `Montador/` | montador do Processador ICMC, com a instrução `SNDN` adicionada |
| `Simulador/` | simulador gráfico (GTK2 + SDL2) com `SNDN`, clock fixo e correções de áudio |
| `SimpleSimulator/` | processador ICMC ciclo a ciclo em C (máquina de estados e muxes), com `SNDN` |
| `build.sh` | compila montador, simulador, Simple Simulator e harness |
| `tools/gera_jogo.py` | regenera sprites, telas e músicas e monta o `cpuram.mif` com um comando |
| `tools/gera_charmap.py` | desenha os sprites do jogo dentro do `charmap.mif` |
| `tools/gera_telas.py` | converte os desenhos de `tools/telas/*.txt` em diretivas `string` no `jogo.asm` |
| `tools/gera_musica.py` | converte as partituras de `tools/musicas/` (lista em `lista.txt`) em mapas de notas |
| `tools/tab_para_jogo.py` | converte uma tablatura em texto (padrão Cifra Club) em partitura do jogo |
| `tools/testa_tudo.py` | roda todos os testes: partituras, conversor de tablatura, jogo e Simple Simulator |
| `tools/testa_jogo.py`, `tools/testa_tab.py` | testes do jogo (de ponta a ponta) e do conversor de tablatura |
| `tools/headless/` | simulador sem janela, usado pelos testes (mesmo `Model.cpp` do gráfico) |
| `tools/versao_sound.py`, `tools/mede_sincronia.py` | versão "antes" (com `SOUND`) para comparação e medição da sincronia |
| `tools/gera_doc.py` | gera este PDF a partir de `docs/documentacao_tecnica.md` |
| `docs/` | este documento, a especificação da `SNDN` e o formato de partitura |
| `testes/` | programas de teste: som (`teste_som`, `teste_sndn`, `teste_beep`, `diagnostico_audio`), clock (`calibra`) e Simple Simulator (`simples/`) |

## 1.2 Fluxo de construção

O código Assembly tem partes **escritas à mão** (a lógica do jogo) e partes **geradas** (telas, músicas, tabela de frequências). As partes geradas ficam entre marcadores de comentário (`; >>> TELA telaL` ... `; <<< TELA telaL` e `; >>> MUSICA` ... `; <<< MUSICA`), e os scripts substituem apenas o que está entre esses marcadores. Assim é possível editar uma tela ou uma música sem tocar no restante do arquivo, e a lógica do jogo nunca é sobrescrita.

```
                        python tools/gera_jogo.py  (um comando faz as 4 etapas)

tools/telas/*.txt           --gera_telas.py-->  \
tools/musicas/lista.txt     --gera_musica.py--> -+-> jogo.asm --montador--> cpuram.mif --+
  (e as partituras listadas)                                                             +--> Simulador/sim
sprites em gera_charmap.py  --gera_charmap.py---------------------------> charmap.mif ---+

tablatura (.txt)  --tab_para_jogo.py-->  tools/musicas/nova.txt  (depois, incluir em lista.txt)
```

Todos os geradores podem ser rodados de novo a qualquer momento: com as mesmas entradas, produzem
exatamente os mesmos arquivos. O `gera_charmap.py` regrava o próprio `charmap.mif` do projeto
(substitui só o bloco dos códigos 0 a 31), então não depende de nenhum arquivo externo.

**Por que gerar código?** Desenhar uma tela de 40x30 caracteres ou transcrever uma música diretamente em diretivas `static` é lento e propenso a erro: um caractere a mais desalinha a tela inteira e uma conta errada de bits produz a nota errada. Os scripts validam as entradas (largura das linhas, faixa das notas, notas impossíveis de jogar) antes de escrever qualquer coisa.

## 1.3 Onde encontrar cada explicação

| Para entender... | Veja |
|---|---|
| o que cada instrução faz e como ler o Assembly do jogo | seções 2.5 e 2.6 |
| como telas, músicas e notas ficam guardadas na memória | capítulo 3 |
| como o jogo mede o tempo e mantém o som sincronizado | capítulo 4 |
| o que acontece em cada frame e o caminho completo de uma nota | capítulo 5 |
| para que serve e como funciona cada subrotina | capítulo 6 |
| a instrução nova e como o montador a traduz | capítulo 8 |
| como o simulador funciona por dentro | capítulo 9 |
| ferramentas em Python e o `build.sh` | capítulo 10 |
| testes automáticos | capítulo 11 |
| o processador ciclo a ciclo em C | capítulo 12 |
| todas as decisões de projeto, resumidas | capítulo 15 |

## 1.4 Requisitos da disciplina

O trabalho da SSC0511 pede quatro itens, além da documentação no repositório. Esta tabela mostra onde cada um está:

| Item do enunciado | Onde está no projeto | Explicação |
|---|---|---|
| 1. Jogo em Assembly | `jogo.asm`, `cpuram.mif` e `charmap.mif` | capítulos 3 a 7 |
| 2. Hardware do processador no Simple Simulator | `simple_simulator.c`, na pasta `SimpleSimulator/` | capítulo 12 |
| 3. Nova instrução no Simple Simulator | `case SNDN` em `simple_simulator.c` | seção 8.7 |
| 3. Montador reconhecendo a instrução | `Montador/defs.h` e `Montador/montador.c` | seção 8.5 |
| 3. README descrevendo a instrução | `README.md` e `docs/nova_instrucao.md` | capítulo 8 |
| 4. Opcional: jogo usando a instrução em um simulador com tela | `TocaMelodia` em `jogo.asm`, no simulador de `Simulador/` | seções 6.3 e 8.4 |
| Vídeo explicando o projeto | link no `README.md`, a preencher pelo grupo | seção "Vídeo" do `README.md` |

# 2. O Processador ICMC: o que o jogo usa

## 2.1 Registradores, memória e pilha

O processador tem oito registradores de uso geral de 16 bits (`r0` a `r7`), o contador de programa `PC`, o ponteiro de pilha `SP`, o registrador de instrução `IR` e o registrador de flags `FR`. A memória tem 32768 palavras de 16 bits e guarda ao mesmo tempo programa e dados (arquitetura de Von Neumann). A pilha começa no fim da memória (`SP = 32767`) e cresce para baixo: `PUSH` grava em `M[SP]` e decrementa `SP`; `POP` incrementa `SP` e lê.

`CALL` grava o endereço de retorno na pilha e salta; `RTS` recupera esse endereço. Como os registradores são poucos, o jogo usa a convenção de que **toda subrotina salva com `push` e restaura com `pop` todos os registradores que usa**, exceto os de retorno, que são documentados no cabeçalho de cada rotina. Com isso, qualquer rotina pode chamar qualquer outra sem se preocupar com registradores destruídos.

## 2.2 Diretivas do montador usadas

| Diretiva | Efeito |
|---|---|
| `rotulo : var #N` | reserva N palavras na memória a partir de `rotulo` (valor inicial 0) |
| `static rotulo + #i, #v` | define o valor inicial da palavra `rotulo + i` como `v` |
| `rotulo : string "..."` | grava um caractere por palavra e um `\0` (zero) no fim |
| `#rotulo` | o endereço do rótulo, usado como constante (ex.: `loadn r1, #telaL00`) |
| `#'d'` | o código ASCII do caractere (ex.: `loadn r1, #'d'` carrega 100) |

A primeira instrução do programa é `jmp main`, porque o processador começa a executar no endereço 0 e as variáveis e tabelas são declaradas antes do código.

## 2.3 Detalhes da semântica que o código respeita

Alguns comportamentos do simulador não são óbvios e moldaram o código. Eles estão anotados no cabeçalho do `jogo.asm`:

- **`CMP` não altera o flag de zero.** Ela altera só os flags maior/menor/igual. Depois de `CMP` usa-se `jeq`, `jne`, `jgr`, `jle`, `jeg` ou `jel`, nunca `jz`/`jnz`.
- **`jle` é "menor estrito".** Na nomenclatura do ICMC: `jgr` = maior, `jle` = menor (estrito), `jeg` = maior ou igual, `jel` = menor ou igual. Por isso `cmp r0, r1` / `jle X` salta quando `r0 < r1`.
- **`INC`, `DEC`, `ADD` e as demais operações da ULA atualizam o flag de zero.** **`STORE` e `STOREI` não mexem nos flags.** O código usa isso no padrão `dec r0` / `store var, r0` / `jnz laco`: o `jnz` testa o resultado do `DEC`, mesmo com o `STORE` no meio.
- **`SUB` com resultado negativo vira 0** e liga o flag de negativo. O jogo nunca depende de números negativos: todas as contas são feitas de forma que o resultado seja não negativo.
- **`INCHAR` devolve 255 quando nenhuma tecla foi apertada.** O controlador do simulador devolve cada tecla uma única vez e volta a 255, então uma tecla apertada é processada uma única vez.

## 2.4 Vídeo: posição, caractere e cor

A tela tem 40 colunas por 30 linhas, ou seja, 1200 posições. A posição de um caractere é `posicao = coluna + 40 * linha`. A instrução `OUTCHAR Rx, Ry` escreve o caractere `Rx` na posição `Ry`.

A palavra escrita pelo `OUTCHAR` codifica caractere e cor ao mesmo tempo:

```
 15       12 11      8 7 6             0
+-----------+---------+-+---------------+
| (ignorado)|   cor   |x| caractere 0-127|
+-----------+---------+-+---------------+
```

O simulador usa `reg[rx] & 0x7f` como código do caractere e os bits 11-8 como índice da cor. Para escrever um caractere colorido, **basta somar `cor * 256` ao código**. Por exemplo, a letra `D` (código 68) em verde (índice 2, ou seja, 512) é `68 + 512 = 580`. As cores usadas pelo jogo:

| Índice | Valor somado | Cor | Uso no jogo |
|---|---|---|---|
| 0 | 0 | branco | texto comum |
| 2 | 512 | verde | pista D, mensagem QUASE |
| 6 | 1536 | verde-azulado | divisórias das pistas |
| 9 | 2304 | vermelho | pista F, mensagens de erro, conceito D |
| 10 | 2560 | verde-limão | mensagem PERFEITO!, conceito A |
| 11 | 2816 | amarelo | pista J, números do placar, título |
| 12 | 3072 | azul | pista K, conceito B |
| 13 | 3328 | rosa | ícone de nota musical, conceito S |
| 14 | 3584 | água | moldura |

## 2.5 Instruções usadas pelo jogo

O código escrito à mão usa só estas 30 instruções:

| Instrução | O que faz | Para que o jogo usa |
|---|---|---|
| `loadn rx, #v` | `rx = v` (constante) | valores fixos e endereços de tabelas; é a instrução mais usada |
| `load rx, var` | `rx = M[var]` | ler uma variável de estado |
| `store var, rx` | `M[var] = rx` | gravar uma variável de estado |
| `loadi rx, ry` | `rx = M[ry]` | ler um elemento de vetor, com o endereço em `ry` |
| `storei rx, ry` | `M[rx] = ry` | gravar um elemento de vetor, com o endereço em `rx` |
| `mov rx, ry` | `rx = ry` | passar um valor no registrador que a rotina chamada espera |
| `add`, `sub` | `rx = ry + rz`, `rx = ry - rz` | endereços, posições na tela, pontuação |
| `mul`, `div`, `mod` | multiplicação, divisão inteira, resto | posição na tela, campos do mapa da música, dígitos decimais, precisão |
| `and rx, ry, rz` | E bit a bit | testar se a máscara da música tem a pista |
| `inc rx`, `dec rx` | `rx + 1`, `rx - 1` | contadores e índices de laço |
| `cmp rx, ry` | compara e liga os flags igual/maior/menor | toda decisão do programa |
| `jeq`, `jne` | salta se igual, se diferente | laços e testes de valor |
| `jgr`, `jle`, `jeg`, `jel` | salta se maior, menor, maior ou igual, menor ou igual | faixas (janela de acerto, teclas 1 a 9, conceitos) |
| `jnz` | salta se o último resultado da ULA não foi zero | laços que contam para baixo |
| `jmp` | salto incondicional | sair de um caso, voltar ao início de um laço |
| `call`, `rts` | chama subrotina, retorna | organização do programa |
| `push rx`, `pop rx` | guarda e recupera um registrador na pilha | preservar registradores |
| `inchar rx` | lê o teclado (255 = nenhuma tecla) | menu, partida e tela de fim |
| `outchar rx, ry` | escreve o caractere `rx` na posição `ry` | todo desenho na tela |
| `sndn rx, ry, rz` | inicia uma nota sem parar a CPU | a melodia |

## 2.6 Padrões que se repetem no código

Quase todo o `jogo.asm` é a combinação de poucos padrões. Quem os reconhece consegue ler qualquer rotina, por isso o código não precisa de um comentário em cada linha: o cabeçalho diz o que a rotina faz, e os comentários marcam só o que não é evidente.

**Preservar registradores.** Toda rotina salva o que vai usar e restaura na ordem inversa, porque a pilha devolve primeiro o último valor guardado:

```
Rotina:
	push r1
	push r2
	...
	pop r2
	pop r1
	rts
```

**Acessar um vetor.** O processador não tem endereçamento com índice, então o endereço é calculado em três passos:

```
loadn r1, #notaY     ; r1 = início do vetor
add r1, r1, r0       ; r1 = endereço de notaY[r0]
loadi r2, r1         ; r2 = notaY[r0]
```

**Laço com índice crescente.** Usado para percorrer os 16 slots ou as 4 pistas:

```
	loadn r0, #0         ; índice
	loadn r4, #16        ; limite
Laco:
	...
	inc r0
	cmp r0, r4
	jne Laco
```

**Laço com contador decrescente.** Mais curto quando o índice não é usado, porque `dec` já liga o flag de zero e dispensa o `cmp`:

```
	loadn r1, #1000
Laco:
	...
	dec r1
	jnz Laco
```

**Temporizador em variável.** O `store` fica entre o `dec` e o `jnz` porque não altera o flag de zero. O salto testa o resultado do `dec`, e é assim que o jogo descobre que o tempo acabou:

```
load r0, msgTimer
dec r0
store msgTimer, r0
jnz AindaNaoVenceu
```

**Testar um valor e desviar.** Sempre um `loadn` com o valor de comparação, um `cmp` e um salto. O processador não tem comparação direta com constante.

**Parâmetros em registradores.** A rotina recebe e devolve valores em registradores combinados, indicados no cabeçalho dela. Por isso aparecem `mov` antes de um `call`, como em `mov r0, r1` / `call Restaura3`. Registradores são mais rápidos e mais simples do que passar valores pela pilha.

# 3. Codificação dos dados do jogo

## 3.1 Sprites no charmap

O `charmap.mif` define o desenho de cada um dos 128 caracteres como uma matriz de 8x8 pixels: são 8 palavras de 8 bits por caractere, 1024 linhas no total (`WIDTH=8; DEPTH=1024`). O caractere de código `c` ocupa as linhas `8c` a `8c+7`. No charmap original, os códigos 0 a 31 (caracteres de controle) ficam em branco, "livres para edição". O jogo desenha seus sprites nesses códigos, sem alterar letras, números e símbolos:

| Código | Sprite | Uso |
|---|---|---|
| 1, 2, 3 | NOTA_ESQ, NOTA_MEIO, NOTA_DIR | a nota (gema), 3 caracteres de largura |
| 5 | PISTA | divisória vertical tracejada entre as pistas |
| 6, 7, 8 | ALVO_ESQ, ALVO_MEIO, ALVO_DIR | alvo vazado na linha 25, mesmo contorno da nota |
| 9, 10 | BORDA_V, BORDA_H | moldura de linha dupla |
| 11 a 14 | cantos | cantos da moldura |
| 15 | BLOCO | bloco cheio (reserva) |
| 16 | NOTA_MUSICAL | enfeite do título |
| 17 | FAISCA | faísca de acerto no centro do alvo |
| 18, 19, 20 | ALVO_CHEIO_* | alvo preenchido: tecla apertada sem nota |
| 21, 22, 23 | NOTA_*_MEIA_CIMA | metade de cima da nota, desenhada no fundo de uma linha |
| 24, 25, 26 | NOTA_*_MEIA_BAIXO | metade de baixo da nota, desenhada no topo da linha seguinte |

**A cor não faz parte do sprite.** Um único desenho de nota serve para as quatro pistas: a cor é somada no Assembly (`1 + 512` = nota verde, `1 + 2304` = nota vermelha). Isso economiza códigos de caractere, que são poucos (31 livres).

**O código 4 não é usado.** O `View.cpp` do simulador pula blocos com `sym == 32`, e `sym = código * 8`. Portanto o código 4 (4 * 8 = 32) nunca é desenhado. O `gera_charmap.py` recusa sprites com esse código.

**Notas de três caracteres.** Uma nota com um único caractere (8 pixels) seria pequena demais para ler numa pista. Com três caracteres (24 pixels) ela tem formato de gema, com pontas arredondadas (`NOTA_ESQ` e `NOTA_DIR`) e um centro vazado (`NOTA_MEIO`). O alvo usa o mesmo contorno vazado, para que o jogador veja claramente quando a nota encaixa no alvo.

## 3.2 Cenários: letras minúsculas como códigos de sprite

As telas são desenhadas em arquivos de texto (`tools/telas/jogo.txt`, `menu.txt`, `fim.txt`). Para que o desenho seja legível num editor comum, usa-se uma convenção: **texto em MAIÚSCULAS é impresso como texto; cada letra minúscula é um código de sprite**. Por exemplo, a linha do alvo é:

```
v          pefgpijkplmnpoqrp           v
```

Aqui, `v` é a borda vertical, `p` é a divisória da pista, `e f g` é o alvo verde (esquerda, meio, direita), `i j k` o vermelho, `l m n` o amarelo e `o q r` o azul. A legenda completa:

| Letra | Sprite | Letra | Sprite |
|---|---|---|---|
| a b c d | cantos da moldura | h | borda horizontal |
| v | borda vertical | p | divisória da pista |
| s | nota musical (rosa) | e f g | alvo verde |
| i j k | alvo vermelho | l m n | alvo amarelo |
| o q r | alvo azul | w x y z | letras D F J K nas cores das pistas |

A tradução é feita em tempo de execução pela tabela `traduz`, um vetor de 128 palavras indexado pelo código ASCII. `traduz[c]` vale 0 quando o caractere é texto comum; caso contrário, contém a palavra final pronta para o `OUTCHAR` (código do sprite + cor). Exemplos:

```
static traduz + #112, #1541     ; 'p' divisoria da pista  ( 5 + verde-azulado 1536)
static traduz + #101, #518      ; 'e' alvo verde, esquerda ( 6 + verde 512)
static traduz + #119, #580      ; 'w' letra D verde       (68 + verde 512)
```

**Por que uma tabela de 128 posições?** A tradução vira uma única leitura indexada (`loadn r1, #traduz` / `add r1, r1, r2` / `loadi r4, r1`), sem cadeias de comparações. Ela custa 128 palavras de memória, que sobram, e é executada para cada caractere desenhado: o cenário inteiro tem 1200.

Cada linha do cenário vira uma diretiva `string` de exatamente 40 caracteres (`telaL00` a `telaL29`). Como o montador grava um `\0` no fim de cada string, **cada linha ocupa 41 palavras na memória**, e as 30 linhas ficam em sequência. Esse detalhe é usado na fórmula de endereço do `RestauraCenario` (seção 6).

## 3.3 Mapa da música: uma palavra por frame

Cada música é um vetor (`musica0`, `musica1`, ...) com **uma palavra de 16 bits por frame** do jogo. A palavra do frame `f` diz quais pistas recebem nota nesse frame e qual som tocar:

```
 15 14 13        10 9              4 3          0
+-----+------------+----------------+------------+
| 0 0 | duração    | índice da nota | pistas     |
|     | (frames)   | em freqs (0-63)| K J F D    |
+-----+------------+----------------+------------+
```

| Campo | Bits | Significado |
|---|---|---|
| pistas | 3-0 | máscara: bit 0 = pista D, bit 1 = F, bit 2 = J, bit 3 = K |
| índice | 9-4 | índice da nota na tabela `freqs` (0 = nenhum som) |
| duração | 13-10 | duração do som, em frames (1 a 15) |
| 65535 | todos | marcador de fim da música |

**Exemplo decodificado.** A primeira nota da Ode à Alegria é `static musica0 + #0, #6420`:

```
6420 = 6 * 1024 + 276          -> duração = 6 frames
 276 = 17 * 16 + 4             -> índice = 17 (E4, 330 Hz), pistas = 4 = 0100b = pista J
```

E a nota final é `12505 = 12 * 1024 + 13 * 16 + 9`: 12 frames, índice 13 (C4), pistas `1001b` = D e K ao mesmo tempo (um acorde).

**Por que essa codificação?**

- **Uma palavra por frame** permite ler o mapa com um acesso indexado direto (`musicaAtual + frame`), sem ponteiros nem contadores de duração. O custo é memória: frames sem nota valem 0 e não precisam de diretiva `static`, porque o `var` já zera a memória. A Ode tem 385 palavras, o que é pouco diante de 32768.
- **Máscara de pistas** permite acordes (várias pistas no mesmo frame) com um simples AND.
- **Índice em vez de frequência.** Uma frequência precisaria de 13 bits (até 4699 Hz) e não caberia junto com os outros campos. Com o índice de 6 bits, a frequência vem da tabela `freqs`.
- **O marcador 65535 nunca colide com uma palavra válida**, porque os bits 15 e 14 de uma palavra válida são sempre 0 (o maior valor possível é `15 * 1024 + 63 * 16 + 15 = 16383`).
- **Limites:** no máximo 15 frames de som por nota (4 bits) e 63 alturas (C3 a D8, 6 bits). O gerador corta notas mais longas para 15 frames de som; a duração musical continua correta, porque a pausa até a próxima nota é dada pela posição dela no vetor, não pelo campo de duração.

Os campos são extraídos no Assembly com divisão e resto por potências de 2, o que equivale a deslocamentos e máscaras:

```
mod r3, r3, #16   -> pistas           (bits 3-0)
div r2, r2, #16   -> descarta as pistas
mod r0, r2, #64   -> índice da nota   (bits 9-4)
div r2, r2, #64   -> duração          (bits 13-10)
```

## 3.4 Tabela de frequências

`freqs[i]` é a frequência, em Hz, da nota de índice `i`. O índice 1 é C3 e cada índice seguinte sobe um semitom, até o 63 (D8). O índice 0 fica livre para significar "sem som". O gerador calcula as frequências pela afinação temperada, `f = 440 * 2^((n - 69) / 12)`, com `n` o número MIDI da nota (`n = índice + 47`), arredondada para inteiro. Exemplos: `freqs[10] = 220` (A3), `freqs[22] = 440` (A4), `freqs[13] = 262` (C4).

## 3.5 Tabelas de músicas do menu

Como o jogo tem várias músicas, o gerador cria tabelas paralelas indexadas por `musicaSel` (0 = primeira música):

| Tabela | Conteúdo |
|---|---|
| `numMusicas` | quantidade de músicas |
| `tabMusicas[i]` | endereço do mapa da música i (`#musica0`, ...) |
| `tabOndas[i]` | forma de onda (0 seno, 1 quadrada, 2 triangular, 3 dente de serra) |
| `tabNomes[i]` | endereço do nome com 20 caracteres, mostrado no menu |
| `tabPainel[i]` | endereço da 1ª de 3 strings de 9 caracteres, mostradas no painel do jogo |

Quais músicas entram no menu, e em que ordem, é definido em `tools/musicas/lista.txt` (um arquivo por linha). Os nomes têm sempre 20 caracteres (completados com espaços pelo gerador). Assim, ao trocar de música no menu, o nome novo cobre o anterior por completo, sem precisar apagar a área antes. As três linhas do painel ocupam 10 palavras cada (9 caracteres + `\0`) e ficam em sequência; por isso o código passa de uma linha para a próxima somando 10 ao endereço.

## 3.6 Outras tabelas

| Tabela | Valores | Uso |
|---|---|---|
| `pistaX[4]` | 12, 16, 20, 24 | coluna onde começa cada pista (cada nota ocupa 3 colunas e a divisória 1) |
| `pistaCor[4]` | 512, 2304, 2816, 3072 | verde, vermelho, amarelo, azul (as cores do Guitar Hero) |
| `bitPista[4]` | 1, 2, 4, 8 | bit de cada pista na máscara do mapa |
| `teclasPista` | `"dDfFjJkK"` | teclas do jogo: um par (minúscula, maiúscula) por pista |
| `tabMsFrame` | 200, 150, 112, 85, 65, 50, 37, 30, 22 | duração de um frame em ms para cada nível de velocidade (posições 1 a 9) |
| `msgPerfeito` etc. | strings de 15 caracteres | mensagens da linha 28 (largura exata das pistas) |

## 3.7 Variáveis de estado

| Variável | Significado |
|---|---|
| `velocidade` | nível de velocidade escolhido no menu (1 a 9, padrão 5) |
| `musicaSel` | índice da música escolhida no menu |
| `musicaAtual` | endereço do mapa da música em jogo (`tabMusicas[musicaSel]`) |
| `ondaMelodia` | forma de onda da música em jogo (`tabOndas[musicaSel]`) |
| `pontos`, `combo`, `comboMax`, `mult` | pontuação, acertos seguidos, recorde de combo, multiplicador (1 a 4) |
| `acertos`, `erros`, `totalNotas` | contadores do resultado final |
| `hudSujo` | 1 quando o placar mudou e precisa ser redesenhado |
| `frame` | número do frame desde o início da música |
| `spawnAcabou` | 1 quando todas as notas já surgiram |
| `musicaAcabou` | 1 quando a última nota já chegou ao alvo |
| `fimContador` | frames que faltam para mostrar a tela de fim |
| `msgTimer` | frames até apagar a mensagem da linha 28 |
| `notasNoMeio` | 1 quando as notas estão desenhadas meia linha abaixo |
| `alvoTimer[4]` | frames até o alvo de cada pista voltar ao normal, depois de uma faísca ou de um preenchimento |
| `notaY[16]`, `notaPista[16]` | as notas ativas na tela (seção 3.8) |

## 3.8 Notas ativas: 16 slots em vetores paralelos

As notas que estão na tela ficam em 16 "slots", em dois vetores paralelos: `notaY[i]` é a linha da nota do slot `i` e `notaPista[i]` é a pista dela (0 a 3). **`notaY[i] = 0` significa slot livre**: como as notas nascem na linha 3 e nunca voltam para a linha 0, o próprio campo de linha serve de indicador de ocupação, sem precisar de um terceiro vetor.

**Por que vetores paralelos e não um vetor de registros?** O Processador ICMC não tem modo de endereçamento com deslocamento: o acesso a `base + i` exige `loadn` + `add` + `loadi`. Com vetores paralelos, o endereço de cada campo é `rótulo + slot`, a forma mais simples possível. Com registros de 2 palavras, seria preciso multiplicar o slot por 2.

**Por que 16 slots?** Uma nota fica na tela por 25 frames (da linha 3 à linha 27). Nas 5 músicas do menu, o maior número de notas visíveis ao mesmo tempo é 9, na MINHA TAB, que tem 948 notas. Dezesseis dá folga, e percorrer 16 slots por frame custa pouco.

# 4. Tempo, sincronia e janela de acerto

## 4.1 O frame do jogo

O jogo é organizado em **frames**. A cada frame, todas as notas descem uma linha, novas notas podem surgir no topo, a melodia pode tocar uma nota e o teclado é lido durante a espera. A duração do frame em milissegundos depende do nível de velocidade (`tabMsFrame`): 200 ms no nível 1, 65 ms no nível 5 (padrão) e 22 ms no nível 9.

## 4.2 Medindo tempo sem relógio: clock fixo de 5 MHz

O Processador ICMC não tem temporizador nem relógio que um programa possa ler. A única forma de medir tempo é **contar instruções**. Isso só funciona se cada instrução levar sempre o mesmo tempo, mas o simulador original rodava "o mais rápido possível": a velocidade do jogo dependia do computador.

Por isso o simulador foi alterado para rodar com **clock fixo de 5 MHz** (constante `CLOCK_HZ` em `Simulador/Mneumonicos.h`): 5 milhões de instruções por segundo, ou seja, **5000 instruções por milissegundo**, como numa placa real. A seção 9.1 descreve a implementação.

A espera do jogo (`EsperaMs`) tem um laço interno de exatamente 5 instruções quando nenhuma tecla é apertada:

```
EsperaMs_interno:
	inchar r0               ; 1
	cmp r0, r3              ; 2
	jeq EsperaMs_semTecla   ; 3
	call ProcessaTecla
EsperaMs_semTecla:
	dec r1                  ; 4
	jnz EsperaMs_interno    ; 5
```

São 1000 voltas por milissegundo, logo 1000 x 5 = 5000 instruções = 1 ms. **A mesma tabela `tabMsFrame` dá o tamanho do Delay e a duração das notas da música**, e por isso o som fica naturalmente sincronizado com a tela. O trabalho do frame (mover notas, desenhar) e as voltas do laço externo somam algumas centenas de instruções, que não são descontadas. A medição com `tools/mede_sincronia.py` mostra que cada nota termina a menos de 0,5% do início da seguinte.

**Por que ler o teclado dentro do laço de espera?** Se o teclado fosse lido só uma vez por frame, uma tecla apertada e solta entre duas leituras poderia se perder. Lendo a cada 5 instruções (1 µs), nenhuma tecla se perde, e ela é tratada na hora (`call ProcessaTecla`), com resolução muito melhor que um frame.

## 4.3 Atraso de 22 frames entre o surgimento e o som

Uma nota nasce na linha 3 e desce uma linha por frame; o alvo fica na linha 25. Portanto, uma nota criada no frame `f` chega ao alvo no frame `f + 22`. O mapa da música é lido **duas vezes** em cada frame:

- `SpawnNotas` lê `mapa[frame]` e cria as notas que estão **nascendo** agora.
- `TocaMelodia` lê `mapa[frame - 22]` e toca o som da nota que está **chegando ao alvo** agora.

Com isso, o som sai exatamente quando a nota passa pelo alvo, que é o momento em que o jogador deve apertar a tecla. É o que faz a música e a jogabilidade parecerem a mesma coisa.

## 4.4 Janela de acerto

| Linha da nota quando a tecla é apertada | Resultado | Pontos base |
|---|---|---|
| 22 ou menos | fora da janela: conta como tecla sem nota | 0 (quebra o combo) |
| 23 | QUASE (2 linhas antes) | 5 |
| 24, 25, 26 | PERFEITO! (alvo com 1 linha de folga) | 10 |
| 27 | QUASE (2 linhas depois) | 5 |
| passou da 27 | ERROU! (nota perdida) | 0 (quebra o combo) |

No nível 5, uma linha corresponde a 65 ms, então o PERFEITO aceita cerca de ±65 ms de erro e o QUASE cerca de ±130 ms. A janela em linhas é fixa; em milissegundos ela encolhe nos níveis mais rápidos, e é isso que torna esses níveis mais difíceis.

**Por que a linha 28 é das mensagens?** A janela vai até a linha 27. As mensagens (PERFEITO!, ERROU!...) ficam na linha 28, logo abaixo da última linha por onde uma nota passa, de modo que uma mensagem nunca é desenhada sobre uma nota e vice-versa.

## 4.5 Animação em meia linha

Uma linha de caractere tem 8 pixels. Descendo uma linha por frame, a nota "pula" 8 pixels de cada vez, o que fica visivelmente aos trancos nos níveis lentos. A solução foi dividir cada frame em duas metades: na metade do `Delay`, a rotina `MeioPasso` redesenha todas as notas **4 pixels mais abaixo**, usando os sprites 21 a 26. Esses sprites são a nota cortada ao meio: a metade de cima da nota aparece no fundo da linha Y (sprites 21 a 23) e a metade de baixo no topo da linha Y+1 (sprites 24 a 26). O `gera_charmap.py` gera esses sprites automaticamente a partir do desenho da nota, deslocando as linhas da matriz.

A **linha lógica** (`notaY`) só muda no `MoveNotas`. A meia linha é apenas visual, e a janela de acerto não é afetada. A variável `notasNoMeio` registra se as notas estão desenhadas na posição deslocada, para que o `ApagaNota` saiba que precisa apagar duas linhas em vez de uma. Notas na linha 27 não são deslocadas, porque a linha 28 é das mensagens.

# 5. Programa principal e laço do jogo

```
main:
	call Menu             ; tela inicial: escolhe velocidade e música, espera ESPACO
	call IniciaJogo       ; zera o estado e desenha o cenário
LoopJogo:
	call AtualizaEfeitos  ; apaga mensagens, faíscas e alvos preenchidos vencidos
	call MoveNotas        ; desce as notas uma linha; nota que passou = erro
	call SpawnNotas       ; cria as notas deste frame no topo das pistas
	call TocaMelodia      ; toca a nota que está chegando ao alvo (SNDN)
	call AtualizaHUD      ; redesenha o placar, se mudou
	call Delay            ; espera o tempo do frame lendo o teclado
	frame++
	se musicaAcabou: fimContador--; quando chegar a 0 -> TelaFim; jmp main
```

**Por que esta ordem?**

- `AtualizaEfeitos` vem **antes** de `MoveNotas`. Quando uma faísca vence, o centro do alvo é restaurado a partir do cenário. Se isso acontecesse depois de a nota ser desenhada sobre o alvo, a restauração cobriria a nota. Restaurando primeiro e desenhando as notas depois, as notas ficam sempre por cima.
- `MoveNotas` vem **antes** de `SpawnNotas`. Assim as notas recém-criadas (na linha 3) não são movidas no mesmo frame em que nascem.
- `TocaMelodia` vem depois do movimento, para que o som saia no mesmo frame em que a nota é desenhada na linha 25.
- `AtualizaHUD` vem depois de tudo que pode alterar o placar no frame (notas perdidas no `MoveNotas`).
- `Delay` fica no fim. As teclas são processadas durante ele, e o placar alterado por um acerto é redesenhado no início do frame seguinte, graças ao `hudSujo`.

**Encerramento.** Quando o `TocaMelodia` encontra o marcador 65535 em `mapa[frame - 22]`, a última nota já passou pelo alvo. Ele liga `musicaAcabou` e põe `fimContador = 4`: mais quatro frames para as últimas notas saírem da janela (e serem contadas como erro, se for o caso) antes da tela de fim. O teste do fim usa `dec` / `store` / `jnz`, aproveitando que `STORE` não altera o flag de zero. Depois da `TelaFim`, `jmp main` volta ao menu; `velocidade` e `musicaSel` são mantidas, e todo o resto é zerado pela `IniciaJogo`.

## 5.1 Organização do jogo.asm

O arquivo segue a ordem abaixo. O montador coloca tudo na memória na ordem em que aparece. Como os dados vêm antes do código, a primeira instrução (`jmp main`) pula por cima deles.

| Parte | Conteúdo | Origem |
|---|---|---|
| cabeçalho | regras do jogo, formato da tela, legenda dos sprites e detalhes do processador | escrito à mão |
| 1. Variáveis | estado da partida (seção 3.7) e slots de notas (seção 3.8) | escrito à mão |
| 2. Tabelas | pistas, teclas, velocidade, tradução de sprites e mensagens (seção 3.6) | escrito à mão |
| 3. Dados gerados | telas, músicas e frequências, entre os marcadores `>>>` e `<<<` | `gera_telas.py` e `gera_musica.py` |
| 4. Programa principal | `main` e `LoopJogo` | escrito à mão |
| 5. Subrotinas | menu, notas, som, tempo, teclado, pontuação, tela de fim e desenho (capítulo 6) | escrito à mão |

## 5.2 O caminho de uma nota, do mapa ao acerto

Este exemplo acompanha a primeira nota da Ode à Alegria no nível 5 (65 ms por frame). Ela passa por quase todas as rotinas do jogo.

1. **Frame 0, nascimento.** `SpawnNotas` lê `mapa[0] = 6420`. O resto da divisão por 16 dá a máscara 4, ou seja, só a pista 2 (J). `CriaNota` encontra o slot 0 livre e grava `notaY[0] = 3` e `notaPista[0] = 2`. `DesenhaNota` calcula a posição `3 * 40 + 20 = 140` e desenha os sprites 1, 2 e 3 em amarelo (cor 2816).
2. **Frame 0, primeira espera.** `Delay` divide 65 ms em 32 e 33. Durante os 32 ms, `EsperaMs` lê o teclado o tempo todo.
3. **Meio do frame 0.** `MeioPasso` apaga a nota e a redesenha 4 pixels abaixo: sprites 21 a 23 na linha 3 e 24 a 26 na linha 4. `notasNoMeio` passa a valer 1. Só o desenho mudou; `notaY` continua em 3.
4. **Frame 1, descida.** `MoveNotas` apaga as duas linhas ocupadas, soma 1 em `notaY` e desenha a nota inteira na linha 4. No fim, `notasNoMeio` volta a 0. Os passos 2 a 4 se repetem a cada frame.
5. **Frame 22, chegada e som.** A nota chega à linha 25. `TocaMelodia` lê `mapa[22 - 22] = 6420`: dividindo por 16 sobra 401, `401 mod 64 = 17` é o índice da nota e `401 / 64 = 6` é a duração. `freqs[17] = 330` Hz e a duração é `65 * 6 = 390` ms. A instrução `sndn` inicia o som e o programa segue na mesma hora.
6. **Frame 22, tecla.** Durante o `Delay`, o jogador aperta J. `INCHAR` devolve 106 (`j`) e `ProcessaTecla` encontra a tecla na posição 4 de `"dDfFjJkK"`, logo a pista é `4 / 2 = 2`.
7. **Acerto.** `TentaAcerto` encontra o slot 0 na pista 2, com linha 25. `Acertou` apaga a nota, libera o slot, acende a faísca na posição `1000 + 20 + 1 = 1021`, soma `10 * 1` pontos, mostra "PERFEITO!", sobe o combo para 1 e liga `hudSujo`.
8. **Frames seguintes.** No frame 23, `AtualizaHUD` redesenha o placar. `AtualizaEfeitos` conta o tempo dos efeitos: o alvo volta ao normal 4 frames depois do acerto e a mensagem some depois de 12.

**Se o jogador não apertar,** a nota continua descendo. No frame 25, `notaY` passaria a 28: como isso é maior que 27, `MoveNotas` libera o slot, não desenha a nota e chama `Errou`, que zera o combo e mostra "ERROU!".

# 6. Referência das subrotinas

Esta seção descreve todas as subrotinas do `jogo.asm`, na ordem em que aparecem no arquivo. "Entrada" e "Saída" indicam registradores; todos os demais registradores são preservados.

## 6.1 Menu e inicialização

### Menu
Desenha a tela inicial (`menuL00` com `ImprimeCenario`), o título colorido (`DesenhaTitulo` na posição 132 = linha 3, coluna 12), o nível de velocidade e o nome da música. Depois fica num laço lendo o teclado com `INCHAR`:

- **ESPAÇO**: sai do menu e o jogo começa.
- **M** ou **m**: `musicaSel = (musicaSel + 1) mod numMusicas`, para avançar circularmente pela lista, e redesenha o nome.
- **1 a 9**: `velocidade = tecla - '0'` e redesenha o número. A faixa é validada com `jle` (menor que '1', ignora) e `jgr` (maior que '9', ignora).
- qualquer outra tecla ou 255 (nenhuma tecla): ignora.

O laço fica preso no `INCHAR` sem nenhum atraso, porque no menu não há nada para animar.

### MostraVelocidadeMenu
Escreve `velocidade` com 1 dígito, em amarelo, na posição 855 (linha 21, coluna 15), via `ImprimeNumero`.

### MostraMusicaMenu
Lê `tabNomes[musicaSel]` (endereço do nome) e o escreve em amarelo na posição 891 (linha 22, coluna 11), via `ImprimeStrT`. Os nomes têm sempre 20 caracteres, então o nome anterior é coberto por inteiro.

### DesenhaTitulo
**Entrada:** `r0` = posição. Escreve a string `tituloJogo` ("GUITAR HERO ICMC") em amarelo. É usada no menu e na tela do jogo, porque o cenário é impresso com texto branco e o título deve se destacar.

### IniciaJogo
Prepara uma partida nova:

1. Zera `pontos`, `combo`, `comboMax`, `acertos`, `erros`, `totalNotas`, `frame`, `spawnAcabou`, `musicaAcabou`, `fimContador`, `msgTimer`, `notasNoMeio`, e põe `mult = 1`.
2. Zera os 16 slots de `notaY` (todos livres).
3. Zera os 4 valores de `alvoTimer` (nenhum efeito ativo nos alvos).
4. Desenha o cenário do jogo (`telaL00`), o título e o nível de velocidade (posição 769 = linha 19, coluna 9).
5. Copia `tabMusicas[musicaSel]` para `musicaAtual` e `tabOndas[musicaSel]` para `ondaMelodia`. Assim, durante o jogo, as rotinas usam uma variável direta em vez de indexar as tabelas a cada frame.
6. Escreve as 3 linhas do painel com o nome da música (posição 202 = linha 5, coluna 2; a cada linha, +40 na posição e +10 no endereço da string).
7. Liga `hudSujo` e chama `AtualizaHUD` para desenhar o placar zerado.

**Por que zerar tudo a cada partida?** Depois da tela de fim o programa volta ao menu sem reiniciar o processador, então as variáveis ainda têm os valores da partida anterior. `velocidade` e `musicaSel` ficam de fora de propósito: assim o menu mantém a última escolha do jogador.

## 6.2 Notas

### MoveNotas
Percorre os 16 slots. Para cada slot ocupado (`notaY != 0`):

1. `ApagaNota` na posição atual. Isso é feito **antes** de alterar a linha, porque a posição a apagar é calculada a partir de `notaY`.
2. `notaY[slot]++`.
3. Se a nova linha passou de 27 (`jgr`), a nota foi perdida: libera o slot (`notaY = 0`) e chama `Errou`. Senão, chama `DesenhaNota` na nova linha.

No fim, põe `notasNoMeio = 0`, porque todas as notas foram redesenhadas alinhadas.

### SpawnNotas
Se `spawnAcabou` já vale 1, não faz nada. Senão, lê `mapa[frame]` (com `musicaAtual + frame`). Se a palavra é 65535, liga `spawnAcabou`. Caso contrário, extrai a máscara (`mod 16`) e, para cada pista 0 a 3, testa `mascara AND bitPista[pista]`; se o bit está ligado, chama `CriaNota` com `r0 = pista`.

**Por que o `spawnAcabou`?** O jogo continua rodando por mais de 22 frames depois do marcador de fim, até a última nota chegar ao alvo. Sem essa variável, `frame` continuaria avançando e `SpawnNotas` leria a memória além do fim do mapa, tratando outros dados como notas.

### CriaNota
**Entrada:** `r0` = pista. Procura o primeiro slot livre (`notaY = 0`), põe `notaY = 3` (linha onde as notas nascem) e `notaPista = pista`, incrementa `totalNotas` e desenha a nota. Se não houver slot livre, a nota é descartada em silêncio. Isso não acontece nas músicas atuais (o pico é de 9 notas na tela), e descartar é mais seguro do que sobrescrever uma nota ativa.

**Por que nascer na linha 3?** As linhas 0 a 2 são a moldura e o título. A linha 3 é a primeira linha livre das pistas.

### PosicaoNota
**Entrada:** `r0` = slot. **Saída:** `r1` = posição na tela da parte esquerda da nota; `r2` = cor da pista. Calcula `r1 = notaY[slot] * 40 + pistaX[notaPista[slot]]` e `r2 = pistaCor[notaPista[slot]]`. Está centralizada numa rotina porque desenhar, apagar e desenhar em meia linha precisam da mesma conta.

### DesenhaNota
**Entrada:** `r0` = slot. Calcula a posição com `PosicaoNota` e chama `Desenha3` com o sprite 1 somado à cor da pista: os sprites 1, 2 e 3 vão para três posições consecutivas. Os códigos são consecutivos de propósito, para que um único utilitário desenhe qualquer objeto de 3 caracteres (nota, nota em meia linha, alvo preenchido).

### ApagaNota
**Entrada:** `r0` = slot. Apaga a nota **redesenhando o cenário por baixo** dela (`Restaura3` nas 3 posições). Se `notasNoMeio = 1` e a nota não está na linha 27 ou abaixo (posição >= 1080), chama `Restaura3` também na linha de baixo (posição + 40), onde fica a metade inferior da nota em meia linha.

**Por que restaurar o cenário em vez de escrever espaços?** As notas passam por cima das divisórias, do alvo (linha 25) e das letras das teclas (linha 26). Escrevendo espaço, o alvo e as letras desapareceriam depois da primeira nota. Restaurando o caractere original do cenário, a tela volta exatamente ao que era.

### DesenhaNotaMeia
**Entrada:** `r0` = slot. Desenha a nota deslocada meia linha para baixo: `Desenha3` com os sprites 21, 22 e 23 na linha Y e de novo com os sprites 24, 25 e 26 na mesma coluna da linha Y+1. Como `Desenha3` preserva a posição recebida, a linha de baixo é simplesmente a posição + 40.

### MeioPasso
Chamada pelo `Delay` na metade do frame. Para cada slot ocupado com linha menor que 27: `ApagaNota` (com `notasNoMeio` ainda 0, apaga só a linha Y) e `DesenhaNotaMeia`. No fim, liga `notasNoMeio`.

## 6.3 Som

### TocaMelodia
Toca a nota da música que está chegando ao alvo neste frame:

1. Se `musicaAcabou` vale 1, retorna.
2. Se `frame < 22`, retorna, porque nenhuma nota chegou ainda ao alvo. O teste é `jle`, menor estrito, então no frame 22 o índice é 0.
3. Lê `mapa[frame - 22]`. Se a palavra é 65535: liga `musicaAcabou`, põe `fimContador = 4` e retorna.
4. Extrai o índice (bits 9-4) e a duração (bits 13-10). Índice 0 significa frame sem nota: retorna.
5. `r0 = freqs[índice]` (Hz); `r1 = tabMsFrame[velocidade] * duração` (ms); `r2 = ondaMelodia`.
6. `sndn r0, r1, r2`: **a nova instrução** inicia a nota e devolve o controle à CPU no mesmo ciclo.

A duração em ms usa a mesma tabela do `Delay`, então uma nota de 6 frames dura exatamente o tempo de 6 frames e termina quando a próxima começa. O maior valor possível é 15 frames x 200 ms = 3000 ms, que cabe com folga em 16 bits.

**Por que a melodia sai do mesmo mapa das notas?** Com uma única fonte de dados, não existe como a nota na tela e o som discordarem: os dois vêm da mesma palavra, lida com 22 frames de diferença.

## 6.4 Tempo e teclado

### Delay
Espera a duração de um frame em duas metades: `r1 = ms / 2` e `r2 = ms - r1`, para que o resto da divisão não se perca em números ímpares. Chama `EsperaMs` na primeira metade, `MeioPasso` e `EsperaMs` na segunda.

### EsperaMs
**Entrada:** `r2` = milissegundos (maior que 0). Laço externo de `r2` voltas, cada uma com um laço interno de 1000 voltas de 5 instruções (seção 4.2). Em cada volta interna, lê o teclado e, se houver tecla (valor diferente de 255), chama `ProcessaTecla`.

### ProcessaTecla
**Entrada:** `r0` = código da tecla. Procura a tecla na string `teclasPista` (`"dDfFjJkK"`). Se encontrar na posição `i`, a pista é `i / 2`, e chama `TentaAcerto`. Outras teclas são ignoradas. Cada pista tem a minúscula e a maiúscula para que o jogo funcione com Caps Lock ligado, e trocar as teclas do jogo exige mudar só essa string.

## 6.5 Acertos, erros e pontuação

### TentaAcerto
**Entrada:** `r0` = pista. Procura, entre os 16 slots, as notas da pista com linha >= 23 (dentro da janela) e escolhe a de **maior linha**, ou seja, a mais baixa e mais antiga, a que sairia da janela primeiro. Se duas notas da mesma pista estão na janela, a tecla vale para a que está mais perto de ser perdida, como nos jogos de ritmo comerciais. Se o critério fosse "a primeira no vetor", a ordem dependeria do slot em que cada nota caiu, o que é arbitrário.

A busca guarda em registradores o slot escolhido (`r2`, começa em 255 = nenhum) e a linha a superar (`r3`). Como `r3` começa em 22, logo acima da janela, um único teste (`cmp r6, r3` / `jel`) resolve três casos de uma vez: nota fora da janela, slot livre (linha 0) e nota que não é a mais baixa até agora. O limite superior não é testado: uma nota com linha maior que 27 já foi removida pelo `MoveNotas`.

Se encontrou uma nota, chama `Acertou` com `r1` = slot e `r2` = linha. Senão, chama `AcendePressionado` (alvo preenchido) e `QuebraCombo` com a mensagem "NADA AQUI!".

### Acertou
**Entrada:** `r1` = slot, `r2` = linha da nota.

1. Apaga a nota, libera o slot e acende a faísca na pista dela.
2. Linhas 24 a 26: 10 pontos, mensagem "PERFEITO!" em verde-limão. Linha 23 ou 27: 5 pontos, "QUASE" em verde.
3. `pontos += base * mult`, com o multiplicador **de antes** deste acerto.
4. `combo++`; se `combo > comboMax`, atualiza o recorde.
5. `mult = min(1 + combo / 10, 4)`: sobe a cada 10 acertos seguidos, até x4.
6. `acertos++` e `hudSujo = 1`.

**Por que o multiplicador de antes do acerto?** O acerto que completa 10 seguidos ainda vale x1, e o bônus começa no seguinte. A regra fica fácil de calcular, como mostra o capítulo 7. O limite x4 e o aumento a cada 10 acertos seguem a mesma ideia do Guitar Hero: premiam a sequência sem deixar a pontuação disparar.

**Por que 10 e 5 pontos?** O QUASE vale exatamente metade do PERFEITO, então um erro de tempo custa menos do que perder a nota, mas ainda faz diferença. Ele não quebra o combo, porque o jogador acertou a nota.

### Errou
Chamada pelo `MoveNotas` quando uma nota passa da linha 27. Chama `QuebraCombo` com a mensagem "ERROU!".

### QuebraCombo
**Entrada:** `r1` = mensagem. Zera o combo, põe o multiplicador em 1, incrementa `erros`, liga `hudSujo` e mostra a mensagem em vermelho. É compartilhada por "nota perdida" e "tecla sem nota", porque as duas situações têm a mesma consequência.

### MostraMensagem
**Entrada:** `r1` = mensagem de 15 caracteres, `r2` = cor. Apaga a mensagem anterior, escreve a nova na posição 1132 (linha 28, coluna 12, alinhada com as pistas) e põe `msgTimer = 12`: a mensagem some após 12 frames.

**Por que 15 caracteres e 12 frames?** Quinze é a largura das pistas (colunas 12 a 26), e todas as mensagens têm esse tamanho para ficarem alinhadas com elas. Doze frames são 780 ms no nível 5, tempo suficiente para ler sem que a mensagem atrapalhe a próxima. O jogo não para durante esse tempo: `AtualizaEfeitos` apaga a mensagem quando o contador termina.

### ApagaMensagem
Restaura o cenário nas posições 1132 a 1146 (linha 28, colunas 12 a 26).

### AcendeFaisca
**Entrada:** `r0` = pista. Restaura o alvo, o que tira um eventual preenchimento de uma tecla errada. Depois desenha o sprite 17 (faísca), na cor da pista, no centro do alvo e põe `alvoTimer = 4`.

### AcendePressionado
**Entrada:** `r0` = pista. Desenha o alvo preenchido (`Desenha3` com os sprites 18, 19 e 20 na cor da pista) e põe `alvoTimer = 3`.

**Por que mostrar o alvo preenchido?** Sem esse retorno visual, o jogador não saberia se a tecla foi lida e simplesmente não havia nota. O preenchimento deixa claro que a tecla funcionou mas foi apertada na hora errada.

**Por que um só temporizador?** A faísca e o preenchimento ficam no mesmo alvo e terminam do mesmo jeito: o alvo volta ao normal. Um efeito novo substitui o anterior só de regravar `alvoTimer`, então os dois nunca precisam ser coordenados.

### PosicaoAlvo
**Entrada:** `r0` = pista. **Saída:** `r1` = posição na tela da parte esquerda do alvo (`1000 + pistaX[pista]`, linha 25); `r2` = cor da pista.

### RestauraAlvo
**Entrada:** `r0` = pista. Redesenha as 3 posições do alvo a partir do cenário, com `PosicaoAlvo` e `Restaura3`.

### AtualizaEfeitos
Executada no início de cada frame. Decrementa os temporizadores e apaga o que venceu:

- `msgTimer`: ao chegar a 0, `ApagaMensagem`.
- `alvoTimer[p]`: ao chegar a 0, `RestauraAlvo`.

Temporizadores já em 0 são ignorados (inativos). O teste usa `dec` / `storei` / `jnz`, porque `STOREI` não altera o flag de zero.

**Por que temporizadores em frames?** Os efeitos precisam durar um tempo visível, mas o jogo não pode parar para esperar. Contar frames reaproveita o relógio do jogo, sem nenhum custo extra.

### AtualizaHUD
Se `hudSujo` vale 0, retorna. Senão, zera `hudSujo` e escreve, em amarelo, `pontos` (5 dígitos, posição 230), `combo` (3 dígitos, 350), `mult` (1 dígito, 471, logo depois do "X"), `acertos` (3 dígitos, 590) e `erros` (3 dígitos, 710).

**Por que o `hudSujo`?** `ImprimeNumero` faz uma divisão e um resto por dígito: são 15 dígitos e centenas de instruções no total. Na maioria dos frames nada muda no placar, e o "flag de sujeira" evita esse trabalho repetido.

## 6.6 Tela de fim

### TelaFim
Desenha a caixa de resultado (`fimL00` a `fimL10`, 22 colunas x 11 linhas) **sobre** a tela do jogo, a partir da posição 369 (linha 9, coluna 9). Cada string da caixa ocupa 23 palavras (22 + `\0`), então o endereço avança 23 e a posição avança 40 por linha. Depois preenche pontos, acertos, total de notas, combo máximo, precisão (`CalculaPrecisao`) e conceito (`Conceito`), e espera ESPAÇO.

**Por que desenhar sobre a tela do jogo?** A caixa só precisa cobrir uma área de 22 x 11 caracteres, em vez de redesenhar as 1200 posições, e o jogador continua vendo o cenário da partida. Não é preciso restaurar nada ao sair, porque o menu redesenha a tela inteira.

### CalculaPrecisao
**Saída:** `r1` = `acertos * 100 / totalNotas`, ou 0 se `totalNotas = 0`, para evitar divisão por zero. A conta direta `acertos * 100` estouraria 16 bits a partir de 656 acertos, o que uma música longa convertida de tablatura alcança facilmente. Por isso ela é feita em duas etapas, com `a = acertos` e `t = totalNotas`:

```
a*10 = q*t + r            ->  precisao = 10*q + (10*r) / t
```

`q` dá as dezenas da porcentagem e `(10*r) / t` as unidades. O resultado é exatamente o mesmo da conta direta, e nenhum valor intermediário passa de `10 * t`, então funciona até 6553 notas. No simulador, que guarda os registradores em `int` de 32 bits, a conta direta também funcionaria. Mas o Processador ICMC tem registradores de 16 bits, e o jogo é escrito para ele.

### Conceito
**Saída:** `r1` = letra com cor, pronta para `OUTCHAR`. Calcula a precisão e compara em cascata com `jeg`:

| Precisão | Conceito | Cor |
|---|---|---|
| >= 95% | S | rosa (3411 = 83 + 3328) |
| >= 85% | A | verde-limão |
| >= 70% | B | azul |
| >= 50% | C | amarelo |
| < 50% | D | vermelho |

As comparações vão do maior limite para o menor, então a primeira que for verdadeira já é a resposta. Os limites são uma escolha de projeto: o S exige quase não errar. As letras ficam como constantes já somadas à cor (`3411 = 'S' + rosa`), porque cada conceito tem uma cor fixa.

## 6.7 Utilitários de desenho

### Traduz
**Entrada:** `r2` = caractere, `r3` = cor padrão do texto. **Saída:** `r2` = palavra final. Se `traduz[r2]` é diferente de 0, o caractere é um sprite e o resultado é o valor da tabela (já com a cor). Senão, é texto comum e o resultado é `r2 + r3`. Todo desenho vindo de texto passa por aqui, então a regra "minúscula = sprite" fica em um único lugar.

### ImprimeCenario
**Entrada:** `r1` = endereço da primeira linha (ex.: `#telaL00`), `r3` = cor do texto. Desenha 30 linhas de 40 caracteres, traduzindo cada um. Depois de cada linha, pula o `\0` (`inc r1` extra). O laço termina quando a posição chega a 1200. Recebe o endereço como parâmetro para que a mesma rotina desenhe o menu e a tela do jogo.

### Desenha3 e Restaura3
`Desenha3` (**entrada:** `r1` = posição, `r3` = código do primeiro sprite + cor) escreve os sprites `c`, `c+1` e `c+2` em três posições seguidas. `Restaura3` (**entrada:** `r0` = posição) chama `RestauraCenario` nessas três posições. Notas, notas em meia linha e alvos têm sempre 3 caracteres (esquerda, meio, direita), e esses dois utilitários concentram esse padrão, que antes era repetido em quatro rotinas. As duas preservam todos os registradores.

### RestauraCenario
**Entrada:** `r0` = posição. Redesenha o caractere do cenário do jogo naquela posição. Como cada linha do cenário ocupa 41 palavras (40 + `\0`), o endereço do caractere é:

```
endereço = telaL00 + linha * 41 + coluna
         = telaL00 + (linha * 40 + coluna) + linha
         = telaL00 + posição + posição / 40
```

Ou seja, basta somar a linha (`posição / 40`) à posição: uma divisão e duas somas, sem multiplicação. É a rotina mais chamada do jogo: ela apaga notas, mensagens, faíscas e alvos. Ela sempre lê `telaL00` porque notas e efeitos só existem na tela do jogo. A memória funciona como uma cópia do cenário, e por isso não é preciso guardar o que havia embaixo de cada nota.

### ImprimeStrT
**Entrada:** `r0` = posição, `r1` = endereço da string, `r3` = cor. Imprime até o `\0`, traduzindo sprites. O "T" do nome vem de "traduzida": os nomes e as mensagens podem conter sprites, como no título do menu.

### ImprimeNumero
**Entrada:** `r0` = posição do primeiro dígito, `r1` = valor, `r2` = número de dígitos, `r3` = cor. Escreve o número em decimal, com zeros à esquerda, **da direita para a esquerda**: começa na posição do último dígito, escreve `valor mod 10` e faz `valor = valor / 10`, repetindo `r2` vezes. Assim não é preciso calcular potências de 10 nem saber de antemão quantos dígitos o número tem. A cor é somada uma única vez a `'0'` antes do laço (`r3 = cor + '0'`), e cada dígito vira uma soma só.

# 7. Pontuação: exemplo completo

A Ode à Alegria tem 62 frames com nota e 63 notas no total (o acorde final tem duas). Acertando todas como PERFEITO:

| Acertos | Multiplicador usado | Pontos |
|---|---|---|
| 1 a 10 | x1 (o combo só chega a 10 depois do 10º acerto) | 10 x 10 = 100 |
| 11 a 20 | x2 | 10 x 20 = 200 |
| 21 a 30 | x3 | 10 x 30 = 300 |
| 31 a 63 | x4 | 33 x 40 = 1320 |
| **total** | | **1920** |

Acertando todas como QUASE, o total é a metade: 960. Os dois valores são verificados pelos testes automáticos (seção 11). A pontuação cabe em 16 bits enquanto houver menos de cerca de 1600 notas (65535 / 40), e o placar mostra 5 dígitos.
# 8. A instrução nova: SNDN

## 8.1 O problema

O Processador ICMC já tinha uma instrução de som, `SOUND Rx, Ry, Rz`. No simulador, ela chama `play_note`, que coloca a nota na fila de áudio e depois executa `beeper.wait()`: um laço que só termina quando a nota acaba de tocar. Ou seja, **a instrução `SOUND` dura o tempo da nota inteira**. Além disso, no simulador gráfico a CPU executa com o lock da interface (`gdk_threads_enter`), então a janela inteira congela junto.

Num jogo de ritmo isso é fatal: enquanto a nota toca, as notas não descem e o teclado não é lido. A medição com o harness, tocando a música inteira no nível 5:

| Versão | Notas tocadas | CPU travada pelo som |
|---|---|---|
| melodia com `SOUND` (`tools/versao_sound.py`) | 62 | **24 960 ms** (a música inteira) |
| melodia com `SNDN` (`jogo.asm`) | 62 | **0 ms** |

## 8.2 Especificação

| | |
|---|---|
| Mnemônico | `SNDN Rx, Ry, Rz` |
| Operandos | `Rx` = frequência (Hz), `Ry` = duração (ms), `Rz` = forma de onda (0 seno, 1 quadrada, 2 triangular, 3 dente de serra) |
| Opcode | `110110` (54) |
| Tamanho | 1 palavra |
| Flags | não altera |
| Semântica | interrompe a nota que estiver tocando, inicia a nova e termina no mesmo ciclo |

```
 15      10 9   7 6   4 3   1 0
+----------+-----+-----+-----+-+
|  110110  | Rx  | Ry  | Rz  |0|
+----------+-----+-----+-----+-+

sndn r1, r2, r3  ->  110110 001 010 011 0  =  1101100010100110
```

## 8.3 Decisões de projeto

- **Opcode `110110`.** Estava livre e fica na família de E/S (`1101xx`), ao lado de `SOUND` (`110100`) e `INCHAR` (`110101`). O formato é idêntico ao do `SOUND`, então o decodificador reaproveita os campos Rx, Ry e Rz sem nenhuma mudança. Numa FPGA, a unidade de controle trataria `110110` como o `SOUND`, só que sem o estado de espera.
- **Interromper em vez de enfileirar (síntese monofônica).** Se a `SNDN` enfileirasse as notas, qualquer diferença entre a duração pedida e a duração real de um frame se acumularia, e a música sairia de sincronia com a tela ao longo da partida. Interrompendo, cada nota começa exatamente no ciclo da instrução: **quem dita o ritmo é o jogo**. É o comportamento de um "note on" num sintetizador monofônico.
- **Mesmos operandos do `SOUND`.** Não há conceito novo a aprender, e trocar uma instrução pela outra é uma substituição de texto. O `versao_sound.py` faz exatamente isso para gerar a versão de comparação.
- **Um único dispositivo de áudio.** O original chamava `SDL_Init` e abria o dispositivo de áudio a cada nota. Com duas instruções de som no mesmo programa, dois `SDL_OpenAudio` simultâneos falhariam. Agora há um `Beeper` global, criado na abertura do simulador (`inicia_audio`, seção 9.2) e compartilhado por `SOUND` e `SNDN`. **O `SOUND` mantém a semântica original** (bloqueante), para não quebrar programas existentes.

## 8.4 Implementação no simulador gráfico

`Simulador/Mneumonicos.h` define o opcode (`#define SNDN 54`). `Simulador/Model.cpp` executa a instrução ao lado do `SOUND`:

```
case SOUND:
  play_note(reg[rx], reg[ry], reg[rz]);         // bloqueante
  break;
case SNDN:    // Rx = frequencia (Hz), Ry = duracao (ms), Rz = forma de onda
  play_note_async(reg[rx], reg[ry], reg[rz]);   // nao espera
  break;
```

Em `Simulador/Sound.cpp`, o áudio é gerado pelo SDL num callback que roda em outra thread: o SDL pede blocos de amostras e o `Beeper::generateSamples` os preenche a partir de uma fila de notas (`queue<BeepObject>`). As duas instruções diferem só no que fazem com essa fila:

```
void Beeper::replace(string wave, double freq, int duration){
    BeepObject bo; ...                     // monta a nota nova
    SDL_LockAudio();                       // exclusão mútua com o callback
    beeps = queue<BeepObject>();           // descarta a nota atual e as pendentes
    beeps.push(bo);
    SDL_UnlockAudio();
}

void play_note (int rx, int ry, int rz) {        // SOUND
    Beeper& beeper = beeperGlobal();
    beeper.beep(tipoOnda(rz), rx, ry);           // enfileira
    beeper.wait(30);                             // espera a fila esvaziar
}

void play_note_async (int rx, int ry, int rz) {  // SNDN
    beeperGlobal().replace(tipoOnda(rz), rx, ry);
}
```

`SDL_LockAudio` / `SDL_UnlockAudio` são necessários porque a fila é lida pelo callback de áudio em outra thread. Sem o lock, a CPU simulada poderia trocar a fila no meio de uma leitura. `beeperGlobal()` usa variáveis `static` locais, que o C++ inicializa uma única vez, na primeira chamada.

## 8.5 Montador

Seguindo o roteiro da disciplina para adicionar instruções, são três pontos no `Montador/defs.h` e três no `Montador/montador.c`:

```
#define SNDN_CODE   99               /* identificador interno     */
#define SNDN        "110110"         /* opcode em binário         */
#define SNDN_STR    "SNDN"           /* mnemônico                 */
```

1. **1ª passada (contagem de palavras):** `case SNDN_CODE:` junto com `SOUND_CODE`, ou seja, 3 registradores e 1 palavra.
2. **2ª passada (geração):** lê os 3 registradores e escreve `sprintf(str_msg, "%s%s%s%s0", SNDN, str_tmp1, str_tmp2, str_tmp3);`.
3. **Reconhecimento do mnemônico:** `else if (strcmp(str_tmp, SNDN_STR) == 0) return SNDN_CODE;`.

O desassemblador do painel "Memória" do simulador (`View.cpp`) também passou a mostrar `SOUND` e `SNDN`. Antes, o `SOUND` caía no `default` e imprimia `ERRO - show program linha` no console.

## 8.6 Como o montador funciona

O montador lê o `jogo.asm` e escreve o `cpuram.mif`. A função `Montar` faz o trabalho em duas passadas sobre o arquivo:

1. **`DetectarLabels` (1ª passada).** Percorre o programa contando quantas palavras cada item ocupa e guarda o endereço de cada rótulo. Nada é escrito ainda.
2. **`MontarInstrucoes` (2ª passada).** Percorre de novo e converte cada instrução em binário, já conhecendo todos os endereços.

**Por que duas passadas?** Um `call` ou `jmp` pode citar um rótulo que aparece mais adiante, como o `jmp main` da primeira linha. Na primeira leitura esse endereço ainda é desconhecido. Por isso a `SNDN` precisa ser registrada também na 1ª passada: se o montador não soubesse que ela ocupa 1 palavra, todos os rótulos seguintes ficariam com o endereço errado.

`BuscaInstrucao` transforma o mnemônico em um código interno (`SNDN_CODE = 99`), que só serve para o `switch` do montador e não vai para a memória. O que vai para a memória é o opcode `110110`.

As palavras montadas ficam primeiro em um buffer do tamanho da memória (`parser_init_out_buffer`), e cada uma é gravada com o seu endereço (`parser_Write_Inst`). Isso permite que um `static` defina o valor de uma posição já reservada por um `var`. No fim, `parser_flush_program` escreve o buffer no `.mif`, depois do cabeçalho com `WIDTH=16`, `DEPTH=32768` e os formatos de endereço e dado. É esse arquivo que o simulador carrega.

## 8.7 Implementação no Simple Simulator

O enunciado da disciplina pede a modificação no Simple Simulator ou na FPGA. Como o projeto não usa FPGA, a `SNDN` foi implementada em `SimpleSimulator/simple_simulator.c`, do mesmo jeito que as outras instruções: o opcode entra na lista de `#define`, ao lado de `OUTCHAR` e `INCHAR`, e a execução é um `case` no estado `DECODE` da máquina de controle:

```
#define SNDN 54     // "110110"; -- SNDN Rx Ry Rz -- Inicia a nota e segue

case SNDN:
    // Sem audio: mostra a nota no terminal. Termina neste ciclo, sem esperar a
    // nota, sem usar a ULA (flags intactos) e sem carregar nenhum registrador.
    printf("[SNDN] freq=%d dur=%d onda=%d\n", reg[rx], reg[ry], reg[rz]);
    fflush(stdout);
    state=STATE_FETCH;
    break;
```

A execução passa por dois estados, como qualquer instrução de um ciclo de `DECODE`:

1. **FETCH:** `IR` recebe a palavra da memória e `PC` avança, como em todas as instruções.
2. **DECODE:** `rx`, `ry` e `rz` já foram separados do `IR` no início do ciclo. A nota é registrada e o próximo estado é `FETCH`.

**Por que voltar direto para o `FETCH`?** É a definição da instrução. Não existe estado de espera, então a CPU busca a instrução seguinte logo depois. Se a `SOUND` fosse implementada aqui, precisaria de um estado que ficasse parado até a nota terminar.

**Por que nenhum sinal de carga é ligado?** A `SNDN` só lê os três registradores. Com `LoadFR` e `LoadReg` desligados, flags e registradores não mudam, e a saída da ULA é ignorada.

**Por que escrever no terminal?** O Simple Simulator não tem áudio nem tela: o `OUTCHAR` também só escreve no terminal. A mensagem mostra a saída do dispositivo de som e não acrescenta nenhuma biblioteca externa ao programa. Como não há som, o corte da nota anterior (seção 8.3) só existe de verdade no simulador gráfico.

**O Assembly é o mesmo nos dois simuladores.** O montador gera a mesma palavra para `sndn r0, r1, r2`, e nada no programa muda. A seção 12.3 mostra o teste que compara as notas dos dois simuladores.

# 9. Outras alterações no simulador

## 9.1 Clock fixo de 5 MHz

O laço do modo automático (`processaAutomatico`, em `Model.cpp`) executava instruções sem parar e chamava um `delay()` a cada 500 instruções, então a velocidade dependia do computador. A versão nova mede o tempo real:

```
const long long BLOCO = 2000;
gint64 inicio = g_get_monotonic_time();          // microssegundos
long long executadas = 0;
while (model->getProcessamento()) {
    gdk_threads_enter(); model->processador(); gdk_threads_leave();
    if (++executadas % BLOCO == 0) {
        gint64 alvo  = inicio + executadas * 1000000LL / CLOCK_HZ;
        gint64 agora = g_get_monotonic_time();
        if (alvo - agora > 1000)        g_usleep(alvo - agora);   // adiantado: dorme
        else if (agora - alvo > 100000) { inicio = agora; executadas = 0; }  // muito atrasado
        else                            g_thread_yield();
    }
}
```

- **A cada 2000 instruções** (0,4 ms de tempo simulado), compara o tempo que deveria ter passado (`executadas / CLOCK_HZ`) com o tempo real, e dorme a diferença se estiver adiantado mais de 1 ms. Comparar contra o instante inicial, e não contra o último bloco, evita que erros de arredondamento do `sleep` se acumulem.
- **Se estiver atrasado mais de 100 ms** (computador lento ou uma pausa longa num `SOUND`), não tenta compensar acelerando, o que causaria uma rajada de frames: apenas recomeça a contagem.
- **A pausa libera o lock do GTK**, e com isso a janela consegue se redesenhar com regularidade. Antes, a thread da tela quase nunca obtinha o lock, e as notas desciam aos trancos.
- **Windows:** `main.cpp` chama `timeBeginPeriod(1)` (winmm). Sem isso, o Windows só acorda threads a cada ~15 ms, e os frames ficariam irregulares.
- **Por que 5 MHz?** Dá números redondos: 5000 instruções por milissegundo e 1000 voltas do laço de 5 instruções do `EsperaMs`. Um frame do nível 5 tem 325 000 instruções (65 x 5000), muito mais que o trabalho de mover e desenhar as notas, então sobra tempo para ler o teclado.
- **Por que blocos de 2000 instruções?** Consultar o relógio a cada instrução gastaria tempo à toa. A cada 0,4 ms de tempo simulado o erro ainda é pequeno demais para aparecer na tela.
- **Por que só dormir acima de 1 ms?** Pausas menores que isso não são precisas no sistema operacional. Nesses casos, `g_thread_yield` apenas cede a vez às outras threads, e a diferença é compensada num bloco seguinte.

O programa `testes/calibra.asm` confere o clock: ele executa blocos de ~20 000 instruções e mostra a contagem na tela. Com 5 MHz devem sair cerca de 250 blocos por segundo.

## 9.2 Correções e melhorias de áudio

| Mudança | Motivo |
|---|---|
| `SDL_OpenAudio(&desired, NULL)` em vez de passar um `obtainedSpec` | com `obtainedSpec`, o SDL2 entrega ao callback o formato nativo da placa, sem conversão. No Windows (WASAPI, float 32 bits estéreo) o callback escrevia inteiros de 16 bits mono e o simulador ficava **mudo**. Com `NULL`, o SDL converte. `testes/diagnostico_audio.cpp` mostra a diferença na máquina |
| buffer de 512 amostras (~12 ms) em vez de 2048 (~46 ms) | com blocos grandes, o som saía visivelmente atrasado em relação à nota chegando ao alvo |
| envelope de 5 ms no início e no fim de cada nota (`RAMPA = FREQUENCY / 200`) | sem rampa, o começo e o fim da onda são degraus e cada nota "estala" |
| `AMPLITUDE = 7000` (era 28000) | quase o máximo de 16 bits: com a onda quadrada ficava alto demais (-12 dB) |
| fase `v` inicializada com 0 | no original ela começava com lixo de memória |
| áudio aberto na abertura do simulador (`inicia_audio`, chamada em `main.cpp`) | abrir o dispositivo leva de 400 a 760 ms. Feito na primeira nota, congelava o jogo bem quando ela chegava ao alvo; agora essa nota leva menos de 1 ms |

**Como o som é gerado.** O SDL chama `audio_callback` em outra thread sempre que precisa de amostras, e ele repassa o pedido a `Beeper::generateSamples`. Essa função preenche o bloco com a nota da frente da fila, ou com zeros (silêncio) se a fila estiver vazia. Cada amostra é a onda escolhida (`sineWave`, `squareWave`, `triangleWave` ou `sawtoothWave`) multiplicada pelo envelope, e a fase `v` avança conforme a frequência da nota. Quando `samplesLeft` chega a 0, a nota sai da fila. A fase não é zerada entre notas: a onda continua de onde parou.

## 9.3 Como o simulador é organizado

O simulador separa o processador da interface, no padrão Modelo-Visão-Controle. É essa separação que permite aos testes usarem o mesmo processador sem abrir janela (seção 11.1).

| Arquivo | Responsabilidade |
|---|---|
| `main.cpp` | confere os argumentos, inicia as threads, o GTK e o áudio, cria `Model` e `Controller` e entra no laço do GTK |
| `Model.cpp` | o processador: memória, registradores, leitura dos `.mif`, execução das instruções (`processador`) e laço do modo automático (`processaAutomatico`) |
| `View.cpp` | a janela: desenho da tela, painel de registradores, painel de memória e captura de teclas |
| `Controller.cpp` | decide o que cada tecla faz e guarda a última tecla do jogo para o `INCHAR` |
| `Sound.cpp` | síntese de áudio com SDL2 e as funções de `SOUND` e `SNDN` |
| `Mneumonicos.h` | os opcodes e o `CLOCK_HZ` |

**Execução de uma instrução.** `Model::processador` lê `ir = mem[pc]` e soma 1 em `pc`. Depois separa os campos com `pega_pedaco`: `rx` nos bits 9-7, `ry` nos bits 6-4, `rz` nos bits 3-1 e o opcode nos bits 15-10. Um `switch(opcode)` executa a instrução. Por isso, no simulador gráfico, cada instrução é uma linha de C, sem os ciclos internos do hardware; o Simple Simulator (capítulo 12) mostra esses ciclos.

**Duas linhas de execução.** O simulador inicia parado. A tecla **Home** liga o modo automático, que cria a thread de `processaAutomatico`, enquanto o laço do GTK continua atendendo a janela e o teclado na thread principal. As duas usam a mesma memória de vídeo, então o processador executa cada instrução dentro de `gdk_threads_enter` / `gdk_threads_leave`.

**Caminho de uma tecla.** O GTK chama `View::teclado`, que repassa a tecla a `Controller::userInput`. As teclas de controle são tratadas ali mesmo (**Home** liga e desliga o automático, **End** executa uma instrução, **Insert** reinicia, **Esc** fecha). As demais ficam guardadas em `key`. Quando o programa executa `INCHAR`, `getKey` devolve esse valor e o troca por 255. É por isso que cada tecla é lida uma única vez.

**Caminho de um caractere.** `OUTCHAR` grava cor e desenho em `block[posição]` e pede o redesenho só dessa área da janela (`updateVideo`). Depois o GTK chama `ViewerExpose`, que desenha os caracteres a partir do charmap. Cada pixel do caractere vira um quadrado de 2 x 2 pixels da janela, ou seja, cada caractere ocupa 16 x 16 e a tela inteira 640 x 480.

# 10. Ferramentas (tools/)

## 10.1 gera_telas.py

Converte `tools/telas/*.txt` nas diretivas `string` do `jogo.asm`. Cada arquivo começa com um cabeçalho (`# prefixo telaL` e `# largura 40`).

| Função | O que faz |
|---|---|
| `le_tela(caminho)` | lê o cabeçalho e as linhas; recusa aspas, barra invertida e caracteres fora do ASCII imprimível (o montador não os aceita dentro de `string`); exige que **todas** as linhas tenham exatamente a largura declarada |
| `injeta(asm, prefixo, linhas, origem)` | substitui o bloco entre `; >>> TELA <prefixo>` e `; <<< TELA <prefixo>` por uma linha `<prefixo>NN : string "..."` para cada linha do desenho |
| `main()` | aplica as três telas (jogo, menu e fim), ou as passadas na linha de comando, e regrava o `jogo.asm` |

A validação de largura é essencial: o `ImprimeCenario` e o `RestauraCenario` assumem exatamente 40 caracteres por linha, e uma linha com 39 deslocaria todo o resto da tela.

**Por que marcadores no `jogo.asm`?** Eles deixam a parte gerada no mesmo arquivo da lógica, porque o montador recebe um único arquivo, e garantem que o script só altere o trecho dele. Se um marcador for removido, o script para com erro em vez de gravar no lugar errado. O cabeçalho de cada tela guarda o prefixo e a largura, então telas de tamanhos diferentes, como a caixa de fim com 22 colunas, usam o mesmo código.

## 10.2 gera_musica.py

Converte as partituras em mapas de notas. Formato resumido (a especificação completa está em `docs/formato_partitura.md`):

```
nome ODE A ALEGRIA               # nome no menu (até 20 caracteres)
painel ODE A|ALEGRIA|BEETHOVEN   # 3 linhas do painel (até 9 cada)
onda 2                           # 0 seno, 1 quadrada, 2 triangular, 3 dente de serra
slots_por_tempo 6                # frames por tempo (semínima)
pistas G3=0 C4=0 D4=1 E4=2 F4=3 G4=3
E4 1                             # NOTA DURAÇÃO_EM_TEMPOS
D4 1.5                           # pontuada
- 1                              # pausa
C4+G4 2                          # acorde: duas notas caem juntas (só a 1ª soa)
E4@3 1                           # pista fixada só para esta nota (sem mudar a altura)
```

| Função | O que faz |
|---|---|
| `midi(nome)` | converte "F#4", "Bb3" etc. no número MIDI: `12 * (oitava + 1) + semitom` |
| `le_nota(...)` | lê uma nota com pista opcional: `E4` -> (64, nenhuma), `E4@2` -> (64, pista 2) |
| `nome_midi(n)` | o inverso, para mensagens e comentários |
| `freq_hz(n)` | `round(440 * 2^((n - 69) / 12))` |
| `texto_tela(...)` | valida e converte para maiúsculas os textos de `nome` e `painel`, completando com espaços até a largura fixa |
| `le_partitura(caminho)` | lê diretivas e eventos; as durações são lidas como `Fraction`, então `1/3` (tercinas) é exato |
| `pistas_automaticas` | sem linha `pistas`: ordena as alturas usadas e as distribui igualmente entre as 4 pistas, das graves (0) para as agudas (3) |
| `gera_mapa(caminho, info)` | gera a lista de palavras: para cada evento, `frames = tempos * slots_por_tempo` (precisa ser inteiro); a pista de cada nota vem do `@` ou da linha `pistas`; monta `mascara \| indice << 4 \| min(frames, 15) << 10` e acrescenta `frames - 1` zeros |
| `bloco_asm(musicas)` | escreve as tabelas do menu, os mapas (com comentário legível em cada palavra) e a tabela `freqs` |
| `valida(caminho)` | modo `--validar`: confere a partitura sem alterar o jogo e aponta trechos injogáveis |
| `le_lista()` | lê `tools/musicas/lista.txt`: as partituras do menu, na ordem do menu |
| `main()` | sem argumentos, gera as músicas da lista no `jogo.asm`; `--validar` sem arquivos confere todas as da lista |

**Por que uma lista em arquivo?** Antes, as músicas do menu eram passadas na linha de comando, e uma música esquecida no comando simplesmente sumia do jogo. Com a lista, o menu fica registrado no repositório e o comando não muda.

**Regras de jogabilidade verificadas pelo `--validar`:** duas notas na mesma pista a menos de 2 frames de distância são **erro** (os sprites ficam grudados e a segunda nota não é distinguível); a 2 frames é aviso (muito rápido); acordes de 3 ou mais notas e notas com mais de 15 frames de som geram aviso.

**Por que usar `Fraction`?** Com ponto flutuante, `1/3 * 6` poderia dar `1.9999999` e a verificação "a duração em frames é inteira?" falharia ou, pior, arredondaria errado. Com frações a conta é exata.

## 10.3 gera_charmap.py

Desenha os sprites do jogo nos códigos 1 a 31 do charmap. Cada sprite é escrito no próprio script como uma matriz 8x8 de `#` (aceso) e `.` (apagado), o que deixa o desenho visível no código. Sem argumentos, regrava o `charmap.mif` do projeto: o bloco dos códigos 0 a 31 é localizado pelos comentários `-- CARACTERES DE CONTROLE` (início) e `-- SPACE` (código 32), que existem tanto no charmap original da disciplina quanto num já gerado.

| Função | O que faz |
|---|---|
| `SPRITES` | dicionário código -> (nome, matriz) |
| geração da meia linha | cria os códigos 21 a 26 a partir das notas 1 a 3: `MEIA_CIMA` = 4 linhas vazias + as 4 de cima da nota; `MEIA_BAIXO` = as 4 de baixo + 4 vazias. Mudar o desenho da nota muda os seis sprites junto |
| `valida()` | recusa códigos fora de 1..31, o código 4 (não desenhado pelo simulador) e matrizes que não sejam 8x8 |
| `bloco_caracteres_controle` | gera as 256 linhas (32 caracteres x 8) dos códigos 0..31, agrupando faixas vazias como `[a..b] : 00000000;` |
| `main()` | substitui o bloco de caracteres de controle e **preserva a quebra de linha** do arquivo de entrada |

**Por que preservar CRLF?** O `load_charmap` do simulador usa `fseek(-1)` em modo texto. No Windows isso só funciona com quebras CRLF; com LF, o charmap seria lido deslocado.

## 10.4 gera_jogo.py

Executa, em ordem, `gera_charmap.py`, `gera_telas.py`, `gera_musica.py` (com a lista de músicas) e o montador, e só termina com sucesso se o montador imprimir `Concluido`. É o único comando necessário depois de mudar sprites, telas, partituras ou a lista de músicas. Como cada gerador é idempotente, rodar o `gera_jogo.py` sem mudar nada produz exatamente os mesmos `jogo.asm`, `charmap.mif` e `cpuram.mif`.

A função `roda(descricao, comando)` executa uma etapa na raiz do projeto, para o script funcionar a partir de qualquer pasta. Se a etapa falhar, ela mostra só o fim da saída e encerra, e as etapas seguintes não rodam. O script usa `sys.executable` para chamar os geradores com o mesmo Python que o iniciou. Ele confere a palavra `Concluido` porque é a última mensagem do montador, a prova de que a montagem chegou ao fim.

## 10.5 tab_para_jogo.py: conversor de tablatura

Converte uma tablatura em texto, no formato dos sites de cifras (linhas como `e|---0---|`), numa partitura do jogo, que é validada no fim. O processo tem cinco etapas:

1. **Encontrar a tablatura.** Uma linha é corda se tem nome opcional (`e`, `B`, `D#`...), separador (`|` ou `:`) e um corpo quase só de traços, números e símbolos de técnica. Título, cifras e letra não passam nesse teste. Linhas de corda seguidas formam um **bloco** de 4 a 7 cordas (baixo, violão, guitarra de 7), e os blocos são lidos em sequência.
2. **Afinação.** Padrão (E2 A2 D3 G3 B3 E4 para 6 cordas), corrigida pelo nome escrito em cada corda (ex.: `D` na corda mais grave = Drop D, D2), ou dada por `--afinacao`. `--capo N` soma N semitons.
3. **Notas.** As colunas de barra de compasso são descartadas. Casas de 1 ou 2 dígitos viram notas (corda solta + casa); hammer-on, pull-off e slide (`5h7`, `7p5`, `5/7`) geram as duas notas; no bend (`7b9`) só a casa antes do `b` conta; `x` (abafada) é ignorado. Notas na mesma coluna formam um acorde (com 1 coluna de tolerância quando há casa de 2 dígitos); fica a mais aguda, ou também a mais grave com `--acordes 2`.
4. **Ritmo.** O espaçamento mais comum entre notas vira 1 tempo (`--frames-por-unidade` frames, padrão 4) e os demais são proporcionais, com no mínimo 2 frames. Espaços muito grandes da tab (fim de bloco, nota sustentada, folga entre partes) virariam silêncios longos, então nenhuma nota passa de `--max-tempos` (padrão 2 tempos; 0 desliga o limite).
5. **Ajuste ao jogo.** Transpõe por oitavas até caber em C3-D8; divide as alturas usadas em 4 pistas, da grave para a aguda; e, se duas notas caírem na mesma pista com menos de 3 frames de distância, move a segunda para a pista vizinha livre mais próxima (no sentido da melodia), marcando-a com `@`.

O cabeçalho gerado registra a afinação, a transposição, a unidade de ritmo e quantas notas foram movidas ou encurtadas. Como a tablatura em texto não codifica o ritmo com exatidão, o resultado deve ser conferido ouvindo no jogo. Os testes ficam em `tools/testa_tab.py`, com tablaturas de exemplo escritas para o teste: casas, técnicas, acordes, ritmo, limite de pausa, Drop D, capotraste e transposição.

| Função | O que faz |
|---|---|
| `linha_de_tab(linha)` | decide se a linha é uma corda; devolve o nome da corda e o corpo. Exige ao menos 3 traços e tolera poucos caracteres estranhos |
| `le_blocos(texto)` | agrupa linhas de corda seguidas em blocos; ignora, com aviso, blocos sem 4 a 7 linhas |
| `midi_da_corda(nome, padrao)` | altura da corda solta pelo nome escrito, na oitava mais próxima da corda padrão |
| `afinacao_do_bloco(bloco, fixa)` | altura de cada linha do bloco, lembrando que a linha de cima é a corda mais aguda |
| `colunas_sem_barras(bloco)` | cria o mapa de coluna da tab para coluna de tempo, sem contar as barras de compasso |
| `eventos_do_bloco(...)` | lê as casas de cada corda e devolve coluna, altura e dígitos de cada nota; pula o número depois de `b` ou `r` (alvo do bend) |
| `agrupa_acordes(eventos)` | junta as notas da mesma coluna |
| `duracoes_em_frames(...)` | escolhe a unidade de ritmo e calcula os frames de cada nota, aplicando o mínimo de 2 e o limite `--max-tempos` |
| `transposicao(alturas, oitava)` | calcula quantas oitavas somar para caber em C3-D8 |
| `escolhe_pista(...)` | escolhe a pista livre mais próxima da ideal, olhando primeiro no sentido da melodia |
| `texto_duracao(...)` | escreve a duração como tempos da partitura (`1`, `0.5`, `1/3`) |
| `sem_acentos(texto)`, `nome_e_painel(nome)` | limpam o nome (o charmap só tem ASCII) e o dividem em até 3 linhas de 9 caracteres |
| `converte(texto, args)` | executa todas as etapas e monta o texto da partitura com o cabeçalho |
| `main()` | lê as opções, grava o arquivo e valida o resultado com `gera_musica.valida` |

**Decisões do conversor:**

- **Ficar com a nota mais aguda do acorde.** O jogo só toca um som por vez (seção 8.3), e a nota mais aguda costuma ser a melodia.
- **Usar o espaçamento mais comum como unidade de ritmo.** A tab em texto não traz o ritmo exato, mas o espaçamento costuma ser proporcional a ele. Em caso de empate, vale o menor espaçamento.
- **Limitar a duração das notas.** A maior parte dos espaços grandes não é pausa de verdade. São traços do fim de um bloco somados aos do começo do próximo, ou notas sustentadas, e virariam silêncios longos no jogo.
- **Distância mínima de 3 frames na mesma pista.** O `gera_musica.py` recusa notas a menos de 2 frames e avisa com 2 frames (seção 10.2). Com 3, a nota passa sem erro nem aviso sempre que há uma pista livre. Se não houver, `escolhe_pista` usa a pista que está há mais tempo sem nota, e o `--validar` do fim aponta o trecho.
- **Mover a nota no sentido da melodia.** Se a melodia sobe, a nota vai de preferência para a pista à direita, então a mão continua acompanhando o desenho da música.
- **Dividir as alturas de grave para agudo.** Uma nota mais aguda fica mais à direita, o que dá ao jogador uma ligação visual com a altura do som.
- **Reutilizar o `gera_musica.py`.** O conversor importa `midi`, `nome_midi` e `valida`, de modo que os dois programas não podem discordar sobre a faixa de notas ou sobre o que é jogável.

## 10.6 versao_sound.py e mede_sincronia.py

`versao_sound.py` gera `testes/jogo_sound.asm`, uma cópia do jogo com a `sndn` trocada por `sound`. O script exige que haja exatamente uma substituição, para garantir que a comparação é justa (a única diferença entre as versões é a instrução). Serve para demonstrar o problema: com `SOUND`, a tela e o teclado congelam a cada nota.

`mede_sincronia.py` roda o jogo no harness, no nível 5, e lê o log de notas (ciclo de cada `SNDN` e a duração pedida). Para cada nota, compara a duração pedida com o tempo real até a próxima nota, `(ciclo_seguinte - ciclo) / 5000` ms. Se as duas coisas batem, cada nota termina exatamente quando a seguinte começa.

## 10.7 gera_doc.py

Gera este PDF a partir de `docs/documentacao_tecnica.md`, usando a biblioteca `reportlab`. A função `parse` lê o texto linha a linha e cria um bloco do PDF para cada título, parágrafo, lista, tabela, nota ou código. `inline` converte `**negrito**` e crases, `tabela` calcula a largura das colunas pelo conteúdo, e a classe `Doc` monta as páginas, o rodapé e as entradas do sumário. `multiBuild` gera o documento mais de uma vez porque os números de página do sumário só são conhecidos depois da primeira.

**Por que manter o texto em markdown?** O texto fica legível no próprio repositório, as alterações aparecem no `git diff` e o PDF pode ser gerado de novo a qualquer momento, sem edição manual.

## 10.8 build.sh

Compila tudo com um comando, em quatro etapas: montador (C), simulador gráfico (C++ com GTK2 e SDL2), Simple Simulator (C) e harness de testes (C++).

- `set -e` interrompe o script no primeiro erro de compilação, e `cd "$(dirname "$0")"` faz com que ele funcione a partir de qualquer pasta.
- O `case` com `uname -s` identifica o Windows, onde é preciso acrescentar `.exe` aos programas e a biblioteca `winmm`.
- `pkg-config` informa os caminhos e as bibliotecas do GTK e do SDL, que variam entre sistemas.
- O harness compila o mesmo `Simulador/Model.cpp`, mas troca `Sound.cpp` por `sound_stub.cpp` e não inclui `View.cpp` nem `Controller.cpp`. Assim os testes exercitam exatamente o processador do jogo.

# 11. Testes automáticos

## 11.1 Harness headless

`tools/headless/headless.cpp` é um simulador **sem janela** que usa o **mesmo `Model.cpp`** do simulador gráfico, com a mesma semântica de instruções. Os componentes de interface (vídeo, painel de registradores, controlador) são substituídos por stubs vazios. O `sound_stub.cpp` substitui o `Sound.cpp`: em vez de tocar, registra cada nota (ciclo, frequência, duração, onda e se foi bloqueante) e soma o tempo que a CPU ficaria travada pelas notas `SOUND`.

| Opção | Efeito |
|---|---|
| `--cycles N` | executa no máximo N instruções |
| `--key CICLO:TECLA` | injeta uma tecla a partir de um ciclo (simula o jogador) |
| `--dump CICLO` | imprime a tela 40x30 como texto naquele ciclo |
| `--autoplay` | liga o "robô" que joga sozinho |
| `--autoplay-linha N` | o robô aperta quando a nota está na linha N (para testar a janela) |
| `--colors`, `--mem`, `--glyphs` | grade de cores, memória e sprites do charmap |
| `--tempo-real S` | roda S segundos com o laço de clock fixo do simulador (para medir o clock) |

Na tela em texto, os sprites aparecem como caracteres: `(=)` é uma nota, `[_]` um alvo, `:` a divisória, `*` a faísca, `{O}` o alvo preenchido, e `/=\` sobre `\=/` é uma nota em meia linha.

**O robô.** A cada 2000 ciclos, o robô olha a linha observada no centro de cada pista. Se vê o meio de uma nota (sprite 2) e nenhuma outra nota mais abaixo na mesma pista, aperta a tecla da pista. Ele só aperta se viu a mesma situação **em duas leituras seguidas**, para ignorar o instante em que o `MoveNotas` apagou uma nota e ainda não a redesenhou. Como ele lê a tela, e não a memória, testa o jogo do ponto de vista do jogador.

**Por que testar sem janela?** O teste fica reproduzível (as teclas entram em ciclos exatos), roda muito mais rápido que o tempo real e não depende de placa de som nem de interface gráfica.

## 11.2 Cenários do testa_jogo.py

Os cenários de pontuação rodam no nível 9, o mais rápido, para o teste terminar logo, e conferem a caixa FIM DE JOGO na última tela:

| Cenário | Resultado esperado |
|---|---|
| robô acerta tudo na linha 25 | 63/63, 1920 pontos, combo 63, 100%, conceito S |
| robô acerta na linha 24 ou 26 | idem (ainda PERFEITO) |
| robô acerta na linha 23 ou 27 | 63/63, 960 pontos (QUASE) |
| robô aperta na linha 21 | 0 acertos, conceito D: mesmo lida no frame seguinte, a nota estaria na 22, fora da janela |
| ninguém joga | 0 acertos, conceito D |
| cada música extra do menu (tecla M) | o robô acerta todas as notas; vale para qualquer partitura nova |
| tecla sem nota | alvo preenchido `{O}`, sem faísca, ERROS = 001 e, depois, o alvo volta ao normal |
| animação | aparecem notas inteiras `(=)` e em meia linha (`/=\` sobre `\=/`) |
| reinício | ESPAÇO no fim volta ao menu e a nova partida começa zerada |

Em todos os cenários de pontuação, o teste exige também **62 notas tocadas, todas via `SNDN`, 0 via `SOUND` e 0 ms de CPU travada**.

## 11.3 testa_tudo.py

Um único comando roda tudo, em cerca de 10 segundos: a validação de todas as partituras da lista (`gera_musica.py --validar`), os testes do conversor de tablatura (`testa_tab.py`), os cenários do jogo (`testa_jogo.py`) e os três programas do Simple Simulator (seção 12.3), conferindo a última linha impressa por cada um. No `TesteSndn.asm`, confere também as notas da `SNDN`, no Simple Simulator e no harness do simulador gráfico.

Cada programa do Simple Simulator é montado em uma pasta temporária, porque ele sempre lê `cpuram.mif` da pasta atual e não deve sobrescrever o arquivo do jogo. A entrada `q` encerra o simulador quando o programa termina. Os resultados são combinados com `&`, e não com `and`, para que todos os programas rodem mesmo se um deles falhar.

## 11.4 Como o testa_jogo.py funciona

| Função | O que faz |
|---|---|
| `ambiente()` | coloca as DLLs do MSYS2 primeiro no `PATH`, porque outras cópias, como a do Git, são incompatíveis e abortam o harness no Windows |
| `roda(*args)` | executa o jogo no harness e devolve o texto impresso; falha se o código de saída não for 0 |
| `ultima_tela(saida)` | separa a última tela impressa |
| `resultado(saida)` | lê com expressões regulares os números da caixa FIM DE JOGO |
| `musicas_do_jogo()` | lê do `jogo.asm` o nome e o tamanho de cada música |
| `som(saida)` | lê o resumo de som: notas, `SOUND`, `SNDN` e tempo de CPU travada |
| `main()` | roda os cenários, compara com o esperado e termina com código 1 se algum falhar |

**Decisões:**

- **Nível 9 nos testes.** É o nível com frames mais curtos, então a partida inteira usa menos instruções e o teste termina mais rápido. A pontuação não depende da velocidade.
- **Conferir a tela, não a memória.** O teste lê os mesmos números que o jogador vê, então também detecta erros de desenho e de cálculo na tela final.
- **Valores calculados à mão.** Os 1920 e 960 pontos do capítulo 7 são conferidos exatamente, por isso uma mudança acidental na regra de pontuação faz o teste falhar.
- **Músicas lidas do `jogo.asm`.** Uma música nova na lista é testada automaticamente, sem alterar o script.

## 11.5 Como o testa_tab.py funciona

Testa o conversor com duas tablaturas escritas para o próprio teste, sem passar pelo jogo. Elas têm texto, cifras, casas de 2 dígitos, bend, hammer-on, nota abafada, acorde e Drop D. A função `args` cria as opções do conversor com os valores padrão, trocando só o que cada caso precisa. `notas_da_saida` extrai as notas e durações da partitura gerada e `confere` compara com o esperado. O último caso passa a partitura pelo `gera_musica.py`, para garantir que a saída do conversor é aceita pelo gerador.

## 11.6 Programas da pasta testes/

| Arquivo | Para que serve |
|---|---|
| `teste_som.asm` | toca Dó-Ré-Mi com `SOUND`: a tela só avança quando cada nota termina |
| `teste_sndn.asm` | o mesmo programa com `SNDN`, para comparar: nenhuma nota trava a CPU |
| `teste_beep.cpp` | teste de ouvido do `Sound.cpp` real, sem o simulador |
| `diagnostico_audio.cpp` | abre o áudio dos dois jeitos (seção 9.2) e mede o buffer entregue, para mostrar o problema de formato |
| `calibra.asm` | mede a velocidade real do simulador (seção 9.1) |
| `simples/TesteCPU.asm`, `simples/TesteExtra.asm`, `simples/TesteSndn.asm` | testes de instruções do Simple Simulator, incluindo a `SNDN` (seção 12.3) |

# 12. Simple Simulator

`SimpleSimulator/simple_simulator.c` implementa o Processador ICMC **ciclo a ciclo**, como no hardware, a partir do template da disciplina. Em vez de executar cada instrução numa linha de C (como o `Model.cpp`), ele modela o caminho de dados: registradores, multiplexadores, ULA, memória e os sinais de controle gerados por uma máquina de estados.

**Para que ele serve?** O simulador gráfico mostra o que cada instrução faz; o Simple Simulator mostra como o hardware faz, sinal por sinal. Ele é um programa separado, que lê `cpuram.mif` da pasta atual e escreve no terminal. Implementa a `SNDN` (seção 8.7), mas não a `SOUND`, que o jogo não usa. O projeto o verifica com programas de teste próprios (seção 12.3).

**O jogo roda nele?** O `cpuram.mif` do jogo executa, e a música sai igual: as 40 primeiras notas da primeira música do menu foram iguais às do harness do simulador gráfico, em uma verificação feita uma vez. Nela, a tecla ESPAÇO foi injetada no código, porque no Windows o `_kbhit` não lê uma entrada redirecionada. Mas ele não serve para jogar: sem tela, cada `OUTCHAR` só acrescenta um caractere ao terminal, e sem clock fixo ele roda mais devagar que o tempo real. Para jogar, o simulador é o gráfico.

Além do laço principal em `main`, o arquivo tem funções de apoio: `le_arquivo` e `processa_linha` carregam a memória, `pega_pedaco` separa campos do `IR`, `condicao_verdadeira` avalia as condições de salto, `ULA` faz os cálculos, `rotl16` e `rotr16` fazem as rotações e `le_tecla` lê o teclado, com uma versão para cada sistema operacional.

## 12.1 Estrutura de um ciclo

Cada volta do laço principal é um ciclo de clock e tem três fases:

1. **Borda de clock:** os registradores com sinal de carga ligado recebem o valor (`if (LoadIR) IR = DATA_OUT;`, `if (LoadReg[rx]) reg[rx] = M2;`, `if (RW == 1) MEMORY[M1] = M5;`...). Depois todos os sinais de carga são zerados.
2. **Unidade de controle:** um `switch(state)` liga os sinais de controle e escolhe as entradas dos muxes para o próximo ciclo, além de decidir o próximo estado.
3. **Lógica combinacional:** calcula as saídas dos muxes, na ordem das dependências (M4 antes de M1 e M2; leitura da memória antes de M2; M3 antes da ULA e de M5), e a ULA.

| Mux | Seleciona | Uso |
|---|---|---|
| M1 | PC, MAR, M4, SP | endereço da memória |
| M2 | ULA, DATA_OUT, M4, SP, teclado | dado escrito no registrador |
| M3 | r0..r7 ou FR (8) | operando X da ULA e dado a gravar |
| M4 | r0..r7 ou a constante 1 (8) | operando Y da ULA, endereço indireto, novo SP |
| M5 | PC ou M3 | dado escrito na memória |
| M6 | ULA ou DATA_OUT | novo valor de FR |

## 12.2 Máquina de estados

| Estado | O que faz |
|---|---|
| RESET | zera registradores e flags; `PC = 0`, `SP = 32767` |
| FETCH (busca) | `selM1 = sPC, RW = 0, LoadIR = 1, IncPC = 1` (comum a todas as instruções) |
| DECODE | decodifica o opcode e termina as instruções de 1 ciclo (LOADN, LOADI, STOREI, MOV, ULA, INC, CMP, JMP, PUSH, SNDN...) |
| EXECUTE | 2º ciclo de LOAD, STORE, CALL, POP e RTS |
| EXECUTE2 | 3º ciclo do RTS: `IncPC`, para pular a palavra de endereço do CALL |
| HALTED | parado; `r` reinicia, `q` sai |

A implementação foi conferida contra os diagramas de estados da disciplina (Figma "CPU_ICMC-team-library"), instrução por instrução: busca, NOOP, LOADN, LOAD, STORE, LOADI, STOREI, MOV, ADD e demais operações da ULA, INC/DEC, CMP, JMP, CALL, RTS, PUSH e POP seguem os mesmos sinais de controle e as mesmas transições de estado. A única diferença é no MOV: o diagrama testa `IR0` e depois `IR1`, e o código usa `switch(IR[1..0])` (`00` -> Rx<-Ry, `01` -> Rx<-SP, demais -> SP<-Rx). Os dois só divergem na codificação `10`, que o montador nunca gera: para `MOV SP, Rx` ele escreve `11` (`montador.c`, linha 593). O simulador gráfico faz igual ao código. A `SNDN` não aparece nos diagramas porque é a instrução criada por este projeto (seção 8.7).

## 12.3 Testes do Simple Simulator

`testes/simples/TesteCPU.asm` imprime uma letra por instrução testada (saída esperada `ABCDEFGHIJKLMNOP`). `testes/simples/TesteExtra.asm` cobre o que o jogo usa e o TesteCPU não cobre: `MOD`, `PUSH FR`/`POP FR`, `MOV SP`, chamadas aninhadas e `jle`/`jeg`/`jel` (saída esperada `abcdefghij`, idêntica à do simulador gráfico).

`testes/simples/TesteSndn.asm` testa a instrução nova (saída esperada `abcdef`, mais 9 notas):

| Letra | O que confere |
|---|---|
| `a` | `Rx` é a frequência, `Ry` a duração e `Rz` a onda, e os registradores não mudam |
| `b` | outros registradores funcionam, ou seja, os três campos são lidos do `IR` |
| `c` | o mesmo registrador pode ser usado nos três operandos |
| `d` | os flags não mudam: `EQUAL` continua ligado ou desligado depois da instrução |
| `e` | operandos montados como no `TocaMelodia` do jogo: tabela, `mul` e variável |
| `f` | em um laço, dentro de uma rotina, ela ocupa uma palavra e a pilha volta ao mesmo lugar |

O `testa_tudo.py` exige as 9 notas na ordem certa e roda o mesmo programa no harness, que usa o `Model.cpp` do simulador gráfico. Se os dois simuladores divergirem, o teste falha.

## 12.4 Limitações conhecidas da ULA do Simple Simulator

Os diagramas definem a máquina de controle, não os cálculos da ULA. Na revisão do código, estes pontos da ULA foram identificados como divergentes de uma ULA de 16 bits correta. O jogo não depende deles:

- `ADD` com estouro faz `result -= 65535` em vez de cortar em 16 bits (`0xFFFF + 1` dá 1 em vez de 0).
- `SUB` usa `unsigned`, então o teste `result < 0` nunca é verdadeiro e o flag de negativo não liga; o SUBC (bit 0) é ignorado.
- `MULT` e os deslocamentos não cortam o resultado em 16 bits.
- `rotl16`/`rotr16` usam `16*8` (128) em vez de 16 bits.
- O teste de limite de memória usa `M1 > TAMANHO_MEMORIA` em vez de `>=`.
- Os `#define` dizem `NEGATIVE = 9` e `DIV_BY_ZERO = 6`, mas a tabela de condições de salto testa os bits trocados (herdado do template).

# 13. Como compilar e executar

**Dependências.** Linux (Debian/Ubuntu): `build-essential pkg-config libgtk2.0-dev libsdl2-dev python3`. Windows: MSYS2 UCRT64 com `gcc`, `gtk2`, `SDL2` e `pkgconf`.

```
./build.sh                                   # compila montador, simulador, Simple Simulator e harness
python tools/gera_jogo.py                    # gera sprites, telas e músicas e monta o cpuram.mif
./Simulador/sim cpuram.mif charmap.mif       # joga (Home = execução automática)
python tools/testa_tudo.py                   # todos os testes
./SimpleSimulator/simples                    # carrega o cpuram.mif da pasta atual, sem tela nem áudio
```

`build.sh` detecta o Windows pelo `uname` e acrescenta a extensão `.exe` e a biblioteca `winmm` (usada pelo `timeBeginPeriod`). No Git Bash, `C:\msys64\ucrt64\bin` precisa estar no `PATH` para os programas encontrarem as bibliotecas do MSYS2.

**Adicionar uma música** (escrita à mão ou convertida de uma tablatura):

```
python tools/tab_para_jogo.py minha_tab.txt -o tools/musicas/nova.txt --nome "NOVA"   # se vier de tab
python tools/gera_musica.py --validar tools/musicas/nova.txt
#   acrescentar "nova.txt" em tools/musicas/lista.txt
python tools/gera_jogo.py
python tools/testa_tudo.py
```

**Alterar telas ou sprites:** edite `tools/telas/*.txt` ou os desenhos em `tools/gera_charmap.py` e rode `python tools/gera_jogo.py`.

**Atualizar este documento:** edite `docs/documentacao_tecnica.md` e rode `python tools/gera_doc.py` (precisa do pacote `reportlab`).

# 14. Limites e restrições do projeto

| Limite | Valor | Origem |
|---|---|---|
| notas simultâneas na tela | 16 | slots de `notaY`/`notaPista` |
| duração do som de uma nota | 15 frames | campo de 4 bits no mapa |
| faixa de alturas | C3 a D8 (63 notas) | índice de 6 bits |
| sons simultâneos | 1 (monofônico) | semântica da `SNDN`; num acorde só a 1ª nota soa |
| notas por música no placar final | 999 | `ImprimeNumero` com 3 dígitos |
| pontuação | 65535 (cerca de 1600 notas todas no x4) | palavra de 16 bits (placar de 5 dígitos) |
| precisão | até 6553 notas | `CalculaPrecisao` em duas etapas, sem passar de `10 * totalNotas` |
| tamanho de uma música | ~1 palavra por frame | a memória de 32768 palavras comporta músicas de vários minutos |
| nome no menu / painel | 20 / 3 x 9 caracteres | largura fixa das áreas na tela |

# 15. Decisões de projeto em resumo

Este capítulo reúne as principais decisões do projeto, o motivo de cada uma e a alternativa descartada. O número entre parênteses é a seção com a explicação completa.

## 15.1 Processador e simulador

| Decisão (seção) | Por quê | Alternativa descartada |
|---|---|---|
| criar a instrução `SNDN` (8.1) | o `SOUND` trava a CPU enquanto a nota toca, o que congela as notas e o teclado | tocar a melodia com `SOUND` |
| `SNDN` interrompe a nota atual (8.3) | cada nota começa exatamente no ciclo da instrução e o erro de tempo não se acumula | enfileirar as notas |
| `SNDN` também no Simple Simulator (8.7) | o enunciado pede a modificação nele ou na FPGA | só no simulador gráfico |
| no Simple Simulator, mostrar a nota no terminal (8.7) | ele não tem áudio, e o `OUTCHAR` também só escreve no terminal | tocar com SDL, criando uma dependência |
| nenhum estado de espera na `SNDN` (8.7) | a CPU segue no ciclo seguinte, o que mostra que ela não bloqueia | esperar a duração da nota |
| mesmos operandos do `SOUND` e opcode vizinho (8.3) | não há formato novo a decodificar; trocar uma instrução pela outra é só mudar o nome | formato próprio |
| manter o `SOUND` bloqueante (8.3) | programas existentes continuam funcionando | alterar a instrução original |
| clock fixo de 5 MHz (4.2, 9.1) | medir tempo contando instruções só funciona se cada instrução levar o mesmo tempo | rodar o mais rápido possível |
| comparar com o instante inicial (9.1) | os erros do `sleep` não se acumulam | dormir um tempo fixo por bloco |
| recomeçar a contagem se atrasar 100 ms (9.1) | evita uma rajada de frames para compensar o atraso | acelerar até alcançar |
| abrir o áudio ao iniciar o simulador (9.2) | abrir leva centenas de ms e congelava o jogo na primeira nota | abrir na primeira nota |
| rampa de 5 ms em cada nota (9.2) | sem ela, cada nota estala | som sem envelope |
| buffer de áudio de 512 amostras (9.2) | reduz o atraso do som de ~46 ms para ~12 ms | 2048 amostras |

## 15.2 Jogo em Assembly

| Decisão (seção) | Por quê | Alternativa descartada |
|---|---|---|
| uma palavra da música por frame (3.3) | leitura direta com `mapa + frame` e nenhum contador de duração | lista de notas com tempos |
| máscara de bits nas pistas (3.3) | permite acordes com um simples `and` | uma palavra por nota |
| índice de nota em vez de frequência (3.3) | a frequência não caberia junto com os outros campos | guardar os Hz na palavra |
| `div` e `mod` para extrair campos (3.3) | cada campo sai com uma instrução | deslocamento e máscara |
| vetores paralelos para os slots (3.8) | endereço é rótulo + slot, sem multiplicar | vetor de registros |
| `notaY = 0` indica slot livre (3.8) | dispensa um terceiro vetor | vetor de ocupação |
| ler o mapa com 22 frames de atraso (4.3) | o som sai quando a nota passa pelo alvo | lista de sons separada |
| ler o teclado dentro da espera (4.2) | nenhuma tecla se perde | ler uma vez por frame |
| janela em linhas (4.4) | em milissegundos ela encolhe nos níveis rápidos, e isso gera a dificuldade | janela fixa em ms |
| meia linha só no desenho (4.5) | a animação fica suave sem mudar as regras de acerto | mudar a linha lógica |
| efeitos antes de mover as notas (5) | as notas ficam sempre por cima dos alvos restaurados | outra ordem no laço |
| apagar redesenhando o cenário (6.2) | alvo, divisórias e letras reaparecem | escrever espaços |
| acertar a nota mais baixa da pista (6.5) | a tecla vale para a que sairia primeiro da janela, como nos jogos de ritmo | a primeira do vetor |
| temporizadores em frames (6.5) | os efeitos duram sem parar o jogo | esperar dentro da rotina |
| um só `alvoTimer` por pista (6.5) | faísca e preenchimento terminam igual, e o novo efeito substitui o anterior | dois temporizadores |
| `hudSujo` (6.5) | o placar só é redesenhado quando muda | redesenhar a cada frame |
| precisão em duas etapas (6.6) | `acertos * 100` estouraria 16 bits a partir de 656 acertos | conta direta |
| tabela `traduz` de 128 posições (3.2) | tradução em uma leitura, sem cadeia de comparações | vários `cmp` |
| sprites com códigos consecutivos (6.7) | `Desenha3` e `Restaura3` servem para todo objeto de 3 caracteres | um desenho por objeto |
| cor somada no Assembly (3.1) | um único sprite de nota serve para as 4 pistas | 4 sprites por cor |
| tabela de teclas com pares (6.4) | funciona com Caps Lock, e trocar as teclas exige mudar só a string | vários `cmp` por tecla |
| `push` e `pop` em toda rotina (2.1) | qualquer rotina chama qualquer outra sem destruir registradores | combinar registradores caso a caso |

## 15.3 Ferramentas e testes

| Decisão (seção) | Por quê | Alternativa descartada |
|---|---|---|
| gerar telas e músicas com scripts (1.2) | desenhar e transcrever à mão é lento e propenso a erro | escrever os `static` diretamente |
| marcadores no `jogo.asm` (10.1) | um script nunca altera a lógica do jogo | arquivos separados, que o montador não une |
| lista de músicas em arquivo (10.2) | o menu fica registrado e nenhuma música some por esquecimento | passar na linha de comando |
| durações com `Fraction` (10.2) | conta exata, inclusive com tercinas | ponto flutuante |
| validar a jogabilidade (10.2) | avisa sobre trechos impossíveis antes de entrar no jogo | descobrir jogando |
| meia linha gerada do desenho da nota (10.3) | mudar a nota atualiza os seis sprites | desenhar cada um à mão |
| preservar CRLF no charmap (10.3) | o `fseek` do simulador só funciona assim no Windows | normalizar para LF |
| testes sem janela (11.1) | reproduzíveis, rápidos e sem depender de som ou interface | testar só jogando |
| mesmo `Model.cpp` nos testes (11.1) | testa o processador real, não uma cópia | simulador de teste separado |
| robô que lê a tela (11.1) | testa o jogo do ponto de vista do jogador | ler as variáveis na memória |
