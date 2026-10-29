#!/bin/bash
# Compila o montador, o simulador grafico e o harness de testes headless.
# Funciona no Linux e no Windows (MSYS2 UCRT64, com gtk2 e SDL2 instalados).
set -e
cd "$(dirname "$0")"

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) EXE=.exe; LIBS_SO=-lwinmm ;;   # winmm: timeBeginPeriod (clock do simulador)
  *) EXE=; LIBS_SO= ;;
esac

echo ">> Montador"
gcc -O2 -o Montador/montador$EXE Montador/main.c Montador/montador.c Montador/parser.c Montador/structs.c

echo ">> Simulador (GTK2 + SDL2)"
g++ -O2 -o Simulador/sim$EXE \
    Simulador/main.cpp Simulador/View.cpp Simulador/Controller.cpp Simulador/Sound.cpp Simulador/Model.cpp \
    $(pkg-config --cflags --libs gtk+-2.0 sdl2) -pthread -lgthread-2.0 -Wno-deprecated-declarations $LIBS_SO

echo ">> Simple Simulator (requisito 2: processador ciclo a ciclo em C)"
gcc -O2 -Wall -o SimpleSimulator/simples$EXE SimpleSimulator/simple_simulator.c -lm

echo ">> Harness headless (testes)"
g++ -O2 -ISimulador -o tools/headless/headless$EXE \
    tools/headless/headless.cpp tools/headless/sound_stub.cpp Simulador/Model.cpp \
    $(pkg-config --cflags --libs gtk+-2.0 sdl2) -pthread -lgthread-2.0 -Wno-deprecated-declarations $LIBS_SO

echo "OK"
