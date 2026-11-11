import unittest

from hamgw.rig import RigctldClient, RigError

from .fakes import FakeRigctld


class RigTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeRigctld()
        await self.fake.start()
        self.rig = RigctldClient("127.0.0.1", self.fake.port, timeout=1)

    async def asyncTearDown(self):
        await self.rig.close()
        await self.fake.stop()

    async def test_poll_reads_everything(self):
        state = await self.rig.poll()
        self.assertTrue(state.online)
        self.assertTrue(state.power_on)
        self.assertEqual(state.frequency_hz, 14_074_000)
        self.assertEqual((state.mode, state.passband_hz), ("PKTUSB", 3000))
        self.assertFalse(state.transmitting)
        self.assertEqual(state.s_meter_db, -54)

    async def test_radio_off_is_offline(self):
        self.fake.power = 0
        state = await self.rig.poll()
        self.assertFalse(state.online)
        self.assertFalse(state.power_on)
        self.assertIsNone(state.frequency_hz)

    async def test_without_powerstat_frequency_decides(self):
        self.fake.powerstat_supported = False
        state = await self.rig.poll()
        self.assertTrue(state.online)
        self.assertTrue(state.power_on)

    async def test_set_commands(self):
        await self.rig.set_frequency(7_078_000)
        await self.rig.set_mode("LSB", 0)
        self.assertEqual(self.fake.frequency, 7_078_000)
        self.assertEqual(self.fake.mode, "LSB")
        self.assertIn("F 7078000", self.fake.commands)

    async def test_failed_set_raises(self):
        with self.assertRaises(RigError):
            await self.rig.set("X nonsense")

    async def test_unreachable_rigctld(self):
        await self.fake.stop()
        rig = RigctldClient("127.0.0.1", 1, timeout=0.5)
        state = await rig.poll()
        self.assertFalse(state.online)
