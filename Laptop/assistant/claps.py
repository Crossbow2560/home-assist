"""Double-clap wake detector.

A clap is a sudden, high-pitched burst that comes out of relative quiet and is followed by
quiet. Speech fails at least one of these checks: vowels are low-pitched, and consonant
bursts like "t" or "k" are immediately followed by a vowel. Two claps close together wake
the assistant.

Audio is analysed in 8 ms blocks, and each block is judged once ~160 ms of audio after it
has arrived, so the detector can check what followed.

Run `uv run python -m assistant.claps` to see live readings and tune the thresholds.
"""

import numpy as np

from . import config

SUB = 128  # samples per analysis block (8 ms at 16 kHz)
SUB_S = SUB / config.SAMPLE_RATE
LOOKBACK = 5  # blocks before the onset that must be quiet (40 ms)
SETTLE = 8  # blocks allowed for the clap to ring out (64 ms)
QUIET = 12  # blocks after that which must be quiet (96 ms)
LOOKAHEAD = SETTLE + QUIET
ISOLATION = round(config.CLAP_ISOLATION_S / SUB_S)  # no other sharp sounds this close
HF_SAMPLES = 256  # burst window used for the pitch check (16 ms)

FREQS = np.fft.rfftfreq(HF_SAMPLES, 1 / config.SAMPLE_RATE)
HIGH_BAND = FREQS >= config.CLAP_HIGH_HZ
WINDOW = np.hanning(HF_SAMPLES)


def high_freq_ratio(burst: np.ndarray) -> float:
    power = np.abs(np.fft.rfft(burst * WINDOW)) ** 2
    return float(power[HIGH_BAND].sum() / (power.sum() + 1e-12))


class ClapDetector:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.reset()

    def reset(self):
        self.audio = np.zeros(0, dtype=np.float32)  # recent samples
        self.offset = 0  # absolute block index of self.audio[0]
        self.levels: list[float] = []  # RMS per block, aligned with self.audio
        self.next_block = LOOKBACK  # next block index to judge
        self.claps: list[int] = []  # onset block indices of accepted claps
        self.onsets: list[int] = []  # every sharp onset, clap or not (typing, knocks...)
        self.armed: tuple[int, int] | None = None  # a clap pair awaiting the isolation check
        self.skip_until = 0

    def feed(self, frame: np.ndarray) -> bool:
        """Feed float32 audio of any length. Returns True when a double clap completes."""
        self.audio = np.concatenate([self.audio, frame.astype(np.float32)])
        done = len(self.levels) * SUB
        while done + SUB <= len(self.audio):
            block = self.audio[done : done + SUB]
            self.levels.append(float(np.sqrt(np.mean(block**2))))
            done += SUB

        woke = False
        while self.next_block + LOOKAHEAD < self.offset + len(self.levels):
            woke |= self._judge(self.next_block)
            self.next_block += 1

        # Keep only what future judgements can still look back at.
        drop = self.next_block - LOOKBACK - self.offset
        if drop > 0:
            self.audio = self.audio[drop * SUB :]
            self.levels = self.levels[drop:]
            self.offset += drop
        return woke

    def _judge(self, b: int) -> bool:
        if self.armed and b >= self.armed[1] + ISOLATION:
            return self._check_isolated()
        if b < self.skip_until:
            return False
        e = self.levels
        i = b - self.offset
        level = e[i]
        if level < config.CLAP_MIN_RMS:
            return False
        before = float(np.mean(e[i - LOOKBACK : i])) + 1e-4
        if level < before * config.CLAP_RISE_RATIO:
            return False  # not a sudden onset

        # From here it's a sharp onset; skip the rest of this sound whatever the verdict.
        self.skip_until = b + SETTLE
        self.onsets = [o for o in self.onsets if b - o <= 2 * ISOLATION + LOOKAHEAD] + [b]
        peak = max(e[i : i + 3])
        after = max(e[i + SETTLE : i + LOOKAHEAD])
        burst = self.audio[i * SUB : i * SUB + HF_SAMPLES]
        hf = high_freq_ratio(burst)
        stats = f"peak {peak:.3f}, rise x{peak / before:.0f}, high-freq {hf:.2f}, tail {after / peak:.2f}"

        if hf < config.CLAP_MIN_HIGH_RATIO:
            self._log(b, f"rejected, too low-pitched ({stats})")
            return False
        if after > peak * config.CLAP_QUIET_RATIO:
            self._log(b, f"rejected, sound kept going ({stats})")
            return False

        self._log(b, f"clap ({stats})")
        self.claps = [c for c in self.claps if (b - c) * SUB_S <= config.CLAP_MAX_GAP_S]
        self.claps.append(b)
        if self.armed:
            self._log(b, "ignored, third clap (applause or typing?)")
            self.armed = None
            self.claps.clear()
        elif len(self.claps) >= 2 and (b - self.claps[-2]) * SUB_S >= config.CLAP_MIN_GAP_S:
            self.armed = (self.claps[-2], b)
            self.claps.clear()
        return False

    def _check_isolated(self) -> bool:
        """A double clap must stand alone: a run of clicks is typing, not a wake signal."""
        first, second = self.armed
        self.armed = None
        others = [o for o in self.onsets if first - ISOLATION <= o <= second + ISOLATION and o not in (first, second)]
        if others:
            self._log(second, f"ignored, {len(others)} other sharp sounds nearby (typing?)")
            return False
        return True

    def _log(self, b: int, msg: str):
        if self.verbose:
            print(f"  [{b * SUB_S:7.2f}s] {msg}")


if __name__ == "__main__":
    # Calibration: clap twice and watch what the detector sees.
    import queue

    import sounddevice as sd

    frames: queue.Queue[np.ndarray] = queue.Queue()
    detector = ClapDetector(verbose=True)
    print("Listening for double claps (Ctrl+C to stop)...")
    with sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=config.BLOCK,
        callback=lambda d, *_: frames.put(d[:, 0].copy()),
    ):
        try:
            while True:
                if detector.feed(frames.get()):
                    print("  👏👏 DOUBLE CLAP — wake!")
        except KeyboardInterrupt:
            pass
