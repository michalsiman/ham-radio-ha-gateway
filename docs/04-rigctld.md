# 4. Radio control: rigctld

`rigctld` (from Hamlib) opens the radio's serial port and shares it on TCP port 4532. JS8Call and the gateway both talk to rigctld, so they can use the radio at the same time; only one program could open the serial port itself.

## Find the radio's serial port

With the radio on and connected:

```sh
ls -l /dev/serial/by-id/
```

The IC-7300 shows up as something like `usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_IC-7300_<serial>-if00-port0`. Use this full `/dev/serial/by-id/...` path: unlike `/dev/ttyUSB0` it doesn't change when other USB devices come and go.

## Configure and start

Edit `/etc/ham-gateway/rigctld.env`:

```sh
RIG_MODEL=3073          # rigctl -l | grep -i 7300
RIG_DEVICE=/dev/serial/by-id/usb-Silicon_Labs_CP2102_..._IC-7300_...-if00-port0
RIG_SPEED=115200
RIGCTLD_LISTEN=127.0.0.1
```

```sh
sudo systemctl restart rigctld
rigctl -m 2 -r 127.0.0.1:4532 f      # prints the frequency in Hz
rigctl -m 2 -r 127.0.0.1:4532 m      # mode and passband
```

Other radios: find the model number with `rigctl -l`, and set the radio's CAT baud rate to match `RIG_SPEED`.

Next: [JS8Call](05-js8call.md).
