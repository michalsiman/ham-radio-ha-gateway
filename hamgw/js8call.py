"""Read and send messages through JS8Call's TCP API.

JS8Call (File → Settings → Reporting → API) can serve its events as JSON,
one object per line, on TCP port 2442: {"type": ..., "value": ...,
"params": {...}}. The same connection takes commands such as
TX.SEND_MESSAGE.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

_LOGGER = logging.getLogger(__name__)


@dataclass
class Js8Message:
    """A directed message heard by JS8Call (RX.DIRECTED)."""

    sender: str
    to: str
    text: str
    snr: int | None = None
    frequency_hz: int | None = None
    offset_hz: int | None = None
    grid: str = ""
    utc_ms: int | None = None
    raw: str = ""

    def as_dict(self) -> dict:
        return {
            "from": self.sender,
            "to": self.to,
            "text": self.text,
            "snr": self.snr,
            "frequency_hz": self.frequency_hz,
            "offset_hz": self.offset_hz,
            "grid": self.grid,
            "utc_ms": self.utc_ms,
            "raw": self.raw,
        }


@dataclass
class Js8Spot:
    """A station JS8Call heard (RX.SPOT)."""

    call: str
    snr: int | None = None
    grid: str = ""
    frequency_hz: int | None = None
    offset_hz: int | None = None
    utc_ms: int | None = None

    def as_dict(self) -> dict:
        return {
            "call": self.call,
            "snr": self.snr,
            "grid": self.grid,
            "frequency_hz": self.frequency_hz,
            "offset_hz": self.offset_hz,
            "utc_ms": self.utc_ms,
        }


@dataclass
class Js8Event:
    """One parsed API event: kind is 'message', 'spot', 'callsign' or 'other'."""

    kind: str
    message: Js8Message | None = None
    spot: Js8Spot | None = None
    callsign: str | None = None
    raw: dict = field(default_factory=dict)


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_event(line: str) -> Js8Event | None:
    """Turn one API line into an event; None for lines that are not JSON objects."""
    try:
        data = json.loads(line)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    kind = str(data.get("type", ""))
    params = data.get("params") or {}
    if not isinstance(params, dict):
        params = {}
    if kind == "RX.DIRECTED":
        text = str(params.get("TEXT") or "")
        value = str(data.get("value") or "")
        return Js8Event(
            "message",
            message=Js8Message(
                sender=str(params.get("FROM") or ""),
                to=str(params.get("TO") or ""),
                text=text.strip() or value.strip(),
                snr=_int(params.get("SNR")),
                frequency_hz=_int(params.get("FREQ")),
                offset_hz=_int(params.get("OFFSET")),
                grid=str(params.get("GRID") or "").strip(),
                utc_ms=_int(params.get("UTC")),
                raw=value,
            ),
            raw=data,
        )
    if kind == "RX.SPOT":
        return Js8Event(
            "spot",
            spot=Js8Spot(
                call=str(params.get("CALL") or data.get("value") or ""),
                snr=_int(params.get("SNR")),
                grid=str(params.get("GRID") or "").strip(),
                frequency_hz=_int(params.get("FREQ")),
                offset_hz=_int(params.get("OFFSET")),
                utc_ms=_int(params.get("UTC")),
            ),
            raw=data,
        )
    if kind == "STATION.CALLSIGN":
        return Js8Event("callsign", callsign=str(data.get("value") or "").strip(), raw=data)
    return Js8Event("other", raw=data)


def addressed_to(message: Js8Message, callsign: str, groups: list[str] | None = None) -> bool:
    """True when the message is for our callsign (any SSID/suffix) or one of our groups."""
    if not callsign:
        return False
    to = message.to.upper().strip()
    base = callsign.upper().split("/")[0]
    if to == callsign.upper() or to.split("/")[0] == base:
        return True
    return any(to == g.upper() for g in (groups or []))


class Js8CallClient:
    """Keeps a connection to JS8Call's API, reconnecting when it drops."""

    def __init__(
        self,
        host: str,
        port: int = 2442,
        on_event: Callable[[Js8Event], Awaitable[None]] | None = None,
        on_connection: Callable[[bool], Awaitable[None]] | None = None,
        retry_seconds: float = 10.0,
    ) -> None:
        self.host = host
        self.port = port
        self.on_event = on_event
        self.on_connection = on_connection
        self.retry_seconds = retry_seconds
        self._writer: asyncio.StreamWriter | None = None
        self.connected = False

    async def run(self) -> None:
        """Connect, read events forever, reconnect after errors."""
        while True:
            try:
                reader, self._writer = await asyncio.open_connection(self.host, self.port)
                await self._set_connected(True)
                await self.send_command("STATION.GET_CALLSIGN")
                while True:
                    raw = await reader.readline()
                    if not raw:
                        break
                    event = parse_event(raw.decode(errors="replace"))
                    if event and self.on_event:
                        await self.on_event(event)
            except (ConnectionError, OSError) as err:
                _LOGGER.debug("JS8Call API: %s", err)
            finally:
                self._writer = None
                await self._set_connected(False)
            await asyncio.sleep(self.retry_seconds)

    async def _set_connected(self, connected: bool) -> None:
        if connected != self.connected:
            self.connected = connected
            _LOGGER.info("JS8Call API %s", "connected" if connected else "disconnected")
            if self.on_connection:
                await self.on_connection(connected)

    async def send_command(self, kind: str, value: str = "", params: dict | None = None) -> None:
        if self._writer is None:
            raise ConnectionError("JS8Call is not connected")
        line = json.dumps({"type": kind, "value": value, "params": params or {}}) + "\n"
        self._writer.write(line.encode())
        await self._writer.drain()

    async def send_message(self, text: str) -> None:
        """Queue a message for transmission, e.g. "OK1ABC hello" or "@ALLCALL CQ"."""
        await self.send_command("TX.SEND_MESSAGE", text)
