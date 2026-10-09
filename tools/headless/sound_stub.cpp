// Substitui Sound.cpp no harness: nao toca audio, apenas registra cada nota.
// Isso permite verificar a musica do jogo e medir quanto tempo a CPU ficaria
// travada pelas chamadas bloqueantes (SOUND).

#include "sound_log.h"

#include <cstdio>
#include <vector>

long g_soundCycle = 0;

struct NotaLog { long ciclo; int freq, dur, onda; bool bloqueante; };
static std::vector<NotaLog> g_log;

void play_note(int rx, int ry, int rz)       { g_log.push_back({g_soundCycle, rx, ry, rz, true}); }
void play_note_async(int rx, int ry, int rz) { g_log.push_back({g_soundCycle, rx, ry, rz, false}); }

void printSoundLog()
{
	long bloqueadoMs = 0;
	int bloqueantes = 0;
	for (const NotaLog &n : g_log) {
		if (n.bloqueante) { bloqueadoMs += n.dur; bloqueantes++; }
	}
	printf("==== som: %zu notas (%d bloqueantes / SOUND, %zu nao-bloqueantes / SNDN); CPU travada por %ld ms ====\n",
	       g_log.size(), bloqueantes, g_log.size() - bloqueantes, bloqueadoMs);
	for (size_t i = 0; i < g_log.size() && i < 40; i++) {
		const NotaLog &n = g_log[i];
		printf("  ciclo %8ld  %-5s freq=%4d Hz dur=%4d ms onda=%d\n",
		       n.ciclo, n.bloqueante ? "SOUND" : "SNDN", n.freq, n.dur, n.onda);
	}
	if (g_log.size() > 40) printf("  ... (%zu notas omitidas)\n", g_log.size() - 40);
}
