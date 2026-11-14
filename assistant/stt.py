import threading

import numpy as np
from RealtimeSTT import AudioToTextRecorder

from . import config


class SpeechToText:
    """RealtimeSTT recorder fed from our own mic stream (see audio.Listener), so the
    clap detector can share the mic and the assistant's own voice is never fed in."""

    def __init__(self):
        self.recorder = AudioToTextRecorder(
            model=config.WHISPER_MODEL,
            language="en",
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
            beam_size=1,
            use_microphone=False,
            silero_sensitivity=config.SILERO_SENSITIVITY,
            post_speech_silence_duration=config.SILENCE_MS / 1000,
            min_length_of_recording=config.MIN_SPEECH_MS / 1000,
            pre_recording_buffer_duration=config.PRE_ROLL_MS / 1000,
            spinner=False,
            no_log_file=True,
        )

    def feed(self, frame: np.ndarray):
        self.recorder.feed_audio(frame, config.SAMPLE_RATE)

    def text(self, timeout: float | None = None) -> str:
        """Block until one utterance has been fed and transcribed.
        Returns "" if no speech starts within `timeout` seconds."""
        self.recorder.clear_audio_queue()
        timer = None
        if timeout:
            timer = threading.Timer(timeout, self._give_up)
            timer.start()
        try:
            return self.recorder.text().strip()
        finally:
            if timer:
                timer.cancel()

    def _give_up(self):
        # Only cancel while still waiting for speech, not mid-sentence or mid-transcription.
        if self.recorder.state == "listening":
            self.recorder.abort()

    def close(self):
        self.recorder.shutdown()
