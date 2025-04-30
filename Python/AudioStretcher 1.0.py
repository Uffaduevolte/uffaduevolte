import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import wave
import sounddevice as sd
from scipy.signal import find_peaks, resample, resample_poly
from scipy.interpolate import interp1d
from matplotlib.widgets import RectangleSelector

# Variabili globali
canvas = None
selected_file = None
update_delay = None  # Timer per gestire ritardi nell'aggiornamento
adjusted_audio = None  # Contiene il segnale audio rielaborato
selected_range = None  # Variabile globale per memorizzare il range selezionato
rectangle_selector = None  # Variabile globale per il selettore

def onselect(eclick, erelease):
    """Gestisce la selezione dell'area nel grafico."""
    global selected_range
    ymin = min(eclick.ydata, erelease.ydata)
    ymax = max(eclick.ydata, erelease.ydata)
    selected_range = (ymin, ymax)
    print(f"Range selezionato: {selected_range}")

    # Abilita il tasto Adjust solo se è stata fatta una selezione valida
    if ymin != ymax:  # Controlla che ci sia effettivamente un range selezionato
        adjust_button.configure(state="normal")  # Abilita il pulsante Adjust
        message_label.configure(text="Range di ampiezza selezionato. Ora puoi cliccare su Adjust.")
    else:
        adjust_button.configure(state="disabled")  # Disabilita il pulsante Adjust
        message_label.configure(text="Seleziona un range valido per abilitare Adjust.")

def enable_selector(ax):
    """Abilita il selettore per scegliere il range di ampiezza nel grafico."""
    global rectangle_selector
    rectangle_selector = RectangleSelector(
        ax, onselect,
        interactive=True,  # Consente l'interazione con il rettangolo
        props=dict(facecolor='blue', edgecolor='black', alpha=0.3, fill=True)  # Stile del rettangolo
    )

def detect_bpm(waveform, framerate):
    """Rileva automaticamente il BPM calcolando gli intervalli tra i picchi."""
    try:
        # Trova i picchi nel segnale audio
        peaks, _ = find_peaks(waveform, height=np.max(waveform) * 0.5, distance=framerate * 0.2)
        
        # Calcola gli intervalli temporali tra i picchi
        if len(peaks) > 1:
            intervals = np.diff(peaks) / framerate  # Intervalli in secondi
            avg_interval = np.mean(intervals)  # Intervallo medio
            bpm = int(60 / avg_interval)  # Converte l'intervallo medio in BPM
            return bpm
        else:
            return 120  # Valore di default se non ci sono abbastanza picchi
    except Exception as e:
        print(f"Errore durante il calcolo del BPM: {e}")
        return 120  # Valore di default in caso di errore

def select_file():
    """Apri finestra di dialogo per selezionare un file .wav e rileva automaticamente il BPM."""
    global selected_file, adjusted_audio
    selected_file = ctk.filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    adjusted_audio = None  # Reset dell'audio rielaborato

    if selected_file:
        try:
            # Carica il file e calcola il BPM
            with wave.open(selected_file, 'r') as wav_file:
                n_frames = wav_file.getnframes()
                framerate = wav_file.getframerate()
                frames = wav_file.readframes(n_frames)
                waveform = np.frombuffer(frames, dtype=np.int16)

            # Rileva il BPM e imposta il valore nella casella BPM
            detected_bpm = detect_bpm(waveform, framerate)
            bpm_entry.delete(0, ctk.END)
            bpm_entry.insert(0, str(detected_bpm))

            # Visualizza la forma d'onda
            visualize_waveform(selected_file)

            # Disabilita il tasto Adjust fino alla selezione
            adjust_button.configure(state="disabled")

            # Abilita il tasto preview
            preview_button.configure(state="normal")

            # Mostra il messaggio sotto il grafico
            message_label.configure(text="Seleziona un range di ampiezza nel grafico per proseguire.")
            message_label.pack(side="bottom", pady=(10, 5))
        except Exception as e:
            print(f"Errore durante il caricamento del file: {e}")

