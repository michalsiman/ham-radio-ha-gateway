"""A fake rigctld and a fake JS8Call API server, and a fake MQTT client."""

from __future__ import annotations

import asyncio
import json


async def _stop_server(server, writers) -> None:
    """Close the clients too: since Python 3.12 wait_closed() waits for them."""
    for w in writers:
        w.close()
    if server is None:
        return
    server.close()
    if hasattr(server, "close_clients"):
        server.close_clients()
    try:
        await asyncio.wait_for(server.wait_closed(), 2)
    except asyncio.TimeoutError:
        pass


class FakeRigctld:
    """Speaks the plain rigctld protocol for the commands the gateway uses."""

    def __init__(self) -> None:
        self.frequency = 14_074_000
        self.mode = "PKTUSB"
        self.passband = 3000
        self.ptt = 0
        self.strength = -54
        self.rfpower = 0.5
        self.power = 1
        self.powerstat_supported = True
        self.commands: list[str] = []
        self.writers: list[asyncio.StreamWriter] = []
        self.server: asyncio.base_events.Server | None = None
        self.port = 0

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._client, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        await _stop_server(self.server, self.writers)
        self.server = None

    def _answer(self, cmd: str) -> list[str]:
        self.commands.append(cmd)
        off = not self.power
        if cmd == "\\get_powerstat":
            return [str(self.power)] if self.powerstat_supported else ["RPRT -11"]
        if off:
            return ["RPRT -5"]
        if cmd == "f":
            return [str(self.frequency)]
        if cmd == "m":
            return [self.mode, str(self.passband)]
        if cmd == "t":
            return [str(self.ptt)]
        if cmd == "l STRENGTH":
            return [str(self.strength)]
        if cmd == "l RFPOWER":
            return [f"{self.rfpower:.6f}"]
        parts = cmd.split()
        if parts[0] == "F":
            self.frequency = int(parts[1])
            return ["RPRT 0"]
        if parts[:2] == ["L", "RFPOWER"]:
            self.rfpower = float(parts[2])
            return ["RPRT 0"]
        if parts[0] == "M":
            self.mode = parts[1]
            return ["RPRT 0"]
        if parts[0] == "\\set_powerstat":
            self.power = int(parts[1])
            return ["RPRT 0"]
        return ["RPRT -1"]

    async def _client(self, reader, writer) -> None:
        self.writers.append(writer)
        while True:
            line = await reader.readline()
            if not line:
                break
            for out in self._answer(line.decode().strip()):
                writer.write((out + "\n").encode())
            await writer.drain()
        writer.close()


class FakeJs8Call:
    """Accepts one API client; sends events, records commands."""

    def __init__(self) -> None:
        self.received: list[dict] = []
        self.writers: list[asyncio.StreamWriter] = []
        self.server = None
        self.port = 0

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._client, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        await _stop_server(self.server, self.writers)
        self.server = None

    async def send(self, event: dict) -> None:
        for w in self.writers:
            w.write((json.dumps(event) + "\n").encode())
            await w.drain()

    async def _client(self, reader, writer) -> None:
        self.writers.append(writer)
        while True:
            line = await reader.readline()
            if not line:
                break
            data = json.loads(line)
            self.received.append(data)
            if data.get("type") == "STATION.GET_CALLSIGN":
                writer.write((json.dumps({"type": "STATION.CALLSIGN", "value": "OK1SIM", "params": {}}) + "\n").encode())
                await writer.drain()


class FakeMqtt:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, bool]] = []
        self.subscribed: list[str] = []

    def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        self.published.append((topic, payload, retain))

    def subscribe(self, topic: str) -> None:
        self.subscribed.append(topic)

    def last(self, topic: str) -> str | None:
        for t, p, _ in reversed(self.published):
            if t == topic:
                return p
        return None

    def all(self, topic: str) -> list[str]:
        return [p for t, p, _ in self.published if t == topic]


async def wait_for(predicate, timeout: float = 2.0) -> None:
    end = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > end:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.01)
