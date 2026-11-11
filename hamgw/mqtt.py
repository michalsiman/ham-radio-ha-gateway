"""MQTT through paho-mqtt (python3-paho-mqtt), bridged into asyncio."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import paho.mqtt.client as paho

_LOGGER = logging.getLogger(__name__)


class PahoMqtt:
    """Connects with a last will, reconnects by itself, hands messages to a coroutine."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        client_id: str,
        will_topic: str,
        loop: asyncio.AbstractEventLoop,
        on_message: Callable[[str, str], Awaitable[None]],
        on_connect: Callable[[], None],
    ) -> None:
        self._loop = loop
        self._on_message = on_message
        self._on_connect = on_connect
        try:  # paho-mqtt 2.x
            self._client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=client_id)
        except AttributeError:  # paho-mqtt 1.x
            self._client = paho.Client(client_id=client_id)
        if username:
            self._client.username_pw_set(username, password)
        self._client.will_set(will_topic, "offline", retain=True)
        self._client.reconnect_delay_set(1, 60)
        self._client.on_connect = self._connected
        self._client.on_disconnect = self._disconnected
        self._client.on_message = self._message
        self._host, self._port = host, port

    def start(self) -> None:
        self._client.connect_async(self._host, self._port, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        self._client.publish(topic, payload, qos=1 if retain else 0, retain=retain)

    def subscribe(self, topic: str) -> None:
        self._client.subscribe(topic, qos=1)

    # paho calls these from its own thread.
    def _connected(self, client, userdata, flags, reason_code, properties=None) -> None:
        code = getattr(reason_code, "value", reason_code)
        if code == 0:
            _LOGGER.info("MQTT connected to %s:%s", self._host, self._port)
            self._loop.call_soon_threadsafe(self._on_connect)
        else:
            _LOGGER.error("MQTT connection refused: %s", reason_code)

    def _disconnected(self, client, userdata, *args) -> None:
        _LOGGER.warning("MQTT disconnected; reconnecting")

    def _message(self, client, userdata, message) -> None:
        payload = message.payload.decode(errors="replace")
        asyncio.run_coroutine_threadsafe(self._on_message(message.topic, payload), self._loop)
