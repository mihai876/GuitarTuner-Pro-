// tuner_go.go — тюнер для гитары с автоопределением нот на Go (PortAudio)

package main

import (
	"fmt"
	"math"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gordonklaus/portaudio"
)

type GuitarTuner struct {
	stream      *portaudio.Stream
	buffer      []float32
	running     bool
	currentFreq float64
	currentCents float64
	currentNote string
	tuning      []float64
	noteNames   map[float64]string
}

func NewGuitarTuner() *GuitarTuner {
	tuner := &GuitarTuner{
		tuning:    []float64{82.41, 110.00, 146.83, 196.00, 246.94, 329.63},
		noteNames: make(map[float64]string),
	}
	tuner.noteNames[82.41] = "E2"
	tuner.noteNames[110.00] = "A2"
	tuner.noteNames[146.83] = "D3"
	tuner.noteNames[196.00] = "G3"
	tuner.noteNames[246.94] = "B3"
	tuner.noteNames[329.63] = "E4"
	return tuner
}

func (t *GuitarTuner) start() error {
	if err := portaudio.Initialize(); err != nil {
		return err
	}
	buffer := make([]float32, 4096)
	stream, err := portaudio.OpenDefaultStream(1, 0, 44100, len(buffer), t.processAudio)
	if err != nil {
		return err
	}
	t.stream = stream
	t.buffer = buffer
	t.running = true
	if err := stream.Start(); err != nil {
		return err
	}
	return nil
}

func (t *GuitarTuner) processAudio(in []float32) {
	if !t.running {
		return
	}
	// Автокорреляция для определения частоты
	if len(in) < 256 {
		return
	}
	maxCorr := 0.0
	maxLag := 0
	for lag := 20; lag < len(in)/2; lag++ {
		corr := 0.0
		for i := 0; i < len(in)-lag; i++ {
			corr += float64(in[i] * in[i+lag])
		}
		if corr > maxCorr {
			maxCorr = corr
			maxLag = lag
		}
	}
	if maxLag > 0 && maxCorr > 0.1 {
		freq := 44100.0 / float64(maxLag)
		if freq > 30 && freq < 1000 {
			t.findNote(freq)
		}
	}
}

func (t *GuitarTuner) findNote(freq float64) {
	bestFreq := 0.0
	bestDiff := 1e9
	for _, target := range t.tuning {
		diff := math.Abs(freq - target)
		if diff < bestDiff {
			bestDiff = diff
			bestFreq = target
		}
	}
	if bestFreq > 0 {
		t.currentFreq = bestFreq
		t.currentCents = 1200 * math.Log2(freq/bestFreq)
		t.currentNote = t.noteNames[bestFreq]
		t.display()
	}
}

func (t *GuitarTuner) display() {
	fmt.Printf("\rНота: %s  Частота: %.1f Гц  Отклонение: %+.1f центов",
		t.currentNote, t.currentFreq, t.currentCents)
}

func (t *GuitarTuner) stop() {
	if t.stream != nil {
		t.stream.Stop()
		t.stream.Close()
	}
	t.running = false
	portaudio.Terminate()
}

func main() {
	tuner := NewGuitarTuner()
	fmt.Println("🎸 GuitarTuner Pro — Go Edition")
	fmt.Println("Нажмите Ctrl+C для выхода.")

	if err := tuner.start(); err != nil {
		fmt.Println("Ошибка:", err)
		return
	}
	fmt.Println("Микрофон активен. Настраивайте инструмент...")

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	tuner.stop()
	fmt.Println("\nТюнер остановлен.")
}
