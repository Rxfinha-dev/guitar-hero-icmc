# Formato de partitura do Guitar Hero ICMC — guia para transcritores

Este documento é **autocontido**: entregue-o a uma pessoa ou cole-o em qualquer modelo de IA
para transcrever uma música no formato que o jogo entende. A seção 12 traz um prompt pronto.

O resultado da transcrição é **um arquivo de texto** (ex.: `tools/musicas/minha_musica.txt`), que o
gerador `tools/gera_musica.py` converte no mapa de notas do jogo.

---

## 1. Como o jogo usa a partitura

- O jogo tem **4 pistas** (teclas **D F J K**, cores verde, vermelho, amarelo e azul). Cada nota da
  partitura cai numa pista, e o jogador aperta a tecla quando ela chega ao alvo.
- O tempo é medido em **frames**. A cada frame as notas descem uma linha. No nível de velocidade
  padrão (5), um frame dura cerca de **65 ms**.
- A música é **monofônica**: soa uma nota por vez, com a onda escolhida (seno, quadrada…). Um "acorde"
  faz duas ou mais notas caírem juntas, mas só a primeira soa.
- Cada nota soa por **no máximo 15 frames**. Uma nota mais longa soa só até esse limite e o resto
  da duração vira silêncio, sem atrasar a música.

---

## 2. Estrutura do arquivo

O arquivo tem um **cabeçalho** (diretivas) seguido do **corpo** (uma nota por linha, em ordem):

```
# comentário: linha começando com '#', ou '#' precedido de espaço
nome NOME NO MENU
painel LINHA1|LINHA2|LINHA3
onda 1
slots_por_tempo 8
pistas C4=0 D4=1 E4=2 G4=3

E4 1
D4 0.5
- 0.5
C4+G4 2
```

### Diretivas do cabeçalho

| Diretiva | Obrigatória | Valores | Para que serve |
|---|---|---|---|
| `nome` | **sim** | até **20** caracteres | nome mostrado no menu |
| `painel` | não | até 3 partes separadas por `\|`, **9** caracteres cada | nome no painel lateral durante o jogo (padrão: começo do `nome`) |
| `onda` | não | `0` seno, `1` quadrada, `2` triangular, `3` dente de serra (padrão `2`) | timbre |
| `slots_por_tempo` | não | inteiro ≥ 1 (padrão `4`) | quantos frames dura **1 tempo** (semínima) |
| `pistas` | recomendada | `NOTA=PISTA` separados por espaço, pista `0`–`3` | pista de cada altura; sem ela, a distribuição é automática |

