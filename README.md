# ham-radio-ha-gateway

Bring a ham radio and [JS8Call](http://js8call.com) into Home Assistant: see when the radio is on, what frequency and mode it is on, when it transmits, and react to JS8 messages with automations.

A Raspberry Pi next to the radio does the work; Home Assistant gets everything over the network through MQTT, as entities that appear on their own.

> **Status: under development.** The gateway and its tests are done; the installation guide, which starts from a new Raspberry Pi and an empty microSD card, is being checked step by step on a Raspberry Pi 4 (1 GB) with an Icom IC-7300. Steps not yet checked on hardware are marked ⚠.

```
 Radio ──USB──► Raspberry Pi ───────── network ─────────► Home Assistant
 (CAT + audio)   • rigctld (Hamlib): shares the radio            • MQTT broker (Mosquitto)
                 • JS8Call, on a virtual display                 • entities, automations
                 • hamgw: the gateway → MQTT
```

Many radios, the IC-7300 among them, carry both radio control (CAT/CI-V) and a sound card on one USB cable, so no extra interface is needed. Any radio [Hamlib](https://hamlib.github.io) supports works for the radio part; the guide uses the IC-7300 as the example.

## What you get in Home Assistant

| Entity | |
|---|---|
| Online | the radio answers (on and connected) |
| Frequency, Mode | what the radio is set to |
| Tune, Set mode | change frequency and mode from Home Assistant |
| Transmitting | PTT |
| TX power, Set TX power | transmit power setting in watts |
| S-meter | signal strength, dB relative to S9 |
| Power *(optional)* | switch the radio on and off, where the radio allows it |
| JS8Call | JS8Call is running and connected |
| JS8 last message / to me / last heard | with sender, recipient, text, SNR, frequency, grid as attributes |
| JS8Call event | `message`, `message_to_me`, `heard`: triggers for automations |
| JS8 send *(optional)* | queue a JS8 message for transmission |

Transmitting from Home Assistant is off by default: a message sent that way goes out with nobody at the radio. Check your licence conditions before you turn it on.

## Guide

1. [What you need](docs/01-hardware.md)
2. [Raspberry Pi: from a new board to the installed gateway](docs/02-raspberry-pi.md)
3. [Radio settings (IC-7300)](docs/03-radio-ic7300.md)
4. [Radio control: rigctld](docs/04-rigctld.md)
5. [JS8Call](docs/05-js8call.md)
6. [Home Assistant: MQTT and the gateway](docs/06-home-assistant.md)
7. [Automations](docs/07-automations.md)
8. [Troubleshooting](docs/08-troubleshooting.md)

## Development

The gateway is plain Python 3.11+ with two packages Raspberry Pi OS ships (`python3-paho-mqtt`, `python3-yaml`). The tests need neither, nor a radio: they run against a fake rigctld, a fake JS8Call and a fake MQTT client.

```sh
python3 -m unittest discover -s tests -t .
```

## License

MIT, see [LICENSE](LICENSE).
