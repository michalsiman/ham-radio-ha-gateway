"""The gateway itself: poll the radio, follow JS8Call, publish to MQTT, act on commands.

The MQTT client is passed in (see hamgw.mqtt for the real one), so the
bridge can be tested with a fake.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Protocol

from . import __version__
from .config import Config
from .ha import Topics, discovery_configs, encode, mhz, parse_mhz
from .js8call import Js8CallClient, Js8Event, addressed_to
from .rig import RigctldClient, RigError, RigState

_LOGGER = logging.getLogger(__name__)


class MqttLike(Protocol):
    def publish(self, topic: str, payload: str, retain: bool = False) -> None: ...
    def subscribe(self, topic: str) -> None: ...


class Bridge:
    def __init__(self, config: Config, mqtt: MqttLike, rig: RigctldClient | None = None) -> None:
        self.config = config
        self.mqtt = mqtt
        self.topics = Topics(config.base_topic)
        self.rig = rig or RigctldClient(config.rig.host, config.rig.port)
        self.js8: Js8CallClient | None = None
        if config.js8call.enabled:
            self.js8 = Js8CallClient(
                config.js8call.host, config.js8call.port,
                on_event=self.on_js8_event, on_connection=self.on_js8_connection,
            )
        self.callsign = config.js8call.callsign.upper()
        self._published: dict[str, str] = {}
        self._last_state = RigState()

    # ── MQTT out ─────────────────────────────────────────────────────

    def _publish(self, topic: str, payload, retain: bool = True, force: bool = False) -> None:
        text = encode(payload)
        if not force and retain and self._published.get(topic) == text:
            return
        self._published[topic] = text
        self.mqtt.publish(topic, text, retain=retain)

    def announce(self) -> None:
        """Discovery configs, availability, subscriptions. Call after every (re)connect."""
        for topic, payload in discovery_configs(
            device_name=self.config.device_name,
            device_id=self.config.device_id,
            model=self.config.rig.model,
            topics=self.topics,
            discovery_prefix=self.config.discovery_prefix,
            modes=self.config.rig.modes,
            js8call=self.config.js8call.enabled,
            allow_transmit=self.config.js8call.allow_transmit,
            power_control=self.config.rig.power_control,
            version=__version__,
            max_power_w=self.config.rig.max_power_w,
        ):
            self.mqtt.publish(topic, encode(payload) if payload else "", retain=True)
        self.mqtt.publish(self.topics.status, "online", retain=True)
        for key in ("frequency", "mode", "power", "tx_power"):
            self.mqtt.subscribe(self.topics.rig_command(key))
        if self.config.js8call.enabled:
            self.mqtt.subscribe(self.topics.js8_command("send"))
        # Republish the last known state after a broker restart.
        published, self._published = self._published, {}
        for topic, text in published.items():
            self.mqtt.publish(topic, text, retain=True)
            self._published[topic] = text

    def publish_rig(self, state: RigState) -> None:
        t = self.topics
        self._publish(t.rig("online"), state.online)
        self._publish(t.rig("power"), bool(state.power_on))
        if state.online:
            self._publish(t.rig("frequency"), mhz(state.frequency_hz))
            if state.mode is not None:
                self._publish(t.rig("mode"), state.mode)
            if state.transmitting is not None:
                self._publish(t.rig("transmitting"), state.transmitting)
            if state.s_meter_db is not None:
                self._publish(t.rig("s_meter"), state.s_meter_db)
            if state.rf_power is not None:
                watts = state.rf_power * self.config.rig.max_power_w
                self._publish(t.rig("tx_power"), f"{watts:.1f}".rstrip("0").rstrip("."))
        else:
            self._publish(t.rig("transmitting"), False)
        self._last_state = state

    # ── radio ────────────────────────────────────────────────────────

    async def poll_rig_once(self) -> RigState:
        try:
            state = await self.rig.poll(read_power=self.config.rig.read_power)
        except RigError as err:
            _LOGGER.debug("rig poll: %s", err)
            state = RigState()
        if state.online != self._last_state.online:
            _LOGGER.info("radio %s", "online" if state.online else "offline")
        self.publish_rig(state)
        return state

    async def run_rig(self) -> None:
        while True:
            await self.poll_rig_once()
            await asyncio.sleep(self.config.rig.poll_seconds)

    # ── JS8Call ──────────────────────────────────────────────────────

    async def on_js8_connection(self, connected: bool) -> None:
        self._publish(self.topics.js8("connected"), connected)

    async def on_js8_event(self, event: Js8Event) -> None:
        t = self.topics
        now = int(time.time())
        if event.kind == "callsign" and event.callsign:
            if not self.config.js8call.callsign:
                self.callsign = event.callsign.upper()
            self._publish(t.js8("callsign"), event.callsign)
        elif event.kind == "message" and event.message:
            data = {**event.message.as_dict(), "received": now}
            self._publish(t.js8("message"), data, force=True)
            self._publish(t.js8("event"), {"event_type": "message", **data}, retain=False)
            if addressed_to(event.message, self.callsign, self.config.js8call.groups):
                self._publish(t.js8("message_to_me"), data, force=True)
                self._publish(t.js8("event"), {"event_type": "message_to_me", **data}, retain=False)
        elif event.kind == "spot" and event.spot and event.spot.call:
            data = {**event.spot.as_dict(), "received": now}
            self._publish(t.js8("heard"), data, force=True)
            self._publish(t.js8("event"), {"event_type": "heard", **data}, retain=False)

    async def run_js8(self) -> None:
        if self.js8 is not None:
            await self.js8.run()

    # ── commands from Home Assistant ─────────────────────────────────

    async def on_command(self, topic: str, payload: str) -> None:
        t = self.topics
        try:
            if topic == t.rig_command("frequency"):
                await self.rig.set_frequency(parse_mhz(payload))
            elif topic == t.rig_command("mode"):
                mode = payload.strip().upper()
                if mode not in self.config.rig.modes:
                    raise ValueError(f"unknown mode {mode!r}")
                await self.rig.set_mode(mode, self.config.rig.passband_hz)
            elif topic == t.rig_command("tx_power"):
                watts = float(payload.strip().replace(",", "."))
                if not 0 <= watts <= self.config.rig.max_power_w:
                    raise ValueError(f"power {watts} W is outside 0–{self.config.rig.max_power_w} W")
                await self.rig.set_rf_power(watts / self.config.rig.max_power_w)
            elif topic == t.rig_command("power"):
                if not self.config.rig.power_control:
                    raise ValueError("power control is off in the configuration")
                await self.rig.set_power(payload.strip().upper() in ("ON", "1", "TRUE"))
            elif topic == t.js8_command("send"):
                if not (self.config.js8call.enabled and self.config.js8call.allow_transmit):
                    raise ValueError("JS8Call transmit is off in the configuration")
                text = payload.strip()
                if not text:
                    return
                if self.js8 is None:
                    raise ValueError("JS8Call is off")
                await self.js8.send_message(text)
                _LOGGER.info("JS8Call: queued %r", text)
            else:
                return
        except (ValueError, RigError, ConnectionError) as err:
            _LOGGER.warning("command %s %r: %s", topic, payload, err)
            return
        await self.poll_rig_once()

    async def run(self) -> None:
        await asyncio.gather(self.run_rig(), self.run_js8())