def preview_file():
    """Riproduce il file originale o rielaborato."""
    if adjusted_audio is not None:
        # Riproduce l'audio rielaborato se disponibile
        print("Riproducendo audio rielaborato...")
        with wave.open(selected_file, 'r') as wav_file:
            framerate = wav_file.getframerate()
        sd.play(adjusted_audio, samplerate=framerate)
    elif selected_file:
        # Riproduce il file originale
        print("Riproducendo audio originale...")
        with wave.open(selected_file, 'r') as wav_file:
            framerate = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())
            waveform = np.frombuffer(frames, dtype=np.int16)
            sd.play(waveform, samplerate=framerate)

def update_waveform_with_markers(marker_positions):
    """Aggiorna il grafico per mostrare i marker verticali."""
    try:
        # Cancella i marker esistenti
        plt.clf()  # Pulisce la figura corrente
        with wave.open(selected_file, 'r') as wav_file:
            n_frames = wav_file.getnframes()
            framerate = wav_file.getframerate()
            frames = wav_file.readframes(n_frames)
            waveform = np.frombuffer(frames, dtype=np.int16)
            duration = n_frames / framerate
            time = np.linspace(0, duration, num=n_frames)

        # Disegna la forma d'onda
        plt.plot(time, waveform, label="Waveform", color="orange")

        # Aggiungi i marker verticali
        for marker in marker_positions:
            plt.axvline(x=marker, color='blue', linestyle='--', label="Marker")

        # Configura il grafico
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.title("Waveform with BPM Markers")
        plt.legend()
        plt.grid()

        # Mostra il grafico
        plt.draw()
    except Exception as e:
        print(f"Errore durante l'aggiornamento dei marker: {e}")

def update_markers():
    """Aggiorna solo i marker verticali nel grafico quando cambiano i BPM."""
    if not selected_file or not canvas:
        return

    try:
        # Rileggi il file originale per calcolare i marker
        with wave.open(selected_file, 'r') as wav_file:
            n_frames = wav_file.getnframes()
            framerate = wav_file.getframerate()
            duration = n_frames / framerate

        # Calcola le posizioni dei marker in base ai BPM
        bpm = int(bpm_entry.get())
        interval = 60 / bpm  # Intervallo tra i marker in secondi
        marker_positions = np.arange(0, duration, interval)

        # Ottieni l'asse corrente dal canvas
        ax = canvas.figure.axes[0]

        # Rimuovi i vecchi marker
        for line in ax.get_lines():
            if line.get_linestyle() == '--':  # Identifica le linee tratteggiate dei marker
                line.remove()

        # Aggiungi i nuovi marker
        for i, t in enumerate(marker_positions):
            if i == 0:  # Aggiungi "Marker" solo per il primo
                ax.axvline(x=t, color='red', linestyle='--', alpha=0.7, label="Marker")
            else:
                ax.axvline(x=t, color='red', linestyle='--', alpha=0.7)

        # Ridisegna il grafico
        ax.legend(loc="upper right")  # Posiziona la legenda in alto a destra
        canvas.draw()

        # Mostra e abilita il tasto Adjust
        adjust_button.pack(pady=10)
        adjust_button.configure(state="normal")

        # Abilita il tasto preview
        preview_button.configure(state="normal")
        
    except Exception as e:
        print(f"Errore durante l'aggiornamento dei marker: {e}")

def crossfade_segments(seg1, seg2, fade_length=100):
    """Applica un crossfade tra due segmenti audio."""
    if len(seg1) < fade_length or len(seg2) < fade_length:
        raise ValueError("I segmenti devono essere più lunghi del fade_length")

    # Converti a float64 per evitare problemi con il tipo di dato
    seg1 = seg1.astype(np.float64)
    seg2 = seg2.astype(np.float64)

    # Crea una transizione graduale (fade-in e fade-out)
    fade_in = np.linspace(0, 1, fade_length)
    fade_out = np.linspace(1, 0, fade_length)

    # Applica il fade-out al segmento precedente
    seg1[-fade_length:] = seg1[-fade_length:] * fade_out

    # Applica il fade-in al segmento successivo
    seg2[:fade_length] = seg2[:fade_length] * fade_in

    # Combina i due segmenti con un crossfade
    combined = np.concatenate((seg1[:-fade_length], seg1[-fade_length:] + seg2[:fade_length], seg2[fade_length:]))

    # Converti di nuovo a int16 prima di restituire
    return combined.astype(np.int16)

