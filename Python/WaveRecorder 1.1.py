import customtkinter as ctk
from tkinter import filedialog
import sounddevice as sd
import soundfile as sf
import threading
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AudioRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Recorder")
        self.root.geometry("600x400")
        self.root.iconbitmap(os.path.join(os.path.dirname(__file__), "io.ico"))
        
        self.recording = False
        self.audio_data = []
        self.sample_rate = 44100
        self.dynamic_gain = 1.0  # Fattore di guadagno dinamico
        
        self.create_widgets()
        
    def create_widgets(self):
        padding = 15
        
        self.title_label = ctk.CTkLabel(self.root, text="Audio Recorder", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.pack(pady=(padding, 5), anchor="w", padx=padding)
        
        self.record_button = ctk.CTkButton(self.root, text="Start", command=self.toggle_recording, width=75)
        self.record_button.pack(pady=5, anchor="w", padx=padding)
        
        self.preview_button = ctk.CTkButton(self.root, text="Preview", command=self.preview_recording, width=75)
        self.preview_button.pack(pady=5, anchor="w", padx=padding)
        
        self.save_button = ctk.CTkButton(self.root, text="Save", command=self.save_recording, width=75)
        self.save_button.pack(pady=5, anchor="w", padx=padding)
        
        self.message_label = ctk.CTkLabel(self.root, text="", font=ctk.CTkFont(size=14))
        self.message_label.pack(pady=(padding, 5), anchor="w", padx=padding)
        
        self.figure, self.ax = plt.subplots()
        self.ax.set_facecolor('#2E2E2E')
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
            self.record_button.configure(text="Stop")
        else:
            self.stop_recording()
            self.record_button.configure(text="Start")
            
    def start_recording(self):
        if not self.recording:
            self.recording = True
            self.audio_data = []
            self.dynamic_gain = 1.0  # Reset del guadagno dinamico
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
            # Calcola il picco massimo nel frame corrente
            max_amplitude = np.max(np.abs(indata))
            
            # Aggiorna il guadagno dinamico per compensare il volume basso
            if max_amplitude > 0:
                self.dynamic_gain = max(1.0, self.dynamic_gain / max_amplitude)
            
            # Applica il guadagno dinamico ai dati audio
            normalized_data = indata * self.dynamic_gain
            
            # Aggiungi i dati normalizzati all'array audio
            self.audio_data.append(normalized_data.copy())
            
    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.message_label.configure(text="Recording stopped.")
            self.plot_waveform()
            
    def save_recording(self):
        if not self.audio_data:
            self.message_label.configure(text="No recording to save. Please record audio first.")
            return
        
        file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if file_path:
            audio_array = np.concatenate(self.audio_data)
            sf.write(file_path, audio_array, self.sample_rate)
            self.message_label.configure(text=f"Recording saved as {file_path}")
            # Clear message after saving
            threading.Timer(3.0, lambda: self.message_label.configure(text="")).start()
            
    def preview_recording(self):
        if not self.audio_data:
            self.message_label.configure(text="No recording to preview. Please record audio first.")
            return
        
        audio_array = np.concatenate(self.audio_data)
        sd.play(audio_array, samplerate=self.sample_rate)
        
    def plot_waveform(self):
        audio_array = np.concatenate(self.audio_data)
        time_axis = np.linspace(0, len(audio_array) / self.sample_rate, num=len(audio_array))
        
        self.ax.clear()
        
        # Set zero at the center of the plot and customize colors
        max_amplitude = np.max(np.abs(audio_array))
        self.ax.set_ylim([-max_amplitude, max_amplitude])
        
        # Customize plot appearance
        plt.rcParams['axes.facecolor'] = 'black'
        
        # Set background color and line color
        self.ax.set_facecolor('#2E2E2E')
        
        # Set axis labels and title color to orange
        self.ax.set_title('Waveform', color='orange')
        self.ax.set_xlabel('Time (s)', color='orange')
        self.ax.set_ylabel('Amplitude', color='orange')
        
        # Set tick parameters color to orange
        self.ax.tick_params(axis='x', colors='orange')
        self.ax.tick_params(axis='y', colors='orange')
        
        # Plot waveform with orange color
        self.ax.plot(time_axis, audio_array, color='orange')
        
        # Draw canvas
        self.canvas.draw()

if __name__ == "__main__":
    app = ctk.CTk()
    AudioRecorderApp(app)
    app.mainloop()
