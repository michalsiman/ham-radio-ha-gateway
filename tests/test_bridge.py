import asyncio
import json
import unittest

from hamgw.bridge import Bridge
from hamgw.config import config_from_dict

from .fakes import FakeJs8Call, FakeMqtt, FakeRigctld, wait_for


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.rig = FakeRigctld()
        self.js8 = FakeJs8Call()
        await self.rig.start()
        await self.js8.start()
        self.mqtt = FakeMqtt()
        self.bridges = []

    async def asyncTearDown(self):
        for b in self.bridges:
            await b.rig.close()
        await self.rig.stop()
        await self.js8.stop()

    def bridge(self, **js8):
        config = config_from_dict({
            "device_name": "IC-7300",
            "rig": {"port": self.rig.port, "model": "Icom IC-7300", "power_control": True},
            "js8call": {"port": self.js8.port, **js8},
        })
        bridge = Bridge(config, self.mqtt)
        self.bridges.append(bridge)
        return bridge

    async def test_announce_and_poll(self):
        b = self.bridge()
        b.announce()
        self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/status"), "online")
        self.assertIn("ham-gateway/ic_7300/rig/frequency/set", self.mqtt.subscribed)
        await b.poll_rig_once()
        self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/rig/frequency"), "14.074000")
        self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/rig/online"), "ON")
        count = len(self.mqtt.published)
        await b.poll_rig_once()
        self.assertEqual(len(self.mqtt.published), count, "unchanged state is not republished")
        self.rig.power = 0
        await b.poll_rig_once()
        self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/rig/online"), "OFF")
        self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/rig/transmitting"), "OFF")

    async def test_commands(self):
        b = self.bridge()
        await b.on_command("ham-gateway/ic_7300/rig/frequency/set", "7.0785")
        self.assertEqual(self.rig.frequency, 7_078_500)
        self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/rig/frequency"), "7.078500")
        await b.on_command("ham-gateway/ic_7300/rig/mode/set", "lsb")
        self.assertEqual(self.rig.mode, "LSB")
        await b.on_command("ham-gateway/ic_7300/rig/mode/set", "NOPE")
        self.assertEqual(self.rig.mode, "LSB")
        self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/rig/tx_power"), "50")
        await b.on_command("ham-gateway/ic_7300/rig/tx_power/set", "25")
        self.assertAlmostEqual(self.rig.rfpower, 0.25)
        self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/rig/tx_power"), "25")
        await b.on_command("ham-gateway/ic_7300/rig/tx_power/set", "150")
        self.assertAlmostEqual(self.rig.rfpower, 0.25)
        await b.on_command("ham-gateway/ic_7300/rig/power/set", "OFF")
        self.assertEqual(self.rig.power, 0)

    async def test_js8_messages_and_transmit_guard(self):
        b = self.bridge(groups=["@OK"])
        task = asyncio.create_task(b.run_js8())
        try:
            await wait_for(lambda: self.mqtt.last("ham-gateway/ic_7300/js8call/callsign") == "OK1SIM")
            self.assertEqual(self.mqtt.last("ham-gateway/ic_7300/js8call/connected"), "ON")
            await self.js8.send({"type": "RX.DIRECTED", "value": "OK1ABC: OK1SIM HI",
                                 "params": {"FROM": "OK1ABC", "TO": "OK1SIM", "TEXT": "HI", "SNR": -10}})
            await self.js8.send({"type": "RX.DIRECTED", "value": "OK1ABC: @ALLCALL CQ",
                                 "params": {"FROM": "OK1ABC", "TO": "@ALLCALL", "TEXT": "CQ"}})
            await wait_for(lambda: len(self.mqtt.all("ham-gateway/ic_7300/js8call/message")) == 2)
            to_me = json.loads(self.mqtt.last("ham-gateway/ic_7300/js8call/message_to_me"))
            self.assertEqual((to_me["from"], to_me["text"]), ("OK1ABC", "HI"))
            events = [json.loads(p)["event_type"] for p in self.mqtt.all("ham-gateway/ic_7300/js8call/event")]
            self.assertEqual(events, ["message", "message_to_me", "message"])
            # Transmit is off by default: nothing reaches JS8Call.
            await b.on_command("ham-gateway/ic_7300/js8call/send/set", "OK1ABC TNX")
            await asyncio.sleep(0.05)
            self.assertFalse(any(r["type"] == "TX.SEND_MESSAGE" for r in self.js8.received))
            b.config.js8call.allow_transmit = True
            await b.on_command("ham-gateway/ic_7300/js8call/send/set", "OK1ABC TNX")
            await wait_for(lambda: any(r["type"] == "TX.SEND_MESSAGE" for r in self.js8.received))
        finally:
            task.cancel()

    def test_config_rejects_typos(self):
        with self.assertRaises(ValueError):
            config_from_dict({"rig": {"prot": 4532}})
