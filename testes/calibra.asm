; Medicao da velocidade do simulador.
; Executa blocos de ~20000 instrucoes e mostra na tela quantos blocos ja rodou.
; Velocidade (instrucoes/s) ~= blocos * 20040 / segundos decorridos.
; Com o clock fixo do simulador (5 MHz) devem sair ~250 blocos por segundo;
; bem menos que isso indica um computador que nao consegue acompanhar o clock.
;
; Linha 0: contador do laco SEM outchar   (dec + jnz)
; Linha 2: contador do laco COM outchar   (outchar + dec + jnz) - roda depois de 300 blocos

jmp main

main:
	loadn r7, #0			; blocos executados (fase 1)
	loadn r6, #300			; numero de blocos da fase 1

fase1:
	loadn r1, #10000
fase1_laco:
	dec r1					; 10000 x 2 instrucoes = 20000
	jnz fase1_laco
	inc r7
	loadn r0, #0			; imprime na posicao 0
	mov r5, r7
	call ImprimeNumero
	cmp r7, r6
	jne fase1

	loadn r7, #0			; blocos executados (fase 2)
	loadn r2, #'*'
	loadn r3, #600			; posicao fixa para o outchar do laco
fase2:
	loadn r1, #6667
fase2_laco:
	outchar r2, r3			; 6667 x 3 instrucoes ~= 20000
	dec r1
	jnz fase2_laco
	inc r7
	loadn r0, #80			; imprime na linha 2
	mov r5, r7
	call ImprimeNumero
	jmp fase2

; Imprime r5 com 5 digitos a partir da posicao r0 (amarelo).
ImprimeNumero:
	push r0
	push r1
	push r2
	push r3
	push r4
	push r5
	loadn r1, #4
	add r0, r0, r1			; comeca pelo digito das unidades (posicao + 4)
	loadn r2, #10
	loadn r3, #2864			; '0' (48) + amarelo (2816)
	loadn r4, #5
ImprimeNumero_laco:
	mod r1, r5, r2
	add r1, r1, r3
	outchar r1, r0
	div r5, r5, r2
	dec r0
	dec r4
	jnz ImprimeNumero_laco
	pop r5
	pop r4
	pop r3
	pop r2
	pop r1
	pop r0
	rts
