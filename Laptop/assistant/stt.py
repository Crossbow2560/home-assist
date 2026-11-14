import numpy as np
from RealtimeSTT import AudioToTextRecorder

from . import config


class SpeechToText:
    """RealtimeSTT recorder fed from our own mic stream (see audio.Listener), so the
    assistant's own voice is never fed in."""

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

    def text(self) -> str:
        """Block until one utterance has been fed and transcribed."""
        return self.recorder.text().strip()

    def close(self):
        self.recorder.shutdown()
