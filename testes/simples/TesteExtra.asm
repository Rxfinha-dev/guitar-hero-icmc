; Teste extra do Simple Simulator: instrucoes que o TesteCPU nao cobre e que o
; jogo usa. Cada verificacao imprime uma letra (a, b, c...) se passou, ou 'X'.
; Saida esperada: abcdefghij

jmp main

valor : var #1

main:
	loadn r7, #0                ; posicao na tela

	; a) MOD
	loadn r1, #17
	loadn r2, #5
	mod r3, r1, r2              ; 17 % 5 = 2
	loadn r4, #2
	loadn r0, #'a'
	cmp r3, r4
	call Confere

	; b) jle (MENOR estrito) e jeg (maior ou igual)
	loadn r1, #3
	loadn r2, #4
	loadn r0, #'b'
	cmp r1, r2
	jle b_ok
	loadn r0, #'X'
b_ok:
	cmp r2, r2
	jeg b_ok2
	loadn r0, #'X'
b_ok2:
	call Imprime

	; c) jel (menor ou igual) com igualdade, e jgr nao salta quando igual
	loadn r0, #'c'
	cmp r1, r1
	jel c_ok
	loadn r0, #'X'
c_ok:
	jgr c_erro
	jmp c_fim
c_erro:
	loadn r0, #'X'
c_fim:
	call Imprime

	; d) PUSH FR / POP FR preserva os flags (EQUAL) apos uma comparacao diferente
	loadn r0, #'d'
	cmp r1, r1                  ; EQUAL = 1
	push fr
	cmp r1, r2                  ; EQUAL = 0
	pop fr                      ; volta EQUAL = 1
	jeq d_ok
	loadn r0, #'X'
d_ok:
	call Imprime

	; e) MOV Rx, SP e MOV SP, Rx (salva e restaura a pilha)
	loadn r0, #'e'
	mov r5, sp
	push r1
	push r1
	mov sp, r5                  ; descarta os dois push
	mov r6, sp
	cmp r5, r6
	call Confere0

	; f) chamadas aninhadas (CALL dentro de CALL)
	loadn r0, #'X'
	call Externa                ; Externa chama Interna, que troca r0 para 'f'
	call Imprime

	; g) laco com DEC + JNZ: soma 1..10 = 55
	loadn r1, #10
	loadn r3, #0
g_laco:
	add r3, r3, r1
	dec r1
	jnz g_laco
	loadn r4, #55
	loadn r0, #'g'
	cmp r3, r4
	call Confere

	; h) LOAD/STORE em variavel + MUL + DIV
	loadn r1, #7
	loadn r2, #6
	mul r3, r1, r2              ; 42
	store valor, r3
	load r4, valor
	loadn r2, #2
	div r4, r4, r2              ; 21
	loadn r5, #21
	loadn r0, #'h'
	cmp r4, r5
	call Confere

	; i) AND como teste de bit (mascara de pistas do jogo)
	loadn r1, #10               ; 1010b
	loadn r2, #8
	and r3, r1, r2              ; bit 3 ligado -> 8
	loadn r0, #'i'
	cmp r3, r2
	call Confere

	; j) LOADI/STOREI com ponteiro incrementado (vetor)
	loadn r1, #valor
	loadn r2, #'j'
	storei r1, r2
	loadi r0, r1
	call Imprime

	halt

; Confere: imprime r0 se a ultima comparacao deu EQUAL, senao imprime 'X'
Confere:
	jeq Imprime
	loadn r0, #'X'
	jmp Imprime

; Confere0: igual a Confere (rotulo separado so' para legibilidade do teste e)
Confere0:
	jeq Imprime
	loadn r0, #'X'

; Imprime: escreve r0 na posicao r7 e avanca
Imprime:
	outchar r0, r7
	inc r7
	rts

Externa:
	call Interna
	rts

Interna:
	loadn r0, #'f'
	rts
