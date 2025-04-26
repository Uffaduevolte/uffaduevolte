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
        self.root.geometry("800x500")
        self.root.iconbitmap(os.path.join(os.path.dirname(__file__), "io.ico"))

        self.recording = False
        self.audio_data = []
        self.sample_rate = 44100

        # Percorso dei file temporanei nella cartella C:/Temp
        self.temp_dir = "C:/Temp"
        self.temp_file_path = os.path.join(self.temp_dir, "temp_recording.wav")
        self.trim_file_path = os.path.join(self.temp_dir, "trimmed_temp.wav")

        # Crea la cartella C:/Temp se non esiste
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

        self.trim_start = None
        self.trim_end = None

        self.create_widgets()

    def create_widgets(self):
        padding = 15
        button_width = 150

        # Contenitore principale
        self.main_frame = ctk.CTkFrame(self.root, fg_color="#2E2E2E")
        self.main_frame.pack(fill="both", expand=True, padx=padding, pady=padding)

        # Frame per i pulsanti
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="#2E2E2E")
        self.button_frame.pack(side="left", fill="y", padx=padding, anchor="n")

        # Label "Audio Recorder"
        self.title_label = ctk.CTkLabel(
            self.button_frame,
            text="Audio Recorder",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FFA500",
            anchor="w"
        )
        self.title_label.pack(fill="x", pady=(padding, 5))

        # Pulsanti
        self.record_button = ctk.CTkButton(self.button_frame, text="Start", command=self.toggle_recording, width=button_width)
        self.record_button.pack(pady=5, anchor="w")

        self.preview_button = ctk.CTkButton(self.button_frame, text="Preview", command=self.preview_recording, width=button_width)
        self.preview_button.pack(pady=5, anchor="w")

        self.save_button = ctk.CTkButton(self.button_frame, text="Save", command=self.save_recording, width=button_width)
        self.save_button.pack(pady=5, anchor="w")

        self.trim_confirm_button = ctk.CTkButton(self.button_frame, text="Confirm Cut", command=self.confirm_trim, width=button_width)
        self.trim_confirm_button.pack_forget()

        # Label dei messaggi
        self.message_label = ctk.CTkLabel(
            self.button_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="#FFA500",
            anchor="w"
        )
        self.message_label.pack(fill="x", pady=(padding, 5))

        # Frame per il grafico
        self.graph_frame = ctk.CTkFrame(self.main_frame, fg_color="#2E2E2E")
        self.graph_frame.pack(side="left", fill="both", expand=True, padx=padding)

        self.figure, self.ax = plt.subplots()
        self.figure.patch.set_facecolor('black')
        self.ax.set_facecolor('#2E2E2E')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('black')

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # Aggiungi selettore di area
        self.span_selector = SpanSelector(
            self.ax,
            self.on_select,
            'horizontal',
            useblit=True
        )

    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
            self.record_button.configure(text="Stop")
            self.preview_button.pack_forget()
            self.save_button.pack_forget()
            self.trim_confirm_button.pack_forget()
        else:
            self.stop_recording()
            self.record_button.configure(text="Start")
            if os.path.exists(self.temp_file_path):
                self.preview_button.pack(pady=5, anchor="w")
                self.save_button.pack(pady=5, anchor="w")

    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.audio_data = []
            self.clear_plot()
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
            self.plot_waveform()

    def save_temp_file(self):
        if self.audio_data:
            audio_array = np.concatenate(self.audio_data)
            sf.write(self.temp_file_path, audio_array, self.sample_rate)

    def save_recording(self):
        if not os.path.exists(self.temp_file_path):
            self.message_label.configure(text="No recording to save. Please record audio first.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if file_path:
            os.rename(self.temp_file_path, file_path)
            self.message_label.configure(text=f"Recording saved as {file_path}")
            # Rimuovi i file temporanei
            self.clean_temp_files()
            threading.Timer(3.0, lambda: self.message_label.configure(text="")).start()

    def clean_temp_files(self):
        """Elimina i file temporanei."""
        if os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)
        if os.path.exists(self.trim_file_path):
            os.remove(self.trim_file_path)

    def preview_recording(self):
        file_to_play = None
        if os.path.exists(self.trim_file_path) and os.path.getsize(self.trim_file_path) > 0:
            # Riproduci la parte NON selezionata
            data, _ = sf.read(self.temp_file_path, dtype='float32')
            non_selected_audio = np.concatenate((data[:self.trim_start], data[self.trim_end:]))
            sd.stop()
            sd.play(non_selected_audio, samplerate=self.sample_rate)
            self.message_label.configure(text="Playing non-selected audio...")
            return
        elif os.path.exists(self.temp_file_path) and os.path.getsize(self.temp_file_path) > 0:
            file_to_play = self.temp_file_path
        else:
            self.message_label.configure(text="No recording to preview. Please record audio first.")
            return

        try:
            data, samplerate = sf.read(file_to_play, dtype='float32')
            sd.stop()
            sd.play(data, samplerate=samplerate)
            self.message_label.configure(text="Playing audio...")
        except Exception as e:
            self.message_label.configure(text=f"Error during playback: {str(e)}")

    def plot_waveform(self):
        if not self.audio_data or len(self.audio_data[0]) == 0:
            self.ax.clear()
            self.ax.set_title('No audio data to display', color='orange')
            self.canvas.draw()
            return

        audio_array = np.concatenate(self.audio_data)
        time_axis = np.linspace(0, len(audio_array) / self.sample_rate, num=len(audio_array))

        self.ax.clear()
        self.ax.plot(time_axis, audio_array, color='orange')

        # Controlla se trim_start e trim_end sono definiti prima di aggiungere l'area evidenziata
        if self.trim_start is not None and self.trim_end is not None:
            self.ax.axvspan(self.trim_start / self.sample_rate, self.trim_end / self.sample_rate, color='red', alpha=0.3)

        self.ax.set_facecolor('#2E2E2E')
        self.ax.set_title('Waveform', color='orange')
        self.ax.set_xlabel('Time (s)', color='orange')
        self.ax.set_ylabel('Amplitude', color='orange')
        self.ax.tick_params(axis='x', colors='orange')
        self.ax.tick_params(axis='y', colors='orange')
        self.canvas.draw()

    def clear_plot(self):
        self.ax.clear()
        self.canvas.draw()

    def on_select(self, xmin, xmax):
        self.trim_start = int(xmin * self.sample_rate)
        self.trim_end = int(xmax * self.sample_rate)
        self.message_label.configure(text=f"Selected range: {xmin:.2f}s to {xmax:.2f}s")
        self.trim_confirm_button.pack(pady=5, anchor="w")

    def confirm_trim(self):
        if self.trim_start is not None and self.trim_end is not None:
            audio_array = np.concatenate(self.audio_data)
            if self.trim_start >= self.trim_end or self.trim_start >= len(audio_array):
                self.message_label.configure(text="Invalid trim range.")
                return

            trimmed_audio = audio_array[self.trim_start:self.trim_end]
            sf.write(self.trim_file_path, trimmed_audio, self.sample_rate)
            self.message_label.configure(text="Trim confirmed. Preview updated.")
            self.audio_data = [audio_array]  # Mantieni l'audio completo per il grafico
            self.plot_waveform()
            self.trim_confirm_button.pack_forget()


if __name__ == "__main__":
    app = ctk.CTk()
    AudioRecorderApp(app)
    app.mainloop()
