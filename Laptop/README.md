# Local voice assistant

Fully offline, on your LAN:

```
laptop: mic or keyboard → RealtimeSTT (Silero VAD + faster-whisper) → Qwen 3.5 0.8B (llama.cpp) → Piper → speaker
                                                               │ tool call (MQTT home/cmd)
Raspberry Pi: Mosquitto + pi/bridge.py ────────────────────────┘
                                │ room/light/main, room/fan
ESP8266 net switch ─────────────┘ → relays
```

## Run

```bash
./run-llm.sh                                       # terminal 1: llama-server on :8080
MQTT_HOST=<pi-ip> uv run python -m assistant       # terminal 2: speak or type to it
```

Add `--text` to type only: no microphone, and it starts faster because Whisper isn't loaded.

`MQTT_HOST` defaults to `raspberrypi.local`, which works if your laptop resolves mDNS names.
The Pi needs to be set up first (see [Raspberry Pi hub](#raspberry-pi-hub)).

It listens all the time: speak, or type at the `>` prompt and press Enter. Ctrl+C quits.

Settings (models, silence timeout, prompts) live in `assistant/config.py`.
Use headphones, or the assistant may hear itself (it ignores the mic while speaking,
but echo right after can leak in).

## Voices

Without a voice file in `voices/`, replies are printed instead of spoken. Change `VOICE` in `assistant/config.py`. Official Piper voices download with:

```bash
uv run python -m piper.download_voices --data-dir voices en_GB-alan-medium
```

The Jarvis voice is a community model (MIT) from https://huggingface.co/jgkawell/jarvis —
grab `jarvis-high.onnx` + `.onnx.json` (or `medium`) into `voices/`.

## Device control

The model gets one tool per device (`set_light`, `set_fan`, from `DEVICES` in `assistant/tools.py`).
A call publishes `{"id": ..., "device": "light", "state": "ON"}` on `home/cmd` and waits up to
3 seconds for the Pi's answer on `home/reply/<id>`. The assistant then says whether it worked:
"the switch is offline", "the home hub didn't answer", and so on.

Test without the Pi: `MQTT_DRY_RUN=1 uv run python -m assistant`.

To add a device, add it to `DEVICES` in both `assistant/tools.py` (description for the model)
and `pi/bridge.py` (the ESP topic), and handle the topic in the firmware.

## Raspberry Pi hub

The Pi runs the MQTT broker that the laptop and the switch both connect to, plus `pi/bridge.py`.
The bridge checks each command, forwards it to the switch's topic, and waits for the switch
to confirm before answering. Give the Pi a fixed IP (a DHCP reservation in your router).

On the Pi (Raspberry Pi OS):

```bash
sudo apt install mosquitto python3-venv
sudo cp mosquitto.conf /etc/mosquitto/conf.d/home.conf
sudo systemctl restart mosquitto
mkdir -p ~/home-bridge && cp bridge.py ~/home-bridge/
python3 -m venv ~/home-bridge/venv && ~/home-bridge/venv/bin/pip install paho-mqtt
sudo cp home-bridge.service /etc/systemd/system/
sudo systemctl enable --now home-bridge
journalctl -u home-bridge -f    # watch commands arrive
```

(Copy the `pi/` folder over first, e.g. `scp -r pi pi@<pi-ip>:`. The service file assumes the
user `pi`; edit `User=` and the paths if yours is different.)

Then point the switch at the Pi: open `http://<switch-ip>/config`, set **MQTT Server** to the
Pi's IP and click **Apply & Reconnect**. The status page should show MQTT connected.

Switch confirmations need the current firmware in [`Node/net_switch`](../Node/net_switch), which
publishes `online`/`offline` on `room/switch/status` (as its MQTT will) and the new state on
`<topic>/state` after each change. Older firmware still works, but commands go unconfirmed.
