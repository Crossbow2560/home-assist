import queue
import threading

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from . import config


class Speaker:
    """Synthesizes sentences with Piper and plays them back in order on a worker thread.
    Without a voice file, replies are only printed."""

    def __init__(self):
        self.voice = None
        self.rate = 22050
        if config.PIPER_VOICE.exists():
            self.voice = PiperVoice.load(str(config.PIPER_VOICE))
            self.rate = self.voice.config.sample_rate
        else:
            print(f"No voice at {config.PIPER_VOICE}; replies will be text only.")
        self.queue: queue.Queue[str | np.ndarray | None] = queue.Queue()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        with sd.OutputStream(samplerate=self.rate, channels=1, dtype="float32") as out:
            while True:
                text = self.queue.get()
                if text is None:
                    self.queue.task_done()
                    return
                if isinstance(text, np.ndarray):
                    out.write(text.reshape(-1, 1))
                elif text and self.voice:
                    for chunk in self.voice.synthesize(text):
                        out.write(chunk.audio_float_array.astype(np.float32).reshape(-1, 1))
                self.queue.task_done()

    def say(self, text: str):
        self.queue.put(text)

    def wait(self):
        """Block until everything queued has been spoken."""
        self.queue.join()
        sd.sleep(150)  # let the output buffer drain

    def close(self):
        # Close the output stream on the worker before interpreter shutdown;
        # tearing down PortAudio from a daemon thread at exit segfaults.
        self.queue.put(None)
        self.thread.join(timeout=5)
