// Diagnostico do audio do simulador (SDL2).
// Abre o audio pedindo S16 mono, como o Sound.cpp, de dois jeitos:
//   1) SDL_OpenAudio(&desejado, &obtido) - como no Sound.cpp ORIGINAL
//   2) SDL_OpenAudio(&desejado, NULL)    - como no Sound.cpp CORRIGIDO
// e mede o tamanho do buffer que o SDL entrega ao callback. Para S16 mono com
// 2048 amostras, o buffer certo tem 4096 bytes; outro tamanho significa que o
// callback esta' recebendo o formato da placa (e escrevendo S16 nele: sem som).
//
// Compilar (MSYS2): g++ testes/diagnostico_audio.cpp -o testes/diagnostico_audio -lSDL2
#define SDL_MAIN_HANDLED
#include <SDL2/SDL.h>
#include <cstdio>

static volatile int g_len = -1;
static void callback(void *, Uint8 *stream, int len) { g_len = len; SDL_memset(stream, 0, len); }

static const char *formato(SDL_AudioFormat f)
{
	switch (f) {
	case AUDIO_S16SYS: return "S16 (inteiro 16 bits)";
	case AUDIO_F32SYS: return "F32 (float 32 bits)";
	case AUDIO_S32SYS: return "S32 (inteiro 32 bits)";
	default:           return "outro";
	}
}

static int testa(bool comObtido)
{
	SDL_AudioSpec desejado = {}, obtido = {};
	desejado.freq = 44100;
	desejado.format = AUDIO_S16SYS;
	desejado.channels = 1;
	desejado.samples = 2048;
	desejado.callback = callback;

	g_len = -1;
	if (SDL_OpenAudio(&desejado, comObtido ? &obtido : NULL) != 0) {
		printf("  SDL_OpenAudio falhou: %s\n", SDL_GetError());
		return 1;
	}
	SDL_PauseAudio(0);
	SDL_Delay(300);
	SDL_PauseAudio(1);
	SDL_CloseAudio();

	if (comObtido)
		printf("  placa aceitou: %s, %d canal(is), %d Hz\n", formato(obtido.format), obtido.channels, obtido.freq);
	printf("  buffer do callback: %d bytes (S16 mono certo = 4096) -> %s\n", g_len,
	       g_len == 4096 ? "OK, som sai" : "FORMATO ERRADO, sem som");
	return g_len == 4096 ? 0 : 1;
}

int main()
{
	SDL_SetMainReady();
	if (SDL_Init(SDL_INIT_AUDIO) != 0) { printf("SDL_Init falhou: %s\n", SDL_GetError()); return 1; }
	printf("driver de audio: %s\n", SDL_GetCurrentAudioDriver());
	printf("1) Sound.cpp ORIGINAL (com obtainedSpec):\n");
	testa(true);
	printf("2) Sound.cpp CORRIGIDO (obtained = NULL):\n");
	int erro = testa(false);
	SDL_Quit();
	return erro;
}
