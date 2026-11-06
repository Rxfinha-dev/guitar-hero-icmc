; Teste da instrucao SNDN no Simple Simulator. Cada verificacao imprime uma letra
; (a, b, c...) se passou, ou 'X'. Saida esperada: abcdef
; E as notas, na ordem (o testa_tudo.py confere e compara com o simulador grafico):
;   262 200 1 / 294 150 2 / 262 262 262 / 330 100 0 / 349 100 3 / 392 390 1 /
;   440 3 0 / 440 2 0 / 440 1 0

jmp main

freqs : var #3
static freqs + #0, #262
static freqs + #1, #330
static freqs + #2, #392

tabMsFrame : var #1
static tabMsFrame + #0, #65

onda : var #1
static onda + #0, #1

main:
	loadn r7, #0                ; posicao na tela

	; a) Rx = frequencia, Ry = duracao, Rz = onda, e os operandos nao mudam
	loadn r1, #262
	loadn r2, #200
	loadn r3, #1
	sndn r1, r2, r3
	loadn r4, #262
	loadn r0, #'a'
	cmp r1, r4
	call Confere

	; b) outros registradores: os tres campos sao decodificados do IR
	loadn r4, #294
	loadn r5, #150
	loadn r6, #2
	sndn r4, r5, r6
	loadn r3, #150
	loadn r0, #'b'
	cmp r5, r3
	call Confere

	; c) o mesmo registrador nos tres operandos
	sndn r1, r1, r1
	loadn r0, #'c'
	cmp r1, r1
	call Confere

	; d) nao altera os flags: EQUAL continua ligado e depois continua desligado
	loadn r4, #330
	loadn r5, #100
	loadn r6, #0
	loadn r0, #'d'
	cmp r4, r4                  ; EQUAL = 1
	sndn r4, r5, r6
	jeq d_ok
	loadn r0, #'X'
d_ok:
	loadn r4, #349
	loadn r6, #3
	cmp r4, r5                  ; EQUAL = 0
	sndn r4, r5, r6
	jne d_ok2
	loadn r0, #'X'
d_ok2:
	call Imprime

	; e) operandos montados como no TocaMelodia do jogo: tabela, mul e variavel
	loadn r1, #freqs
	loadn r2, #2
	add r1, r1, r2
	loadi r0, r1                ; r0 = frequencia
	loadn r2, #6                ; duracao em frames
	loadn r1, #tabMsFrame
	loadi r1, r1
	mul r1, r1, r2              ; r1 = duracao em ms
	load r2, onda
	sndn r0, r1, r2
	loadn r3, #390
	loadn r0, #'e'
	cmp r1, r3
	call Confere

	; f) ocupa uma palavra e devolve o controle: laco com a nota dentro de uma rotina
	loadn r1, #440
	loadn r2, #3
	loadn r3, #0
	mov r5, sp
f_laco:
	call Nota
	dec r2
	jnz f_laco
	mov r6, sp
	loadn r0, #'f'
	cmp r5, r6                  ; a pilha voltou ao mesmo lugar
	call Confere

	halt

Nota:
	push r1
	sndn r1, r2, r3
	pop r1
	rts

; Confere: imprime r0 se a ultima comparacao deu EQUAL, senao imprime 'X'
Confere:
	jeq Imprime
	loadn r0, #'X'

; Imprime: escreve r0 na posicao r7 e avanca
Imprime:
	outchar r0, r7
	inc r7
	rts