def fade_segment(segment, fade_samples=10):
    """Applica un fade-in e fade-out leggero a un segmento."""
    if len(segment) < 2 * fade_samples:
        return segment  # troppo corto per fare fade
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    segment[:fade_samples] *= fade_in
    segment[-fade_samples:] *= fade_out
    return segment

def fade_segment(segment, fade_samples=10):
    if len(segment) < 2 * fade_samples:
        return segment
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    segment[:fade_samples] *= fade_in
    segment[-fade_samples:] *= fade_out
    return segment

def stretch_segment(segment, target_len):
    original_len = len(segment)
    if original_len < 2 or target_len < 2 or original_len == target_len:
        return segment
    gcd = np.gcd(original_len, target_len)
    up = target_len // gcd
    down = original_len // gcd
    return resample_poly(segment, up, down)

def adjust_audio():
    global adjusted_audio
    if not selected_file or selected_range is None:
        print("File non selezionato o range non definito.")
        return

    try:
        import wave
        with wave.open(selected_file, 'r') as wav_file:
            n_frames  = wav_file.getnframes()
            framerate = wav_file.getframerate()
            frames    = wav_file.readframes(n_frames)
            waveform  = np.frombuffer(frames, dtype=np.int16)

        duration = n_frames / framerate
        time = np.arange(n_frames) / framerate

        # --- Parametri ---
        ymin, ymax = selected_range
        bpm = int(bpm_entry.get())
        interval_sec = 60 / bpm
        interval_samples = int(interval_sec * framerate)
        TP = interval_samples // 8

        stretch_factor_max = 2.0
        stretch_factor_min = 0.5

        # --- Marker ---
        marker_pos = (np.arange(0, duration, interval_sec) * framerate).astype(int)
        marker_pos = marker_pos[marker_pos < n_frames]

        # --- RAP ---
        peaks, _ = find_peaks(np.abs(waveform), height=1000)
        rap = [p for p in peaks if waveform[p] < ymin or waveform[p] > ymax]
        rap = [p for p in rap if 0 < p < n_frames - 1]

        # --- Assegnamento RAP ---
        marker_assigned = {}
        rap_used = set()

        for m in marker_pos:
            close_raps = [p for p in rap if abs(p - m) <= TP and p not in rap_used]
            if close_raps:
                best = max(close_raps, key=lambda p: abs(waveform[p]))
                marker_assigned[best] = m
                rap_used.add(best)

        # --- Costruzione cardini ---
        cardini = [0] + sorted(marker_assigned.keys()) + [n_frames - 1]
        destinazioni = [0] + [marker_assigned[p] for p in sorted(marker_assigned)] + [n_frames - 1]

        # --- Rimuovi RAP che causano fattori eccessivi ---
        revised_cardini = [cardini[0]]
        revised_dest = [destinazioni[0]]
        for i in range(1, len(cardini)):
            src_len = cardini[i] - revised_cardini[-1]
            dst_len = destinazioni[i] - revised_dest[-1]
            if src_len < 2 or dst_len < 2:
                continue
            factor = dst_len / src_len
            if stretch_factor_min <= factor <= stretch_factor_max:
                revised_cardini.append(cardini[i])
                revised_dest.append(destinazioni[i])
            else:
                print(f"⚠️ RAP rimosso tra {cardini[i-1]} e {cardini[i]} (fattore {factor:.2f})")

        # --- Stretch finale ---
        result_audio = []
        for i in range(len(revised_cardini)-1):
            src_start = revised_cardini[i]
            src_end   = revised_cardini[i+1]
            dst_start = revised_dest[i]
            dst_end   = revised_dest[i+1]

            segment = waveform[src_start:src_end]
            target_len = max(2, dst_end - dst_start)

            stretched = stretch_segment(segment, target_len)
            smoothed = fade_segment(stretched, 10)
            result_audio.append(smoothed)

        # --- Ricostruzione e normalizzazione ---
        adjusted_audio = np.concatenate(result_audio).astype(np.float64)
        adjusted_audio = adjusted_audio / np.max(np.abs(adjusted_audio)) * 32767
        adjusted_audio = adjusted_audio.astype(np.int16)

        # --- Plot ---
        ax = canvas.figure.axes[0]
        ax.cla()
        ax.plot(time, waveform, color='orange', label="Originale")
        t_new = np.linspace(0, duration, len(adjusted_audio))
        ax.plot(t_new, adjusted_audio, color='green', alpha=0.6, label="Rielaborato")
        for m in marker_pos / framerate:
            ax.axvline(x=m, color='red', linestyle='--', alpha=0.7)
        for rap_idx, marker in marker_assigned.items():
            if rap_idx in revised_cardini:
                ax.plot(rap_idx / framerate, waveform[rap_idx], 'bo')
                ax.annotate("RAP", (rap_idx / framerate, waveform[rap_idx]), xytext=(0,10),
                            textcoords='offset points', ha='center', fontsize=8, color='blue')

        ax.legend(loc="upper center", bbox_to_anchor=(0.5,-0.1), ncol=3, fontsize="small")
        canvas.draw()
        print("✅ Adjust_audio completato con filtro di stretching restrittivo.")

    except Exception as e:
        print(f"❌ Errore durante Adjust_audio: {e}")

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
    ax.plot(time, waveform, color='orange', label="Forma d'onda originale")

    # Aggiungere linee verticali per i BPM
    try:
        bpm = int(bpm_entry.get())
        interval = 60 / bpm  # Intervallo in secondi
        first_marker = True  # Per aggiungere la label una sola volta
        for t in np.arange(0, duration, interval):
            if first_marker:
                ax.axvline(x=t, color='red', linestyle='--', alpha=0.7, label="Marker")
                first_marker = False
            else:
                ax.axvline(x=t, color='red', linestyle='--', alpha=0.7)

        ax.set_title("Forma d'onda con marker BPM", color='orange')
        ax.set_xlabel("Tempo (s)", color='orange')
        ax.set_ylabel("Ampiezza (valori normalizzati)", color='orange')  # Unità di misura
        ax.tick_params(axis='x', colors='orange')
        ax.tick_params(axis='y', colors='orange')
        # Sposta la legenda sopra il grafico
        ax.legend(
            loc="upper center",  # Posizione sopra il grafico
            bbox_to_anchor=(0.5, -0.1),  # Coordina fuori dal grafico
            ncol=3,  # Numero di colonne
            fontsize="small"  # Dimensione del testo
        )
    except ValueError:
        pass  # Ignora errori se il campo BPM non è un numero valido

    # Rimuovere il grafico precedente
    if canvas:
        canvas.get_tk_widget().destroy()

    # Visualizzare il grafico in customtkinter
    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas.get_tk_widget().pack(fill='both', expand=True)
    canvas.draw()

    # Abilita il selettore per scegliere il range
    enable_selector(ax)

