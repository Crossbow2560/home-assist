from RealtimeSTT import AudioToTextRecorder
from pathlib import Path
import subprocess

AGENT  = Path(__file__).parent / "agent" / "agent.py"
PYTHON = Path(__file__).parent / "venv" / "bin" / "python3"

WAKE_VARIANTS = {"friday", "fri day", "fry day"}

recorder     = AudioToTextRecorder()
cmd_recorder = AudioToTextRecorder(model="small")

def is_wakeword(text):
    return any(w in text.lower() for w in WAKE_VARIANTS)

print("Listening for 'Friday'...")

while True:
    text = recorder.text()
    print(text)
    if text and is_wakeword(text):
        print("Detected — listening for command...")
        cmd = cmd_recorder.text()
        if cmd:
            print(f"Command: {cmd}")
            subprocess.run([str(PYTHON), str(AGENT), cmd])
