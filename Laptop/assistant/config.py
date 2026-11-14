import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Audio
SAMPLE_RATE = 16000
BLOCK = 512  # samples per mic frame (32 ms at 16 kHz)

# Voice activity detection (done inside RealtimeSTT)
SILERO_SENSITIVITY = 0.4  # 0-1, higher starts recording on quieter sounds
SILENCE_MS = 700  # stop recording after this much silence
MIN_SPEECH_MS = 250  # ignore blips shorter than this
PRE_ROLL_MS = 300  # audio kept from before speech started

# Wake on double clap (set False to always listen)
CLAP_WAKE = True
CLAP_MIN_RMS = 0.03  # loudness floor over an 8 ms block
CLAP_RISE_RATIO = 6.0  # must jump this many times above the 40 ms before it
CLAP_HIGH_HZ = 2000
CLAP_MIN_HIGH_RATIO = 0.15  # share of burst energy above CLAP_HIGH_HZ; real claps ~0.2-0.45, speech <0.07
CLAP_QUIET_RATIO = 0.5  # 64-160 ms after the onset, level must fall under this share of the peak (real rooms ~0.3-0.4)
CLAP_MIN_GAP_S = 0.2  # closer than this falls inside the first clap's quiet check
CLAP_MAX_GAP_S = 0.8
CLAP_ISOLATION_S = 0.45  # quiet needed around the pair; rejects typing and applause
COMMAND_TIMEOUT_S = 6  # after waking, give up if nothing is said for this long
FOLLOWUP_S = 5  # after a reply, keep listening this long without needing to clap

# Speech-to-text (RealtimeSTT, running faster-whisper)
WHISPER_MODEL = "small.en"
WHISPER_DEVICE = "cpu"  # "cuda" works if cuBLAS/cuDNN 9 are installed
WHISPER_COMPUTE = "int8"

# LLM (llama-server, OpenAI-compatible)
LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"
MAX_HISTORY = 6  # previous turns kept for conversation

# Each turn runs two passes. The device pass sees only the current sentence: at 0.8B,
# conversation history makes the model copy earlier turns instead of acting.
# Thinking + greedy decoding there is what makes tool calls reliable (~0.5s).
DEVICE_PROMPT = """You are Friday, a smart home assistant. You control two devices: the light and the fan. \
Only change the device the user needs; leave the other one alone. \
Examples: "it's dark" -> light ON. "I'm hot" -> fan ON. "I'm cold" -> fan OFF. \
"goodnight" -> light OFF and fan OFF. \
If no device change is needed, reply in one short spoken sentence with no markdown."""

# The chat pass runs only when no device changed; it has history but no tools.
CHAT_PROMPT = """You are Friday, a friendly smart home voice assistant. Your replies are spoken aloud, \
so answer in one or two short sentences of plain text with no markdown, lists, or emoji. \
You did not change any device this turn; if the user asked you to, say you didn't catch which device."""
CHAT_TEMPERATURE = 0.7

# MQTT broker on the Raspberry Pi. The Pi's bridge (pi/bridge.py) takes commands on
# CMD_TOPIC, forwards them to the ESP8266 net switch and answers on REPLY_TOPIC/<id>.
MQTT_HOST = os.environ.get("MQTT_HOST", "raspberrypi.local")
MQTT_PORT = 1883
CMD_TOPIC = "home/cmd"
REPLY_TOPIC = "home/reply"
REPLY_TIMEOUT_S = 3  # give up on the Pi after this long
MQTT_DRY_RUN = os.environ.get("MQTT_DRY_RUN") == "1"  # print instead of publishing

# Text-to-speech
# Any voices/<name>.onnx: jarvis-high, jarvis-medium, en_GB-alan-medium,
# en_GB-northern_english_male-medium, en_US-ryan-high, en_US-lessac-medium
VOICE = "en_GB-northern_english_male-medium"
PIPER_VOICE = ROOT / "voices" / f"{VOICE}.onnx"
