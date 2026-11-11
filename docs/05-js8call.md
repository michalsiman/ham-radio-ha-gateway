# 5. JS8Call

JS8Call is a desktop program. On the Pi it runs on a virtual display (Xvfb, display `:1`); you set it up once over VNC, after that it runs on its own.

## Install

`install.sh` installs Debian's `js8call` package (version 2.2.0 on Raspberry Pi OS based on Debian 12 or 13), on 32-bit and 64-bit systems alike. To install it by hand: `sudo apt install js8call`.

## Set up over VNC (once)

```sh
sudo systemctl start xvfb
sudo -u ham DISPLAY=:1 js8call &
x11vnc -display :1 -localhost -nopw &     # VNC on the Pi only
```

From your computer: `ssh -L 5900:localhost:5900 <user>@ham-gateway.local`, then connect a VNC viewer to `localhost:5900`.

In JS8Call, **File → Settings**:

- **General → Station**: your callsign and grid.
- **Radio**: Rig *Hamlib NET rigctl*, Network Server `127.0.0.1:4532`; PTT Method *CAT*; Mode *Data/Pkt*; Split Operation *Fake It*. Press *Test CAT*: it turns green.
- **Audio**: Input and Output: the radio's *USB Audio CODEC*.
- **Reporting → API**: tick *Enable TCP Server API* (port 2442) and *Accept TCP Requests*.

Close JS8Call and the VNC server, then let systemd run it:

```sh
sudo systemctl enable --now xvfb js8call
```

Next: [Home Assistant](06-home-assistant.md).
