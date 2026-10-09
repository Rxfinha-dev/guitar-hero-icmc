; Teste da instrucao sndn original (bloqueante).
; Toca Do-Re-Mi com 200 ms cada e escreve um '*' na tela entre as notas.
; No simulador grafico a tela congela durante cada nota; no harness headless
; o log de som mostra as tres chamadas marcadas como bloqueantes.

jmp main

main:
	loadn r2, #200		; duracao: 200 ms
	loadn r3, #1		; onda quadrada
	loadn r5, #'*'
	loadn r6, #0		; posicao na tela

	loadn r1, #262		; Do
	sndn r1, r2, r3
	outchar r5, r6
	inc r6

	loadn r1, #294		; Re
	sndn r1, r2, r3
	outchar r5, r6
	inc r6

	loadn r1, #330		; Mi
	sndn r1, r2, r3
	outchar r5, r6

	halt
