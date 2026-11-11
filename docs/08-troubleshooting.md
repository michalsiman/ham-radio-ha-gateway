# 8. Troubleshooting

| Symptom | Check |
|---|---|
| `rigctl ... f` hangs or fails | the radio is on; `RIG_DEVICE` exists (`ls /dev/serial/by-id/`); `RIG_SPEED` equals *CI-V USB Baud Rate*; *CI-V USB Echo Back* is OFF; `journalctl -u rigctld` |
| Permission denied on the serial port | the `ham` user is in `dialout`: `id ham` |
| Radio "Offline" in HA, rigctl works | `journalctl -u ham-gateway`; `rig.host`/`rig.port` in config.yaml |
| No entities in HA | gateway log shows `MQTT connected`; MQTT login in config.yaml; Mosquitto add-on log |
| Entities unavailable | the gateway is stopped: its last will set `<base_topic>/status` to `offline` |
| JS8Call decodes nothing | clock (`chronyc tracking`); audio input is the radio's USB CODEC; *USB AF Output Level*; radio in USB-D |
| JS8Call: "JS8Call" entity off | JS8Call running (`systemctl status js8call`); *Enable TCP Server API* and *Accept TCP Requests* on, port 2442 |
| Transmit is distorted or wide | ALC: lower *USB MOD Level* or JS8Call's output level |
| USB disconnects while transmitting | RF on the USB cable: ferrites, shorter cable, check the station ground |

Logs: `journalctl -u rigctld -u js8call -u ham-gateway -f`
