# 3. Radio settings (IC-7300)

⚠ Menu names below follow the IC-7300 manual; check them against your firmware.

**MENU → SET → Connectors**

| Setting | Value | Why |
|---|---|---|
| CI-V → CI-V Baud Rate | 115200 | |
| CI-V → CI-V Address | 94h (default) | Hamlib expects it |
| CI-V → CI-V Transceive | ON | |
| CI-V → CI-V USB Port | Unlink from [REMOTE] | USB CI-V independent of the REMOTE jack |
| CI-V → CI-V USB Baud Rate | 115200 | must match `RIG_SPEED` in rigctld.env |
| CI-V → CI-V USB Echo Back | OFF | |
| USB MOD Level | 50 % | start here, adjust for ALC (below) |
| DATA OFF MOD | MIC,ACC | your microphone still works |
| DATA MOD | USB | data modes take audio from the Pi |
| USB AF Output Level | 50 % | JS8Call's input level |
| USB SEND / USB Keying (CW/RTTY) | OFF | PTT goes over CI-V |

For JS8 the radio runs in **USB-D** (data) mode; JS8Call sets it through rigctld.

**Power level and ALC**: transmit a JS8 message and watch the ALC meter: it should barely move. Lower *USB MOD Level* (or JS8Call's output level) until it does; overdriving makes a broad, distorted signal.

## Switching the radio on from Home Assistant

`power_control: true` in the gateway's config adds a switch that sends Hamlib's power-on and power-off commands. ⚠ Whether the IC-7300 can be woken this way over USB is to be checked: if the radio's USB port goes dead when the radio is off, the Pi can't reach it, and only switching off works.

Next: [rigctld](04-rigctld.md).
