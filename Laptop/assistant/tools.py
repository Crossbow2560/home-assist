"""Tools the LLM can call. Device commands go over MQTT to the bridge on the Raspberry Pi
(pi/bridge.py), which switches the ESP8266 net switch and replies whether it worked."""

import json
import queue
import uuid

import paho.mqtt.client as mqtt

from . import config

# name -> description for the model. The Pi maps names to the ESP's topics.
# Each device becomes its own set_<name> tool; the 0.8B model picks the right
# device more reliably that way than with one shared tool taking a device argument.
DEVICES = {
    "light": "Turn the main ceiling light on or off.",
    "fan": "Turn the ceiling fan on or off.",
}

_client: mqtt.Client | None = None
_replies: dict[str, queue.Queue] = {}


def _on_message(client, userdata, msg):
    request_id = msg.topic.rsplit("/", 1)[-1]
    if waiter := _replies.get(request_id):
        waiter.put(msg.payload)


def connect() -> bool:
    """Connect to the broker on the Pi. Returns False if it can't be reached."""
    global _client
    if config.MQTT_DRY_RUN or _client:
        return True
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = _on_message
    try:
        client.connect(config.MQTT_HOST, config.MQTT_PORT)
    except OSError:
        return False
    client.subscribe(f"{config.REPLY_TOPIC}/+")
    client.loop_start()  # also reconnects on its own if the Pi drops
    _client = client
    return True


def set_device(device: str, state: str) -> str:
    state = str(state).upper()
    if state not in ("ON", "OFF"):
        return f"Invalid state '{state}' for the {device}. Use ON or OFF."

    if config.MQTT_DRY_RUN:
        print(f"  [dry run] mqtt {config.CMD_TOPIC} <- {device} {state}")
        return f"The {device} is now {state.lower()}."
    if not connect():
        return "Sorry, I can't reach the home hub."

    request_id = uuid.uuid4().hex[:8]
    waiter = _replies[request_id] = queue.Queue()
    try:
        command = {"id": request_id, "device": device, "state": state}
        _client.publish(config.CMD_TOPIC, json.dumps(command), qos=1)
        reply = json.loads(waiter.get(timeout=config.REPLY_TIMEOUT_S))
    except queue.Empty:
        return "Sorry, the home hub didn't answer."
    finally:
        del _replies[request_id]

    if reply.get("ok"):
        return f"The {device} is now {state.lower()}."
    return reply.get("error") or f"Sorry, I couldn't switch the {device}."


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": f"set_{name}",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {"state": {"type": "string", "enum": ["ON", "OFF"]}},
                "required": ["state"],
            },
        },
    }
    for name, description in DEVICES.items()
]


def call(name: str, arguments: str) -> str:
    device = name.removeprefix("set_")
    if device not in DEVICES:
        return f"Unknown tool '{name}'."
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return f"Sorry, I didn't catch what to do with the {device}."
    return set_device(device, args.get("state", ""))
