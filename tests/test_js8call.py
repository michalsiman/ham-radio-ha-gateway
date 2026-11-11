import json
import unittest

from hamgw.js8call import Js8Message, addressed_to, parse_event


class ParseTests(unittest.TestCase):
    def test_directed_message(self):
        line = json.dumps({
            "type": "RX.DIRECTED",
            "value": "OK1ABC: OK1SIM HELLO FROM PRAGUE",
            "params": {"FROM": "OK1ABC", "TO": "OK1SIM", "TEXT": "HELLO FROM PRAGUE", "SNR": -12,
                       "FREQ": 7079500, "OFFSET": 1500, "GRID": "JO70", "UTC": 1794400000000},
        })
        event = parse_event(line)
        self.assertEqual(event.kind, "message")
        m = event.message
        self.assertEqual((m.sender, m.to, m.text, m.snr, m.frequency_hz, m.grid), ("OK1ABC", "OK1SIM", "HELLO FROM PRAGUE", -12, 7079500, "JO70"))

    def test_text_falls_back_to_value(self):
        event = parse_event(json.dumps({"type": "RX.DIRECTED", "value": "A: B HI", "params": {"FROM": "A", "TO": "B"}}))
        self.assertEqual(event.message.text, "A: B HI")

    def test_spot_and_callsign(self):
        spot = parse_event(json.dumps({"type": "RX.SPOT", "value": "", "params": {"CALL": "DL1XYZ", "SNR": -5, "GRID": "JO62"}}))
        self.assertEqual((spot.kind, spot.spot.call, spot.spot.snr), ("spot", "DL1XYZ", -5))
        call = parse_event(json.dumps({"type": "STATION.CALLSIGN", "value": "OK1SIM"}))
        self.assertEqual((call.kind, call.callsign), ("callsign", "OK1SIM"))

    def test_garbage(self):
        self.assertIsNone(parse_event("not json"))
        self.assertIsNone(parse_event("[1, 2]"))
        self.assertEqual(parse_event(json.dumps({"type": "RIG.FREQ"})).kind, "other")

    def test_addressed_to(self):
        msg = lambda to: Js8Message(sender="X", to=to, text="")
        self.assertTrue(addressed_to(msg("OK1SIM"), "OK1SIM"))
        self.assertTrue(addressed_to(msg("ok1sim/p"), "OK1SIM"))
        self.assertTrue(addressed_to(msg("@OK"), "OK1SIM", ["@OK"]))
        self.assertFalse(addressed_to(msg("@ALLCALL"), "OK1SIM"))
        self.assertFalse(addressed_to(msg("OK1SIM"), ""))
