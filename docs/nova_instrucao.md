# Instrução nova: `SNDN` — som não-bloqueante

## 1. Motivação

O Processador ICMC já tem uma instrução de som, `SOUND Rx, Ry, Rz`. No simulador
(`Simulator_Source/Model.cpp`) ela é executada assim:

```cpp
case SOUND:
  play_note(reg[rx], reg[ry], reg[rz]);
  break;
```

E a `play_note` original (`Simulator_Source/Sound.cpp`) faz:

```cpp
void play_note (int rx, int ry, int rz) {
    SDL_Init(SDL_INIT_AUDIO);   // reinicializa o audio a cada nota
    Beeper beeper;              // abre o dispositivo de audio a cada nota
    ...
    beeper.beep(type, rx, ry);
    beeper.wait(30);            // laco ate' a nota terminar de tocar
}
```

O `wait` deixa a CPU parada até a nota acabar, ou seja, **a instrução `SOUND` dura o
tempo da nota**. No simulador gráfico a execução acontece com o lock da interface
(`gdk_threads_enter`) e a janela inteira congela junto.

Num jogo de ritmo isso inviabiliza a música: enquanto uma nota toca, as notas não
descem e o teclado não é lido. Medimos isso com o harness de testes, rodando a música
inteira do jogo no nível de velocidade 5:

| Versão do jogo | Notas tocadas | CPU travada pelo som |
|---|---|---|
| melodia com `SOUND` (`tools/versao_sound.py`) | 62 | **24 960 ms**, a duração da música inteira |
| melodia com `SNDN` (`jogo.asm`) | 62 | **0 ms** |

## 2. Especificação

| | |
|---|---|
| **Mnemônico** | `SNDN Rx, Ry, Rz` |
| **Operandos** | `Rx` = frequência (Hz), `Ry` = duração (ms), `Rz` = forma de onda (0 seno, 1 quadrada, 2 triangular, 3 dente de serra) |
| **Opcode** | `110110` (54) |
| **Palavras** | 1 |
| **Flags** | não altera |

Formato (idêntico ao `SOUND`, muda só o opcode):

```
 15      10 9   7 6   4 3   1 0
+----------+-----+-----+-----+-+
|  110110  | Rx  | Ry  | Rz  |0|
+----------+-----+-----+-----+-+
```

Exemplo, montado pelo montador modificado: `sndn r1, r2, r3` → `1101100010100110`.

**Semântica.** Síntese **monofônica**: a instrução interrompe a nota que estiver
tocando, inicia a nova e termina no mesmo ciclo. A CPU segue executando enquanto
o áudio toca em paralelo.

### Decisões de projeto

- **Opcode `110110`.** Era livre e fica na família de E/S (`1101xx`), ao lado de
  `SOUND` (`110100`) e `INCHAR` (`110101`). O formato é o mesmo do `SOUND`, então o
  decodificador do hardware reaproveita os campos Rx/Ry/Rz sem nenhuma mudança.
- **Interromper em vez de enfileirar.** Se a `SNDN` só enfileirasse as notas, qualquer
  diferença entre a duração pedida e o tempo real de um frame se acumularia e a música
  sairia de sincronia com as notas na tela. Interrompendo, cada nota começa exatamente
  no ciclo da instrução, e o jogo é que dita o ritmo. É assim que funciona um "note on"
  num sintetizador monofônico.
- **Um único dispositivo de áudio.** O original abria e fechava o áudio (e chamava
  `SDL_Init`) a cada nota. Com duas instruções de som no mesmo programa, dois
  `SDL_OpenAudio` simultâneos falhariam. Agora há um `Beeper` global, criado uma
  única vez, compartilhado por `SOUND` e `SNDN`. **O `SOUND` mantém a semântica
  original:** continua esperando a nota terminar.

## 3. Arquivos alterados

### Simulador (`Simulador/`)

**`Mneumonicos.h`**: o opcode:
```c
#define SNDN 54      // "110110" - som nao-bloqueante (nova instrucao)
```

**`Model.cpp`**: a execução, ao lado do `SOUND`:
```cpp
case SNDN:    // Rx = frequencia (Hz), Ry = duracao (ms), Rz = forma de onda
  play_note_async(reg[rx], reg[ry], reg[rz]);
  break;
```

