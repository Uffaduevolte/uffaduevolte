import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import wave

def select_file():
    """Apri finestra di dialogo per selezionare un file .wav."""
    file_path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if file_path:
        visualize_waveform(file_path)

def visualize_waveform(file_path):
    """Carica il file .wav e rappresenta la forma d'onda con divisioni di tempo basate sui BPM."""
    # Leggere i dati dal file .wav
    with wave.open(file_path, 'r') as wav_file:
        n_frames = wav_file.getnframes()
        n_channels = wav_file.getnchannels()
        framerate = wav_file.getframerate()
        duration = n_frames / float(framerate)
        frames = wav_file.readframes(n_frames)
        waveform = np.frombuffer(frames, dtype=np.int16)
        if n_channels == 2:
            waveform = waveform[::2]  # Utilizza solo un canale per l'analisi

    # Creare il grafico
    fig, ax = plt.subplots(figsize=(8, 4))
    time = np.linspace(0, duration, num=len(waveform))
    ax.plot(time, waveform, label="Forma d'onda")

    # Aggiungere linee verticali per i BPM
    try:
        bpm = int(bpm_entry.get())
        interval = 60 / bpm  # Intervallo tra le linee verticali in secondi
        for t in np.arange(0, duration, interval):
            ax.axvline(x=t, color='red', linestyle='--', alpha=0.7, label='BPM Marker' if t == 0 else "")

        ax.set_title("Forma d'onda con marker BPM")
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Ampiezza")
        ax.legend()
    except ValueError:
        tk.messagebox.showerror("Errore", "Inserisci un valore BPM valido!")

    # Visualizzare il grafico in Tkinter
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack()
    canvas.draw()

# Creare l'interfaccia grafica con Tkinter
root = tk.Tk()
root.title("Visualizzatore di Forma d'Onda")

frame = tk.Frame(root)
frame.pack()

select_button = tk.Button(frame, text="Seleziona file WAV", command=select_file)
select_button.pack()

bpm_label = tk.Label(frame, text="BPM:")
bpm_label.pack(side=tk.LEFT)

bpm_entry = tk.Entry(frame)
bpm_entry.pack(side=tk.LEFT)

root.mainloop()
