// tuner_rs.rs — тюнер для гитары с автоопределением нот на Rust (cpal)

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::f64::consts::PI;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicBool, Ordering};

struct GuitarTuner {
    running: Arc<AtomicBool>,
    freq: Arc<Mutex<f64>>,
    cents: Arc<Mutex<f64>>,
    note: Arc<Mutex<String>>,
}

impl GuitarTuner {
    fn new() -> Self {
        GuitarTuner {
            running: Arc::new(AtomicBool::new(false)),
            freq: Arc::new(Mutex::new(0.0)),
            cents: Arc::new(Mutex::new(0.0)),
            note: Arc::new(Mutex::new("--".to_string())),
        }
    }

    fn start(&self) -> Result<(), Box<dyn std::error::Error>> {
        let host = cpal::default_host();
        let device = host.default_input_device().expect("No input device");
        let config = device.default_input_config().unwrap();
        let sample_rate = config.sample_rate().0;
        self.running.store(true, Ordering::SeqCst);

        let running = self.running.clone();
        let freq_arc = self.freq.clone();
        let cents_arc = self.cents.clone();
        let note_arc = self.note.clone();
        let tuning = vec![82.41, 110.00, 146.83, 196.00, 246.94, 329.63];
        let note_names: HashMap<f64, String> = vec![
            (82.41, "E2".to_string()), (110.00, "A2".to_string()),
            (146.83, "D3".to_string()), (196.00, "G3".to_string()),
            (246.94, "B3".to_string()), (329.63, "E4".to_string())
        ].into_iter().collect();

        let stream = device.build_input_stream(
            &config.into(),
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                if !running.load(Ordering::SeqCst) { return; }
                // Анализ частоты (автокорреляция)
                if data.len() < 256 { return; }
                let mut max_corr = 0.0;
                let mut max_lag = 0;
                let half = data.len() / 2;
                for lag in 20..half {
                    let mut corr = 0.0;
                    for i in 0..data.len() - lag {
                        corr += data[i] as f64 * data[i + lag] as f64;
                    }
                    if corr > max_corr {
                        max_corr = corr;
                        max_lag = lag;
                    }
                }
                if max_lag > 0 && max_corr > 0.1 {
                    let freq = sample_rate as f64 / max_lag as f64;
                    if freq > 30.0 && freq < 1000.0 {
                        // Находим ближайшую ноту
                        let mut best_freq = 0.0;
                        let mut best_diff = 1e9;
                        for &target in &tuning {
                            let diff = (freq - target).abs();
                            if diff < best_diff {
                                best_diff = diff;
                                best_freq = target;
                            }
                        }
                        if best_freq > 0.0 {
                            let cents = 1200.0 * (freq / best_freq).log2();
                            let note = note_names.get(&best_freq).unwrap_or(&"--".to_string()).clone();
                            *freq_arc.lock().unwrap() = best_freq;
                            *cents_arc.lock().unwrap() = cents;
                            *note_arc.lock().unwrap() = note;
                            // Вывод в консоль
                            print!("\rНота: {}  Частота: {:.1} Гц  Отклонение: {:+.1} центов",
                                   note, best_freq, cents);
                        }
                    }
                }
            },
            move |err| {
                eprintln!("Ошибка: {}", err);
            },
        )?;
        stream.play()?;
        println!("🎸 GuitarTuner Pro — Rust Edition");
        println!("Микрофон активен. Нажмите Ctrl+C для выхода.");
        Ok(())
    }

    fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
        println!("\nТюнер остановлен.");
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let tuner = GuitarTuner::new();
    tuner.start()?;
    let mut input = String::new();
    std::io::stdin().read_line(&mut input)?;
    tuner.stop();
    Ok(())
}
