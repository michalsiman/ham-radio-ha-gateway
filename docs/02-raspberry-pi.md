# 2. Raspberry Pi: system and gateway

## System

1. Flash **Raspberry Pi OS Lite** with [Raspberry Pi Imager](https://www.raspberrypi.com/software/). In the Imager's settings set a host name (e.g. `ham-gateway`), your user and password, Wi-Fi if needed, your time zone, and turn on SSH.
   - ⚠ 32-bit or 64-bit: JS8Call's Raspberry Pi package and the build differ per architecture, see [JS8Call](05-js8call.md). Decide after reading that page.
2. Boot the Pi and log in: `ssh <user>@ham-gateway.local`
3. Update: `sudo apt update && sudo apt full-upgrade -y && sudo reboot`

## Gateway

```sh
sudo apt install -y git
git clone https://github.com/michalsiman/ham-radio-ha-gateway.git
cd ham-radio-ha-gateway
sudo ./install.sh
```

The script installs Hamlib (rigctld), the virtual display and VNC for JS8Call, time sync (chrony; JS8 needs the clock within about a second), compressed swap in RAM, and the gateway as services. It creates the user `ham`, which may use the serial port and sound card. Your settings go to `/etc/ham-gateway/`; running the script again keeps them.

Check the clock: `chronyc tracking` should show a system time offset well below a second.

Next: [Radio settings](03-radio-ic7300.md).
