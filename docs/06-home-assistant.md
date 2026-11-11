# 6. Home Assistant: MQTT and the gateway

## MQTT broker

In Home Assistant: **Settings → Add-ons → Add-on store → Mosquitto broker → Install → Start**. Home Assistant offers to set up the **MQTT** integration for it; accept.

## A login for the gateway

Create a Home Assistant user for the gateway: **Settings → People → Users → Add user** (needs *Advanced mode* in your profile), e.g. `ham-gateway`, with a strong password; it doesn't need to be an administrator. Mosquitto accepts Home Assistant users.

## Configure the gateway

Edit `/etc/ham-gateway/config.yaml` on the Pi:

```yaml
device_name: IC-7300
mqtt:
  host: 192.168.1.10        # Home Assistant
  username: ham-gateway
  password: <the password>
rig:
  model: Icom IC-7300
js8call:
  callsign: ""              # taken from JS8Call
```

See [config.example.yaml](../config.example.yaml) for all options.

```sh
sudo systemctl restart ham-gateway
journalctl -u ham-gateway -f
```

The log shows `MQTT connected`, then `radio online`. In Home Assistant the device appears under **Settings → Devices & services → MQTT**, named after `device_name`.

Next: [Automations](07-automations.md).
