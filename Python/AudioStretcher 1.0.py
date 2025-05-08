import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import RectangleSelector
import numpy as np
import wave
import sounddevice as sd
from scipy.signal import resample_poly

# Variabili globali
canvas = None
selected_file = None
adjusted_audio = None
selected_range = None
markers = []  # Posizioni dei marker
undo_stack = []  # Stack per undo
redo_stack = []  # Stack per redo
rectangle_selector = None
is_playing = False  # Stato del tasto Preview (True = Riproduzione attiva)

def onselect(eclick, erelease):
    """Gestisce la selezione di un'area sul grafico."""
    global selected_range
    xmin = min(eclick.xdata, erelease.xdata)
    xmax = max(eclick.xdata, erelease.xdata)
    selected_range = (xmin, xmax)
    print(f"Area selezionata: {selected_range}")
    update_graph()

def add_marker(event):
    """Aggiunge un marker cliccando nell'area selezionata."""
    global markers
    if selected_range and selected_range[0] <= event.xdata <= selected_range[1]:
        markers.append(event.xdata)
        markers.sort()
        print(f"Marker aggiunto: {event.xdata}")
        push_undo_state()
        update_graph()

def remove_marker(event):
    """Rimuove un marker con doppio clic."""
    global markers
    tolerance = 0.1  # Tolleranza per selezionare un marker
    for marker in markers:
        if abs(marker - event.xdata) < tolerance:
            markers.remove(marker)
            print(f"Marker rimosso: {marker}")
            push_undo_state()
            update_graph()
            return

def enable_selector(ax):
    """Abilita il RectangleSelector per selezionare un'area."""
    global rectangle_selector
    rectangle_selector = RectangleSelector(
        ax, onselect,
        useblit=True, button=[1],
        interactive=True,
        props=dict(facecolor='blue', edgecolor='black', alpha=0.3, fill=True)
    )

def on_click(event):
    """Gestisce il clic per aggiungere o rimuovere marker."""
    if event.dblclick:
        remove_marker(event)
    elif event.button == 1:
        add_marker(event)

def drag_marker(event):
    """Gestisce lo spostamento di un marker."""
    global markers
    if event.button == 1 and event.xdata:
        tolerance = 0.1
        closest_marker = None
        for marker in markers:
            if abs(marker - event.xdata) < tolerance:
                closest_marker = marker
                break
        if closest_marker is not None:
            min_limit = selected_range[0] if markers.index(closest_marker) == 0 else markers[markers.index(closest_marker) - 1]
            max_limit = selected_range[1] if markers.index(closest_marker) == len(markers) - 1 else markers[markers.index(closest_marker) + 1]
            new_position = max(min(event.xdata, max_limit), min_limit)
            markers[markers.index(closest_marker)] = new_position
            push_undo_state()
            update_graph()

def update_graph():
    """Aggiorna il grafico con i marker e l'area selezionata."""
    if not selected_file:
        return

    with wave.open(selected_file, 'r') as wav_file:
        n_frames = wav_file.getnframes()
        framerate = wav_file.getframerate()
        frames = wav_file.readframes(n_frames)
        waveform = np.frombuffer(frames, dtype=np.int16)
        time = np.linspace(0, n_frames / framerate, num=n_frames)

    ax = canvas.figure.axes[0]
    ax.clear()
    ax.set_facecolor('#333333')  # Sfondo grigio scuro
    ax.spines['top'].set_color('#333333')  # Cornice grigio scuro
    ax.spines['right'].set_color('#333333')
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')
    ax.plot(time, waveform, color='orange', label="Forma d'onda originale")

    if selected_range:
        ax.axvspan(selected_range[0], selected_range[1], color='blue', alpha=0.3)

    for marker in markers:
        ax.axvline(x=marker, color='white', linestyle='--')

    ax.legend()
    canvas.draw()

def push_undo_state():
    """Salva lo stato corrente per undo."""
    global undo_stack, redo_stack
    undo_stack.append((selected_range, markers.copy()))
    redo_stack.clear()
    update_button_visibility()  # Aggiorna la visibilità dei tasti

def undo():
    """Esegue undo."""
    global selected_range, markers
    if undo_stack:
        redo_stack.append((selected_range, markers.copy()))
        selected_range, markers = undo_stack.pop()
        update_graph()
        update_button_visibility()  # Aggiorna la visibilità dei tasti

def redo():
    """Esegue redo."""
    global selected_range, markers
    if redo_stack:
        undo_stack.append((selected_range, markers.copy()))
        selected_range, markers = redo_stack.pop()
        update_graph()
        update_button_visibility()  # Aggiorna la visibilità dei tasti

def update_button_visibility():
    """Aggiorna la visibilità dei tasti Undo, Redo e Preview."""
    if undo_stack:
        undo_button.pack(pady=10)  # Mostra il tasto Undo
    else:
        undo_button.pack_forget()  # Nascondi il tasto Undo
    
    if redo_stack:
        redo_button.pack(pady=10)  # Mostra il tasto Redo
    else:
        redo_button.pack_forget()  # Nascondi il tasto Redo

def update_preview_visibility():
    """Aggiorna la visibilità del tasto Preview."""
    if selected_file:
        preview_button.pack(pady=10)  # Mostra il tasto Preview
    else:
        preview_button.pack_forget()  # Nascondi il tasto Preview

def update_graph_visibility():
    """Aggiorna la visibilità del grafico."""
    if selected_file:
        canvas.get_tk_widget().pack(fill='both', expand=True)  # Mostra il grafico
    else:
        canvas.get_tk_widget().pack_forget()  # Nascondi il grafico

def select_file():
    """Carica un file WAV e visualizza la forma d'onda."""
    global selected_file
    selected_file = ctk.filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if selected_file:
        push_undo_state()
        update_graph()
        update_preview_visibility()  # Aggiorna la visibilità del tasto Preview
        update_graph_visibility()  # Aggiorna la visibilità del grafico

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

undo_button = ctk.CTkButton(control_frame, text="Undo", command=undo)
redo_button = ctk.CTkButton(control_frame, text="Redo", command=redo)

graph_frame = ctk.CTkFrame(main_frame)
graph_frame.pack(side="left", fill="both", expand=True)

fig, ax = plt.subplots(figsize=(8, 4))
canvas = FigureCanvasTkAgg(fig, master=graph_frame)

canvas.mpl_connect("button_press_event", on_click)
canvas.mpl_connect("motion_notify_event", drag_marker)

enable_selector(ax)
update_graph()
update_button_visibility()  # Controlla visibilità iniziale dei tasti
update_preview_visibility()  # Controlla visibilità iniziale del tasto Preview
update_graph_visibility()  # Controlla visibilità iniziale del grafico

root.mainloop()
