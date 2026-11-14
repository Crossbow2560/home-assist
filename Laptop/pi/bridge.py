"""Home hub bridge for the Raspberry Pi.

The laptop assistant publishes a command like {"id": "ab12", "device": "light", "state": "ON"}
on home/cmd. The bridge forwards it to the ESP8266 net switch's topic, waits for the switch
to confirm, and answers on home/reply/<id> with {"ok": true} or {"ok": false, "error": "..."}.

The switch announces itself on room/switch/status ("online", or "offline" via its MQTT will)
and confirms each change on <topic>/state. Firmware that doesn't report either still works:
commands are forwarded unconfirmed.

Run: MQTT_HOST=localhost python3 bridge.py
"""

import json
import os
import threading

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
CMD_TOPIC = "home/cmd"
REPLY_TOPIC = "home/reply"
STATUS_TOPIC = "room/switch/status"
CONFIRM_TIMEOUT_S = 2

# Device name the assistant uses -> topic the ESP subscribes to.
DEVICES = {
    "light": "room/light/main",
    "fan": "room/fan",
}

switch_status: str | None = None  # None until the switch first reports
states: dict[str, str] = {}  # last confirmed state per device
changed = threading.Condition()


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to {MQTT_HOST}:{MQTT_PORT} ({reason_code})", flush=True)
    client.subscribe([(CMD_TOPIC, 1), (STATUS_TOPIC, 1)] + [(f"{t}/state", 1) for t in DEVICES.values()])


def on_message(client, userdata, msg):
    global switch_status
    payload = msg.payload.decode(errors="replace").strip()
    if msg.topic == CMD_TOPIC:
        # Wait for the confirmation off the network thread, so it can still receive it.
        threading.Thread(target=handle_command, args=(client, payload), daemon=True).start()
        return
    with changed:
        if msg.topic == STATUS_TOPIC:
            switch_status = payload
            print(f"Switch is {payload}", flush=True)
        else:
            for device, topic in DEVICES.items():
                if msg.topic == f"{topic}/state":
                    states[device] = payload
        changed.notify_all()


def handle_command(client, payload: str):
    try:
        command = json.loads(payload)
        request_id = str(command["id"])
    except (json.JSONDecodeError, KeyError, TypeError):
        print(f"Ignoring malformed command: {payload!r}", flush=True)
        return
    reply = run(client, command.get("device"), str(command.get("state", "")).upper())
    print(f"{command.get('device')} {command.get('state')} -> {reply}", flush=True)
    client.publish(f"{REPLY_TOPIC}/{request_id}", json.dumps(reply), qos=1)


def run(client, device, state: str) -> dict:
    if device not in DEVICES:
        return {"ok": False, "error": f"I don't know a device called {device}."}
    if state not in ("ON", "OFF"):
        return {"ok": False, "error": f"I can only turn the {device} on or off."}
    if switch_status == "offline":
        return {"ok": False, "error": "The switch is offline."}

    with changed:
        states.pop(device, None)
    client.publish(DEVICES[device], state)
    if switch_status is None:
        return {"ok": True, "confirmed": False}

    with changed:
        confirmed = changed.wait_for(lambda: states.get(device) == state, CONFIRM_TIMEOUT_S)
    if confirmed:
        return {"ok": True, "confirmed": True}
    return {"ok": False, "error": f"The switch didn't confirm the {device}."}


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="home-bridge")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
