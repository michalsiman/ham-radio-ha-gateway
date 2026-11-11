import unittest

from hamgw.ha import Topics, discovery_configs, encode, mhz, parse_mhz


class DiscoveryTests(unittest.TestCase):
    def configs(self, **kw):
        return dict(discovery_configs(device_name="IC-7300", device_id="ic_7300", model="Icom IC-7300",
                                      topics=Topics("ham-gateway/ic_7300"), **kw))

    def test_entities_and_device(self):
        c = self.configs()
        freq = c["homeassistant/sensor/hamgw_ic_7300_frequency/config"]
        self.assertEqual(freq["state_topic"], "ham-gateway/ic_7300/rig/frequency")
        self.assertEqual(freq["availability_topic"], "ham-gateway/ic_7300/status")
        self.assertEqual(freq["device"]["identifiers"], ["hamgw_ic_7300"])
        self.assertIn("homeassistant/event/hamgw_ic_7300_js8_event/config", c)
        tune = c["homeassistant/number/hamgw_ic_7300_frequency_set/config"]
        self.assertGreaterEqual(tune["step"], 0.001, "Home Assistant rejects smaller steps")

    def test_transmit_and_power_are_opt_in(self):
        c = self.configs()
        self.assertEqual(c["homeassistant/text/hamgw_ic_7300_js8_send/config"], {})
        self.assertEqual(c["homeassistant/switch/hamgw_ic_7300_power/config"], {})
        c = self.configs(allow_transmit=True, power_control=True)
        self.assertEqual(c["homeassistant/text/hamgw_ic_7300_js8_send/config"]["command_topic"], "ham-gateway/ic_7300/js8call/send/set")
        self.assertIn("command_topic", c["homeassistant/switch/hamgw_ic_7300_power/config"])

    def test_without_js8call(self):
        c = self.configs(js8call=False)
        self.assertFalse(any("js8" in topic for topic in c))

    def test_encoding(self):
        self.assertEqual(encode(True), "ON")
        self.assertEqual(encode(None), "")
        self.assertEqual(encode({"a": "č"}), '{"a": "č"}')
        self.assertEqual(mhz(14074000), "14.074000")
        self.assertEqual(parse_mhz("14.074"), 14074000)
        self.assertEqual(parse_mhz("7,0785"), 7078500)
        self.assertEqual(parse_mhz("14074000"), 14074000)
        with self.assertRaises(ValueError):
            parse_mhz("-1")
