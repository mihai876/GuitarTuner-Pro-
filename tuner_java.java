// tuner_java.java — тюнер для гитары с автоопределением нот на Java (JavaSound)

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import javax.sound.sampled.*;
import java.util.*;

public class GuitarTuner extends JFrame {
    private static final int SAMPLE_RATE = 44100;
    private static final int SAMPLE_SIZE = 1024;
    private TargetDataLine line;
    private boolean running = false;
    private double currentFreq = 0;
    private double currentCents = 0;
    private String currentNote = "--";
    private Map<Double, String> noteNames = new HashMap<>();
    private double[] tuning = {82.41, 110.00, 146.83, 196.00, 246.94, 329.63};

    private JLabel noteLabel, freqLabel, statusLabel;
    private JProgressBar progressBar;
    private JButton startBtn, stopBtn;

    public GuitarTuner() {
        setTitle("🎸 GuitarTuner Pro — Java");
        setSize(500, 400);
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setLayout(new BorderLayout(10, 10));

        noteNames.put(82.41, "E2");
        noteNames.put(110.00, "A2");
        noteNames.put(146.83, "D3");
        noteNames.put(196.00, "G3");
        noteNames.put(246.94, "B3");
        noteNames.put(329.63, "E4");

        createUI();
        pack();
        setLocationRelativeTo(null);
    }

    private void createUI() {
        JPanel mainPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.fill = GridBagConstraints.HORIZONTAL;

        // Заголовок
        JLabel title = new JLabel("🎸 GuitarTuner Pro — Java");
        title.setFont(new Font("Arial", Font.BOLD, 18));
        gbc.gridx = 0; gbc.gridy = 0; gbc.gridwidth = 2;
        mainPanel.add(title, gbc);

        // Нота и частота
        noteLabel = new JLabel("Нота: --");
        noteLabel.setFont(new Font("Arial", Font.BOLD, 24));
        gbc.gridy = 1; gbc.gridwidth = 1;
        mainPanel.add(noteLabel, gbc);

        freqLabel = new JLabel("Частота: -- Гц");
        freqLabel.setFont(new Font("Arial", Font.PLAIN, 14));
        gbc.gridx = 1;
        mainPanel.add(freqLabel, gbc);

        // Прогресс-бар для индикации отклонения
        progressBar = new JProgressBar(-50, 50);
        progressBar.setValue(0);
        progressBar.setStringPainted(true);
        progressBar.setForeground(Color.GREEN);
        gbc.gridx = 0; gbc.gridy = 2; gbc.gridwidth = 2;
        gbc.fill = GridBagConstraints.HORIZONTAL;
        mainPanel.add(progressBar, gbc);

        // Статус
        statusLabel = new JLabel("Статус: Ожидание...");
        gbc.gridy = 3;
        mainPanel.add(statusLabel, gbc);

        // Кнопки
        JPanel btnPanel = new JPanel(new FlowLayout());
        startBtn = new JButton("▶ Запустить");
        startBtn.setBackground(Color.GREEN);
        startBtn.addActionListener(e -> start());
        btnPanel.add(startBtn);

        stopBtn = new JButton("■ Остановить");
        stopBtn.setBackground(Color.RED);
        stopBtn.setEnabled(false);
        stopBtn.addActionListener(e -> stop());
        btnPanel.add(stopBtn);

        gbc.gridy = 4;
        mainPanel.add(btnPanel, gbc);

        add(mainPanel, BorderLayout.CENTER);
    }

    private void start() {
        try {
            AudioFormat format = new AudioFormat(SAMPLE_RATE, 16, 1, true, true);
            DataLine.Info info = new DataLine.Info(TargetDataLine.class, format);
            line = (TargetDataLine) AudioSystem.getLine(info);
            line.open(format);
            line.start();
            running = true;
            startBtn.setEnabled(false);
            stopBtn.setEnabled(true);
            statusLabel.setText("Слушаем...");
            new Thread(() -> {
                byte[] buffer = new byte[SAMPLE_SIZE * 2];
                while (running) {
                    int bytesRead = line.read(buffer, 0, buffer.length);
                    if (bytesRead > 0) {
                        double freq = detectPitch(buffer);
                        if (freq > 0) {
                            findNote(freq);
                        }
                    }
                }
            }).start();
        } catch (Exception e) {
            JOptionPane.showMessageDialog(this, "Ошибка: " + e.getMessage());
        }
    }

    private void stop() {
        running = false;
        if (line != null) {
            line.stop();
            line.close();
            line = null;
        }
        startBtn.setEnabled(true);
        stopBtn.setEnabled(false);
        statusLabel.setText("Остановлено");
        progressBar.setValue(0);
        noteLabel.setText("Нота: --");
        freqLabel.setText("Частота: -- Гц");
    }

    private double detectPitch(byte[] data) {
        // Преобразование byte в double
        double[] signal = new double[data.length / 2];
        for (int i = 0; i < signal.length; i++) {
            signal[i] = (data[i*2] | (data[i*2+1] << 8)) / 32768.0;
        }

        // Автокорреляция
        double maxCorr = 0;
        int maxLag = 0;
        for (int lag = 20; lag < signal.length / 2; lag++) {
            double corr = 0;
            for (int i = 0; i < signal.length - lag; i++) {
                corr += signal[i] * signal[i + lag];
            }
            if (corr > maxCorr) {
                maxCorr = corr;
                maxLag = lag;
            }
        }
        if (maxLag > 0 && maxCorr > 0.1) {
            return (double)SAMPLE_RATE / maxLag;
        }
        return 0;
    }

    private void findNote(double freq) {
        double bestFreq = 0;
        double bestDiff = 1e9;
        for (double target : tuning) {
            double diff = Math.abs(freq - target);
            if (diff < bestDiff) {
                bestDiff = diff;
                bestFreq = target;
            }
        }
        if (bestFreq > 0) {
            currentFreq = bestFreq;
            currentCents = 1200 * (Math.log(freq / bestFreq) / Math.log(2));
            currentNote = noteNames.getOrDefault(bestFreq, "?");

            SwingUtilities.invokeLater(() -> {
                noteLabel.setText("Нота: " + currentNote);
                freqLabel.setText(String.format("Частота: %.1f Гц", freq));
                progressBar.setValue((int)currentCents);
                if (Math.abs(currentCents) < 2) {
                    progressBar.setForeground(Color.GREEN);
                    statusLabel.setText("✅ В строю!");
                } else if (Math.abs(currentCents) < 10) {
                    progressBar.setForeground(Color.ORANGE);
                    statusLabel.setText("🟡 Близко");
                } else {
                    progressBar.setForeground(Color.RED);
                    statusLabel.setText("🔴 Далеко");
                }
            });
        }
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new GuitarTuner().setVisible(true));
    }
}
