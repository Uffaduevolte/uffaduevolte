import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import wave
import sounddevice as sd

# Variabili globali
canvas = None
selected_file = None
adjusted_audio = None
markers = []  # Posizioni dei marker
undo_stack = []  # Stack per undo
redo_stack = []  # Stack per redo
is_playing = False  # Stato del tasto Preview (True = Riproduzione attiva)
bpm = 120  # BPM iniziale (120 BPM di default)

def update_bpm(new_bpm):
    """Aggiorna il valore di BPM e ridisegna il grafico."""
    global bpm
    bpm = int(new_bpm)
    print(f"BPM aggiornato a: {bpm}")
    update_graph()

def calculate_beat_positions(framerate, duration, bpm):
    """Calcola le posizioni dei battiti in base al BPM."""
    beat_interval = 60 / bpm  # Intervallo tra i battiti in secondi
    num_beats = int(duration / beat_interval)
    return [i * beat_interval for i in range(num_beats)]

def update_graph():
    """Aggiorna il grafico con i battiti calcolati (linee verticali rosse)."""
    if not selected_file:
        return

    with wave.open(selected_file, 'r') as wav_file:
        n_frames = wav_file.getnframes()
        framerate = wav_file.getframerate()
        frames = wav_file.readframes(n_frames)
        waveform = np.frombuffer(frames, dtype=np.int16)
        time = np.linspace(0, n_frames / framerate, num=n_frames)

    duration = len(time) / framerate  # Durata totale dell'audio in secondi
    beat_positions = calculate_beat_positions(framerate, duration, bpm)

    ax = canvas.figure.axes[0]
    ax.clear()
    ax.set_facecolor('#333333')  # Sfondo grigio scuro
    ax.spines['top'].set_color('#333333')  # Cornice grigio scuro
    ax.spines['right'].set_color('#333333')
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')
    ax.plot(time, waveform, color='orange', label="Forma d'onda originale")

    # Disegna le linee verticali rosse per ogni battito
    for beat in beat_positions:
        ax.axvline(x=beat, color='red', linestyle='--', label='BPM Marker' if beat == beat_positions[0] else None)

    ax.legend()
    canvas.draw()

def select_file():
    """Carica un file WAV e visualizza la forma d'onda con i marker BPM."""
    global selected_file
    selected_file = ctk.filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if selected_file:
        update_graph()  # Aggiorna il grafico dopo aver caricato un file

def preview_file():
    """Riproduce o interrompe l'audio (originale o modificato)."""
    global is_playing  # Accedi alla variabile globale
    if is_playing:
        # Se è in riproduzione, ferma l'audio
        sd.stop()
        print("Riproduzione interrotta.")
        preview_button.configure(text="Preview")  # Modifica la caption del pulsante
        is_playing = False
    else:
        # Se non è in riproduzione, avvia l'audio
        if adjusted_audio is not None:
            print("Riproducendo audio rielaborato...")
            with wave.open(selected_file, 'r') as wav_file:
                framerate = wav_file.getframerate()
            sd.play(adjusted_audio, samplerate=framerate)
        elif selected_file:
            print("Riproducendo audio originale...")
            with wave.open(selected_file, 'r') as wav_file:
                framerate = wav_file.getframerate()
                frames = wav_file.readframes(wav_file.getnframes())
                waveform = np.frombuffer(frames, dtype=np.int16)
                sd.play(waveform, samplerate=framerate)
        preview_button.configure(text="Stop")  # Modifica la caption del pulsante
        is_playing = True

# Configurazione CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Creazione finestra principale
root = ctk.CTk()
root.title("Editor Audio")
root.geometry("1000x600")

main_frame = ctk.CTkFrame(root)
main_frame.pack(fill="both", expand=True, padx=20, pady=20)

control_frame = ctk.CTkFrame(main_frame)
control_frame.pack(side="left", fill="y", padx=20)

select_button = ctk.CTkButton(control_frame, text="Seleziona file WAV", command=select_file)
select_button.pack(pady=10)

preview_button = ctk.CTkButton(control_frame, text="Preview", command=preview_file)
preview_button.pack(pady=10)

bpm_label = ctk.CTkLabel(control_frame, text="BPM:")
bpm_label.pack(pady=5)

bpm_slider = ctk.CTkSlider(control_frame, from_=60, to=240, number_of_steps=180, command=update_bpm)
bpm_slider.set(bpm)  # Imposta il valore iniziale dello slider
bpm_slider.pack(pady=5)

graph_frame = ctk.CTkFrame(main_frame)
graph_frame.pack(side="left", fill="both", expand=True)

fig, ax = plt.subplots(figsize=(8, 4))
canvas = FigureCanvasTkAgg(fig, master=graph_frame)

canvas.get_tk_widget().pack(fill='both', expand=True)

update_graph()  # Aggiorna il grafico all'avvio
root.mainloop()
