    def __init__(self, root):
        ...
        self.frames_to_discard = 4410  # Numero di frame da scartare (circa 0.1 secondi con sample rate 44100 Hz)
        ...

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        if self.recording:
            # Scarta i frame iniziali solo durante le prime iterazioni
            if self.frames_to_discard > 0:
                if self.frames_to_discard >= len(indata):
                    self.frames_to_discard -= len(indata)
                    return
                else:
                    indata = indata[self.frames_to_discard:]
                    self.frames_to_discard = 0
            
            self.audio_data.append(indata.copy())
