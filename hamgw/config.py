"""Configuration: a YAML file, see config.example.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field

from .ha import DEFAULT_MODES, slug


@dataclass
class MqttConfig:
    host: str = "homeassistant.local"
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = ""


@dataclass
class RigConfig:
    host: str = "127.0.0.1"
    port: int = 4532
    model: str = "Radio"
    poll_seconds: float = 2.0
    # Ask the radio whether it is switched on (not every radio/Hamlib backend answers).
    read_power: bool = True
    # Offer a power switch in Home Assistant (\set_powerstat).
    power_control: bool = False
    modes: list[str] = field(default_factory=lambda: list(DEFAULT_MODES))
    # Passband for mode changes; 0 = the radio's default for the mode.
    passband_hz: int = 0
    # The radio's maximum transmit power, to show the power setting in watts.
    max_power_w: float = 100


@dataclass
class Js8Config:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 2442
    # Your callsign; empty = take it from JS8Call.
    callsign: str = ""
    # Groups you count as "to me", e.g. ["@OK"].
    groups: list[str] = field(default_factory=list)
    # Let Home Assistant queue messages for transmission. Off by default:
    # anything sent this way transmits without you at the radio.
    allow_transmit: bool = False


@dataclass
class Config:
    device_name: str = "HF radio"
    device_id: str = ""
    base_topic: str = ""
    discovery_prefix: str = "homeassistant"
    log_level: str = "INFO"
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    rig: RigConfig = field(default_factory=RigConfig)
    js8call: Js8Config = field(default_factory=Js8Config)

    def __post_init__(self) -> None:
        if not self.device_id:
            self.device_id = slug(self.device_name)
        if not self.base_topic:
            self.base_topic = f"ham-gateway/{self.device_id}"


def _section(cls, data: dict | None):
    data = dict(data or {})
    known = {f for f in cls.__dataclass_fields__}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"unknown {cls.__name__} option(s): {', '.join(sorted(unknown))}")
    return cls(**data)


def config_from_dict(data: dict) -> Config:
    data = dict(data or {})
    sections = {
        "mqtt": _section(MqttConfig, data.pop("mqtt", None)),
        "rig": _section(RigConfig, data.pop("rig", None)),
        "js8call": _section(Js8Config, data.pop("js8call", None)),
    }
    config = _section(Config, data)
    config.mqtt, config.rig, config.js8call = sections["mqtt"], sections["rig"], sections["js8call"]
    config.rig.modes = [m.upper() for m in config.rig.modes]
    return config


def load_config(path: str) -> Config:
    import yaml  # python3-yaml

    with open(path, encoding="utf-8") as handle:
        return config_from_dict(yaml.safe_load(handle) or {})
