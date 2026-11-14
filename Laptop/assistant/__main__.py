import time

import httpx

from . import config, tools
from .audio import Listener
from .llm import Chat
from .tts import Speaker


def main():
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

    listener = Listener()
    speaker.say("Hi, clap twice when you need me." if config.CLAP_WAKE else "Hi, I'm listening.")
    speaker.wait()

    try:
        while True:
            if config.CLAP_WAKE:
                print("\n👏 Waiting for a double clap...")
                listener.wait_for_claps()
                speaker.chime()
                speaker.wait()
                timeout = config.COMMAND_TIMEOUT_S
            else:
                timeout = None

            # Keep the conversation going without re-clapping until it goes quiet.
            while True:
                print("🎤 Listening...")
                text = listener.listen(timeout)
                if not text:
                    print("   (nothing heard)")
                    break
                print(f"You: {text}")
                t0 = time.perf_counter()

                print("AI: ", end="", flush=True)
                first = None
                for sentence in chat.reply(text):
                    if first is None:
                        first = time.perf_counter() - t0
                    print(sentence, end=" ", flush=True)
                    speaker.say(sentence)
                print(f"  [first audio queued {first or 0:.2f}s after transcription]")
                speaker.wait()
                if config.CLAP_WAKE:
                    timeout = config.FOLLOWUP_S
    except KeyboardInterrupt:
        print("\nBye.")
    finally:
        listener.close()
        speaker.close()


if __name__ == "__main__":
    main()
