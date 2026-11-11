# 2. Raspberry Pi: from a new board to the installed gateway

This page starts with a new, never used Raspberry Pi and an empty microSD card.

## What to have ready

- **microSD card, 16–32 GB**, a known brand, class *A1* or *A2* (e.g. SanDisk, Samsung, Kingston). The card is the Pi's disk: a cheap one is the most common reason a Pi stops booting after months.
- **A card reader** for your computer (many laptops have one; a USB reader otherwise).
- **Power supply**: the official Raspberry Pi 4 supply (USB-C, 5.1 V 3 A) or an equally strong one. Phone chargers often give too little and the Pi restarts under load.
- **Ethernet cable** to your router (recommended next to a transmitter), or your Wi-Fi name and password.
- Optional: a case with a heatsink or fan; JS8Call keeps the CPU busy.

No monitor or keyboard is needed: everything is done over the network.

## Write the system to the card

1. On your computer install **Raspberry Pi Imager** from <https://www.raspberrypi.com/software/> and start it.
2. **Choose device**: *Raspberry Pi 4*.
3. **Choose OS**: *Raspberry Pi OS (other)* → **Raspberry Pi OS Lite (64-bit)**. *Lite* means without a desktop: the gateway doesn't need one, and on a 1 GB board the memory is better spent on JS8Call.
4. **Choose storage**: your microSD card. Check it is the card and not another disk: it will be erased.
5. **Next** → **Edit settings** (OS customisation):
   - **General**
     - Hostname: `ham-gateway`
     - Username and password: your choice, e.g. `pi` and a strong password. Remember them.
     - Wireless LAN: only if you use Wi-Fi: name, password, and your country.
     - Locale: your time zone and keyboard layout.
   - **Services**: tick **Enable SSH**, *Use password authentication* (or paste your public key if you use SSH keys).
   - **Save**, then **Yes** to apply the settings, and **Yes** to write.
6. Wait until Imager has written and verified the card, then take it out.

## First start

1. Put the card into the Pi (slot on the underside), connect Ethernet if you use it, then connect power. The red LED lights, the green one flickers while it boots.
2. Give it two to three minutes: the first boot grows the file system and applies your settings.
3. From your computer, log in (Windows: PowerShell; macOS/Linux: Terminal):

   ```sh
   ssh pi@ham-gateway.local
   ```

   Answer `yes` to the question about the host key, then enter your password.
   If `ham-gateway.local` isn't found, look up the Pi's IP address in your router's list of devices and use `ssh pi@192.168.x.y`.

4. Bring the system up to date and restart:

   ```sh
   sudo apt update && sudo apt full-upgrade -y
   sudo reboot
   ```

   Log in again after a minute.

## Install the gateway

```sh
sudo apt install -y git
git clone https://github.com/michalsiman/ham-radio-ha-gateway.git
cd ham-radio-ha-gateway
sudo ./install.sh
```

The script installs:

- **Hamlib** (`rigctld`) to share the radio,
- **JS8Call** (Debian's package) with a virtual display and VNC for setting it up once,
- **chrony** for an accurate clock (JS8 needs it within about a second),
- compressed swap in memory (**zram**), which helps on 1 GB boards,
- the **gateway** and the services that start it all at boot.

It creates the user `ham`, which may use the serial port and the sound card. Your settings go to `/etc/ham-gateway/`; running the script again keeps them.

Check the clock: `chronyc tracking` should show a *System time* offset well below a second.

Next: [Radio settings](03-radio-ic7300.md).
