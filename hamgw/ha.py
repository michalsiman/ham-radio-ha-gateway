"""Home Assistant MQTT discovery: which entities the gateway creates, and their topics.

Pure functions, no network, so the payloads can be tested on their own.
Every entity belongs to one HA device and goes unavailable with the
gateway (the MQTT last will sets <base>/status to "offline").
"""

from __future__ import annotations

import json
import re

DEFAULT_MODES = ["USB", "LSB", "CW", "CWR", "AM", "FM", "RTTY", "PKTUSB", "PKTLSB"]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "radio"


class Topics:
    """MQTT topics under one base, e.g. ham-gateway/ic7300."""

    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    @property
    def status(self) -> str:
        return f"{self.base}/status"

    def rig(self, key: str) -> str:
        return f"{self.base}/rig/{key}"

    def rig_command(self, key: str) -> str:
        return f"{self.base}/rig/{key}/set"

    def js8(self, key: str) -> str:
        return f"{self.base}/js8call/{key}"

    def js8_command(self, key: str) -> str:
        return f"{self.base}/js8call/{key}/set"


def discovery_configs(
    *,
    device_name: str,
    device_id: str,
    model: str,
    topics: Topics,
    discovery_prefix: str = "homeassistant",
    modes: list[str] | None = None,
    js8call: bool = True,
    allow_transmit: bool = False,
    power_control: bool = False,
    version: str = "",
) -> list[tuple[str, dict]]:
    """(config topic, payload) for every entity; an empty payload removes one."""
    device = {
        "identifiers": [f"hamgw_{device_id}"],
        "name": device_name,
        "model": model,
        "manufacturer": "ham-radio-ha-gateway",
        "sw_version": version,
    }
    availability = {"availability_topic": topics.status, "payload_available": "online", "payload_not_available": "offline"}

    def entity(component: str, key: str, payload: dict) -> tuple[str, dict]:
        unique = f"hamgw_{device_id}_{key}"
        # Entity ids come from the device and entity names, e.g. sensor.ic_7300_frequency.
        config = {"unique_id": unique, "device": device, **availability, **payload}
        return f"{discovery_prefix}/{component}/{unique}/config", config

    configs = [
        entity("binary_sensor", "online", {
            "name": "Online", "device_class": "connectivity",
            "state_topic": topics.rig("online"), "payload_on": "ON", "payload_off": "OFF",
        }),
        entity("sensor", "frequency", {
            "name": "Frequency", "device_class": "frequency", "unit_of_measurement": "MHz",
            "suggested_display_precision": 4, "state_class": "measurement",
            "state_topic": topics.rig("frequency"), "icon": "mdi:sine-wave",
        }),
        entity("number", "frequency_set", {
            "name": "Tune", "unit_of_measurement": "MHz", "mode": "box",
            "min": 0.1, "max": 470, "step": 0.0001, "icon": "mdi:knob",
            "state_topic": topics.rig("frequency"), "command_topic": topics.rig_command("frequency"),
        }),
        entity("sensor", "mode", {"name": "Mode", "state_topic": topics.rig("mode"), "icon": "mdi:waveform"}),
        entity("select", "mode_set", {
            "name": "Set mode", "options": modes or DEFAULT_MODES, "icon": "mdi:waveform",
            "state_topic": topics.rig("mode"), "command_topic": topics.rig_command("mode"),
        }),
        entity("binary_sensor", "transmitting", {
            "name": "Transmitting", "icon": "mdi:radio-tower",
            "state_topic": topics.rig("transmitting"), "payload_on": "ON", "payload_off": "OFF",
        }),
        entity("sensor", "s_meter", {
            "name": "S-meter", "unit_of_measurement": "dB", "state_class": "measurement",
            "icon": "mdi:signal", "state_topic": topics.rig("s_meter"),
        }),
    ]
    if power_control:
        configs.append(entity("switch", "power", {
            "name": "Power", "icon": "mdi:power",
            "state_topic": topics.rig("power"), "command_topic": topics.rig_command("power"),
            "payload_on": "ON", "payload_off": "OFF",
        }))
    else:
        configs.append((f"{discovery_prefix}/switch/hamgw_{device_id}_power/config", {}))

    if js8call:
        configs += [
            entity("binary_sensor", "js8call", {
                "name": "JS8Call", "device_class": "connectivity",
                "state_topic": topics.js8("connected"), "payload_on": "ON", "payload_off": "OFF",
            }),
            entity("sensor", "js8_callsign", {"name": "JS8Call callsign", "icon": "mdi:card-account-details", "state_topic": topics.js8("callsign")}),
            entity("sensor", "js8_last_message", {
                "name": "JS8 last message", "icon": "mdi:message-text",
                "state_topic": topics.js8("message"), "value_template": "{{ value_json.text[:255] }}",
                "json_attributes_topic": topics.js8("message"),
            }),
            entity("sensor", "js8_last_message_to_me", {
                "name": "JS8 last message to me", "icon": "mdi:message-alert",
                "state_topic": topics.js8("message_to_me"), "value_template": "{{ value_json.text[:255] }}",
                "json_attributes_topic": topics.js8("message_to_me"),
            }),
            entity("sensor", "js8_last_heard", {
                "name": "JS8 last heard", "icon": "mdi:account-voice",
                "state_topic": topics.js8("heard"), "value_template": "{{ value_json.call }}",
                "json_attributes_topic": topics.js8("heard"),
            }),
            entity("event", "js8_event", {
                "name": "JS8Call", "icon": "mdi:message-flash",
                "event_types": ["message", "message_to_me", "heard"],
                "state_topic": topics.js8("event"),
            }),
        ]
        if allow_transmit:
            configs.append(entity("text", "js8_send", {
                "name": "JS8 send", "icon": "mdi:send", "max": 255,
                "command_topic": topics.js8_command("send"),
            }))
        else:
            configs.append((f"{discovery_prefix}/text/hamgw_{device_id}_js8_send/config", {}))
    return configs


def encode(payload) -> str:
    """MQTT payload text: dicts as JSON, booleans as ON/OFF, None as empty."""
    if payload is None:
        return ""
    if isinstance(payload, bool):
        return "ON" if payload else "OFF"
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, ensure_ascii=False)
    return str(payload)


def mhz(hz: int | None) -> str | None:
    return None if hz is None else f"{hz / 1_000_000:.6f}"


def parse_mhz(text: str) -> int:
    """'14.074' or '14074000' (Hz) → Hz. Raises ValueError."""
    value = float(text.strip().replace(",", "."))
    if value <= 0:
        raise ValueError("frequency must be positive")
    return int(round(value * 1_000_000)) if value < 10_000 else int(round(value))
