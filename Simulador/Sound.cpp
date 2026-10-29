#include "Sound.h"
#include <cstdio>

Beeper::Beeper()
{
    v = 0;

    SDL_AudioSpec desiredSpec;

    desiredSpec.freq = FREQUENCY;
    desiredSpec.format = AUDIO_S16SYS;
    desiredSpec.channels = 1;
    // 512 amostras = ~12 ms por bloco. O original usava 2048 (~46 ms), e o som
    // saia visivelmente atrasado em relacao a nota chegando ao alvo.
    desiredSpec.samples = 512;
    desiredSpec.callback = audio_callback;
    desiredSpec.userdata = this;

    // obtained = NULL: o SDL converte nosso S16 mono para o formato da placa.
    // O original passava um obtainedSpec, e com isso o SDL2 NAO converte: no
    // Windows (WASAPI, float 32 bits estereo) o callback escrevia no formato
    // errado e nao saia som nenhum.
    if (SDL_OpenAudio(&desiredSpec, NULL) != 0)
        fprintf(stderr, "Erro ao abrir o audio: %s\n", SDL_GetError());

    // start play audio
    SDL_PauseAudio(0);
}

Beeper::~Beeper(){
    SDL_CloseAudio();
}



// Cada nota entra e sai com uma rampa de volume de RAMPA amostras (~5 ms):
// sem ela, o inicio e o fim da onda sao degraus e cada nota "estala".
static const int RAMPA = FREQUENCY / 200;

void Beeper::generateSamples(Sint16 *stream, int length)
{
    int i = 0;
    while (i < length) {

        if (beeps.empty()) {
            while (i < length) {
                stream[i] = 0;
                i++;
            }
            return;
        }
        BeepObject& bo = beeps.front();
        if (bo.samplesLeft <= 0) {
            beeps.pop();
            continue;
        }

        int feitas = bo.totalSamples - bo.samplesLeft;
        double envelope = 1.0;
        if (feitas < RAMPA)
            envelope = (double) feitas / RAMPA;
        if (bo.samplesLeft < RAMPA)
            envelope = std::min(envelope, (double) bo.samplesLeft / RAMPA);

        stream[i] = (Sint16) (chooseWave(bo.wave_type, FREQUENCY, AMPLITUDE, v) * envelope);
        i++;
        v += bo.freq;
        bo.samplesLeft--;
    }
}

double sineWave(double freq, double amplitude, double v){
    return amplitude * std::sin(v * 2 * M_PI / freq);
}

double squareWave(double freq, double amplitude, double v){
    double w = v * 2 * M_PI / freq;
    double value = std::sin(w) >= 0.0 ? 1.0 : -1.0;

    return (value * amplitude);
}

double triangleWave(double freq, double amplitude, double v){
    double w = v * 2 * M_PI / freq;
    double value = (2.0 / M_PI) * std::asin(std::sin(w));

    return (value * amplitude);
}

double sawtoothWave(double freq, double amplitude, double v){
    double wave = 2 * ( (v/freq) - std::floor(0.5 + (v/freq)) );

    return (wave * amplitude);
}


double Beeper::chooseWave(string wave, double freq, double amplitude, double v){
    if (wave == "sine"){
        return sineWave(freq, amplitude, v);
    } else if (wave == "square"){
        return squareWave(freq, amplitude, v);
    } else if (wave == "triangle"){
        return triangleWave(freq, amplitude, v);
    } else if (wave == "sawtooth"){
        return sawtoothWave(freq, amplitude, v);
    } else {
        return sineWave(freq, amplitude, v);
    }
}

void Beeper::beep(string wave, double freq, int duration){
    BeepObject bo;
    bo.freq = freq;
    bo.wave_type = wave;
    bo.samplesLeft = duration * FREQUENCY / 1000;
    bo.totalSamples = bo.samplesLeft;

    SDL_LockAudio();
    beeps.push(bo);
    SDL_UnlockAudio();
}

// Descarta as notas pendentes (incluindo a que esta' tocando) e inicia a nova.
void Beeper::replace(string wave, double freq, int duration){
    BeepObject bo;
    bo.freq = freq;
    bo.wave_type = wave;
    bo.samplesLeft = duration * FREQUENCY / 1000;
    bo.totalSamples = bo.samplesLeft;

    SDL_LockAudio();
    beeps = queue<BeepObject>();
    beeps.push(bo);
    SDL_UnlockAudio();
}

void Beeper::wait(int time){
    int size;
    do {
        SDL_Delay(time);
        SDL_LockAudio();
        size = beeps.size();
        SDL_UnlockAudio();
    } while (size > 0);

}

void audio_callback(void *_beeper, Uint8 *_stream, int _length)
{
    Sint16 *stream = (Sint16*) _stream;
    int length = _length / 2;
    Beeper* beeper = (Beeper*) _beeper;

    beeper->generateSamples(stream, length);
}

static std::string tipoOnda(int rz) {
    switch (rz) {
    case 1:  return "square";
    case 2:  return "triangle";
    case 3:  return "sawtooth";
    default: return "sine";
    }
}

// Um unico dispositivo de audio para o simulador inteiro. O original criava e
// destruia um Beeper (e chamava SDL_Init) a cada nota; com SOUND e SNDN no
// mesmo programa, dois SDL_OpenAudio simultaneos falhariam.
static Beeper& beeperGlobal() {
    static bool iniciado = (SDL_Init(SDL_INIT_AUDIO) == 0);
    static Beeper beeper;
    (void) iniciado;
    return beeper;
}

// SOUND - rx: frequencia (Hz), ry: duracao (ms), rz: forma de onda.
// Bloqueante: a CPU so' continua quando a nota termina de tocar.
void play_note (int rx, int ry, int rz) {
    Beeper& beeper = beeperGlobal();
    beeper.beep(tipoOnda(rz), rx, ry);
    beeper.wait(30);
}

// SNDN - mesmos operandos do SOUND, mas nao espera: troca a nota atual pela
// nova e devolve o controle para a CPU na hora.
void play_note_async (int rx, int ry, int rz) {
    beeperGlobal().replace(tipoOnda(rz), rx, ry);
}