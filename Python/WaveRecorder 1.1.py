import customtkinter as ctk
from tkinter import filedialog
import sounddevice as sd
import soundfile as sf
import threading
import numpy as np
import os
import shutil
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

        self.temp_dir = "C:/Temp"
        self.temp_file_path = os.path.join(self.temp_dir, "temp_recording.wav")

        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

        self.trim_start = None
        self.trim_end = None

        self.create_widgets()

        # Pulizia file temporanei alla chiusura
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        padding = 15
        button_width = 150

        self.main_frame = ctk.CTkFrame(self.root, fg_color="#2E2E2E")
        self.main_frame.pack(fill="both", expand=True, padx=padding, pady=padding)

        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="#2E2E2E")
        self.button_frame.pack(side="left", fill="y", padx=padding, anchor="n")

        self.title_label = ctk.CTkLabel(
            self.button_frame, text="Audio Recorder",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFA500",
            anchor="w"
        )
        self.title_label.pack(fill="x", pady=(padding, 5))

        self.record_button = ctk.CTkButton(self.button_frame, text="Start", command=self.toggle_recording, width=button_width)
        self.record_button.pack(pady=5, anchor="w")

        self.preview_button = ctk.CTkButton(self.button_frame, text="Preview", command=self.preview_recording, width=button_width)
        self.preview_button.pack_forget()

        self.save_button = ctk.CTkButton(self.button_frame, text="Save", command=self.save_recording, width=button_width)
        self.save_button.pack_forget()

        self.trim_confirm_button = ctk.CTkButton(self.button_frame, text="Confirm Cut", command=self.confirm_trim, width=button_width)
        self.trim_confirm_button.pack_forget()

        self.message_label = ctk.CTkLabel(
            self.button_frame, text="",
            font=ctk.CTkFont(size=14), text_color="#FFA500",
            anchor="w"
        )
        self.message_label.pack(fill="x", pady=(padding, 5))

        self.graph_frame = ctk.CTkFrame(self.main_frame, fg_color="#2E2E2E")
        self.graph_frame.pack(side="left", fill="both", expand=True, padx=padding)

        self.figure, self.ax = plt.subplots()
        self.figure.patch.set_facecolor('black')
        self.ax.set_facecolor('#2E2E2E')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('black')

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        self.span_selector = SpanSelector(self.ax, self.on_select, 'horizontal', useblit=True)

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
        self.recording = True
        self.audio_data.clear()
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
            shutil.copy(self.temp_file_path, file_path)
            self.message_label.configure(text=f"Recording saved as {file_path}")
            self.clean_temp_file()

    def clean_temp_file(self):
        if os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)

    def preview_recording(self):
        if not os.path.exists(self.temp_file_path):
            self.message_label.configure(text="No recording to preview. Please record audio first.")
            return
        try:
            # Sempre leggere il file fresco
            full_audio, samplerate = sf.read(self.temp_file_path, dtype='float32')

            if self.trim_start is not None and self.trim_end is not None:
                if self.trim_start >= self.trim_end or self.trim_start >= len(full_audio):
                    self.message_label.configure(text="Invalid selection for preview.")
                    return

                # Gestione delle diverse selezioni
                if self.trim_start == 0:
                    # Suona solo la parte destra dopo il taglio
                    preview_audio = full_audio[self.trim_end:]
                elif self.trim_end >= len(full_audio):
                    # Suona solo la parte sinistra prima del taglio
                    preview_audio = full_audio[:self.trim_start]
                else:
                    # Concatenazione delle due parti (sinistra + destra)
                    preview_audio = np.concatenate((full_audio[:self.trim_start], full_audio[self.trim_end:]))

                if preview_audio.shape[0] == 0:
                    self.message_label.configure(text="Selection leaves no audio to play.")
                    return

                sd.stop()
                sd.play(preview_audio.copy(), samplerate=samplerate)
                self.message_label.configure(text="Playing trimmed preview...")

            else:
                # Nessuna selezione → suona tutto
                sd.stop()
                sd.play(full_audio.copy(), samplerate=samplerate)
                self.message_label.configure(text="Playing full audio...")

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
        self.plot_waveform()

    def confirm_trim(self):
        if self.trim_start is not None and self.trim_end is not None:
            audio_array = np.concatenate(self.audio_data)
            if self.trim_start >= self.trim_end or self.trim_start >= len(audio_array):
                self.message_label.configure(text="Invalid trim range.")
                return

            new_audio = np.concatenate((audio_array[:self.trim_start], audio_array[self.trim_end:]))

            sf.write(self.temp_file_path, new_audio, self.sample_rate)

            self.audio_data.clear()
            trimmed_data, _ = sf.read(self.temp_file_path, dtype='float32')
            self.audio_data.append(trimmed_data.reshape(-1, 1))

            self.trim_start = None
            self.trim_end = None

            self.plot_waveform()

            self.message_label.configure(text="Trim confirmed and waveform updated.")
            self.trim_confirm_button.pack_forget()

    def on_close(self):
        self.clean_temp_file()
        self.root.destroy()

if __name__ == "__main__":
    app = ctk.CTk()
    AudioRecorderApp(app)
    app.mainloop()
