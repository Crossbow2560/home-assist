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
