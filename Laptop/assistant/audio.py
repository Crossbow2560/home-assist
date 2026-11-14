import sounddevice as sd

from . import config
from .stt import SpeechToText


class Listener:
    """Owns the mic and feeds it to RealtimeSTT. Paused while the assistant replies,
    so speech it plays back is never transcribed."""

    def __init__(self):
        self.stt = SpeechToText()
        self.paused = False
        self.stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=config.BLOCK,
            callback=self._on_audio,
        )
        self.stream.start()

    def _on_audio(self, data, frames, time, status):
        if not self.paused:
            self.stt.feed(data[:, 0].copy())

    def listen(self) -> str:
        """Block until one utterance has been heard and transcribed."""
        return self.stt.text()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def close(self):
        self.stream.stop()
        self.stream.close()
        self.stt.close()
