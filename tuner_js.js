// tuner_js.js — тюнер для гитары с автоопределением нот на JavaScript (Web Audio API)

class GuitarTuner {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.source = null;
        this.running = false;
        this.freq = 0;
        this.cents = 0;
        this.note = '--';
        this.tuning = [82.41, 110.00, 146.83, 196.00, 246.94, 329.63];
        this.noteNames = {
            82.41: 'E2', 110.00: 'A2', 146.83: 'D3',
            196.00: 'G3', 246.94: 'B3', 329.63: 'E4'
        };
        this.animationId = null;
    }

    async init() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.source = this.audioContext.createMediaStreamSource(stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;
            this.source.connect(this.analyser);
            return true;
        } catch (err) {
            console.error('Ошибка доступа к микрофону:', err);
            return false;
        }
    }

    detectPitch() {
        const dataArray = new Float32Array(this.analyser.fftSize);
        this.analyser.getFloatTimeDomainData(dataArray);

        // Автокорреляция
        let maxCorr = 0;
        let maxLag = 0;
        const half = dataArray.length / 2;
        for (let lag = 20; lag < half; lag++) {
            let corr = 0;
            for (let i = 0; i < dataArray.length - lag; i++) {
                corr += dataArray[i] * dataArray[i + lag];
            }
            if (corr > maxCorr) {
                maxCorr = corr;
                maxLag = lag;
            }
        }
        if (maxLag > 0 && maxCorr > 0.1) {
            return this.audioContext.sampleRate / maxLag;
        }
        return 0;
    }

    findNote(freq) {
        if (freq < 30 || freq > 1000) return;
        let bestFreq = 0;
        let bestDiff = Infinity;
        for (const target of this.tuning) {
            const diff = Math.abs(freq - target);
            if (diff < bestDiff) {
                bestDiff = diff;
                bestFreq = target;
            }
        }
        if (bestFreq > 0) {
            this.freq = bestFreq;
            this.cents = 1200 * Math.log2(freq / bestFreq);
            this.note = this.noteNames[bestFreq] || '?';
            this.updateUI();
        }
    }

    updateUI() {
        const noteEl = document.getElementById('note');
        const freqEl = document.getElementById('freq');
        const centsEl = document.getElementById('cents');
        const statusEl = document.getElementById('status');
        const progressEl = document.getElementById('progress');

        if (noteEl) noteEl.textContent = `Нота: ${this.note}`;
        if (freqEl) freqEl.textContent = `Частота: ${this.freq.toFixed(1)} Гц`;
        if (centsEl) {
            const sign = this.cents > 0 ? '+' : '';
            centsEl.textContent = `Отклонение: ${sign}${this.cents.toFixed(1)} центов`;
        }
        if (progressEl) {
            progressEl.value = Math.max(-50, Math.min(50, this.cents));
            progressEl.style.background = Math.abs(this.cents) < 2 ? 'green' :
                                         Math.abs(this.cents) < 10 ? 'orange' : 'red';
        }
        if (statusEl) {
            if (Math.abs(this.cents) < 2) {
                statusEl.textContent = '✅ В строю!';
                statusEl.style.color = 'green';
            } else if (Math.abs(this.cents) < 10) {
                statusEl.textContent = '🟡 Близко';
                statusEl.style.color = 'orange';
            } else {
                statusEl.textContent = '🔴 Далеко';
                statusEl.style.color = 'red';
            }
        }
    }

    start() {
        if (this.running) return;
        this.running = true;
        this.animate();
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
    }

    stop() {
        this.running = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        document.getElementById('status').textContent = 'Остановлено';
    }

    animate() {
        if (!this.running) return;
        const freq = this.detectPitch();
        if (freq > 0) {
            this.findNote(freq);
        }
        this.animationId = requestAnimationFrame(() => this.animate());
    }
}

// Создание HTML интерфейса (для браузера)
document.addEventListener('DOMContentLoaded', async () => {
    const container = document.createElement('div');
    container.style.padding = '20px';
    container.style.fontFamily = 'Arial, sans-serif';
    container.innerHTML = `
        <h1>🎸 GuitarTuner Pro — JavaScript</h1>
        <div id="status">Инициализация...</div>
        <div id="note" style="font-size: 28px; font-weight: bold;">Нота: --</div>
        <div id="freq" style="font-size: 18px;">Частота: -- Гц</div>
        <div id="cents" style="font-size: 18px;">Отклонение: -- центов</div>
        <input type="range" id="progress" min="-50" max="50" value="0" disabled style="width: 100%; height: 30px;">
        <div style="display: flex; gap: 10px; margin-top: 10px;">
            <button id="startBtn" style="padding: 10px 20px; background: green; color: white; border: none; border-radius: 5px;">▶ Запустить</button>
            <button id="stopBtn" style="padding: 10px 20px; background: red; color: white; border: none; border-radius: 5px;" disabled>■ Остановить</button>
        </div>
        <div style="margin-top: 10px; font-size: 12px; color: gray;">Нажмите "Запустить" и разрешите доступ к микрофону.</div>
    `;
    document.body.appendChild(container);

    const tuner = new GuitarTuner();
    const initialized = await tuner.init();
    if (!initialized) {
        document.getElementById('status').textContent = '❌ Ошибка доступа к микрофону';
        return;
    }
    document.getElementById('status').textContent = '✅ Микрофон готов';

    document.getElementById('startBtn').addEventListener('click', () => tuner.start());
    document.getElementById('stopBtn').addEventListener('click', () => tuner.stop());
});

// Для Node.js: вывод сообщения
if (typeof window === 'undefined') {
    console.log('🎸 GuitarTuner Pro — JavaScript Edition');
    console.log('Для работы требуется браузер с поддержкой Web Audio API.');
}
