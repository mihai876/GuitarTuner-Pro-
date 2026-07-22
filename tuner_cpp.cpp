// tuner_cpp.cpp — тюнер для гитары с автоопределением нот на C++ (PortAudio + FFTW)

#include <iostream>
#include <vector>
#include <cmath>
#include <portaudio.h>
#include <fftw3.h>
#include <map>
#include <string>

class GuitarTuner {
private:
    static const int SAMPLE_RATE = 44100;
    static const int FRAMES_PER_BUFFER = 4096;
    PaStream* stream;
    double currentFreq;
    double currentCents;
    std::string currentNote;
    std::vector<double> tuning;
    std::map<double, std::string> noteNames;
    double refFreq = 440.0;
    bool running;

    static int paCallback(const void* inputBuffer, void* outputBuffer,
                          unsigned long framesPerBuffer,
                          const PaStreamCallbackTimeInfo* timeInfo,
                          PaStreamCallbackFlags statusFlags,
                          void* userData) {
        auto* tuner = static_cast<GuitarTuner*>(userData);
        const float* in = static_cast<const float*>(inputBuffer);
        if (in && tuner->running) {
            tuner->processAudio(in, framesPerBuffer);
        }
        return paContinue;
    }

    void processAudio(const float* data, unsigned long frames) {
        // Анализ частоты через FFT
        std::vector<double> signal(frames);
        for (unsigned long i = 0; i < frames; ++i) {
            signal[i] = data[i];
            // Окно Хэмминга
            signal[i] *= 0.54 - 0.46 * cos(2 * M_PI * i / (frames - 1));
        }

        // FFT
        fftw_complex* out = (fftw_complex*)fftw_malloc(sizeof(fftw_complex) * frames);
        fftw_plan plan = fftw_plan_dft_r2c_1d(frames, signal.data(), out, FFTW_ESTIMATE);
        fftw_execute(plan);

        // Поиск пика
        double maxAmp = 0;
        int maxIdx = 0;
        for (int i = 1; i < frames / 2; ++i) {
            double amp = sqrt(out[i][0]*out[i][0] + out[i][1]*out[i][1]);
            if (amp > maxAmp) {
                maxAmp = amp;
                maxIdx = i;
            }
        }
        double freq = (double)maxIdx * SAMPLE_RATE / frames;

        fftw_destroy_plan(plan);
        fftw_free(out);

        if (freq > 30 && freq < 1000) {
            findNote(freq);
        }
    }

    void findNote(double freq) {
        double bestFreq = 0;
        double bestDiff = 1e9;
        for (double target : tuning) {
            double diff = std::abs(freq - target);
            if (diff < bestDiff) {
                bestDiff = diff;
                bestFreq = target;
            }
        }
        if (bestFreq > 0) {
            currentFreq = bestFreq;
            currentCents = 1200 * std::log2(freq / bestFreq);
            currentNote = noteNames[bestFreq];
            displayResult();
        }
    }

    void displayResult() {
        std::cout << "\rНота: " << currentNote
                  << "  Частота: " << currentFreq << " Гц"
                  << "  Отклонение: " << std::showpos << currentCents << " центов"
                  << std::noshowpos << std::flush;
    }

public:
    GuitarTuner() : stream(nullptr), currentFreq(0), currentCents(0), running(false) {
        // Инициализация строя
        std::vector<double> standard = {82.41, 110.00, 146.83, 196.00, 246.94, 329.63};
        tuning = standard;
        noteNames = {
            {82.41, "E2"}, {110.00, "A2"}, {146.83, "D3"},
            {196.00, "G3"}, {246.94, "B3"}, {329.63, "E4"}
        };
    }

    bool start() {
        PaError err = Pa_Initialize();
        if (err != paNoError) return false;

        err = Pa_OpenDefaultStream(&stream, 1, 0, paFloat32, SAMPLE_RATE,
                                    FRAMES_PER_BUFFER, paCallback, this);
        if (err != paNoError) return false;

        running = true;
        err = Pa_StartStream(stream);
        if (err != paNoError) return false;
        return true;
    }

    void stop() {
        running = false;
        if (stream) {
            Pa_StopStream(stream);
            Pa_CloseStream(stream);
            stream = nullptr;
        }
        Pa_Terminate();
        std::cout << "\nТюнер остановлен." << std::endl;
    }

    void run() {
        std::cout << "🎸 GuitarTuner Pro — C++ Edition" << std::endl;
        std::cout << "Нажмите Ctrl+C для выхода." << std::endl;
        if (start()) {
            std::cout << "Микрофон активен. Настраивайте инструмент..." << std::endl;
            while (running) {
                // Основной цикл
            }
        } else {
            std::cout << "Ошибка запуска микрофона." << std::endl;
        }
    }
};

int main() {
    GuitarTuner tuner;
    tuner.run();
    return 0;
}