Regras dos textos (`nome` e `painel`): letras sem acento, números, espaços e símbolos simples.
Sem aspas (`"`) e sem barra invertida (`\`). O gerador converte tudo para maiúsculas.

### Linhas do corpo

| Forma | Significado |
|---|---|
| `NOTA DURAÇÃO` | uma nota (ex.: `E4 1`) |
| `NOTA+NOTA DURAÇÃO` | notas juntas, até 4, em pistas diferentes (ex.: `C4+G4 2`); só a primeira soa |
| `NOTA@PISTA DURAÇÃO` | fixa a pista (0–3) só desta nota, sem mudar a altura (ex.: `E4@3 1`); vale também dentro de acordes (`C4@0+G4@2 2`) |
| `- DURAÇÃO` | pausa |

Não existe sintaxe de repetição (ritornelo, "2x"): escreva tudo por extenso, na ordem em que toca.

---

## 3. Notas

**Formato:** `LETRA` + `ACIDENTE` opcional + `OITAVA`, em notação científica (C4 = dó central, A4 = 440 Hz).

| Exemplo | Significado |
|---|---|
| `C4` | dó central |
| `F#4` | fá sustenido |
| `Bb3` | si bemol |
| `A4` | lá 440 Hz |

- Letras: `C D E F G A B` (dó ré mi fá sol lá si).
- Acidentes: `#` sustenido e `b` bemol. Equivalências: `C#` = `Db`, `D#` = `Eb`, `F#` = `Gb`, `G#` = `Ab`, `A#` = `Bb`.
- **Faixa aceita: `C3` a `D8`.** Nota mais grave que `C3` deve subir uma oitava (`E2` → `E3`). Se a música
  inteira ficar grave demais, transponha tudo junto, oitava por oitava, para não deformar a melodia.

**A partir de um número MIDI** (0–127): oitava = `n ÷ 12 − 1` (divisão inteira) e nome = posição `n mod 12`
na sequência `C C# D D# E F F# G G# A A# B`. Exemplo: MIDI 64 → 64 mod 12 = 4 → `E`, oitava 64 ÷ 12 − 1 = 4 → `E4`.

---

## 4. Durações

A duração é escrita em **tempos**, tomando a semínima (pulso) como 1. Pode ser inteiro, decimal ou fração:

| Figura | Duração |
|---|---|
| semibreve | `4` |
| mínima pontuada | `3` |
| mínima | `2` |
| semínima pontuada | `1.5` |
| semínima | `1` |
| colcheia pontuada | `0.75` |
| colcheia | `0.5` |
| semicolcheia | `0.25` |
| fusa | `0.125` |
| tercina de colcheias (3 no tempo) | `1/3` cada |
| tercina de semínimas (3 em 2 tempos) | `2/3` cada |

Em compassos compostos (6/8, 12/8), a colcheia vale `0.5` e a semínima pontuada vale `1.5`, como de costume.

**Regra obrigatória:** `duração × slots_por_tempo` precisa dar um **número inteiro de frames**.

| `slots_por_tempo` | Menor figura possível | Tercinas? | Andamento aproximado no nível 5 |
|---|---|---|---|
| `4` | semicolcheia (1 frame) | não | ~230 BPM |
| `6` | colcheia (3 frames), tercina de colcheia (2 frames) | sim | ~155 BPM |
| `8` | semicolcheia (2 frames) | não | ~115 BPM |
| `12` | semicolcheia (3 frames), tercina de colcheia (4 frames) | sim | ~77 BPM |

Andamento ≈ 60000 ÷ (`slots_por_tempo` × 65) BPM. Ele não precisa bater com o original, porque o jogador
ajusta a velocidade no menu (níveis 1 a 9). **Escolha `slots_por_tempo` primeiro pela menor figura
rítmica da música**, garantindo que ela dure pelo menos 2 ou 3 frames.

**Casos especiais:**
- **Ligadura:** some as durações numa nota só (semínima ligada a colcheia = `1.5`).
- **Anacruse** (começa no meio do compasso): escreva só as notas que existem; não precisa de pausa antes.
- **Swing:** aproxime cada par de colcheias como `2/3` + `1/3` (exige `slots_por_tempo` múltiplo de 3).
- **Mudança de andamento:** não é suportada. Use o andamento principal, ou multiplique as durações do
  trecho (ex.: trecho com o dobro da velocidade → durações pela metade).
- **Fermata:** aumente a duração da nota (o som para em 15 frames, mas a pausa continua).

---

## 5. Pistas

Na diretiva `pistas`, toda altura usada no corpo precisa aparecer com uma pista de `0` a `3`
(`0` = D, verde; `1` = F, vermelho; `2` = J, amarelo; `3` = K, azul).

1. **Preserve o contorno:** notas mais graves à esquerda, mais agudas à direita, como no Guitar Hero.
2. Com mais de 4 alturas, **agrupe** alturas vizinhas na mesma pista (ex.: `C4=0 D4=0 E4=1 F4=1 G4=2 A4=3`).
3. Se a mesma pista receber notas muito próximas (regra da seção 7), troque uma delas para a pista vizinha.
4. Notas juntas (`+`) precisam cair em **pistas diferentes**.

Sem a diretiva `pistas`, o gerador divide as alturas em 4 faixas iguais, da mais grave para a mais aguda.

---

## 6. Reduzindo a música para o jogo

O jogo toca **uma linha melódica**, então:

- Transcreva a **melodia principal**: a voz cantada, o riff principal ou a voz mais aguda e marcante.
- **Ignore** acompanhamento, baixo, bateria e harmonia de fundo.
- Use `+` com moderação, para destacar momentos fortes (fim de frase, ataque de refrão). A primeira
  nota do `+` é a que soa, então coloque a nota da melodia primeiro.
- Notas ornamentais muito rápidas (apojaturas, trinados) podem ser omitidas ou simplificadas.

---

## 7. Regras de jogabilidade

O validador (seção 10) confere estas regras automaticamente:

| Regra | Tipo |
|---|---|
| Duas notas na **mesma pista** a menos de **2 frames** uma da outra | **erro**: ficam grudadas na tela |
| Mesma pista a **2 frames** | aviso: rápido demais para a maioria dos jogadores |
| **3 ou mais** notas juntas (`+`) | aviso: muito difícil |
| Nota com mais de **15 frames** | aviso: o som é cortado em 15 frames |

**Recomendado:** pelo menos **3 a 4 frames** entre notas da mesma pista, e no máximo 2 notas juntas.
Uma música de 20 a 60 segundos (300 a 900 frames) é um bom tamanho para uma partida.

---

## 8. Como transcrever a partir de cada tipo de fonte

**Partitura:** leia nome e oitava de cada nota (a clave de sol tem o mi da primeira linha = `E4`) e a
figura rítmica (tabela da seção 4). Aplique as alterações da armadura de clave em todas as notas.

**Tablatura de guitarra (conversão automática):** o conversor `tools/tab_para_jogo.py` lê a tablatura em
texto do jeito que aparece no Cifra Club e gera a partitura pronta, já validada:

```bash
python tools/tab_para_jogo.py minha_tab.txt -o tools/musicas/minha_tab.txt --nome "MINHA TAB"
```

Ele ignora título, cifras e letra; lê a afinação pelos nomes das cordas (ex.: Drop D) ou por
`--afinacao`; trata casas de 2 dígitos, hammer-on/pull-off e slide (viram notas), bend (só a casa
antes do `b`) e notas abafadas (`x`, ignoradas); em acordes fica a nota mais aguda (`--acordes 2`
acrescenta a mais grave); aceita `--capo N`; transpõe por oitavas para caber em C3–D8; e distribui as
pistas da grave para a aguda, movendo com `@` as notas que ficariam grudadas na mesma pista.
O ritmo é deduzido do espaçamento entre as notas (o espaçamento mais comum vira 1 tempo; mude a
velocidade com `--frames-por-unidade`). Como tablatura em texto não tem ritmo exato, **ouça no jogo e
ajuste as durações se precisar**. Rode `python tools/tab_para_jogo.py --help` para ver todas as opções.

**Tablatura de guitarra (à mão):** cada número é a casa. Comece pela nota da corda solta e suba um semitom por casa.

| Corda | 6ª (mais grossa) | 5ª | 4ª | 3ª | 2ª | 1ª (mais fina) |
|---|---|---|---|---|---|---|
| Solta (afinação padrão) | E2 | A2 | D3 | G3 | B3 | E4 |

Exemplo: corda G (`G3`) na casa 5 → `G#3 A3 A#3 B3 C4` → **`C4`**. Afinações alternativas (Drop D, meio tom
abaixo…) mudam as notas soltas. As tablaturas raramente trazem o ritmo, então confira ouvindo a música.
Notas abaixo de `C3` sobem uma oitava.

**Arquivo MIDI:** pegue a trilha da melodia e converta cada número com a fórmula da seção 3. A duração
em tempos é `ticks da nota ÷ PPQ` (*pulses per quarter*, do cabeçalho do arquivo). Intervalos entre o fim
de uma nota e o início da próxima viram pausa `-`.

**Cifra (só acordes):** não basta, porque não traz a melodia. Use junto com outra fonte.

**De ouvido:** com um app de piano ou afinador, encontre cada nota tocando até soar igual. Bata o pé no
pulso: cada batida vale `1`, meia batida vale `0.5`.

---

## 9. Exemplo completo

Melodia tradicional *Brilha, Brilha, Estrelinha* (*Ah! vous dirai-je, maman*, França, séc. XVIII, domínio público):

```
# Brilha, Brilha, Estrelinha - melodia tradicional (dominio publico)
nome BRILHA ESTRELINHA
painel BRILHA|BRILHA|ESTRELA
onda 2
slots_por_tempo 6
pistas C4=0 D4=1 E4=1 F4=2 G4=2 A4=3

C4 1
C4 1
G4 1
G4 1
A4 1
A4 1
G4 2
F4 1
F4 1
E4 1
E4 1
D4 1
D4 1
C4 2
G4 1
G4 1
F4 1
F4 1
E4 1
E4 1
D4 2
G4 1
G4 1
F4 1
F4 1
E4 1
E4 1
D4 2
C4 1
C4 1
G4 1
G4 1
A4 1
A4 1
G4 2
F4 1
F4 1
E4 1
E4 1
D4 1
D4 1
C4+G4 2
```

O mesmo trecho, com ritmo de tercina (cada tempo dividido em 3), só para mostrar a sintaxe:

```
nome EXEMPLO TERCINAS
slots_por_tempo 6
pistas C4=0 D4=1 E4=2 G4=3
C4 1/3
D4 1/3
E4 1/3
G4 1
- 1
```

---

## 10. Validar e colocar no jogo

Na raiz do projeto:

```bash
# 1. confere o arquivo (formato + jogabilidade) sem mexer no jogo
python tools/gera_musica.py --validar tools/musicas/minha_musica.txt

# 2. gera o jogo com as musicas, na ordem do menu (tecla M troca)
python tools/gera_musica.py jogo.asm tools/musicas/ode_alegria.txt tools/musicas/minha_musica.txt

# 3. monta e testa (o robo de testes precisa acertar todas as notas da 2a musica)
./Montador/montador jogo.asm cpuram.mif
python tools/testa_jogo.py
```

Mensagens comuns do gerador:

| Mensagem | Correção |
|---|---|
| `nota X fora da faixa C3..D8` | suba ou desça uma oitava |
| `nota X sem pista definida` | acrescente `X=pista` na linha `pistas` |
| `... precisa ser inteiro` | aumente `slots_por_tempo` (múltiplo de 3 para tercinas) |
| `passa de 20 caracteres` / `passa de 9 caracteres` | encurte `nome` / `painel` |
| `ERRO: ... notas a 1 frame` | aumente `slots_por_tempo` ou mude uma nota de pista |

---

## 11. Checklist do transcritor

- [ ] Cabeçalho com `nome` (≤ 20), `painel` (≤ 9 por parte), `onda` e `slots_por_tempo`
- [ ] `pistas` lista **todas** as alturas usadas, preservando grave → agudo
- [ ] Todas as notas entre `C3` e `D8`, no formato `C4`, `F#4`, `Bb3`
- [ ] Cada `duração × slots_por_tempo` é um número inteiro
- [ ] Só a melodia principal; acordes `+` só em pistas diferentes, no máximo 2
- [ ] Repetições escritas por extenso
- [ ] `--validar` sem erros

---

## 12. Prompt pronto para um modelo de IA

Copie o bloco abaixo, preencha os campos entre `<...>` e anexe este documento (ou cole-o antes do prompt):

```
Você é um transcritor musical. Converta a música indicada para o formato de partitura do
"Guitar Hero ICMC", seguindo EXATAMENTE a especificação do documento anexado
(docs/formato_partitura.md).

Música: <título e autor>
Fonte que estou fornecendo: <partitura / tablatura / MIDI / descrição>
<cole aqui a fonte, se houver>

Requisitos:
1. Responda APENAS com o conteúdo do arquivo .txt, sem explicações antes ou depois.
2. Cabeçalho: nome (até 20 caracteres, sem acentos), painel (até 3 partes de 9 caracteres,
   separadas por |), onda (use 1 para rock/eletrônica, 2 para músicas suaves) e slots_por_tempo
   escolhido pela menor figura rítmica (seção 4 do documento).
3. Linha "pistas" com TODAS as alturas usadas, da mais grave (0) para a mais aguda (3).
4. Só a melodia principal, uma nota por linha: "NOTA DURAÇÃO", pausas "- DURAÇÃO",
   no máximo 2 notas juntas com "+".
5. Notas entre C3 e D8 (transponha oitavas se preciso); durações em tempos (semínima = 1),
   frações como 1/3 para tercinas; duração × slots_por_tempo sempre inteiro.
6. Mesma pista: pelo menos 3 frames entre notas.
7. Repetições escritas por extenso. Comentários com # marcando as seções (ex.: # --- Refrão ---).
```

Depois de receber a resposta, salve o texto em `tools/musicas/<nome>.txt` e rode o `--validar` (seção 10).
A IA pode errar notas ou ritmo, então **ouça no jogo e corrija**.

---

## 13. Direitos autorais

Músicas em **domínio público** (no Brasil, autores falecidos há mais de 70 anos: compositores clássicos,
Chiquinha Gonzaga, Ernesto Nazareth, cantigas folclóricas) podem ser transcritas e publicadas livremente.
Músicas protegidas podem ter restrições de reprodução e distribuição. Se o repositório for público,
prefira obras em domínio público ou composições próprias.
