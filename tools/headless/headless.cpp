// Harness headless do Processador ICMC.
// Usa o MESMO Model.cpp do simulador grafico (mesma semantica de instrucoes),
// mas sem janela: executa N instrucoes, injeta teclas em ciclos definidos
// e imprime a tela 40x30 como texto. Serve para testar o jogo de forma
// automatica e reprodutivel.
//
// Uso:
//   headless cpuram.mif charmap.mif [opcoes]
//     --cycles N          executa no maximo N instrucoes (padrao 2000000)
//     --key CICLO:TECLA   injeta TECLA (1 caractere) a partir do CICLO
//     --dump CICLO        imprime a tela quando atingir CICLO (pode repetir)
//     --colors            imprime tambem a grade de cores (0-15, em hex)
//     --mem END[:N]       imprime N palavras da memoria a partir de END no fim
//     --quiet             nao imprime a tela final
//     --glyphs A:B        imprime os sprites dos codigos A..B como lidos do charmap
//     --autoplay          "robo" do Guitar Hero ICMC: le a linha do alvo na tela
//                         e aperta a tecla da pista quando ve o meio de uma nota
//     --autoplay-linha N  igual, mas o robo aperta quando a nota esta na linha N
//                         (25 = no alvo, 24/26 = "quase", 23 = fora da janela)
//     --gui-lock          envolve cada instrucao em gdk_threads_enter/leave,
//                         como faz o simulador grafico (para medir velocidade)
//
// A execucao termina no HALT ou ao atingir --cycles.

#include "Model.h"
#include "sound_log.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <set>
#include <vector>

struct StubVideo : public Video { void updateVideo(int) {} };
struct StubIns : public Instrucoes { void updateInstrucoes(unsigned int, unsigned int, unsigned int) {} };
struct StubRegs : public Registradores {
	void updatePC() {} void updateIR() {} void updateSP() {} void updateFR() {} void updateRegistradores() {}
};

struct StubController : public ControllerInterface {
	int key = 255;
	bool halted = false;
	void AlteraRegistradores(GtkWidget **) {}
	bool userInput(const char *) { return false; }
	void reset() {}
	int getKey() { int k = key; key = 255; return k; }
	void setDelay(int) {}
	void setResetVideo(bool) {}
	void setRegistradorHex(bool) {}
	void switchExecucao() {}
	bool getHex() { return false; }
	void notifyProcessamento() {}
	void pauseProcessamento() { halted = true; }
};

// Como mostrar os sprites do jogo (codigos < 32 do charmap) em texto.
static char spriteChar(int c)
{
	static const char *tabela = " (=)?:[_]|-++++#s*";   // codigos 0..17
	if (c >= 0 && c <= 17) return tabela[c];
	return '#';
}

static void dumpScreen(Model &m, long ciclo, bool colors)
{
	pixblock *b = m.getPixblock();
	printf("---- tela no ciclo %ld ----\n", ciclo);
	for (int y = 0; y < 30; y++) {
		putchar('|');
		for (int x = 0; x < 40; x++) {
			int c = b[y * 40 + x].sym / 8;
			putchar(c >= 32 && c < 127 ? c : spriteChar(c));
		}
		printf("|%02d\n", y);
	}
	if (colors) {
		printf("---- cores (hex) ----\n");
		for (int y = 0; y < 30; y++) {
			for (int x = 0; x < 40; x++) {
				int c = b[y * 40 + x].sym / 8;
				putchar(c == 0 ? '.' : "0123456789ABCDEF"[b[y * 40 + x].color & 15]);
			}
			printf(" %02d\n", y);
		}
	}
	fflush(stdout);
}

