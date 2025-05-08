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
is_playing = False  # Stato del tasto Preview (True = Riproduzione attiva)
bpm = 120  # BPM iniziale (120 BPM di default)
beat_positions = []  # Posizioni calcolate delle linee BPM

def update_bpm():
    """Aggiorna il valore di BPM e ridisegna il grafico."""
    global bpm, beat_positions
    try:
        new_bpm = int(bpm_entry.get())
        if 30 <= new_bpm <= 180:
            bpm = new_bpm
            print(f"BPM aggiornato a: {bpm}")
            update_graph()  # Aggiorna il grafico con le nuove barre rosse
        else:
            print("Il valore di BPM deve essere compreso tra 30 e 180.")
    except ValueError:
        print("Inserisci un valore numerico valido per il BPM.")

def calculate_beat_positions(framerate, duration, bpm):
    """Calcola le posizioni delle linee BPM in base al BPM."""
    beat_interval = 60 / bpm  # Intervallo tra i battiti in secondi
    num_beats = int(duration / beat_interval)
    return [i * beat_interval for i in range(num_beats)]

def update_graph_visibility():
    """Aggiorna la visibilità del grafico in base al caricamento del file."""
    if selected_file:
        canvas.get_tk_widget().pack(fill='both', expand=True)  # Mostra il grafico
    else:
        canvas.get_tk_widget().pack_forget()  # Nascondi il grafico
        
def update_graph():
    """Aggiorna il grafico con i marker e le linee BPM."""
    global beat_positions
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
    ax.set_facecolor('#2b2b2b')  # Sfondo grigio scuro
    ax.spines['top'].set_color('#2b2b2b')  # Cornice grigio scuro
    ax.spines['right'].set_color('#2b2b2b')
    ax.spines['left'].set_color('#2b2b2b')
    ax.spines['bottom'].set_color('#2b2b2b')
    ax.plot(time, waveform, color='orange', label="Forma d'onda originale")

    # Disegna le linee verticali rosse per ogni battito
    for beat in beat_positions:
        ax.axvline(x=beat, color='red', linestyle='--', label='BPM Marker' if beat == beat_positions[0] else None)

    # Disegna i marker
    for marker in markers:
        ax.axvline(x=marker, color='white', linestyle='--')

    ax.legend()
    canvas.draw()

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

    # Disegna i marker
    for marker in markers:
        ax.axvline(x=marker, color='white', linestyle='--')

    ax.legend()
    canvas.draw()

def select_file():
    """Carica un file WAV e visualizza la forma d'onda con i marker BPM."""
    global selected_file
    selected_file = ctk.filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if selected_file:
        update_graph()  # Aggiorna il grafico
        canvas.get_tk_widget().pack(fill='both', expand=True)  # Mostra il grafico
        preview_button.pack(pady=10)  # Mostra il tasto Preview
        bpm_frame.pack(pady=10)  # Mostra il controllo BPM
    else:
        canvas.get_tk_widget().pack_forget()  # Nascondi il grafico se non c'è un file

def add_marker(event):
    """Aggiunge o rimuove un marker cliccando sul grafico."""
    global markers
    if event.dblclick:  # Se l'utente fa doppio clic, rimuovi il marker
        if len(markers) > 0:
            print(f"Marker rimosso: {markers[0]}")
            markers.clear()
            update_graph()
        return

    if len(markers) > 0:
        print("Esiste già un marker. Cancella il marker esistente per crearne uno nuovo.")
        return  # Non consentire di aggiungere altri marker
    if event.xdata:
        markers.append(event.xdata)
        print(f"Marker aggiunto: {event.xdata}")
        update_graph()

def drag_marker(event):
    """Gestisce lo spostamento di un marker tramite drag & drop."""
    global markers
    if event.button == 1 and event.xdata:  # Verifica che il pulsante sinistro del mouse sia premuto
        tolerance = 12 / canvas.figure.get_size_inches()[0] / canvas.figure.dpi  # Tolleranza in unità del grafico
        closest_marker = None

        # Trova il marker più vicino al punto cliccato considerando la tolleranza
        for marker in markers:
            if abs(marker - event.xdata) < tolerance:
                closest_marker = marker
                break

        if closest_marker is not None:
            # Limita il movimento del marker tra l'inizio e la fine del grafico
            min_limit = 0  # Limite minimo (inizio della forma d'onda)
            max_limit = canvas.figure.axes[0].get_xlim()[1]  # Limite massimo (fine della forma d'onda)
            new_position = max(min(event.xdata, max_limit), min_limit)

            # Aggiorna la posizione del marker
            markers[markers.index(closest_marker)] = new_position
            print(f"Marker spostato: {closest_marker} -> {new_position}")
            update_graph()

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
        if selected_file:
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
preview_button.pack_forget()  # Nascondi il tasto Preview all'inizio

bpm_frame = ctk.CTkFrame(control_frame)
bpm_label = ctk.CTkLabel(bpm_frame, text="BPM:")
bpm_label.pack(side="left", padx=5)

bpm_entry = ctk.CTkEntry(bpm_frame, width=60)
bpm_entry.insert(0, str(bpm))  # Imposta il valore iniziale del BPM
bpm_entry.pack(side="left", padx=5)
bpm_entry.bind("<Return>", lambda event: update_bpm())  # Aggiorna il BPM quando si preme Invio
bpm_frame.pack_forget()  # Nascondi il controllo BPM all'inizio

graph_frame = ctk.CTkFrame(main_frame)
graph_frame.pack(side="left", fill="both", expand=True)

fig, ax = plt.subplots(figsize=(8, 4))
canvas = FigureCanvasTkAgg(fig, master=graph_frame)
canvas.get_tk_widget().pack(fill='both', expand=True)
canvas.mpl_connect("button_press_event", add_marker)
canvas.mpl_connect("motion_notify_event", drag_marker)

update_graph()  # Aggiorna il grafico all'avvio
root.mainloop()
