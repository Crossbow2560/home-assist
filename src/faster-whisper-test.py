import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

# Initialize model for translation
model = WhisperModel("tiny", device="cuda", compute_type="int8")

# Configuration
SAMPLE_RATE = 16000
CHUNK_DURATION = 2.0
buffer = np.zeros(0, dtype=np.float32)

def callback(indata, frames, time, status):
    global buffer
    # Append incoming audio to buffer
    buffer = np.concatenate([buffer, indata[:, 0]])

    # Process when buffer has enough data
    if len(buffer) >= SAMPLE_RATE * CHUNK_DURATION:
        # Transcribe and translate to English
        segments, info = model.transcribe(
            buffer,
            task="translate",
            beam_size=1,  # Faster for real-time
            vad_filter=True
        )

        for segment in segments:
            print(segment.text.strip(), end=" ", flush=True)

        # Clear processed buffer
        buffer = np.zeros(0, dtype=np.float32)

# Start listening
print("Listening... (Ctrl+C to stop)")
with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
    sd.sleep(100000)