**`Sound.h` / `Sound.cpp`**: o comportamento:
```cpp
// Descarta as notas pendentes (incluindo a que esta' tocando) e inicia a nova.
void Beeper::replace(string wave, double freq, int duration){
    ...
    SDL_LockAudio();
    beeps = queue<BeepObject>();
    beeps.push(bo);
    SDL_UnlockAudio();
}

static Beeper& beeperGlobal() {          // um dispositivo de audio para tudo
    static bool iniciado = (SDL_Init(SDL_INIT_AUDIO) == 0);
    static Beeper beeper;
    ...
}

void play_note (int rx, int ry, int rz) {        // SOUND: continua bloqueante
    Beeper& beeper = beeperGlobal();
    beeper.beep(tipoOnda(rz), rx, ry);
    beeper.wait(30);
}

void play_note_async (int rx, int ry, int rz) {  // SNDN: nao espera
    beeperGlobal().replace(tipoOnda(rz), rx, ry);
}
```
Também corrigimos a fase da onda (`Beeper::v`), que começava sem inicialização, e um
**defeito do original que deixava o simulador mudo no Windows**. O `Beeper` abria o áudio com
`SDL_OpenAudio(&desiredSpec, &obtainedSpec)`, e nesse modo o SDL2 entrega ao callback o
formato da placa, sem conversão. No Windows (driver WASAPI) a placa trabalha com float de
32 bits estéreo, mas o callback escrevia inteiros de 16 bits mono, e o resultado era silêncio.
Passando `NULL` no lugar de `&obtainedSpec`, o SDL converte automaticamente. O programa
`testes/diagnostico_audio.cpp` mostra a diferença na própria máquina:

```
driver de audio: wasapi
1) Sound.cpp ORIGINAL (com obtainedSpec):
  placa aceitou: F32 (float 32 bits), 2 canal(is), 44100 Hz
  buffer do callback: 3528 bytes (S16 mono certo = 4096) -> FORMATO ERRADO, sem som
2) Sound.cpp CORRIGIDO (obtained = NULL):
  buffer do callback: 4096 bytes (S16 mono certo = 4096) -> OK, som sai
```

**`View.cpp`**: o desassemblador do painel "Memória" passa a mostrar `SOUND` e `SNDN`.
Antes, o `SOUND` caía no `default` e imprimia `ERRO - show program linha` no console.

### Montador (`Montador/`)

Seguindo o [roteiro do professor](https://gitlab.com/simoesusp/disciplinas/-/blob/master/SSC0119-Pratica-em-Organizacao-de-Computadores/Modificar_Montador/README.md):
três pontos no `defs.h` e três no `montador.c`.

**`defs.h`**
```c
#define SNDN_CODE               99
#define SNDN            "110110"   /* som nao-bloqueante (nova instrucao) */
#define SNDN_STR                "SNDN"
```

**`montador.c`**
1. Contagem de palavras (1ª passada): `case SNDN_CODE:` junto com `SOUND_CODE`, ou seja,
   3 registradores separados por vírgula e 1 palavra.
2. Geração do binário (2ª passada): bloco `case SNDN_CODE:` que lê os 3 registradores e
   escreve `sprintf(str_msg, "%s%s%s%s0", SNDN, str_tmp1, str_tmp2, str_tmp3);`.
3. Reconhecimento do mnemônico: `else if (strcmp(str_tmp, SNDN_STR) == 0) return SNDN_CODE;`.

### Hardware (FPGA)

Para levar a `SNDN` à FPGA, a unidade de controle trata o opcode `110110` como o
`SOUND`, mas sem o estado de espera. Os campos Rx/Ry/Rz já são decodificados do
mesmo jeito. *(Este trabalho foi feito para a SSC0511, em que o simulador basta.)*

## 4. Uso no jogo

A subrotina `TocaMelodia` do `jogo.asm` toca, a cada frame, a nota da música que está
chegando ao alvo:

```asm
	load r2, ondaMelodia        ; r2 = forma de onda
	sndn r0, r1, r2             ; NOVA INSTRUCAO: inicia a nota e segue em frente
```

Com `SOUND` no lugar, cada nota pararia o laço do jogo pela duração inteira dela.

## 5. Como reproduzir a comparação

```bash
./build.sh
python tools/versao_sound.py                                   # gera testes/jogo_sound.asm (SOUND)
./Montador/montador testes/jogo_sound.asm testes/jogo_sound.mif
./Simulador/sim testes/jogo_sound.mif charmap.mif              # ANTES: congela a cada nota
./Simulador/sim cpuram.mif charmap.mif                         # DEPOIS: fluido

# medicao automatica (sem janela), na velocidade padrao:
./tools/headless/headless testes/jogo_sound.mif charmap.mif --key "350000: " --autoplay --cycles 600000000 --quiet
./tools/headless/headless cpuram.mif charmap.mif --key "350000: " --autoplay --cycles 600000000 --quiet
```

E os programas mínimos `testes/teste_som.asm` (`SOUND`) e `testes/teste_sndn.asm` (`SNDN`)
tentam tocar Dó-Ré-Mi escrevendo um `*` entre as notas. Com `SOUND`, ouvem-se as três notas
e os `*` aparecem com atraso, um a cada nota. Com `SNDN`, os três `*` aparecem na hora e
só se ouve o Mi: as instruções executam em microssegundos e cada uma substitui a nota
anterior (síntese monofônica). Para tocar uma melodia com `SNDN`, o programa precisa
espaçar as notas no tempo, como o jogo faz a cada frame.
