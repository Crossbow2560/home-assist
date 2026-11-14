import queue

import numpy as np
import sounddevice as sd

from . import config
from .claps import ClapDetector
from .stt import SpeechToText


class Listener:
    """Owns the mic. Frames go to the clap detector while waiting to wake, and to
    RealtimeSTT only while listening for a command, so speech played back by the
    assistant is never transcribed."""

    def __init__(self):
        self.stt = SpeechToText()
        self.claps = ClapDetector()
        self.frames: queue.Queue[np.ndarray] = queue.Queue()
        self.feeding = False
        self.stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=config.BLOCK,
            callback=self._on_audio,
        )
        self.stream.start()

    def _on_audio(self, data, frames, time, status):
        frame = data[:, 0].copy()
        if self.feeding:
            self.stt.feed(frame)
        else:
            self.frames.put(frame)

    def _flush(self):
        while not self.frames.empty():
            self.frames.get_nowait()

    def wait_for_claps(self):
        """Block until a double clap is heard."""
        self._flush()
        self.claps.reset()
        while not self.claps.feed(self.frames.get()):
            pass

    def listen(self, timeout: float | None = None) -> str:
        """Transcribe one utterance. Returns "" if no speech starts within `timeout` seconds."""
        self.feeding = True
        try:
            return self.stt.text(timeout)
        finally:
            self.feeding = False

    def close(self):
        self.stream.stop()
        self.stream.close()
        self.stt.close()
