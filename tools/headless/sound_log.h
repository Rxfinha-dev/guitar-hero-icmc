#ifndef SOUND_LOG_H
#define SOUND_LOG_H

// Ciclo atual da simulacao, atualizado pelo harness antes de cada instrucao.
extern long g_soundCycle;

// Imprime todas as notas emitidas durante a execucao.
void printSoundLog();

#endif