# Associa l'aggiornamento del BPM all'esecuzione di adjust_audio
def delayed_update_bpm(*args):
    """Gestisce l'aggiornamento del grafico e rilancia Adjust quando cambia il BPM."""
    global update_delay
    if update_delay is not None:
        root.after_cancel(update_delay)  # Cancella eventuali timer in corso
    update_delay = root.after(300, adjust_audio)  # Rilancia adjust_audio con il nuovo BPM
    
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
# Associa l'aggiornamento dei marker al cambio del controllo BPM
bpm_entry.bind("<KeyRelease>", lambda event: update_markers())

# Associa l'esecuzione di adjust_audio al pulsante "Adjust"
adjust_button = ctk.CTkButton(control_frame, text="Adjust", command=adjust_audio)
adjust_button.pack(pady=10)
adjust_button.pack_forget()  # Nascondi finché non è caricato un file

# Frame per il grafico
graph_frame = ctk.CTkFrame(main_frame, fg_color="#2E2E2E")
graph_frame.pack(side="left", fill="both", expand=True)

# Messaggio per guidare l'utente sotto il grafico
message_label = ctk.CTkLabel(graph_frame, text="", text_color="orange")
message_label.pack(side="bottom", pady=(10, 5))  # Posizionato sotto il grafico

# Nascondi il tasto Adjust inizialmente
adjust_button.configure(state="disabled")

# Avvio applicazione
root.mainloop()
