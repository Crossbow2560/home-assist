# Local voice assistant

Fully offline, on your LAN:

```
laptop: mic → RealtimeSTT (Silero VAD + faster-whisper) → Qwen 3.5 0.8B (llama.cpp) → Piper → speaker
                                                               │ tool call (MQTT home/cmd)
Raspberry Pi: Mosquitto + pi/bridge.py ────────────────────────┘
                                │ room/light/main, room/fan
ESP8266 net switch ─────────────┘ → relays
```

## Run

```bash
./run-llm.sh                                       # terminal 1: llama-server on :8080
MQTT_HOST=<pi-ip> uv run python -m assistant       # terminal 2: talk to it
```

`MQTT_HOST` defaults to `raspberrypi.local`, which works if your laptop resolves mDNS names.
The Pi needs to be set up first (see [Raspberry Pi hub](#raspberry-pi-hub)).

Clap twice to wake it (you'll hear a chime), then speak. After it replies you have
5 seconds to say something else without clapping again. Set `CLAP_WAKE = False` to always listen.

Settings (models, silence timeout, prompts, clap thresholds) live in `assistant/config.py`.
Use headphones, or the assistant may hear itself (it ignores the mic while speaking,
but echo right after can leak in).

## Voices

Change `VOICE` in `assistant/config.py`. Official Piper voices download with:

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

Switch confirmations need the firmware from
[Crossbow2560/home-assist](https://github.com/Crossbow2560/home-assist) (`Node/net_switch`) to
publish `online`/`offline` on `room/switch/status` (as its MQTT will) and the new state on
`<topic>/state` after each change. Older firmware still works, but commands go unconfirmed.

## Clap wake

`assistant/claps.py` listens for two sharp, high-pitched sounds 0.2–0.8 s apart, each followed
by quiet, with no other sharp sounds around them (so typing and applause don't count).
To tune it for your room, run the calibration mode and clap:

```bash
uv run python -m assistant.claps
```

It prints every candidate with its readings and why it was rejected. If real claps show
`too low-pitched` or `sound kept going`, relax `CLAP_MIN_HIGH_RATIO` or `CLAP_QUIET_RATIO`;
if they don't show up at all, lower `CLAP_MIN_RMS` or `CLAP_RISE_RATIO`.
