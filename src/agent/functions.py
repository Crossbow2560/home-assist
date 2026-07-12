from langchain_core.tools import tool
import subprocess
from pydantic import BaseModel

class SwitchInput(BaseModel):
    target: str
    status: str


MQTT_HOST = "192.168.0.107"
MQTT_PORT = 1883

TOPICS = ['room/light/main', 'room/fan']

@tool(args_schema=SwitchInput)
def switch(target: str, status: str) -> str:
    """Turn a device on or off.

    Args:
        target: The device to control
        status: Desired state — 'ON' or 'OFF'.
    """
    if target not in TOPICS:
        return f"Unknown device '{target}'. Valid targets: {TOPICS}"

    status_upper = status.upper()
    if status_upper not in ("ON", "OFF"):
        return f"Invalid status '{status}'. Use 'ON' or 'OFF'."

    subprocess.run(["mosquitto_pub", "-h", MQTT_HOST, "-t", target, "-m", status_upper])
    return f"{target.capitalize()} turned {status_upper}."

tools = [switch]
