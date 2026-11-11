"""Talk to a radio through Hamlib's rigctld over TCP.

rigctld owns the radio's CAT/CI-V port and shares it on the network, so
JS8Call, this gateway and other programs can use the radio at the same
time. The plain rigctld protocol is used: one command per line; a "get"
answers with its value lines, a "set" (or a failed command) with
"RPRT <code>", 0 meaning success.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


class RigError(Exception):
    """rigctld refused a command or could not be reached."""


@dataclass
class RigState:
    """What the gateway knows about the radio after one poll."""

    online: bool = False
    frequency_hz: int | None = None
    mode: str | None = None
    passband_hz: int | None = None
    transmitting: bool | None = None
    s_meter_db: int | None = None
    # Transmit power setting, 0.0–1.0 of the radio's maximum.
    rf_power: float | None = None
    power_on: bool | None = None
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "online": self.online,
            "frequency_hz": self.frequency_hz,
            "mode": self.mode,
            "passband_hz": self.passband_hz,
            "transmitting": self.transmitting,
            "s_meter_db": self.s_meter_db,
            "rf_power": self.rf_power,
            "power_on": self.power_on,
        }


# Lines of answer for each "get" command of the plain protocol.
_ANSWER_LINES = {
    "f": 1,
    "m": 2,
    "t": 1,
    "l STRENGTH": 1,
    "l RFPOWER": 1,
    "\\get_powerstat": 1,
}


class RigctldClient:
    """One TCP connection to rigctld; commands are sent one at a time."""

    def __init__(self, host: str, port: int = 4532, timeout: float = 3.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), self.timeout
        )

    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except (ConnectionError, OSError):
                pass
        self._reader = self._writer = None

    async def _command(self, command: str, answer_lines: int) -> list[str]:
        """Send a command; return its value lines, or raise RigError on RPRT != 0."""
        async with self._lock:
            try:
                if not self.connected:
                    await self.connect()
                assert self._reader is not None and self._writer is not None
                self._writer.write((command + "\n").encode())
                await self._writer.drain()
                lines: list[str] = []
                while len(lines) < max(answer_lines, 1):
                    raw = await asyncio.wait_for(self._reader.readline(), self.timeout)
                    if not raw:
                        raise ConnectionError("rigctld closed the connection")
                    line = raw.decode(errors="replace").strip()
                    if line.startswith("RPRT"):
                        code = int(line.split()[1]) if len(line.split()) > 1 else -1
                        if code != 0:
                            raise RigError(f"{command!r} failed: RPRT {code}")
                        return lines
                    lines.append(line)
                return lines
            except (asyncio.TimeoutError, ConnectionError, OSError) as err:
                await self.close()
                raise RigError(f"{command!r}: {err or type(err).__name__}") from err

    async def get(self, command: str) -> list[str]:
        return await self._command(command, _ANSWER_LINES.get(command, 1))

    async def set(self, command: str) -> None:
        await self._command(command, 0)

    # ── typed helpers ────────────────────────────────────────────────

    async def frequency(self) -> int:
        return int(float((await self.get("f"))[0]))

    async def mode(self) -> tuple[str, int | None]:
        lines = await self.get("m")
        passband = int(lines[1]) if len(lines) > 1 and lines[1].lstrip("-").isdigit() else None
        return lines[0], passband

    async def ptt(self) -> bool:
        return (await self.get("t"))[0] not in ("0", "")

    async def strength(self) -> int:
        return int(float((await self.get("l STRENGTH"))[0]))

    async def rf_power(self) -> float:
        return float((await self.get("l RFPOWER"))[0])

    async def set_rf_power(self, fraction: float) -> None:
        await self.set(f"L RFPOWER {max(0.0, min(1.0, fraction)):.3f}")

    async def power_status(self) -> bool:
        return (await self.get("\\get_powerstat"))[0] == "1"

    async def set_frequency(self, hz: int) -> None:
        await self.set(f"F {int(hz)}")

    async def set_mode(self, mode: str, passband: int = 0) -> None:
        await self.set(f"M {mode} {int(passband)}")

    async def set_power(self, on: bool) -> None:
        await self.set(f"\\set_powerstat {1 if on else 0}")

    async def poll(self, read_power: bool = True) -> RigState:
        """Read everything the radio reports. Offline when the radio doesn't answer."""
        state = RigState()
        if read_power:
            try:
                state.power_on = await self.power_status()
            except RigError:
                state.power_on = None
        try:
            state.frequency_hz = await self.frequency()
        except RigError:
            # Radio off, unplugged, or rigctld down: nothing else will answer.
            if state.power_on is None:
                state.power_on = False
            return state
        state.online = True
        if state.power_on is None:
            state.power_on = True
        for name, reader in (("mode", self.mode), ("ptt", self.ptt), ("strength", self.strength), ("rfpower", self.rf_power)):
            try:
                value = await reader()
            except RigError:
                continue
            if name == "mode":
                state.mode, state.passband_hz = value  # type: ignore[misc]
            elif name == "ptt":
                state.transmitting = value  # type: ignore[assignment]
            elif name == "rfpower":
                state.rf_power = value  # type: ignore[assignment]
            else:
                state.s_meter_db = value  # type: ignore[assignment]
        return state
