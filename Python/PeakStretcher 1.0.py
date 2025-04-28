import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import wave
import sounddevice as sd

# Variabili globali
canvas = None
selected_file = None
update_delay = None  # Timer per gestire ritardi nell'aggiornamento

def select_file():
    """Apri finestra di dialogo per selezionare un file .wav."""
    global selected_file
    selected_file = ctk.filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if selected_file:
        visualize_waveform(selected_file)
        preview_button.configure(state="normal")  # Abilita il tasto Preview
        adjust_button.pack(pady=10)  # Mostra il pulsante Adjust

def preview_file():
    """Riproduce il file selezionato."""
    if selected_file:
        # Carica il file e riproducilo
        with wave.open(selected_file, 'r') as wav_file:
            framerate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())
            waveform = np.frombuffer(frames, dtype=np.int16)
            sd.play(waveform, samplerate=framerate)

def visualize_waveform(file_path):
    """Carica il file .wav e rappresenta la forma d'onda con divisioni di tempo basate sui BPM."""
    global canvas
    # Leggere i dati dal file .wav
    with wave.open(file_path, 'r') as wav_file:
        n_frames = wav_file.getnframes()
        n_channels = wav_file.getnchannels()
        framerate = wav_file.getframerate()
        duration = n_frames / float(framerate)
        frames = wav_file.readframes(n_frames)
        waveform = np.frombuffer(frames, dtype=np.int16)
        if n_channels == 2:
            waveform = waveform[::2]

    # Creare il grafico
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor('black')  # Sfondo del grafico
    ax.set_facecolor('#2E2E2E')       # Sfondo interno del grafico
    for spine in ax.spines.values():
        spine.set_edgecolor('white')  # Colore dei bordi

    time = np.linspace(0, duration, num=len(waveform))
    ax.plot(time, waveform, color='orange', label="Forma d'onda")

    # Aggiungere linee verticali per i BPM
    try:
        bpm = int(bpm_entry.get())
        interval = 60 / bpm  # Intervallo in secondi
        for t in np.arange(0, duration, interval):
            ax.axvline(x=t, color='red', linestyle='--', alpha=0.7)

        ax.set_title("Forma d'onda con marker BPM", color='orange')
        ax.set_xlabel("Tempo (s)", color='orange')
        ax.set_ylabel("Ampiezza (valori normalizzati)", color='orange')  # Unità di misura
        ax.tick_params(axis='x', colors='orange')
        ax.tick_params(axis='y', colors='orange')
    except ValueError:
        pass  # Ignora errori se il campo BPM non è un numero valido

    # Rimuovere il grafico precedente
    if canvas:
        canvas.get_tk_widget().destroy()

    # Visualizzare il grafico in customtkinter
    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas.get_tk_widget().pack(fill='both', expand=True)
    canvas.draw()

def delayed_update_bpm(*args):
    """Gestisce l'aggiornamento del grafico con un ritardo per permettere all'utente di completare l'inserimento."""
    global update_delay
    if update_delay is not None:
        root.after_cancel(update_delay)  # Cancella eventuali timer in corso
    update_delay = root.after(300, update_bpm)  # Attendi 300ms prima di aggiornare

def update_bpm():
    """Aggiorna le linee verticali del grafico quando cambia il BPM."""
    if selected_file:
        visualize_waveform(selected_file)

# Configurazione CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Creare la finestra principale
root = ctk.CTk()
root.title("Visualizzatore di Forma d'Onda")
root.geometry("1000x600")

main_frame = ctk.CTkFrame(root, fg_color="#2E2E2E")
main_frame.pack(fill="both", expand=True, padx=20, pady=20)

# Frame per i controlli
control_frame = ctk.CTkFrame(main_frame, fg_color="#2E2E2E")
control_frame.pack(side="left", fill="y", padx=20)

select_button = ctk.CTkButton(control_frame, text="Seleziona file WAV", command=select_file)
select_button.pack(pady=(20, 10))

preview_button = ctk.CTkButton(control_frame, text="Preview", command=preview_file, state="disabled")
preview_button.pack(pady=(0, 10))

bpm_frame = ctk.CTkFrame(control_frame, fg_color="#2E2E2E")
bpm_frame.pack(pady=(10, 5), anchor="w")

bpm_label = ctk.CTkLabel(bpm_frame, text="BPM:", font=ctk.CTkFont(size=14, weight="bold"), text_color="orange")
bpm_label.pack(side="left", padx=(0, 5))

bpm_entry = ctk.CTkEntry(bpm_frame, width=100)
bpm_entry.insert(0, "100")  # Valore predefinito
bpm_entry.pack(side="right")
bpm_entry.bind("<KeyRelease>", delayed_update_bpm)  # Usa un ritardo per aggiornare il grafico al cambiare del valore BPM

adjust_button = ctk.CTkButton(control_frame, text="Adjust", command=None)  # Placeholder per futura funzione
adjust_button.pack_forget()  # Nascondi finché non è caricato un file

# Frame per il grafico
graph_frame = ctk.CTkFrame(main_frame, fg_color="#2E2E2E")
graph_frame.pack(side="left", fill="both", expand=True)

# Avvio applicazione
root.mainloop()
