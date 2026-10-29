// Teste de ouvido do audio do simulador, usando o Sound.cpp real.
//   1) SOUND (play_note):       Do, Re, Mi - cada uma espera terminar
//   2) SNDN  (play_note_async): Ode a Alegria, as notas espacadas com SDL_Delay
// Se nao sair som, rode antes o testes/diagnostico_audio.
//
// Compilar (MSYS2): g++ testes/teste_beep.cpp Simulador/Sound.cpp -ISimulador -o testes/teste_beep -lSDL2
#define SDL_MAIN_HANDLED
#include "Sound.h"
#include <cstdio>

int main()
{
	SDL_SetMainReady();

	printf("SOUND (bloqueante): Do Re Mi...\n");
	fflush(stdout);
	play_note(262, 300, 1);
	play_note(294, 300, 1);
	play_note(330, 300, 1);

	printf("SNDN (nao-bloqueante): Ode a Alegria...\n");
	fflush(stdout);
	const int melodia[] = {330, 330, 349, 392, 392, 349, 330, 294, 262, 262, 294, 330, 330, 294, 294};
	const int ms[]      = {300, 300, 300, 300, 300, 300, 300, 300, 300, 300, 300, 300, 450, 150, 600};
	for (int i = 0; i < 15; i++) {
		play_note_async(melodia[i], ms[i], 2);   // retorna na hora
		SDL_Delay(ms[i]);                        // quem espera e' o programa
	}
	printf("fim\n");
	return 0;
}
