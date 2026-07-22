# tuner_python.py — тюнер для гитары с автоопределением нот на Python

import pyaudio
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import math
import time
import json
import os

class GuitarTuner:
    def __init__(self, root):
        self.root = root
        self.root.title("🎸 GuitarTuner Pro — Python")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        # Параметры аудио
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 4096
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.running = False

        # Настройки тюнера
        self.sample_rate = 44100
        self.notes = ['E', 'A', 'D', 'G', 'B', 'E']
        self.frequencies = [82.41, 110.00, 146.83, 196.00, 246.94, 329.63]  # стандартный строй
        self.note_names = {
            82.41: 'E2', 110.00: 'A2', 146.83: 'D3',
            196.00: 'G3', 246.94: 'B3', 329.63: 'E4'
        }
        self.current_note = None
        self.current_freq = 0.0
        self.current_cents = 0
        self.tunings = {
            'Стандартный': [82.41, 110.00, 146.83, 196.00, 246.94, 329.63],
            'Drop D': [73.42, 110.00, 146.83, 196.00, 246.94, 329.63],
            'Open G': [98.00, 123.47, 146.83, 196.00, 246.94, 392.00],
            'DADGAD': [73.42, 110.00, 146.83, 196.00, 246.94, 392.00],
            'Bass (4 str)': [41.20, 55.00, 73.42, 98.00]
        }
        self.tuning = self.tunings['Стандартный']

        self.config_file = "tuner_config.json"
        self.load_config()

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # Заголовок
        title = tk.Label(self.root, text="🎸 GuitarTuner Pro", font=("Arial", 18))
        title.pack(pady=10)

        # Статус микрофона
        self.mic_status = tk.Label(self.root, text="Микрофон: не активен", font=("Arial", 12))
        self.mic_status.pack()

        # Нота и частота
        self.note_label = tk.Label(self.root, text="Нота: --", font=("Arial", 24, "bold"))
        self.note_label.pack(pady=5)
        self.freq_label = tk.Label(self.root, text="Частота: -- Гц", font=("Arial", 14))
        self.freq_label.pack()

        # Индикатор отклонения (Canvas)
        self.canvas = tk.Canvas(self.root, width=400, height=80, bg="white")
        self.canvas.pack(pady=10)
        self.canvas.create_line(50, 40, 350, 40, fill="gray", width=2)
        self.canvas.create_line(200, 30, 200, 50, fill="black", width=2)
        # Шкала
        for i in range(-50, 51, 25):
            x = 200 + i * 3
            self.canvas.create_line(x, 35, x, 45, fill="gray")
            self.canvas.create_text(x, 55, text=str(i), font=("Arial", 8))

        self.pointer = self.canvas.create_rectangle(195, 30, 205, 50, fill="blue", outline="")

        # Статус
        self.status_label = tk.Label(self.root, text="Статус: Ожидание...", font=("Arial", 12))
        self.status_label.pack(pady=5)

        # Кнопки управления
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        self.start_btn = tk.Button(btn_frame, text="▶ Запустить", command=self.start,
                                   bg="green", fg="white", font=("Arial", 12), width=12)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = tk.Button(btn_frame, text="■ Остановить", command=self.stop,
                                  bg="red", fg="white", font=("Arial", 12), width=12, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Настройки
        settings_frame = tk.Frame(self.root)
        settings_frame.pack(pady=5)
        tk.Label(settings_frame, text="Строй:").pack(side=tk.LEFT, padx=5)
        self.tuning_var = tk.StringVar(value="Стандартный")
        tuning_combo = ttk.Combobox(settings_frame, textvariable=self.tuning_var,
                                    values=list(self.tunings.keys()), width=15, state="readonly")
        tuning_combo.pack(side=tk.LEFT, padx=5)
        tuning_combo.bind("<<ComboboxSelected>>", self.on_tuning_change)

        # Калибровка
        self.ref_freq_var = tk.StringVar(value="440")
        ref_frame = tk.Frame(self.root)
        ref_frame.pack(pady=5)
        tk.Label(ref_frame, text="Эталонная частота:").pack(side=tk.LEFT, padx=5)
        ref_entry = tk.Entry(ref_frame, textvariable=self.ref_freq_var, width=8)
        ref_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(ref_frame, text="Применить", command=self.apply_ref_freq).pack(side=tk.LEFT, padx=5)

    def on_tuning_change(self, event):
        tuning_name = self.tuning_var.get()
        self.tuning = self.tunings[tuning_name]
        self.save_config()

    def apply_ref_freq(self):
        try:
            ref = float(self.ref_freq_var.get())
            if ref > 0:
                # Пересчёт частот нот с учётом эталонной
                ratio = ref / 440.0
                self.tuning = [f * ratio for f in self.tunings['Стандартный']]
                self.note_names = {
                    self.tuning[0]: 'E2',
                    self.tuning[1]: 'A2',
                    self.tuning[2]: 'D3',
                    self.tuning[3]: 'G3',
                    self.tuning[4]: 'B3',
                    self.tuning[5]: 'E4'
                }
                self.status_label.config(text=f"Калибровка применена (A = {ref:.1f} Гц)")
                self.save_config()
        except:
            pass

    def detect_pitch(self, data):
        # Преобразование данных в массив float
        audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        audio_data = audio_data / np.iinfo(np.int16).max

        # Автокорреляция для определения частоты
        correlation = np.correlate(audio_data, audio_data, mode='full')
        correlation = correlation[len(correlation)//2:]

        # Поиск пика
        min_lag = int(0.8 * self.sample_rate / 500)  # для частот до 500 Гц
        max_lag = int(0.8 * self.sample_rate / 60)   # для частот от 60 Гц
        if max_lag > len(correlation):
            max_lag = len(correlation) - 1
        if min_lag >= len(correlation):
            return 0.0

        # Усреднение для подавления шума
        try:
            peak = np.argmax(correlation[min_lag:max_lag]) + min_lag
            if peak > 0:
                freq = self.sample_rate / peak
                return freq
        except:
            pass
        return 0.0

    def find_note(self, freq):
        if freq < 30 or freq > 1000:
            return None, 0, 0

        # Находим ближайшую ноту из текущего строя
        best_freq = 0
        best_diff = float('inf')
        for target_freq in self.tuning:
            diff = abs(freq - target_freq)
            if diff < best_diff:
                best_diff = diff
                best_freq = target_freq

        # Вычисляем отклонение в центах
        cents = 1200 * math.log2(freq / best_freq) if best_freq > 0 else 0
        return best_freq, cents, self.note_names.get(best_freq, "?")

    def update_display(self, freq, note_name, cents):
        if note_name:
            self.note_label.config(text=f"Нота: {note_name}")
            self.freq_label.config(text=f"Частота: {freq:.1f} Гц")
            # Обновление указателя
            x = 200 + cents * 3
            if x < 50:
                x = 50
            elif x > 350:
                x = 350
            self.canvas.coords(self.pointer, x-5, 30, x+5, 50)

            # Цветовая индикация
            if abs(cents) < 2:
                self.status_label.config(text="✅ В строю!", fg="green")
                self.canvas.itemconfig(self.pointer, fill="green")
            elif abs(cents) < 10:
                self.status_label.config(text="🟡 Близко", fg="orange")
                self.canvas.itemconfig(self.pointer, fill="orange")
            else:
                self.status_label.config(text="🔴 Далеко", fg="red")
                self.canvas.itemconfig(self.pointer, fill="red")
        else:
            self.note_label.config(text="Нота: --")
            self.freq_label.config(text="Частота: -- Гц")
            self.status_label.config(text="Ожидание сигнала...", fg="black")
            self.canvas.coords(self.pointer, 195, 30, 205, 50)
            self.canvas.itemconfig(self.pointer, fill="blue")

    def audio_callback(self, in_data, frame_count, time_info, status):
        if self.running:
            freq = self.detect_pitch(in_data)
            if freq > 0:
                note_freq, cents, note_name = self.find_note(freq)
                self.root.after(0, lambda: self.update_display(note_freq, note_name, cents))
        return (in_data, pyaudio.paContinue)

    def start(self):
        if self.running:
            return
        try:
            self.stream = self.audio.open(format=self.FORMAT,
                                          channels=self.CHANNELS,
                                          rate=self.RATE,
                                          input=True,
                                          frames_per_buffer=self.CHUNK,
                                          stream_callback=self.audio_callback)
            self.running = True
            self.stream.start_stream()
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.mic_status.config(text="Микрофон: активен", fg="green")
            self.status_label.config(text="Слушаем...", fg="black")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить микрофон:\n{e}")

    def stop(self):
        if self.running:
            self.running = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.mic_status.config(text="Микрофон: не активен", fg="red")
            self.status_label.config(text="Остановлено", fg="black")

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.ref_freq_var.set(str(data.get('ref_freq', 440)))
                tuning_name = data.get('tuning', 'Стандартный')
                if tuning_name in self.tunings:
                    self.tuning_var.set(tuning_name)
                    self.tuning = self.tunings[tuning_name]

    def save_config(self):
        data = {
            'ref_freq': float(self.ref_freq_var.get()),
            'tuning': self.tuning_var.get()
        }
        with open(self.config_file, 'w') as f:
            json.dump(data, f)

    def on_close(self):
        self.stop()
        self.audio.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GuitarTuner(root)
    root.mainloop()
