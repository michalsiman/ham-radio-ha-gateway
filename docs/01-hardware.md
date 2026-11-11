# 1. What you need

- **A radio Hamlib can control**, with a USB connection that carries both CAT and audio. The guide uses the **Icom IC-7300**: one USB cable gives a serial port (CI-V) and a USB sound card.
- **A Raspberry Pi 4** (1 GB is enough without a desktop; 2 GB or more is more comfortable) or a Pi 5, with power supply and a microSD card of 16 GB or more.
- **A USB A–B cable** (the IC-7300's port is USB-B). Short and with ferrite cores: RF on the USB cable is the most common source of trouble.
- **Network**: Ethernet is the safer choice next to a transmitter; Wi-Fi works.
- **Home Assistant** with the Mosquitto broker add-on (or any MQTT broker).

Optional: a computer to reach the Pi over SSH and, once, to set up JS8Call over VNC.
