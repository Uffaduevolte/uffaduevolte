import customtkinter as ctk
from tkinter import filedialog
import sounddevice as sd
import soundfile as sf
import threading
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import SpanSelector

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AudioRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Recorder")
        self.root.geometry("800x500")  # Dimensione della finestra
        self.root.iconbitmap(os.path.join(os.path.dirname(__file__), "io.ico"))

        self.recording = False
        self.audio_data = []
        self.sample_rate = 44100
        self.temp_file_path = "temp_recording.wav"  # File temporaneo per preview e salvataggio
        self.trim_file_path = "trimmed_temp.wav"  # File temporaneo per preview del taglio
        self.trim_start = None  # Indice di inizio del trim
        self.trim_end = None  # Indice di fine del trim

        self.create_widgets()

    def create_widgets(self):
        padding = 15

        # Contenitore principale
        self.main_frame = ctk.CTkFrame(self.root, fg_color="#2E2E2E")  # Sfondo uniforme grigio
        self.main_frame.pack(fill="both", expand=True, padx=padding, pady=padding)

        # Frame per i pulsanti
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="#2E2E2E")  # Sfondo grigio
        self.button_frame.pack(side="left", fill="y", padx=padding)

        self.title_label = ctk.CTkLabel(
            self.button_frame,
            text="Audio Recorder",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FFA500"  # Colore arancione
        )
        self.title_label.pack(pady=(padding, 5))

        self.record_button = ctk.CTkButton(self.button_frame, text="Start", command=self.toggle_recording, width=75)
        self.record_button.pack(pady=5)

        # Pulsanti di interazione
        self.preview_button = ctk.CTkButton(self.button_frame, text="Preview", command=self.preview_recording, width=75)
        self.save_button = ctk.CTkButton(self.button_frame, text="Save", command=self.save_recording, width=75)
        self.trim_confirm_button = ctk.CTkButton(self.button_frame, text="Conferma Taglio", command=self.confirm_trim, width=150)
        self.trim_confirm_button.pack_forget()  # Nascondi il pulsante di conferma inizialmente

        self.message_label = ctk.CTkLabel(
            self.button_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="#FFA500"  # Colore arancione
        )
        self.message_label.pack(pady=(padding, 5))

        # Frame per il grafico
        self.graph_frame = ctk.CTkFrame(self.main_frame, fg_color="#2E2E2E")  # Sfondo grigio
        self.graph_frame.pack(side="left", fill="both", expand=True, padx=padding)

        self.figure, self.ax = plt.subplots()

        # Imposta la cornice del grafico come nero assoluto
        self.figure.patch.set_facecolor('black')  # Sfondo della figura
        self.ax.set_facecolor('#2E2E2E')  # Sfondo dell'area del grafico
        for spine in self.ax.spines.values():
            spine.set_edgecolor('black')  # Colore dei bordi

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # Aggiungi il selettore di area per il trim
        self.span_selector = SpanSelector(
            self.ax,
            self.on_select,
            'horizontal',
            useblit=True,
            rectprops=dict(alpha=0.5, facecolor='orange')
        )

    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
            self.record_button.configure(text="Stop")
            # Nascondi i pulsanti Preview, Save e Conferma Taglio durante la registrazione
            self.preview_button.pack_forget()
            self.save_button.pack_forget()
            self.trim_confirm_button.pack_forget()
        else:
            self.stop_recording()
            self.record_button.configure(text="Start")
            # Mostra i pulsanti Preview e Save solo se esiste un file temporaneo
            if os.path.exists(self.temp_file_path):
                self.preview_button.pack(pady=5)
                self.save_button.pack(pady=5)

    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.audio_data = []
            self.clear_plot()  # Pulisce il grafico all'avvio di una nuova registrazione
            threading.Thread(target=self.record_audio).start()
            self.message_label.configure(text="Recording started.")

    def record_audio(self):
        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=self.audio_callback):
            while self.recording:
                sd.sleep(100)

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        if self.recording:
            self.audio_data.append(indata.copy())

    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.message_label.configure(text="Recording stopped.")
            self.save_temp_file()
            self.plot_waveform()  # Aggiorna il grafico al termine della registrazione

    def save_temp_file(self):
        """Salva temporaneamente l'audio registrato per preview e salvataggio successivo."""
        if self.audio_data:
            audio_array = np.concatenate(self.audio_data)
            sf.write(self.temp_file_path, audio_array, self.sample_rate)

    def save_recording(self):
        """Salva l'audio registrato in un file scelto dall'utente."""
        if not os.path.exists(self.temp_file_path):
            self.message_label.configure(text="No recording to save. Please record audio first.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if file_path:
            os.rename(self.temp_file_path, file_path)  # Sposta il file temporaneo nella destinazione finale
            self.message_label.configure(text=f"Recording saved as {file_path}")
            # Clear message after saving
            threading.Timer(3.0, lambda: self.message_label.configure(text="")).start()

    def preview_recording(self):
        if not os.path.exists(self.temp_file_path):
            self.message_label.configure(text="No recording to preview. Please record audio first.")
            return

        sd.play(sf.read(self.temp_file_path, dtype='float32')[0], samplerate=self.sample_rate)

    def plot_waveform(self):
        if not self.audio_data:
            return

        audio_array = np.concatenate(self.audio_data)
        time_axis = np.linspace(0, len(audio_array) / self.sample_rate, num=len(audio_array))

        self.ax.clear()

        # Set zero at the center of the plot and customize colors
        max_amplitude = np.max(np.abs(audio_array))
        self.ax.set_ylim([-max_amplitude, max_amplitude])
        self.ax.set_facecolor('#2E2E2E')
        self.ax.set_title('Waveform', color='orange')
        self.ax.set_xlabel('Time (s)', color='orange')
        self.ax.set_ylabel('Amplitude', color='orange')
        self.ax.tick_params(axis='x', colors='orange')
        self.ax.tick_params(axis='y', colors='orange')
        self.ax.plot(time_axis, audio_array, color='orange')

        self.canvas.draw()

    def clear_plot(self):
        """Pulisce il grafico."""
        self.ax.clear()
        self.canvas.draw()

    def on_select(self, xmin, xmax):
        """Gestisce la selezione dell'area per il trim."""
        self.trim_start = int(xmin * self.sample_rate)
        self.trim_end = int(xmax * self.sample_rate)
        self.message_label.configure(text=f"Selected range: {xmin:.2f}s to {xmax:.2f}s")
        self.trim_confirm_button.pack(pady=5)  # Mostra il pulsante di conferma del taglio

    def confirm_trim(self):
        """Conferma il taglio e aggiorna il grafico."""
        if self.trim_start is not None and self.trim_end is not None:
            audio_array = np.concatenate(self.audio_data)
            trimmed_audio = audio_array[self.trim_start:self.trim_end]
            sf.write(self.trim_file_path, trimmed_audio, self.sample_rate)  # Salva il file tagliato temporaneamente
            self.message_label.configure(text="Trim confirmed. Preview updated.")
            self.audio_data = [trimmed_audio]  # Aggiorna l'audio corrente con il taglio
            self.plot_waveform()  # Aggiorna il grafico
            self.trim_confirm_button.pack_forget()  # Nascondi il pulsante di conferma


if __name__ == "__main__":
    app = ctk.CTk()
    AudioRecorderApp(app)
    app.mainloop()
