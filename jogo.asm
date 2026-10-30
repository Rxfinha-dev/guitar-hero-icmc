;==============================================================================
;
;   GUITAR HERO ICMC - jogo de ritmo em Assembly do Processador ICMC
;
;   Disciplina: SSC0511 - Organizacao de Computadores Digitais (ICMC-USP)
;
;------------------------------------------------------------------------------
;   COMO JOGAR
;     As notas descem por 4 pistas. Aperte a tecla da pista (D, F, J, K)
;     quando a nota estiver sobre o alvo (linha 25 da tela).
;       - nota no alvo, com folga de 1 linha (linhas 24 a 26) ... 10 pontos ("PERFEITO!")
;       - nota a 2 linhas do alvo (linha 23 ou 27) .............  5 pontos ("QUASE")
;         (nos dois casos aparece uma faisca no alvo)
;       - a cada 10 acertos seguidos o multiplicador sobe (maximo x4)
;       - deixar a nota passar zera o combo ("ERROU!")
;       - apertar sem nota na janela preenche o alvo da pista e zera o combo
;     A musica toca sozinha, sincronizada com as notas.
;
;   No menu: teclas 1 a 9 escolhem a velocidade, M troca a musica
;   (as musicas vem de tools/musicas/*.txt) e ESPACO comeca.
;
;------------------------------------------------------------------------------
;   MODIFICACAO DA ARQUITETURA: instrucao SNDN
;     A instrucao original SOUND Rx, Ry, Rz trava a CPU enquanto a nota toca.
;     Num jogo de ritmo isso congela as notas e o teclado. A nova instrucao
;     SNDN Rx, Ry, Rz (opcode 110110) tem os mesmos operandos, mas apenas
;     inicia a nota e devolve o controle na hora (ver subrotina TocaMelodia).
;       Rx = frequencia em Hz   Ry = duracao em ms   Rz = forma de onda
;
;------------------------------------------------------------------------------
;   TELA: 40 colunas x 30 linhas. posicao = coluna + 40 * linha
;
;   Um caractere na tela e' uma palavra de 16 bits:
;       bits 6-0  = codigo do caractere (0..127, desenho no charmap.mif)
;       bits 11-8 = indice da cor  -> basta somar (cor * 256) ao codigo
;
;   Cores (indice * 256):
;       0 branco      512 verde      1024 azul marinho   1536 verde-azulado
;    1792 prata      2048 cinza      2304 vermelho       2560 verde-limao
;    2816 amarelo    3072 azul       3328 rosa           3584 agua
;
;   Sprites do jogo no charmap (codigos livres 1..31, gerados por tools/gera_charmap.py):
;       1,2,3 = nota (esquerda, meio, direita)     5 = divisoria da pista
;       6,7,8 = alvo vazado (esquerda, meio, dir)  9,10 = borda vertical/horizontal
;       11..14 = cantos da moldura                 16 = nota musical   17 = faisca
;
;   Os cenarios sao desenhados em tools/telas/*.txt e viram as strings
;   telaLxx / menuLxx / fimLxx (tools/gera_telas.py). Nesses desenhos o TEXTO
;   fica em MAIUSCULAS e cada letra minuscula e' um sprite, traduzido pela
;   tabela `traduz` (subrotina Traduz). Legenda:
;       a b c d = cantos   h = borda horizontal   v = borda vertical
;       p = divisoria das pistas                  s = nota musical
;       e f g = alvo verde    i j k = alvo vermelho
;       l m n = alvo amarelo  o q r = alvo azul
;       w x y z = letras D F J K nas cores das pistas
;
;------------------------------------------------------------------------------
;   ORGANIZACAO DO ARQUIVO
;     1. Configuracao e variaveis de estado
;     2. Tabelas (pistas, velocidade, traducao de sprites, mensagens)
;     3. Dados gerados: telas e musica
;     4. Programa principal e laco do jogo
;     5. Subrotinas: menu, notas, teclado, pontuacao, som, desenho, utilitarios
;
;   Convencao: toda subrotina preserva os registradores que usa (push/pop),
;   exceto os de retorno, que estao documentados no cabecalho dela.
;
;   Detalhes do processador/simulador que o codigo respeita:
;     - CMP nao altera o flag de zero: depois de CMP use jeq/jne/jgr/jle/jeg/jel
;       (jgr = maior, jle = MENOR estrito, jeg = maior ou igual, jel = menor ou igual)
;     - DEC/INC/ADD... atualizam o flag de zero (usado por jz/jnz);
;       STORE e STOREI nao mexem nos flags.
;     - SUB com resultado negativo vira 0: o codigo nunca depende de negativos.
;     - INCHAR devolve 255 quando nenhuma tecla foi apertada.
;
;==============================================================================

jmp main

;==============================================================================
; 1. CONFIGURACAO E VARIAVEIS DE ESTADO
;==============================================================================

velocidade : var #1             ; nivel de velocidade escolhido no menu (1..9)
static velocidade + #0, #5

musicaSel : var #1              ; musica escolhida no menu (0 = primeira da lista)
musicaAtual : var #1            ; endereco do mapa da musica em jogo = tabMusicas[musicaSel]
ondaMelodia : var #1            ; forma de onda da musica em jogo = tabOndas[musicaSel]
                                ; (0 seno, 1 quadrada, 2 triangular, 3 dente de serra)

pontos : var #1                 ; pontuacao (cabe em 16 bits: no maximo ~3000)
combo : var #1                  ; acertos seguidos
comboMax : var #1               ; maior combo da partida
mult : var #1                   ; multiplicador de pontos (1..4)
acertos : var #1
erros : var #1                  ; notas perdidas + teclas apertadas sem nota
totalNotas : var #1             ; notas que ja surgiram na tela
hudSujo : var #1                ; 1 = placar mudou e precisa ser redesenhado

frame : var #1                  ; contador de frames desde o inicio da musica
spawnAcabou : var #1            ; 1 = todas as notas da musica ja surgiram
musicaAcabou : var #1           ; 1 = a ultima nota ja chegou no alvo
fimContador : var #1            ; frames que faltam para a tela de fim de jogo

msgTimer : var #1               ; frames ate apagar a mensagem (PERFEITO!/ERROU!)
notasNoMeio : var #1            ; 1 = notas desenhadas meia linha abaixo (2a metade do frame)
faiscaTimer : var #4            ; frames ate apagar a faisca de cada pista
pressTimer : var #4             ; frames ate esvaziar o alvo preenchido (tecla sem nota)

; Usados pela TentaAcerto para escolher a nota mais antiga da janela
acertoSlot : var #1             ; slot da nota escolhida (255 = nenhuma)
acertoY : var #1                ; linha dela

; Notas ativas na tela: 16 "slots" em vetores paralelos.
; notaY[i] = linha da nota (0 = slot livre); notaPista[i] = pista 0..3
notaY : var #16
notaPista : var #16

;==============================================================================
; 2. TABELAS
;==============================================================================

; Coluna onde comeca cada pista (cada nota ocupa 3 colunas)
pistaX : var #4
static pistaX + #0, #12
static pistaX + #1, #16
static pistaX + #2, #20
static pistaX + #3, #24

; Cor de cada pista, como no Guitar Hero: verde, vermelho, amarelo, azul
pistaCor : var #4
static pistaCor + #0, #512
static pistaCor + #1, #2304
static pistaCor + #2, #2816
static pistaCor + #3, #3072

; Bit de cada pista na mascara do mapa da musica
bitPista : var #4
static bitPista + #0, #1
static bitPista + #1, #2
static bitPista + #2, #4
static bitPista + #3, #8

; Velocidade: duracao de um frame do jogo, em ms, para cada nivel (1..9).
; O simulador roda com clock fixo de 5 MHz (CLOCK_HZ em Mneumonicos.h), e cada
; volta do laco externo do Delay executa 5000 instrucoes = exatamente 1 ms.
; Por isso a mesma tabela da' o tamanho do Delay E a duracao das notas da musica,
; e o som fica sincronizado com as notas na tela.
tabMsFrame : var #10
static tabMsFrame + #1, #200
static tabMsFrame + #2, #150
static tabMsFrame + #3, #112
static tabMsFrame + #4, #85
static tabMsFrame + #5, #65
static tabMsFrame + #6, #50
static tabMsFrame + #7, #37
static tabMsFrame + #8, #30
static tabMsFrame + #9, #22

; traduz[c] = palavra final (sprite + cor) da letra minuscula c dos cenarios.
; 0 = nao e' sprite (texto comum). Valor = codigo do sprite + cor * 256.
traduz : var #128
static traduz + #97, #3595      ; 'a' canto superior esquerdo  (11 + agua)
static traduz + #98, #3596      ; 'b' canto superior direito   (12 + agua)
static traduz + #99, #3597      ; 'c' canto inferior esquerdo  (13 + agua)
static traduz + #100, #3598     ; 'd' canto inferior direito   (14 + agua)
static traduz + #104, #3594     ; 'h' borda horizontal         (10 + agua)
static traduz + #118, #3593     ; 'v' borda vertical           ( 9 + agua)
static traduz + #112, #1541     ; 'p' divisoria da pista       ( 5 + verde-azulado)
static traduz + #115, #3344     ; 's' nota musical             (16 + rosa)
static traduz + #101, #518      ; 'e' alvo verde, esquerda     ( 6 + verde)
static traduz + #102, #519      ; 'f' alvo verde, meio         ( 7 + verde)
static traduz + #103, #520      ; 'g' alvo verde, direita      ( 8 + verde)
static traduz + #105, #2310     ; 'i' alvo vermelho, esquerda  ( 6 + vermelho)
static traduz + #106, #2311     ; 'j' alvo vermelho, meio
static traduz + #107, #2312     ; 'k' alvo vermelho, direita
static traduz + #108, #2822     ; 'l' alvo amarelo, esquerda   ( 6 + amarelo)
static traduz + #109, #2823     ; 'm' alvo amarelo, meio
static traduz + #110, #2824     ; 'n' alvo amarelo, direita
static traduz + #111, #3078     ; 'o' alvo azul, esquerda      ( 6 + azul)
static traduz + #113, #3079     ; 'q' alvo azul, meio
static traduz + #114, #3080     ; 'r' alvo azul, direita
static traduz + #119, #580      ; 'w' letra D verde            (68 + verde)
static traduz + #120, #2374     ; 'x' letra F vermelha         (70 + vermelho)
static traduz + #121, #2890     ; 'y' letra J amarela          (74 + amarelo)
static traduz + #122, #3147     ; 'z' letra K azul             (75 + azul)

; Mensagens da linha 28 (exatamente 15 caracteres: a largura das pistas)
msgPerfeito : string "   PERFEITO!   "
msgQuase    : string "     QUASE     "
msgErrou    : string "    ERROU!     "
msgSemNota  : string "  NADA AQUI!   "
tituloJogo  : string "GUITAR HERO ICMC"

;==============================================================================
; 3. DADOS GERADOS (nao edite a mao: rode os scripts de tools/)
;==============================================================================

; >>> TELA telaL  (gerado por tools/gera_telas.py a partir de tools/telas/jogo.txt - nao edite a mao)
telaL00 : string "ahhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhb"
telaL01 : string "v         s GUITAR HERO ICMC s         v"
telaL02 : string "vhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhv"
telaL03 : string "v          p   p   p   p   p           v"
telaL04 : string "v MUSICA   p   p   p   p   p PONTOS    v"
telaL05 : string "v          p   p   p   p   p  00000    v"
telaL06 : string "v          p   p   p   p   p           v"
telaL07 : string "v          p   p   p   p   p COMBO     v"
telaL08 : string "v          p   p   p   p   p  000      v"
telaL09 : string "v          p   p   p   p   p           v"
telaL10 : string "v TECLAS   p   p   p   p   p MULT      v"
telaL11 : string "v w x y z  p   p   p   p   p  X1       v"
telaL12 : string "v          p   p   p   p   p           v"
telaL13 : string "v ACERTE ASp   p   p   p   p ACERTOS   v"
telaL14 : string "v AS NOTAS p   p   p   p   p  000      v"
telaL15 : string "v NO ALVO  p   p   p   p   p           v"
telaL16 : string "v          p   p   p   p   p ERROS     v"
telaL17 : string "v          p   p   p   p   p  000      v"
telaL18 : string "v          p   p   p   p   p           v"
telaL19 : string "v VELOC.   p   p   p   p   p           v"
telaL20 : string "v          p   p   p   p   p           v"
telaL21 : string "v          p   p   p   p   p           v"
telaL22 : string "v          p   p   p   p   p           v"
telaL23 : string "v          p   p   p   p   p           v"
telaL24 : string "v          p   p   p   p   p           v"
telaL25 : string "v          pefgpijkplmnpoqrp           v"
telaL26 : string "v          p w p x p y p z p           v"
telaL27 : string "v          p   p   p   p   p           v"
telaL28 : string "v          p   p   p   p   p           v"
telaL29 : string "chhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhd"
; <<< TELA telaL

; >>> TELA menuL  (gerado por tools/gera_telas.py a partir de tools/telas/menu.txt - nao edite a mao)
menuL00 : string "ahhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhb"
menuL01 : string "v                                      v"
menuL02 : string "v                                      v"
menuL03 : string "v         s GUITAR HERO ICMC s         v"
menuL04 : string "v                                      v"
menuL05 : string "v      JOGO DE RITMO EM ASSEMBLY       v"
menuL06 : string "v         DO PROCESSADOR ICMC          v"
menuL07 : string "v                                      v"
menuL08 : string "v          efg  ijk  lmn  oqr          v"
menuL09 : string "v           w    x    y    z           v"
menuL10 : string "v                                      v"
menuL11 : string "v  COMO JOGAR:                         v"
menuL12 : string "v  AS NOTAS DESCEM PELAS 4 PISTAS.     v"
menuL13 : string "v  APERTE A TECLA DA PISTA QUANDO A    v"
menuL14 : string "v  NOTA ESTIVER SOBRE O ALVO.          v"
menuL15 : string "v                                      v"
menuL16 : string "v  NO ALVO (1 LINHA DE FOLGA) 10 PONTOSv"
menuL17 : string "v  QUASE (2 LINHAS) .......... 5 PONTOSv"
menuL18 : string "v  10 ACERTOS SEGUIDOS SOBEM O         v"
menuL19 : string "v  MULTIPLICADOR (ATE X4).             v"
menuL20 : string "v                                      v"
menuL21 : string "v  VELOCIDADE: 5   (TECLAS 1 A 9)      v"
menuL22 : string "v  MUSICA:                             v"
menuL23 : string "v  M: TROCA A MUSICA   ESPACO: COMECAR v"
menuL24 : string "v                                      v"
menuL25 : string "v  NOVA INSTRUCAO SNDN: A MUSICA TOCA  v"
menuL26 : string "v  SEM TRAVAR O PROCESSADOR.           v"
menuL27 : string "v                                      v"
menuL28 : string "v  SSC0511 - ICMC/USP                  v"
menuL29 : string "chhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhd"
; <<< TELA menuL

; >>> TELA fimL  (gerado por tools/gera_telas.py a partir de tools/telas/fim.txt - nao edite a mao)
fimL00 : string "ahhhhhhhhhhhhhhhhhhhhb"
fimL01 : string "v                    v"
fimL02 : string "v    FIM DE JOGO!    v"
fimL03 : string "v                    v"
fimL04 : string "v PONTOS      00000  v"
fimL05 : string "v ACERTOS   000/000  v"
fimL06 : string "v COMBO MAX     000  v"
fimL07 : string "v PRECISAO     000%  v"
fimL08 : string "v CONCEITO        -  v"
fimL09 : string "v ESPACO: DE NOVO    v"
fimL10 : string "chhhhhhhhhhhhhhhhhhhhd"
; <<< TELA fimL

; >>> MUSICA  (gerado por tools/gera_musica.py - nao edite a mao)
; Musicas, na ordem do menu: ODE A ALEGRIA, ARPEJO EM LA MENOR, MINHA MUSICA
numMusicas : var #1
static numMusicas + #0, #3
tabMusicas : var #3           ; endereco do mapa de cada musica
static tabMusicas + #0, #musica0
static tabMusicas + #1, #musica1
static tabMusicas + #2, #musica2
tabOndas : var #3             ; forma de onda de cada musica
static tabOndas + #0, #2
static tabOndas + #1, #1
static tabOndas + #2, #1
tabNomes : var #3             ; nome no menu (20 caracteres)
static tabNomes + #0, #nomeMusica0
static tabNomes + #1, #nomeMusica1
static tabNomes + #2, #nomeMusica2
tabPainel : var #3            ; 3 linhas do painel (9 caracteres + \0 cada = 10 palavras)
static tabPainel + #0, #painel0L0
static tabPainel + #1, #painel1L0
static tabPainel + #2, #painel2L0

; ---- musica 0: ODE A ALEGRIA (tools/musicas/ode_alegria.txt) ----
nomeMusica0 : string "ODE A ALEGRIA       "
painel0L0 : string "ODE A    "
painel0L1 : string "ALEGRIA  "
painel0L2 : string "BEETHOVEN"
musica0 : var #385        ; 1 palavra por frame + marcador de fim
static musica0 + #0, #6420		; pistas J    nota E4   6 frames
static musica0 + #6, #6420		; pistas J    nota E4   6 frames
static musica0 + #12, #6440		; pistas K    nota F4   6 frames
static musica0 + #18, #6472		; pistas K    nota G4   6 frames
static musica0 + #24, #6472		; pistas K    nota G4   6 frames
static musica0 + #30, #6440		; pistas K    nota F4   6 frames
static musica0 + #36, #6420		; pistas J    nota E4   6 frames
static musica0 + #42, #6386		; pistas F    nota D4   6 frames
static musica0 + #48, #6353		; pistas D    nota C4   6 frames
static musica0 + #54, #6353		; pistas D    nota C4   6 frames
static musica0 + #60, #6386		; pistas F    nota D4   6 frames
static musica0 + #66, #6420		; pistas J    nota E4   6 frames
static musica0 + #72, #9492		; pistas J    nota E4   9 frames
static musica0 + #81, #3314		; pistas F    nota D4   3 frames
static musica0 + #84, #12530		; pistas F    nota D4   12 frames
static musica0 + #96, #6420		; pistas J    nota E4   6 frames
static musica0 + #102, #6420		; pistas J    nota E4   6 frames
static musica0 + #108, #6440		; pistas K    nota F4   6 frames
static musica0 + #114, #6472		; pistas K    nota G4   6 frames
static musica0 + #120, #6472		; pistas K    nota G4   6 frames
static musica0 + #126, #6440		; pistas K    nota F4   6 frames
static musica0 + #132, #6420		; pistas J    nota E4   6 frames
static musica0 + #138, #6386		; pistas F    nota D4   6 frames
static musica0 + #144, #6353		; pistas D    nota C4   6 frames
static musica0 + #150, #6353		; pistas D    nota C4   6 frames
static musica0 + #156, #6386		; pistas F    nota D4   6 frames
static musica0 + #162, #6420		; pistas J    nota E4   6 frames
static musica0 + #168, #9458		; pistas F    nota D4   9 frames
static musica0 + #177, #3281		; pistas D    nota C4   3 frames
static musica0 + #180, #12497		; pistas D    nota C4   12 frames
static musica0 + #192, #6386		; pistas F    nota D4   6 frames
static musica0 + #198, #6386		; pistas F    nota D4   6 frames
static musica0 + #204, #6420		; pistas J    nota E4   6 frames
static musica0 + #210, #6353		; pistas D    nota C4   6 frames
static musica0 + #216, #6386		; pistas F    nota D4   6 frames
static musica0 + #222, #3348		; pistas J    nota E4   3 frames
static musica0 + #225, #3368		; pistas K    nota F4   3 frames
static musica0 + #228, #6420		; pistas J    nota E4   6 frames
static musica0 + #234, #6353		; pistas D    nota C4   6 frames
static musica0 + #240, #6386		; pistas F    nota D4   6 frames
static musica0 + #246, #3348		; pistas J    nota E4   3 frames
static musica0 + #249, #3368		; pistas K    nota F4   3 frames
static musica0 + #252, #6420		; pistas J    nota E4   6 frames
static musica0 + #258, #6386		; pistas F    nota D4   6 frames
static musica0 + #264, #6353		; pistas D    nota C4   6 frames
static musica0 + #270, #6386		; pistas F    nota D4   6 frames
static musica0 + #276, #12417		; pistas D    nota G3   12 frames
static musica0 + #288, #6420		; pistas J    nota E4   6 frames
static musica0 + #294, #6420		; pistas J    nota E4   6 frames
static musica0 + #300, #6440		; pistas K    nota F4   6 frames
static musica0 + #306, #6472		; pistas K    nota G4   6 frames
static musica0 + #312, #6472		; pistas K    nota G4   6 frames
static musica0 + #318, #6440		; pistas K    nota F4   6 frames
static musica0 + #324, #6420		; pistas J    nota E4   6 frames
static musica0 + #330, #6386		; pistas F    nota D4   6 frames
static musica0 + #336, #6353		; pistas D    nota C4   6 frames
static musica0 + #342, #6353		; pistas D    nota C4   6 frames
static musica0 + #348, #6386		; pistas F    nota D4   6 frames
static musica0 + #354, #6420		; pistas J    nota E4   6 frames
static musica0 + #360, #9458		; pistas F    nota D4   9 frames
static musica0 + #369, #3281		; pistas D    nota C4   3 frames
static musica0 + #372, #12505		; pistas DK   nota C4   12 frames
static musica0 + #384, #65535		; fim da musica

; ---- musica 1: ARPEJO EM LA MENOR (tools/musicas/arpejo_la_menor.txt) ----
nomeMusica1 : string "ARPEJO EM LA MENOR  "
painel1L0 : string "ARPEJO   "
painel1L1 : string "EM LA    "
painel1L2 : string "MENOR    "
musica1 : var #653        ; 1 palavra por frame + marcador de fim
static musica1 + #0, #4450		; pistas F    nota A4   4 frames
static musica1 + #4, #4500		; pistas J    nota C5   4 frames
static musica1 + #8, #4568		; pistas K    nota E5   4 frames
static musica1 + #12, #4450		; pistas F    nota A4   4 frames
static musica1 + #16, #4532		; pistas J    nota D5   4 frames
static musica1 + #20, #4500		; pistas J    nota C5   4 frames
static musica1 + #24, #4482		; pistas F    nota B4   4 frames
static musica1 + #28, #4500		; pistas J    nota C5   4 frames
static musica1 + #32, #4385		; pistas D    nota F4   4 frames
static musica1 + #36, #4450		; pistas F    nota A4   4 frames
static musica1 + #40, #4500		; pistas J    nota C5   4 frames
static musica1 + #44, #4385		; pistas D    nota F4   4 frames
static musica1 + #48, #4532		; pistas J    nota D5   4 frames
static musica1 + #52, #4500		; pistas J    nota C5   4 frames
static musica1 + #56, #4450		; pistas F    nota A4   4 frames
static musica1 + #60, #4500		; pistas J    nota C5   4 frames
static musica1 + #64, #4417		; pistas D    nota G4   4 frames
static musica1 + #68, #4482		; pistas F    nota B4   4 frames
static musica1 + #72, #4532		; pistas J    nota D5   4 frames
static musica1 + #76, #4417		; pistas D    nota G4   4 frames
static musica1 + #80, #4568		; pistas K    nota E5   4 frames
static musica1 + #84, #4532		; pistas J    nota D5   4 frames
static musica1 + #88, #4482		; pistas F    nota B4   4 frames
static musica1 + #92, #4532		; pistas J    nota D5   4 frames
static musica1 + #96, #4369		; pistas D    nota E4   4 frames
static musica1 + #100, #4417		; pistas D    nota G4   4 frames
static musica1 + #104, #4482		; pistas F    nota B4   4 frames
static musica1 + #108, #8664		; pistas K    nota E5   8 frames
static musica1 + #116, #4532		; pistas J    nota D5   4 frames
static musica1 + #120, #8578		; pistas F    nota B4   8 frames
static musica1 + #128, #4450		; pistas F    nota A4   4 frames
static musica1 + #132, #4500		; pistas J    nota C5   4 frames
static musica1 + #136, #4568		; pistas K    nota E5   4 frames
static musica1 + #140, #4450		; pistas F    nota A4   4 frames
static musica1 + #144, #4532		; pistas J    nota D5   4 frames
static musica1 + #148, #4500		; pistas J    nota C5   4 frames
static musica1 + #152, #4482		; pistas F    nota B4   4 frames
static musica1 + #156, #4500		; pistas J    nota C5   4 frames
static musica1 + #160, #4385		; pistas D    nota F4   4 frames
static musica1 + #164, #4450		; pistas F    nota A4   4 frames
static musica1 + #168, #4500		; pistas J    nota C5   4 frames
static musica1 + #172, #4385		; pistas D    nota F4   4 frames
static musica1 + #176, #4532		; pistas J    nota D5   4 frames
static musica1 + #180, #4500		; pistas J    nota C5   4 frames
static musica1 + #184, #4450		; pistas F    nota A4   4 frames
static musica1 + #188, #4500		; pistas J    nota C5   4 frames
static musica1 + #192, #4417		; pistas D    nota G4   4 frames
static musica1 + #196, #4482		; pistas F    nota B4   4 frames
static musica1 + #200, #4532		; pistas J    nota D5   4 frames
static musica1 + #204, #4417		; pistas D    nota G4   4 frames
static musica1 + #208, #4568		; pistas K    nota E5   4 frames
static musica1 + #212, #4532		; pistas J    nota D5   4 frames
static musica1 + #216, #4482		; pistas F    nota B4   4 frames
static musica1 + #220, #4532		; pistas J    nota D5   4 frames
static musica1 + #224, #4369		; pistas D    nota E4   4 frames
static musica1 + #228, #4417		; pistas D    nota G4   4 frames
static musica1 + #232, #4482		; pistas F    nota B4   4 frames
static musica1 + #236, #4532		; pistas J    nota D5   4 frames
static musica1 + #240, #12760		; pistas K    nota E5   12 frames
static musica1 + #256, #8664		; pistas K    nota E5   8 frames
static musica1 + #264, #4532		; pistas J    nota D5   4 frames
static musica1 + #268, #4500		; pistas J    nota C5   4 frames
static musica1 + #272, #8628		; pistas J    nota D5   8 frames
static musica1 + #280, #8664		; pistas K    nota E5   8 frames
static musica1 + #288, #12692		; pistas J    nota C5   12 frames
static musica1 + #300, #4450		; pistas F    nota A4   4 frames
static musica1 + #304, #8596		; pistas J    nota C5   8 frames
static musica1 + #312, #8628		; pistas J    nota D5   8 frames
static musica1 + #320, #8578		; pistas F    nota B4   8 frames
static musica1 + #328, #4417		; pistas D    nota G4   4 frames
static musica1 + #332, #4482		; pistas F    nota B4   4 frames
static musica1 + #336, #8628		; pistas J    nota D5   8 frames
static musica1 + #344, #8664		; pistas K    nota E5   8 frames
static musica1 + #352, #12760		; pistas K    nota E5   12 frames
static musica1 + #376, #8578		; pistas F    nota B4   8 frames
static musica1 + #384, #8664		; pistas K    nota E5   8 frames
static musica1 + #392, #4532		; pistas J    nota D5   4 frames
static musica1 + #396, #4500		; pistas J    nota C5   4 frames
static musica1 + #400, #8628		; pistas J    nota D5   8 frames
static musica1 + #408, #8664		; pistas K    nota E5   8 frames
static musica1 + #416, #8680		; pistas K    nota F5   8 frames
static musica1 + #424, #4568		; pistas K    nota E5   4 frames
static musica1 + #428, #4532		; pistas J    nota D5   4 frames
static musica1 + #432, #8596		; pistas J    nota C5   8 frames
static musica1 + #440, #8546		; pistas F    nota A4   8 frames
static musica1 + #448, #8578		; pistas F    nota B4   8 frames
static musica1 + #456, #4500		; pistas J    nota C5   4 frames
static musica1 + #460, #4532		; pistas J    nota D5   4 frames
static musica1 + #464, #8664		; pistas K    nota E5   8 frames
static musica1 + #472, #8712		; pistas K    nota G5   8 frames
static musica1 + #480, #12844		; pistas JK   nota A5   12 frames
static musica1 + #512, #4450		; pistas F    nota A4   4 frames
static musica1 + #516, #4500		; pistas J    nota C5   4 frames
static musica1 + #520, #4568		; pistas K    nota E5   4 frames
static musica1 + #524, #4450		; pistas F    nota A4   4 frames
static musica1 + #528, #4532		; pistas J    nota D5   4 frames
static musica1 + #532, #4500		; pistas J    nota C5   4 frames
static musica1 + #536, #4482		; pistas F    nota B4   4 frames
static musica1 + #540, #4500		; pistas J    nota C5   4 frames
static musica1 + #544, #4385		; pistas D    nota F4   4 frames
static musica1 + #548, #4450		; pistas F    nota A4   4 frames
static musica1 + #552, #4500		; pistas J    nota C5   4 frames
static musica1 + #556, #4385		; pistas D    nota F4   4 frames
static musica1 + #560, #4532		; pistas J    nota D5   4 frames
static musica1 + #564, #4500		; pistas J    nota C5   4 frames
static musica1 + #568, #4450		; pistas F    nota A4   4 frames
static musica1 + #572, #4500		; pistas J    nota C5   4 frames
static musica1 + #576, #4417		; pistas D    nota G4   4 frames
static musica1 + #580, #4482		; pistas F    nota B4   4 frames
static musica1 + #584, #4532		; pistas J    nota D5   4 frames
static musica1 + #588, #4417		; pistas D    nota G4   4 frames
static musica1 + #592, #4568		; pistas K    nota E5   4 frames
static musica1 + #596, #4532		; pistas J    nota D5   4 frames
static musica1 + #600, #4482		; pistas F    nota B4   4 frames
static musica1 + #604, #4532		; pistas J    nota D5   4 frames
static musica1 + #608, #4369		; pistas D    nota E4   4 frames
static musica1 + #612, #4417		; pistas D    nota G4   4 frames
static musica1 + #616, #4482		; pistas F    nota B4   4 frames
static musica1 + #620, #8664		; pistas K    nota E5   8 frames
static musica1 + #628, #4532		; pistas J    nota D5   4 frames
static musica1 + #632, #8578		; pistas F    nota B4   8 frames
static musica1 + #640, #12650		; pistas FK   nota A4   12 frames
static musica1 + #652, #65535		; fim da musica

; ---- musica 2: MINHA MUSICA (tools/musicas/minha_musica.txt) ----
nomeMusica2 : string "MINHA MUSICA        "
painel2L0 : string "MINHA    "
painel2L1 : string "MUSICA   "
painel2L2 : string "         "
musica2 : var #125        ; 1 palavra por frame + marcador de fim
static musica2 + #0, #4257		; pistas D    nota A3   4 frames
static musica2 + #4, #4306		; pistas F    nota C4   4 frames
static musica2 + #8, #4372		; pistas J    nota E4   4 frames
static musica2 + #12, #4424		; pistas K    nota G4   4 frames
static musica2 + #16, #4372		; pistas J    nota E4   4 frames
static musica2 + #20, #4306		; pistas F    nota C4   4 frames
static musica2 + #24, #8353		; pistas D    nota A3   8 frames
static musica2 + #32, #4388		; pistas J    nota F4   4 frames
static musica2 + #36, #4372		; pistas J    nota E4   4 frames
static musica2 + #40, #4338		; pistas F    nota D4   4 frames
static musica2 + #44, #4306		; pistas F    nota C4   4 frames
static musica2 + #48, #8434		; pistas F    nota D4   8 frames
static musica2 + #64, #4257		; pistas D    nota A3   4 frames
static musica2 + #68, #4306		; pistas F    nota C4   4 frames
static musica2 + #72, #4372		; pistas J    nota E4   4 frames
static musica2 + #76, #4424		; pistas K    nota G4   4 frames
static musica2 + #80, #4372		; pistas J    nota E4   4 frames
static musica2 + #84, #4306		; pistas F    nota C4   4 frames
static musica2 + #88, #8353		; pistas D    nota A3   8 frames
static musica2 + #96, #4338		; pistas F    nota D4   4 frames
static musica2 + #100, #4372		; pistas J    nota E4   4 frames
static musica2 + #104, #4388		; pistas J    nota F4   4 frames
static musica2 + #108, #4372		; pistas J    nota E4   4 frames
static musica2 + #112, #12453		; pistas DJ   nota A3   12 frames
static musica2 + #124, #65535		; fim da musica

; freqs[i] = frequencia em Hz da nota de indice i (indice 1 = C3, sobe de semitom em semitom)
freqs : var #64
static freqs + #1, #131		; C3
static freqs + #2, #139		; C#3
static freqs + #3, #147		; D3
static freqs + #4, #156		; D#3
static freqs + #5, #165		; E3
static freqs + #6, #175		; F3
static freqs + #7, #185		; F#3
static freqs + #8, #196		; G3
static freqs + #9, #208		; G#3
static freqs + #10, #220		; A3
static freqs + #11, #233		; A#3
static freqs + #12, #247		; B3
static freqs + #13, #262		; C4
static freqs + #14, #277		; C#4
static freqs + #15, #294		; D4
static freqs + #16, #311		; D#4
static freqs + #17, #330		; E4
static freqs + #18, #349		; F4
static freqs + #19, #370		; F#4
static freqs + #20, #392		; G4
static freqs + #21, #415		; G#4
static freqs + #22, #440		; A4
static freqs + #23, #466		; A#4
static freqs + #24, #494		; B4
static freqs + #25, #523		; C5
static freqs + #26, #554		; C#5
static freqs + #27, #587		; D5
static freqs + #28, #622		; D#5
static freqs + #29, #659		; E5
static freqs + #30, #698		; F5
static freqs + #31, #740		; F#5
static freqs + #32, #784		; G5
static freqs + #33, #831		; G#5
static freqs + #34, #880		; A5
static freqs + #35, #932		; A#5
static freqs + #36, #988		; B5
static freqs + #37, #1047		; C6
static freqs + #38, #1109		; C#6
static freqs + #39, #1175		; D6
static freqs + #40, #1245		; D#6
static freqs + #41, #1319		; E6
static freqs + #42, #1397		; F6
static freqs + #43, #1480		; F#6
static freqs + #44, #1568		; G6
static freqs + #45, #1661		; G#6
static freqs + #46, #1760		; A6
static freqs + #47, #1865		; A#6
static freqs + #48, #1976		; B6
static freqs + #49, #2093		; C7
static freqs + #50, #2217		; C#7
static freqs + #51, #2349		; D7
static freqs + #52, #2489		; D#7
static freqs + #53, #2637		; E7
static freqs + #54, #2794		; F7
static freqs + #55, #2960		; F#7
static freqs + #56, #3136		; G7
static freqs + #57, #3322		; G#7
static freqs + #58, #3520		; A7
static freqs + #59, #3729		; A#7
static freqs + #60, #3951		; B7
static freqs + #61, #4186		; C8
static freqs + #62, #4435		; C#8
static freqs + #63, #4699		; D8
; <<< MUSICA

;==============================================================================
; 4. PROGRAMA PRINCIPAL
;==============================================================================

main:
	call Menu                   ; tela inicial: escolhe a velocidade e espera ESPACO
	call IniciaJogo             ; zera o estado e desenha o cenario

; Cada volta deste laco e' um frame do jogo.
LoopJogo:
	call AtualizaEfeitos        ; apaga mensagens e faiscas antigas (ANTES de desenhar
	                            ; as notas: senao o alvo restaurado cobriria uma nota)
	call MoveNotas              ; desce as notas uma linha; nota que passou = erro
	call SpawnNotas             ; cria as notas deste frame no topo das pistas
	call TocaMelodia            ; toca a nota que esta chegando no alvo (SNDN)
	call AtualizaHUD            ; redesenha o placar, se mudou
	call Delay                  ; espera o tempo do frame lendo o teclado

	load r0, frame
	inc r0
	store frame, r0

	; Depois que a ultima nota chegou ao alvo, espera alguns frames e encerra.
	load r0, musicaAcabou
	loadn r1, #0
	cmp r0, r1
	jeq LoopJogo
	load r0, fimContador
	dec r0
	store fimContador, r0
	jnz LoopJogo                ; (STORE nao altera o flag de zero do DEC)

	call TelaFim                ; mostra o resultado e espera ESPACO
	jmp main

;==============================================================================
; 5. SUBROTINAS
;==============================================================================

;------------------------------------------------------------------------------
; Menu: desenha a tela inicial e espera o jogador.
;   Teclas 1..9 mudam a velocidade; M troca a musica; ESPACO comeca o jogo.
;------------------------------------------------------------------------------
Menu:
	push r0
	push r1
	push r3

	loadn r1, #menuL00
	loadn r3, #0                ; texto em branco
	call ImprimeCenario
	loadn r0, #132              ; titulo colorido (linha 3, coluna 12)
	call DesenhaTitulo
	call MostraVelocidadeMenu
	call MostraMusicaMenu

	loadn r3, #255
Menu_espera:
	inchar r0
	cmp r0, r3
	jeq Menu_espera             ; nenhuma tecla
	loadn r1, #' '
	cmp r0, r1
	jeq Menu_fim                ; ESPACO: comeca
	loadn r1, #'m'
	cmp r0, r1
	jeq Menu_trocaMusica
	loadn r1, #'M'
	cmp r0, r1
	jeq Menu_trocaMusica
	loadn r1, #'1'
	cmp r0, r1
	jle Menu_espera             ; menor que '1': ignora
	loadn r1, #'9'
	cmp r0, r1
	jgr Menu_espera             ; maior que '9': ignora
	loadn r1, #'0'
	sub r0, r0, r1              ; converte o caractere no numero 1..9
	store velocidade, r0
	call MostraVelocidadeMenu
	jmp Menu_espera

Menu_trocaMusica:                   ; proxima musica da lista, voltando para a primeira
	load r0, musicaSel
	inc r0
	load r1, numMusicas
	mod r0, r0, r1
	store musicaSel, r0
	call MostraMusicaMenu
	jmp Menu_espera

Menu_fim:
	pop r3
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; MostraVelocidadeMenu: escreve o nivel de velocidade na linha 21 do menu.
;------------------------------------------------------------------------------
MostraVelocidadeMenu:
	push r0
	push r1
	push r2
	push r3
	loadn r0, #855              ; linha 21, coluna 15
	load r1, velocidade
	loadn r2, #1                ; 1 digito
	loadn r3, #2816             ; amarelo
	call ImprimeNumero
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; MostraMusicaMenu: escreve o nome da musica escolhida na linha 22 do menu.
;   Os nomes tem sempre 20 caracteres (completados com espacos pelo gerador),
;   entao o nome novo cobre o anterior por inteiro.
;------------------------------------------------------------------------------
MostraMusicaMenu:
	push r0
	push r1
	push r3
	load r0, musicaSel
	loadn r1, #tabNomes
	add r1, r1, r0
	loadi r1, r1                ; r1 = endereco do nome da musica
	loadn r0, #891              ; linha 22, coluna 11
	loadn r3, #2816             ; amarelo
	call ImprimeStrT
	pop r3
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; DesenhaTitulo: escreve "GUITAR HERO ICMC" em amarelo.
;   r0 = posicao na tela
;------------------------------------------------------------------------------
DesenhaTitulo:
	push r1
	push r3
	loadn r1, #tituloJogo
	loadn r3, #2816             ; amarelo
	call ImprimeStrT
	pop r3
	pop r1
	rts

;------------------------------------------------------------------------------
; IniciaJogo: zera todo o estado da partida e desenha o cenario.
;------------------------------------------------------------------------------
IniciaJogo:
	push r0
	push r1
	push r2
	push r3

	loadn r0, #0
	store pontos, r0
	store combo, r0
	store comboMax, r0
	store acertos, r0
	store erros, r0
	store totalNotas, r0
	store frame, r0
	store spawnAcabou, r0
	store musicaAcabou, r0
	store fimContador, r0
	store msgTimer, r0
	store notasNoMeio, r0
	loadn r0, #1
	store mult, r0

	; libera os 16 slots de notas
	loadn r0, #notaY
	loadn r1, #16
	loadn r2, #0
IniciaJogo_zeraNotas:
	storei r0, r2
	inc r0
	dec r1
	jnz IniciaJogo_zeraNotas

	; apaga as faiscas e os alvos preenchidos das 4 pistas
	; (faiscaTimer e pressTimer sao vizinhos na memoria: 8 palavras seguidas)
	loadn r0, #faiscaTimer
	loadn r1, #8
IniciaJogo_zeraFaiscas:
	storei r0, r2
	inc r0
	dec r1
	jnz IniciaJogo_zeraFaiscas

	; cenario do jogo
	loadn r1, #telaL00
	loadn r3, #0                ; texto em branco
	call ImprimeCenario
	loadn r0, #52               ; titulo colorido (linha 1, coluna 12)
	call DesenhaTitulo

	; nivel de velocidade no painel esquerdo (linha 19, coluna 9)
	loadn r0, #769
	load r1, velocidade
	loadn r2, #1
	loadn r3, #2816
	call ImprimeNumero

	; musica escolhida: endereco do mapa e forma de onda
	load r0, musicaSel
	loadn r1, #tabMusicas
	add r1, r1, r0
	loadi r1, r1
	store musicaAtual, r1
	loadn r1, #tabOndas
	add r1, r1, r0
	loadi r1, r1
	store ondaMelodia, r1

	; nome da musica no painel esquerdo: 3 strings de 9 caracteres (+ \0),
	; nas linhas 5, 6 e 7, colunas 2 a 10 (alinhado com o rotulo MUSICA)
	loadn r1, #tabPainel
	add r1, r1, r0
	loadi r1, r1                ; r1 = endereco da 1a linha do nome
	loadn r0, #202              ; linha 5, coluna 2
	loadn r2, #3                ; 3 linhas
	loadn r3, #0                ; branco
IniciaJogo_nome:
	call ImprimeStrT
	push r2
	loadn r2, #40
	add r0, r0, r2              ; proxima linha da tela
	loadn r2, #10
	add r1, r1, r2              ; proxima string (9 caracteres + \0)
	pop r2
	dec r2
	jnz IniciaJogo_nome

	loadn r0, #1
	store hudSujo, r0
	call AtualizaHUD

	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; MoveNotas: desce todas as notas ativas uma linha.
;   A nota que passa da linha 26 (ultima chance de acerto) e' perdida.
;------------------------------------------------------------------------------
MoveNotas:
	push r0
	push r1
	push r2
	push r3
	push r4

	loadn r0, #0                ; r0 = slot
	loadn r4, #16
MoveNotas_laco:
	loadn r1, #notaY
	add r1, r1, r0              ; r1 = &notaY[slot]
	loadi r2, r1                ; r2 = linha da nota
	loadn r3, #0
	cmp r2, r3
	jeq MoveNotas_prox          ; slot livre

	call ApagaNota              ; apaga na linha atual (antes de mudar Y)
	inc r2
	storei r1, r2               ; notaY[slot]++
	loadn r3, #27               ; linha 27 = ultima chance ("QUASE")
	cmp r2, r3
	jgr MoveNotas_perdeu        ; passou do alvo sem ser acertada
	call DesenhaNota
	jmp MoveNotas_prox

MoveNotas_perdeu:
	loadn r3, #0
	storei r1, r3               ; libera o slot
	call Errou

MoveNotas_prox:
	inc r0
	cmp r0, r4
	jne MoveNotas_laco

	loadn r3, #0
	store notasNoMeio, r3       ; todas as notas estao alinhadas de novo

	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; SpawnNotas: le o mapa da musica no frame atual e cria as notas indicadas
; pela mascara de pistas (bits 3-0) no topo das pistas.
;------------------------------------------------------------------------------
SpawnNotas:
	push r0
	push r1
	push r2
	push r3
	push r4

	load r0, spawnAcabou
	loadn r1, #0
	cmp r0, r1
	jne SpawnNotas_fim          ; a musica ja terminou de soltar notas

	load r1, frame
	load r2, musicaAtual        ; endereco do mapa da musica escolhida
	add r2, r2, r1
	loadi r3, r2                ; r3 = palavra do mapa para este frame
	loadn r4, #65535
	cmp r3, r4
	jne SpawnNotas_mascara
	loadn r0, #1                ; chegou no marcador de fim
	store spawnAcabou, r0
	jmp SpawnNotas_fim

SpawnNotas_mascara:
	loadn r4, #16
	mod r3, r3, r4              ; r3 = mascara das pistas (bits 3-0)
	loadn r0, #0                ; r0 = pista
SpawnNotas_laco:
	loadn r2, #bitPista
	add r2, r2, r0
	loadi r2, r2                ; bit desta pista
	and r1, r3, r2
	loadn r4, #0
	cmp r1, r4
	jeq SpawnNotas_prox         ; nao ha nota nesta pista
	call CriaNota
SpawnNotas_prox:
	inc r0
	loadn r4, #4
	cmp r0, r4
	jne SpawnNotas_laco

SpawnNotas_fim:
	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; CriaNota: coloca uma nota nova no topo de uma pista.
;   r0 = pista (0..3)
;------------------------------------------------------------------------------
CriaNota:
	push r0
	push r1
	push r2
	push r3
	push r4
	push r5

	loadn r1, #0                ; r1 = slot procurado
	loadn r4, #16
	loadn r5, #0
CriaNota_procura:
	loadn r2, #notaY
	add r2, r2, r1
	loadi r3, r2
	cmp r3, r5
	jeq CriaNota_achou          ; slot livre
	inc r1
	cmp r1, r4
	jne CriaNota_procura
	jmp CriaNota_fim            ; sem slot livre (nao ocorre: no maximo ~8 notas na tela)

CriaNota_achou:
	loadn r3, #3                ; linha onde as notas nascem
	storei r2, r3               ; notaY[slot] = 3
	loadn r2, #notaPista
	add r2, r2, r1
	storei r2, r0               ; notaPista[slot] = pista
	load r3, totalNotas
	inc r3
	store totalNotas, r3
	mov r0, r1
	call DesenhaNota

CriaNota_fim:
	pop r5
	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; PosicaoNota: calcula onde desenhar uma nota.
;   r0 = slot
;   Retorna: r1 = posicao na tela da parte esquerda da nota, r2 = cor da pista
;------------------------------------------------------------------------------
PosicaoNota:
	push r3
	push r4

	loadn r3, #notaY
	add r3, r3, r0
	loadi r1, r3                ; r1 = linha
	loadn r4, #40
	mul r1, r1, r4              ; r1 = linha * 40

	loadn r3, #notaPista
	add r3, r3, r0
	loadi r4, r3                ; r4 = pista
	loadn r3, #pistaX
	add r3, r3, r4
	loadi r2, r3
	add r1, r1, r2              ; r1 = linha * 40 + coluna da pista

	loadn r3, #pistaCor
	add r3, r3, r4
	loadi r2, r3                ; r2 = cor da pista

	pop r4
	pop r3
	rts

;------------------------------------------------------------------------------
; DesenhaNota: desenha a nota de um slot (3 caracteres na cor da pista).
;   r0 = slot
;------------------------------------------------------------------------------
DesenhaNota:
	push r1
	push r2
	push r3

	call PosicaoNota            ; r1 = posicao, r2 = cor
	loadn r3, #1                ; sprite NOTA_ESQ
	add r3, r3, r2
	outchar r3, r1
	inc r1
	inc r3                      ; sprite NOTA_MEIO (codigo 2), mesma cor
	outchar r3, r1
	inc r1
	inc r3                      ; sprite NOTA_DIR (codigo 3)
	outchar r3, r1

	pop r3
	pop r2
	pop r1
	rts

;------------------------------------------------------------------------------
; ApagaNota: apaga a nota de um slot redesenhando o cenario por baixo dela
; (assim a divisoria, o alvo e as letras das teclas reaparecem).
; Se as notas estao em meia linha (notasNoMeio = 1), apaga as duas linhas
; que a nota ocupa.
;   r0 = slot
;------------------------------------------------------------------------------
ApagaNota:
	push r0
	push r1
	push r2
	push r3

	call PosicaoNota            ; r1 = posicao
	mov r0, r1
	call RestauraCenario
	inc r0
	call RestauraCenario
	inc r0
	call RestauraCenario

	load r2, notasNoMeio
	loadn r3, #0
	cmp r2, r3
	jeq ApagaNota_fim           ; nota alinhada: so' uma linha
	loadn r3, #1080             ; linha 27 * 40: nessa linha a nota nao desce meia
	cmp r1, r3                  ; linha (a linha 28 e' das mensagens)
	jeg ApagaNota_fim
	loadn r3, #40
	add r0, r1, r3              ; mesma coluna, linha de baixo
	call RestauraCenario
	inc r0
	call RestauraCenario
	inc r0
	call RestauraCenario

ApagaNota_fim:
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; DesenhaNotaMeia: desenha a nota de um slot meia linha (4 pixels) abaixo da
; posicao dela: a parte de cima da nota no fundo da linha Y e a parte de baixo
; no topo da linha Y+1 (sprites 21..26). So' muda o desenho, nao a linha logica.
;   r0 = slot
;------------------------------------------------------------------------------
DesenhaNotaMeia:
	push r1
	push r2
	push r3
	push r4

	call PosicaoNota            ; r1 = posicao, r2 = cor
	loadn r3, #21               ; NOTA_ESQ_MEIA_CIMA
	add r3, r3, r2
	outchar r3, r1
	inc r1
	inc r3                      ; NOTA_MEIO_MEIA_CIMA (22)
	outchar r3, r1
	inc r1
	inc r3                      ; NOTA_DIR_MEIA_CIMA (23)
	outchar r3, r1

	loadn r4, #38
	add r1, r1, r4              ; linha de baixo, primeira coluna (+40 -2)
	loadn r3, #24               ; NOTA_ESQ_MEIA_BAIXO
	add r3, r3, r2
	outchar r3, r1
	inc r1
	inc r3                      ; NOTA_MEIO_MEIA_BAIXO (25)
	outchar r3, r1
	inc r1
	inc r3                      ; NOTA_DIR_MEIA_BAIXO (26)
	outchar r3, r1

	pop r4
	pop r3
	pop r2
	pop r1
	rts

;------------------------------------------------------------------------------
; MeioPasso: na metade de cada frame, redesenha todas as notas meia linha
; abaixo. Assim cada nota anda 4 pixels por vez em vez de 8 (uma linha inteira
; = 8 pixels do charmap), com o dobro de quadros: a animacao fica mais suave.
; A linha logica (notaY) so' muda no MoveNotas; a janela de acerto nao muda.
;------------------------------------------------------------------------------
MeioPasso:
	push r0
	push r1
	push r2
	push r3
	push r4

	loadn r0, #0                ; r0 = slot
	loadn r4, #16
MeioPasso_laco:
	loadn r1, #notaY
	add r1, r1, r0
	loadi r2, r1                ; r2 = linha da nota
	loadn r3, #0
	cmp r2, r3
	jeq MeioPasso_prox          ; slot livre
	loadn r3, #27
	cmp r2, r3
	jeg MeioPasso_prox          ; linha 27 fica inteira (a 28 e' das mensagens)
	call ApagaNota              ; notasNoMeio ainda e' 0: apaga so' a linha Y
	call DesenhaNotaMeia
MeioPasso_prox:
	inc r0
	cmp r0, r4
	jne MeioPasso_laco

	loadn r0, #1
	store notasNoMeio, r0

	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; TocaMelodia: toca a nota da musica que esta chegando no alvo neste frame.
;   Uma nota criada no frame f nasce na linha 3 e chega na linha 25 (alvo)
;   22 frames depois. Por isso a melodia le o mapa da musica com 22 frames de
;   atraso: o som sai exatamente quando a nota passa pelo alvo.
;
;   Usa a NOVA INSTRUCAO SNDN: o som comeca e a CPU continua na hora. Com a
;   instrucao SOUND original o jogo inteiro pararia durante cada nota.
;------------------------------------------------------------------------------
TocaMelodia:
	push r0
	push r1
	push r2
	push r3

	load r0, musicaAcabou
	loadn r1, #0
	cmp r0, r1
	jne TocaMelodia_fim

	load r0, frame
	loadn r1, #22               ; atraso entre nascer (linha 3) e chegar ao alvo (linha 25)
	cmp r0, r1
	jle TocaMelodia_fim         ; frame < 22: nenhuma nota chegou ainda
	sub r0, r0, r1              ; r0 = indice no mapa = frame - 22
	load r1, musicaAtual
	add r1, r1, r0
	loadi r2, r1                ; r2 = palavra do mapa

	loadn r3, #65535
	cmp r2, r3
	jne TocaMelodia_nota
	loadn r0, #1                ; a ultima nota ja passou pelo alvo
	store musicaAcabou, r0
	loadn r0, #4                ; mais 4 frames para as ultimas notas sairem da tela
	store fimContador, r0
	jmp TocaMelodia_fim

TocaMelodia_nota:
	loadn r3, #16
	div r2, r2, r3              ; descarta a mascara de pistas (bits 3-0)
	loadn r3, #64
	mod r0, r2, r3              ; r0 = indice da nota (bits 9-4)
	div r2, r2, r3              ; r2 = duracao em frames (bits 13-10)
	loadn r3, #0
	cmp r0, r3
	jeq TocaMelodia_fim         ; indice 0: nenhuma nota neste frame

	loadn r1, #freqs
	add r1, r1, r0
	loadi r0, r1                ; r0 = frequencia (Hz)

	load r3, velocidade
	loadn r1, #tabMsFrame
	add r1, r1, r3
	loadi r1, r1                ; r1 = duracao de um frame (ms)
	mul r1, r1, r2              ; r1 = duracao da nota (ms)

	load r2, ondaMelodia        ; r2 = forma de onda
	sndn r0, r1, r2             ; NOVA INSTRUCAO: inicia a nota e segue em frente

TocaMelodia_fim:
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; Delay: espera o tempo de um frame, em duas metades. Entre elas, o MeioPasso
; desce as notas meia linha na tela (animacao mais suave).
;------------------------------------------------------------------------------
Delay:
	push r1
	push r2
	push r3

	load r2, velocidade
	loadn r1, #tabMsFrame
	add r1, r1, r2
	loadi r2, r1                ; r2 = ms do frame
	loadn r3, #2
	div r1, r2, r3              ; r1 = primeira metade
	sub r2, r2, r1              ; r2 = segunda metade (o resto)

	push r2
	mov r2, r1
	call EsperaMs               ; 1a metade do frame
	call MeioPasso              ; notas descem meia linha (so' o desenho)
	pop r2
	call EsperaMs               ; 2a metade do frame

	pop r3
	pop r2
	pop r1
	rts

;------------------------------------------------------------------------------
; EsperaMs: espera r2 milissegundos lendo o teclado. A cada volta do laco
; interno le o teclado, e a tecla e' tratada na hora (assim nenhuma tecla se
; perde). O laco interno tem 5 instrucoes; 1000 voltas = 5000 instrucoes =
; 1 ms com o clock de 5 MHz.
;   r2 = milissegundos (maior que 0)
;------------------------------------------------------------------------------
EsperaMs:
	push r0
	push r1
	push r2
	push r3

	loadn r3, #255              ; valor do INCHAR sem tecla
EsperaMs_externo:
	loadn r1, #1000
EsperaMs_interno:
	inchar r0
	cmp r0, r3
	jeq EsperaMs_semTecla
	call ProcessaTecla
EsperaMs_semTecla:
	dec r1
	jnz EsperaMs_interno
	dec r2
	jnz EsperaMs_externo

	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; ProcessaTecla: converte a tecla na pista correspondente e tenta acertar.
;   r0 = codigo da tecla (aceita minuscula e maiuscula). Outras teclas: ignora.
;------------------------------------------------------------------------------
ProcessaTecla:
	push r0
	push r1

	loadn r1, #'d'
	cmp r0, r1
	jeq ProcessaTecla_pista0
	loadn r1, #'D'
	cmp r0, r1
	jeq ProcessaTecla_pista0
	loadn r1, #'f'
	cmp r0, r1
	jeq ProcessaTecla_pista1
	loadn r1, #'F'
	cmp r0, r1
	jeq ProcessaTecla_pista1
	loadn r1, #'j'
	cmp r0, r1
	jeq ProcessaTecla_pista2
	loadn r1, #'J'
	cmp r0, r1
	jeq ProcessaTecla_pista2
	loadn r1, #'k'
	cmp r0, r1
	jeq ProcessaTecla_pista3
	loadn r1, #'K'
	cmp r0, r1
	jeq ProcessaTecla_pista3
	jmp ProcessaTecla_fim       ; nao e' tecla do jogo

ProcessaTecla_pista0:
	loadn r0, #0
	jmp ProcessaTecla_tenta
ProcessaTecla_pista1:
	loadn r0, #1
	jmp ProcessaTecla_tenta
ProcessaTecla_pista2:
	loadn r0, #2
	jmp ProcessaTecla_tenta
ProcessaTecla_pista3:
	loadn r0, #3
ProcessaTecla_tenta:
	call TentaAcerto

ProcessaTecla_fim:
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; TentaAcerto: procura uma nota da pista dentro da janela de acerto
; (linhas 23 a 27) e acerta a MAIS ANTIGA (a mais baixa, que sairia da janela
; primeiro), como nos jogos de ritmo: se duas notas da mesma pista estao na
; janela, a tecla vale para a que esta' mais perto de sair.
; Sem nota na janela: o alvo da pista fica preenchido e o combo zera.
;   r0 = pista
;------------------------------------------------------------------------------
TentaAcerto:
	push r1
	push r2
	push r3
	push r4
	push r5
	push r6
	push r7

	loadn r7, #255
	store acertoSlot, r7        ; nenhuma nota encontrada ainda
	loadn r7, #0
	store acertoY, r7           ; linha da mais baixa encontrada ate agora

	loadn r1, #0                ; r1 = slot
	loadn r6, #16
TentaAcerto_laco:
	loadn r2, #notaY
	add r2, r2, r1
	loadi r3, r2                ; r3 = linha da nota
	loadn r4, #23
	cmp r3, r4
	jle TentaAcerto_prox        ; linha < 23 (inclui slot livre, linha 0)
	loadn r2, #notaPista
	add r2, r2, r1
	loadi r5, r2
	cmp r5, r0
	jne TentaAcerto_prox        ; nota de outra pista

	load r7, acertoY
	cmp r3, r7
	jel TentaAcerto_prox        ; nao e' mais baixa que a escolhida ate agora
	store acertoY, r3
	store acertoSlot, r1
TentaAcerto_prox:
	inc r1
	cmp r1, r6
	jne TentaAcerto_laco

	load r1, acertoSlot
	loadn r7, #255
	cmp r1, r7
	jeq TentaAcerto_semNota
	load r2, acertoY
	call Acertou                ; r1 = slot, r2 = linha
	jmp TentaAcerto_fim

TentaAcerto_semNota:
	call AcendePressionado      ; alvo da pista preenchido na cor dela
	loadn r1, #msgSemNota
	call QuebraCombo

TentaAcerto_fim:
	pop r7
	pop r6
	pop r5
	pop r4
	pop r3
	pop r2
	pop r1
	rts

;------------------------------------------------------------------------------
; Acertou: conta um acerto.
;   r1 = slot da nota, r2 = linha da nota
;   Linhas 24 a 26 (alvo com folga de 1 linha) = PERFEITO; 23 ou 27 = QUASE.
;------------------------------------------------------------------------------
Acertou:
	push r0
	push r1
	push r2
	push r3
	push r4

	mov r0, r1
	call ApagaNota
	loadn r3, #notaY
	add r3, r3, r1
	loadn r4, #0
	storei r3, r4               ; libera o slot
	loadn r3, #notaPista
	add r3, r3, r1
	loadi r0, r3                ; r0 = pista da nota
	call AcendeFaisca

	loadn r4, #24
	cmp r2, r4
	jle Acertou_quase           ; linha 23
	loadn r4, #26
	cmp r2, r4
	jgr Acertou_quase           ; linha 27
	loadn r3, #10               ; linhas 24..26: 10 pontos
	loadn r1, #msgPerfeito
	loadn r2, #2560             ; verde-limao
	jmp Acertou_pontua
Acertou_quase:
	loadn r3, #5                ; 2 linhas fora: 5 pontos
	loadn r1, #msgQuase
	loadn r2, #512              ; verde
Acertou_pontua:
	call MostraMensagem         ; r1 = mensagem, r2 = cor
	load r4, mult
	mul r3, r3, r4
	load r4, pontos
	add r4, r4, r3
	store pontos, r4

	; combo e recorde de combo
	load r4, combo
	inc r4
	store combo, r4
	load r3, comboMax
	cmp r4, r3
	jel Acertou_semRecorde      ; combo <= comboMax
	store comboMax, r4
Acertou_semRecorde:

	; multiplicador = 1 + combo / 10, no maximo 4
	loadn r3, #10
	div r4, r4, r3
	inc r4
	loadn r3, #4
	cmp r4, r3
	jel Acertou_multOk
	mov r4, r3
Acertou_multOk:
	store mult, r4

	load r4, acertos
	inc r4
	store acertos, r4
	loadn r4, #1
	store hudSujo, r4

	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; Errou: a nota passou do alvo sem ser acertada.
;------------------------------------------------------------------------------
Errou:
	push r1
	loadn r1, #msgErrou
	call QuebraCombo
	pop r1
	rts

;------------------------------------------------------------------------------
; QuebraCombo: zera o combo e o multiplicador, conta um erro e mostra a
; mensagem em vermelho.
;   r1 = mensagem
;------------------------------------------------------------------------------
QuebraCombo:
	push r0
	push r2

	loadn r0, #0
	store combo, r0
	loadn r0, #1
	store mult, r0
	load r0, erros
	inc r0
	store erros, r0
	loadn r0, #1
	store hudSujo, r0
	loadn r2, #2304             ; vermelho
	call MostraMensagem

	pop r2
	pop r0
	rts

;------------------------------------------------------------------------------
; MostraMensagem: escreve uma mensagem de 15 caracteres na linha 28, sobre as
; pistas (abaixo da linha 27, a ultima por onde as notas passam), e marca
; para ser apagada depois de 12 frames.
;   r1 = mensagem, r2 = cor
;------------------------------------------------------------------------------
MostraMensagem:
	push r0
	push r3

	call ApagaMensagem
	loadn r0, #1132             ; linha 28, coluna 12
	mov r3, r2
	call ImprimeStrT
	loadn r3, #12
	store msgTimer, r3

	pop r3
	pop r0
	rts

;------------------------------------------------------------------------------
; ApagaMensagem: restaura o cenario na area da mensagem (linha 28, colunas 12..26).
;------------------------------------------------------------------------------
ApagaMensagem:
	push r0
	push r1
	loadn r0, #1132
	loadn r1, #1147
ApagaMensagem_laco:
	call RestauraCenario
	inc r0
	cmp r0, r1
	jne ApagaMensagem_laco
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; AcendeFaisca: desenha uma faisca no centro do alvo de uma pista (por 4 frames).
; So' acontece em acertos (PERFEITO ou QUASE). Se o alvo estava preenchido por
; uma tecla errada, ele volta ao normal antes.
;   r0 = pista
;------------------------------------------------------------------------------
AcendeFaisca:
	push r1
	push r2
	push r3

	call RestauraAlvo           ; tira um eventual preenchimento
	loadn r1, #pressTimer
	add r1, r1, r0
	loadn r2, #0
	storei r1, r2

	loadn r1, #pistaX
	add r1, r1, r0
	loadi r1, r1
	loadn r2, #1001             ; linha 25 (alvo) * 40 + 1 (centro da nota)
	add r1, r1, r2              ; r1 = posicao do centro do alvo
	loadn r2, #pistaCor
	add r2, r2, r0
	loadi r2, r2
	loadn r3, #17               ; sprite FAISCA
	add r3, r3, r2
	outchar r3, r1

	loadn r1, #faiscaTimer
	add r1, r1, r0
	loadn r2, #4
	storei r1, r2

	pop r3
	pop r2
	pop r1
	rts

;------------------------------------------------------------------------------
; AcendePressionado: preenche o alvo de uma pista com a cor dela (por 3 frames),
; para mostrar que a tecla foi apertada sem nota na janela de acerto.
;   r0 = pista
;------------------------------------------------------------------------------
AcendePressionado:
	push r1
	push r2
	push r3

	loadn r1, #pistaX
	add r1, r1, r0
	loadi r1, r1
	loadn r2, #1000             ; linha 25 (alvo) * 40
	add r1, r1, r2              ; r1 = posicao da parte esquerda do alvo
	loadn r2, #pistaCor
	add r2, r2, r0
	loadi r2, r2
	loadn r3, #18               ; sprite ALVO_CHEIO_ESQ
	add r3, r3, r2
	outchar r3, r1
	inc r1
	inc r3                      ; ALVO_CHEIO_MEIO (19)
	outchar r3, r1
	inc r1
	inc r3                      ; ALVO_CHEIO_DIR (20)
	outchar r3, r1

	loadn r1, #pressTimer
	add r1, r1, r0
	loadn r2, #3
	storei r1, r2
	loadn r1, #faiscaTimer      ; o preenchimento cobre uma faisca antiga
	add r1, r1, r0
	loadn r2, #0
	storei r1, r2

	pop r3
	pop r2
	pop r1
	rts

;------------------------------------------------------------------------------
; RestauraAlvo: redesenha o alvo vazado de uma pista (3 caracteres da linha 25).
;   r0 = pista
;------------------------------------------------------------------------------
RestauraAlvo:
	push r0
	push r1

	loadn r1, #pistaX
	add r1, r1, r0
	loadi r1, r1
	loadn r0, #1000             ; linha 25 * 40
	add r0, r0, r1              ; r0 = posicao da parte esquerda do alvo
	call RestauraCenario
	inc r0
	call RestauraCenario
	inc r0
	call RestauraCenario

	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; AtualizaEfeitos: conta o tempo da mensagem, das faiscas e dos alvos
; preenchidos, e apaga os que venceram.
;------------------------------------------------------------------------------
AtualizaEfeitos:
	push r0
	push r1
	push r2
	push r3
	push r4

	load r0, msgTimer
	loadn r1, #0
	cmp r0, r1
	jeq AtualizaEfeitos_faiscas
	dec r0
	store msgTimer, r0
	jnz AtualizaEfeitos_faiscas
	call ApagaMensagem

AtualizaEfeitos_faiscas:
	loadn r2, #0                ; r2 = pista
AtualizaEfeitos_laco:
	loadn r3, #faiscaTimer
	add r3, r3, r2
	loadi r4, r3
	loadn r1, #0
	cmp r4, r1
	jeq AtualizaEfeitos_prox    ; sem faisca nesta pista
	dec r4
	storei r3, r4
	jnz AtualizaEfeitos_prox    ; ainda nao venceu (STOREI nao altera o flag)
	loadn r3, #pistaX           ; venceu: devolve o alvo ao centro da pista
	add r3, r3, r2
	loadi r0, r3
	loadn r3, #1001
	add r0, r0, r3
	call RestauraCenario
AtualizaEfeitos_prox:
	inc r2
	loadn r3, #4
	cmp r2, r3
	jne AtualizaEfeitos_laco

	loadn r0, #0                ; r0 = pista
AtualizaEfeitos_pressLaco:
	loadn r3, #pressTimer
	add r3, r3, r0
	loadi r4, r3
	loadn r1, #0
	cmp r4, r1
	jeq AtualizaEfeitos_pressProx   ; alvo desta pista nao esta preenchido
	dec r4
	storei r3, r4
	jnz AtualizaEfeitos_pressProx   ; ainda nao venceu (STOREI nao altera o flag)
	call RestauraAlvo               ; venceu: o alvo volta a ser vazado
AtualizaEfeitos_pressProx:
	inc r0
	loadn r3, #4
	cmp r0, r3
	jne AtualizaEfeitos_pressLaco

	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; AtualizaHUD: redesenha o placar do painel direito, se algo mudou.
;------------------------------------------------------------------------------
AtualizaHUD:
	push r0
	push r1
	push r2
	push r3

	load r0, hudSujo
	loadn r1, #0
	cmp r0, r1
	jeq AtualizaHUD_fim
	store hudSujo, r1

	loadn r3, #2816             ; amarelo
	loadn r0, #230              ; PONTOS  (linha 5, coluna 30)
	load r1, pontos
	loadn r2, #5
	call ImprimeNumero
	loadn r0, #350              ; COMBO   (linha 8, coluna 30)
	load r1, combo
	loadn r2, #3
	call ImprimeNumero
	loadn r0, #471              ; MULT    (linha 11, coluna 31, depois do 'X')
	load r1, mult
	loadn r2, #1
	call ImprimeNumero
	loadn r0, #590              ; ACERTOS (linha 14, coluna 30)
	load r1, acertos
	loadn r2, #3
	call ImprimeNumero
	loadn r0, #710              ; ERROS   (linha 17, coluna 30)
	load r1, erros
	loadn r2, #3
	call ImprimeNumero

AtualizaHUD_fim:
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; TelaFim: desenha a caixa de resultado sobre o jogo e espera ESPACO.
;   A caixa (tools/telas/fim.txt) tem 22 colunas x 11 linhas e fica com o
;   canto superior esquerdo na linha 9, coluna 9.
;------------------------------------------------------------------------------
TelaFim:
	push r0
	push r1
	push r2
	push r3
	push r4
	push r5

	loadn r0, #369              ; linha 9, coluna 9
	loadn r1, #fimL00
	loadn r2, #11               ; linhas da caixa
	loadn r3, #0                ; texto em branco
	loadn r4, #40               ; proxima linha da tela
	loadn r5, #23               ; proxima string (22 caracteres + \0)
TelaFim_caixa:
	call ImprimeStrT
	add r0, r0, r4
	add r1, r1, r5
	dec r2
	jnz TelaFim_caixa

	loadn r3, #2816             ; numeros em amarelo
	loadn r0, #543              ; pontos
	load r1, pontos
	loadn r2, #5
	call ImprimeNumero
	loadn r0, #581              ; acertos
	load r1, acertos
		loadn r2, #3
	call ImprimeNumero
	loadn r0, #585              ; total de notas
	load r1, totalNotas
	call ImprimeNumero
	loadn r0, #625              ; combo maximo
	load r1, comboMax
	call ImprimeNumero

	call CalculaPrecisao        ; r1 = precisao em %
	loadn r0, #664
	call ImprimeNumero

	call Conceito               ; r1 = letra do conceito ja com cor
	loadn r0, #707
	outchar r1, r0

	loadn r1, #' '
TelaFim_espera:
	inchar r0
	cmp r0, r1
	jne TelaFim_espera

	pop r5
	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; CalculaPrecisao: r1 = acertos * 100 / totalNotas (0 se nao houve notas).
;------------------------------------------------------------------------------
CalculaPrecisao:
	push r2
	load r2, totalNotas
	loadn r1, #0
	cmp r2, r1
	jeq CalculaPrecisao_fim
	load r1, acertos
	push r3
	loadn r3, #100
	mul r1, r1, r3
	pop r3
	div r1, r1, r2
CalculaPrecisao_fim:
	pop r2
	rts

;------------------------------------------------------------------------------
; Conceito: converte a precisao numa letra.
;   S >= 95%   A >= 85%   B >= 70%   C >= 50%   D abaixo disso
;   Retorna: r1 = letra + cor, pronta para OUTCHAR
;------------------------------------------------------------------------------
Conceito:
	push r2
	call CalculaPrecisao        ; r1 = precisao
	loadn r2, #95
	cmp r1, r2
	jeg Conceito_S
	loadn r2, #85
	cmp r1, r2
	jeg Conceito_A
	loadn r2, #70
	cmp r1, r2
	jeg Conceito_B
	loadn r2, #50
	cmp r1, r2
	jeg Conceito_C
	loadn r1, #2372             ; 'D' (68) + vermelho
	jmp Conceito_fim
Conceito_S:
	loadn r1, #3411             ; 'S' (83) + rosa
	jmp Conceito_fim
Conceito_A:
	loadn r1, #2625             ; 'A' (65) + verde-limao
	jmp Conceito_fim
Conceito_B:
	loadn r1, #3138             ; 'B' (66) + azul
	jmp Conceito_fim
Conceito_C:
	loadn r1, #2883             ; 'C' (67) + amarelo
Conceito_fim:
	pop r2
	rts

;==============================================================================
; UTILITARIOS DE DESENHO
;==============================================================================

;------------------------------------------------------------------------------
; Traduz: converte um caractere de cenario na palavra que vai para o OUTCHAR.
;   Letra minuscula com entrada na tabela `traduz` vira o sprite colorido;
;   qualquer outro caractere e' texto comum e recebe a cor padrao.
;   r2 = caractere, r3 = cor padrao do texto
;   Retorna: r2 = palavra final (codigo + cor)
;------------------------------------------------------------------------------
Traduz:
	push r1
	push r4

	loadn r1, #traduz
	add r1, r1, r2
	loadi r4, r1                ; r4 = traduz[caractere]
	loadn r1, #0
	cmp r4, r1
	jeq Traduz_texto
	mov r2, r4                  ; e' sprite: ja vem com codigo e cor
	jmp Traduz_fim
Traduz_texto:
	add r2, r2, r3              ; texto comum: soma a cor padrao
Traduz_fim:
	pop r4
	pop r1
	rts

;------------------------------------------------------------------------------
; ImprimeCenario: desenha uma tela inteira (30 strings de 40 caracteres).
;   r1 = endereco da primeira linha (ex.: #telaL00), r3 = cor padrao do texto
;   Cada linha ocupa 41 palavras na memoria por causa do '\0' do fim.
;------------------------------------------------------------------------------
ImprimeCenario:
	push r0
	push r1
	push r2
	push r4
	push r5
	push r6

	loadn r0, #0                ; r0 = posicao na tela
	loadn r4, #40
	loadn r5, #1200
ImprimeCenario_linha:
	loadn r6, #0                ; r6 = coluna
ImprimeCenario_coluna:
	loadi r2, r1
	call Traduz
	outchar r2, r0
	inc r0
	inc r1
	inc r6
	cmp r6, r4
	jne ImprimeCenario_coluna
	inc r1                      ; pula o '\0' do fim da linha
	cmp r0, r5
	jne ImprimeCenario_linha

	pop r6
	pop r5
	pop r4
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; RestauraCenario: redesenha o caractere do cenario do jogo numa posicao
; (tecnica para apagar objetos sem destruir o fundo).
;   r0 = posicao na tela
;   Endereco do caractere = telaL00 + posicao + linha (cada linha tem um '\0').
;------------------------------------------------------------------------------
RestauraCenario:
	push r1
	push r2
	push r3

	loadn r3, #40
	div r1, r0, r3              ; r1 = linha
	add r1, r1, r0              ; r1 = posicao + linha
	loadn r3, #telaL00
	add r1, r1, r3
	loadi r2, r1                ; r2 = caractere do cenario
	loadn r3, #0
	call Traduz
	outchar r2, r0

	pop r3
	pop r2
	pop r1
	rts

;------------------------------------------------------------------------------
; ImprimeStrT: imprime uma string terminada em '\0', traduzindo os sprites.
;   r0 = posicao na tela, r1 = endereco da string, r3 = cor do texto
;------------------------------------------------------------------------------
ImprimeStrT:
	push r0
	push r1
	push r2
	push r4

	loadn r4, #0
ImprimeStrT_laco:
	loadi r2, r1
	cmp r2, r4
	jeq ImprimeStrT_fim         ; chegou no '\0'
	call Traduz
	outchar r2, r0
	inc r0
	inc r1
	jmp ImprimeStrT_laco
ImprimeStrT_fim:
	pop r4
	pop r2
	pop r1
	pop r0
	rts

;------------------------------------------------------------------------------
; ImprimeNumero: escreve um numero em decimal com zeros a esquerda.
;   r0 = posicao do primeiro digito, r1 = valor, r2 = quantidade de digitos,
;   r3 = cor
;------------------------------------------------------------------------------
ImprimeNumero:
	push r0
	push r1
	push r2
	push r3
	push r4
	push r5

	loadn r4, #'0'
	add r3, r3, r4              ; r3 = cor + '0'
	add r0, r0, r2
	dec r0                      ; comeca pelas unidades (ultimo digito)
	loadn r4, #10
ImprimeNumero_laco:
	mod r5, r1, r4              ; digito = valor % 10
	add r5, r5, r3
	outchar r5, r0
	div r1, r1, r4              ; valor = valor / 10
	dec r0
	dec r2
	jnz ImprimeNumero_laco

	pop r5
	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts
