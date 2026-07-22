// tuner_cs.cs — тюнер для гитары с автоопределением нот на C# (NAudio + WPF)

using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using NAudio.Wave;
using NAudio.Dsp;

namespace GuitarTunerWPF
{
    public partial class MainWindow : Window
    {
        private WaveInEvent waveIn;
        private BufferedWaveProvider waveProvider;
        private bool running = false;
        private double currentFreq = 0;
        private double currentCents = 0;
        private string currentNote = "--";
        private double[] tuning = {82.41, 110.00, 146.83, 196.00, 246.94, 329.63};
        private Dictionary<double, string> noteNames = new Dictionary<double, string>();

        private Label noteLabel, freqLabel, statusLabel;
        private ProgressBar progressBar;
        private Button startBtn, stopBtn;

        public MainWindow()
        {
            InitializeComponent();
            noteNames.Add(82.41, "E2");
            noteNames.Add(110.00, "A2");
            noteNames.Add(146.83, "D3");
            noteNames.Add(196.00, "G3");
            noteNames.Add(246.94, "B3");
            noteNames.Add(329.63, "E4");
            CreateUI();
        }

        private void CreateUI()
        {
            Title = "🎸 GuitarTuner Pro — C#";
            Width = 500;
            Height = 450;
            var grid = new Grid();
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            int row = 0;
            // Заголовок
            var titleLabel = new Label { Content = "🎸 GuitarTuner Pro — C#", FontSize = 18, FontWeight = FontWeights.Bold, HorizontalAlignment = HorizontalAlignment.Center };
            Grid.SetRow(titleLabel, row++);
            grid.Children.Add(titleLabel);

            // Нота
            noteLabel = new Label { Content = "Нота: --", FontSize = 24, FontWeight = FontWeights.Bold, HorizontalAlignment = HorizontalAlignment.Center };
            Grid.SetRow(noteLabel, row++);
            grid.Children.Add(noteLabel);

            // Частота
            freqLabel = new Label { Content = "Частота: -- Гц", FontSize = 14, HorizontalAlignment = HorizontalAlignment.Center };
            Grid.SetRow(freqLabel, row++);
            grid.Children.Add(freqLabel);

            // Прогресс-бар
            progressBar = new ProgressBar { Minimum = -50, Maximum = 50, Value = 0, Height = 30, Foreground = Brushes.Green };
            Grid.SetRow(progressBar, row++);
            grid.Children.Add(progressBar);

            // Статус
            statusLabel = new Label { Content = "Статус: Ожидание...", HorizontalAlignment = HorizontalAlignment.Center };
            Grid.SetRow(statusLabel, row++);
            grid.Children.Add(statusLabel);

            // Кнопки
            var btnPanel = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Center };
            startBtn = new Button { Content = "▶ Запустить", Width = 100, Background = Brushes.Green, Foreground = Brushes.White };
            startBtn.Click += (s, e) => Start();
            btnPanel.Children.Add(startBtn);
            stopBtn = new Button { Content = "■ Остановить", Width = 100, Background = Brushes.Red, Foreground = Brushes.White };
            stopBtn.IsEnabled = false;
            stopBtn.Click += (s, e) => Stop();
            btnPanel.Children.Add(stopBtn);
            Grid.SetRow(btnPanel, row++);
            grid.Children.Add(btnPanel);

            Content = grid;
        }

        private void Start()
        {
            try
            {
                waveIn = new WaveInEvent();
                waveIn.DeviceNumber = 0;
                waveIn.WaveFormat = new WaveFormat(44100, 16, 1);
                waveIn.DataAvailable += OnDataAvailable;
                waveIn.StartRecording();
                running = true;
                startBtn.IsEnabled = false;
                stopBtn.IsEnabled = true;
                statusLabel.Content = "Слушаем...";
                statusLabel.Foreground = Brushes.Green;
            }
            catch (Exception ex)
            {
                MessageBox.Show("Ошибка: " + ex.Message);
            }
        }

        private void Stop()
        {
            if (waveIn != null)
            {
                waveIn.StopRecording();
                waveIn.Dispose();
                waveIn = null;
            }
            running = false;
            startBtn.IsEnabled = true;
            stopBtn.IsEnabled = false;
            statusLabel.Content = "Остановлено";
            statusLabel.Foreground = Brushes.Black;
            progressBar.Value = 0;
            noteLabel.Content = "Нота: --";
            freqLabel.Content = "Частота: -- Гц";
        }

        private void OnDataAvailable(object sender, WaveInEventArgs e)
        {
            if (!running) return;
            // Конвертация байтов в float
            float[] samples = new float[e.BytesRecorded / 2];
            for (int i = 0; i < samples.Length; i++)
            {
                samples[i] = BitConverter.ToInt16(e.Buffer, i * 2) / 32768.0f;
            }

            // Простой детектор частоты через автокорреляцию
            double freq = DetectPitch(samples);
            if (freq > 0)
            {
                FindNote(freq);
            }
        }

        private double DetectPitch(float[] signal)
        {
            if (signal.Length < 256) return 0;
            double maxCorr = 0;
            int maxLag = 0;
            for (int lag = 20; lag < signal.Length / 2; lag++)
            {
                double corr = 0;
                for (int i = 0; i < signal.Length - lag; i++)
                {
                    corr += signal[i] * signal[i + lag];
                }
                if (corr > maxCorr)
                {
                    maxCorr = corr;
                    maxLag = lag;
                }
            }
            if (maxLag > 0 && maxCorr > 0.1)
            {
                return 44100.0 / maxLag;
            }
            return 0;
        }

        private void FindNote(double freq)
        {
            double bestFreq = 0;
            double bestDiff = 1e9;
            foreach (var target in tuning)
            {
                double diff = Math.Abs(freq - target);
                if (diff < bestDiff)
                {
                    bestDiff = diff;
                    bestFreq = target;
                }
            }
            if (bestFreq > 0)
            {
                currentFreq = bestFreq;
                currentCents = 1200 * Math.Log2(freq / bestFreq);
                currentNote = noteNames.ContainsKey(bestFreq) ? noteNames[bestFreq] : "?";

                Dispatcher.Invoke(() =>
                {
                    noteLabel.Content = $"Нота: {currentNote}";
                    freqLabel.Content = $"Частота: {freq:F1} Гц";
                    progressBar.Value = currentCents;
                    if (Math.Abs(currentCents) < 2)
                    {
                        progressBar.Foreground = Brushes.Green;
                        statusLabel.Content = "✅ В строю!";
                        statusLabel.Foreground = Brushes.Green;
                    }
                    else if (Math.Abs(currentCents) < 10)
                    {
                        progressBar.Foreground = Brushes.Orange;
                        statusLabel.Content = "🟡 Близко";
                        statusLabel.Foreground = Brushes.Orange;
                    }
                    else
                    {
                        progressBar.Foreground = Brushes.Red;
                        statusLabel.Content = "🔴 Далеко";
                        statusLabel.Foreground = Brushes.Red;
                    }
                });
            }
        }

        [STAThread]
        public static void Main()
        {
            var app = new Application();
            app.Run(new MainWindow());
        }
    }
}