int main(int argc, char *argv[])
{
	if (argc < 3) {
		fprintf(stderr, "uso: %s cpuram.mif charmap.mif [opcoes]\n", argv[0]);
		return 1;
	}

	long maxCycles = 2000000;
	std::multimap<long, int> keys;
	std::set<long> dumps;
	bool colors = false, quiet = false, guiLock = false, autoplay = false;
	int linhaRobo = 25;
	int memStart = -1, memCount = 1;
	int glyphFrom = -1, glyphTo = -1;

	for (int i = 3; i < argc; i++) {
		if (!strcmp(argv[i], "--cycles") && i + 1 < argc) maxCycles = atol(argv[++i]);
		else if (!strcmp(argv[i], "--key") && i + 1 < argc) {
			char *spec = argv[++i];
			char *colon = strchr(spec, ':');
			if (!colon || !colon[1]) { fprintf(stderr, "--key espera CICLO:TECLA\n"); return 1; }
			keys.insert(std::make_pair(atol(spec), (int)(unsigned char)colon[1]));
		}
		else if (!strcmp(argv[i], "--dump") && i + 1 < argc) dumps.insert(atol(argv[++i]));
		else if (!strcmp(argv[i], "--colors")) colors = true;
		else if (!strcmp(argv[i], "--quiet")) quiet = true;
		else if (!strcmp(argv[i], "--gui-lock")) guiLock = true;
		else if (!strcmp(argv[i], "--autoplay")) autoplay = true;
		else if (!strcmp(argv[i], "--autoplay-linha") && i + 1 < argc) { autoplay = true; linhaRobo = atoi(argv[++i]); }
		else if (!strcmp(argv[i], "--glyphs") && i + 1 < argc) {
			char *spec = argv[++i];
			glyphFrom = glyphTo = atoi(spec);
			char *colon = strchr(spec, ':');
			if (colon) glyphTo = atoi(colon + 1);
		}
		else if (!strcmp(argv[i], "--mem") && i + 1 < argc) {
			char *spec = argv[++i];
			memStart = atoi(spec);
			char *colon = strchr(spec, ':');
			if (colon) memCount = atoi(colon + 1);
		}
		else { fprintf(stderr, "opcao desconhecida: %s\n", argv[i]); return 1; }
	}

	if (guiLock) {
		g_thread_init(NULL);
		gdk_threads_init();
	}

	StubVideo vid; StubIns ins; StubRegs regs; StubController ctrl;
	Model m(argv[1], argv[2]);
	m.registraVideo(&vid);
	m.registraInstrucoes(&ins);
	m.registraRegistrador(&regs);
	m.setController(&ctrl);
	m.reset();
	m.resetVideo();

	if (glyphFrom >= 0) {
		short int **chars = m.getChars();
		for (int c = glyphFrom; c <= glyphTo; c++) {
			printf("codigo %d:\n", c);
			for (int y = 0; y < 8; y++) {
				printf("  ");
				for (int x = 0; x < 8; x++) putchar(chars[c * 8 + y][x] ? '#' : '.');
				putchar('\n');
			}
		}
		return 0;
	}

	auto nextKey = keys.begin();
	long ciclo = 0;
	for (; ciclo < maxCycles && !ctrl.halted; ciclo++) {
		while (nextKey != keys.end() && nextKey->first <= ciclo) {
			ctrl.key = nextKey->second;
			++nextKey;
		}
		// Robo: o meio de uma nota (sprite 2) no centro da pista, na linha observada, e
		// nenhuma outra nota mais abaixo na mesma pista => aperta a tecla da pista.
		if (autoplay && ctrl.key == 255 && ciclo % 2000 == 0) {
			static const int centroX[4] = {13, 17, 21, 25};
			static const char tecla[4] = {'d', 'f', 'j', 'k'};
			pixblock *b = m.getPixblock();
			for (int p = 0; p < 4; p++) {
				if (b[linhaRobo * 40 + centroX[p]].sym / 8 != 2) continue;
				bool maisBaixa = true;
				for (int y = linhaRobo + 1; y <= 26; y++)
					if (b[y * 40 + centroX[p]].sym / 8 == 2) maisBaixa = false;
				if (maisBaixa) { ctrl.key = tecla[p]; break; }
			}
		}
		g_soundCycle = ciclo;
		if (guiLock) {
			gdk_threads_enter();
			m.processador();
			gdk_threads_leave();
		} else {
			m.processador();
		}
		if (dumps.count(ciclo)) dumpScreen(m, ciclo, colors);
	}

	printf("==== fim: %ld instrucoes executadas, %s ====\n", ciclo, ctrl.halted ? "HALT" : "limite de ciclos");
	printSoundLog();
	if (memStart >= 0) {
		for (int i = 0; i < memCount; i++) printf("mem[%d] = %d\n", memStart + i, m.getMem(memStart + i));
	}
	if (!quiet) dumpScreen(m, ciclo, colors);
	return 0;
}
