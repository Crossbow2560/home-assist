import queue
import sys
import threading

import httpx

from . import config, tools
from .llm import Chat
from .tts import Speaker

USAGE = "usage: python -m assistant [--text]   (--text: type only, no microphone)"


def read_keyboard(inbox: queue.Queue):
    while True:
        try:
            line = input()
        except EOFError:
            inbox.put(None)  # Ctrl+D quits
            return
        if line.strip():
            inbox.put(line.strip())


def read_mic(listener, inbox: queue.Queue):
    while True:
        if text := listener.listen():
            print(f"\rYou (voice): {text}")
            inbox.put(text)


def main():
    args = sys.argv[1:]
    if args not in ([], ["--text"]):
        print(USAGE)
        return
    use_mic = not args

    print("Loading models...")
    speaker = Speaker()
    chat = Chat()

    try:
        httpx.get(config.LLM_URL.replace("/v1/chat/completions", "/health"), timeout=3)
    except httpx.HTTPError:
        print(f"Can't reach llama-server at {config.LLM_URL}. Start it with ./run-llm.sh")
        speaker.close()
        return
    if not tools.connect():
        print(f"Can't reach the MQTT broker at {config.MQTT_HOST}:{config.MQTT_PORT}; device commands will fail.")

    inbox: queue.Queue[str | None] = queue.Queue()
    listener = None
    if use_mic:
        from .audio import Listener  # loads Whisper, so only when the mic is used

        listener = Listener()
        threading.Thread(target=read_mic, args=(listener, inbox), daemon=True).start()
    threading.Thread(target=read_keyboard, args=(inbox,), daemon=True).start()

    print("Speak or type a message (Ctrl+C to quit)." if use_mic else "Type a message (Ctrl+C to quit).")
    speaker.say("Hi, I'm listening.")
    speaker.wait()

    try:
        while True:
            print("> ", end="", flush=True)
            text = inbox.get()
            if text is None:
                break
            if listener:
                listener.pause()

            for i, sentence in enumerate(chat.reply(text)):
                print("AI: " if i == 0 else " ", end="", flush=True)
                print(sentence, end="", flush=True)
                speaker.say(sentence)
            print()
            speaker.wait()
            if listener:
                listener.resume()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nBye.")
        if listener:
            listener.close()
        speaker.close()


if __name__ == "__main__":
    main()
