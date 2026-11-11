#!/bin/sh
# Install ham-radio-ha-gateway on Raspberry Pi OS (Debian 12 "bookworm" or newer).
# Run from the cloned repository:  sudo ./install.sh
# Safe to run again: it keeps your configuration files.
set -eu

PREFIX=/opt/ham-radio-ha-gateway
ETC=/etc/ham-gateway
USER_NAME=ham

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo ./install.sh" >&2
  exit 1
fi
cd "$(dirname "$0")"

echo "== Packages"
apt-get update
apt-get install -y python3 python3-paho-mqtt python3-yaml libhamlib-utils \
  xvfb x11vnc chrony zram-tools alsa-utils

echo "== User '$USER_NAME' (serial port and sound access)"
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "$USER_NAME"
fi
usermod -aG dialout,audio "$USER_NAME"

echo "== Gateway into $PREFIX"
mkdir -p "$PREFIX"
cp -r hamgw "$PREFIX/"
find "$PREFIX" -name __pycache__ -prune -exec rm -rf {} +

echo "== Configuration in $ETC"
mkdir -p "$ETC"
[ -f "$ETC/config.yaml" ] || install -m 640 -g "$USER_NAME" config.example.yaml "$ETC/config.yaml"
[ -f "$ETC/rigctld.env" ] || install -m 644 systemd/rigctld.env.example "$ETC/rigctld.env"

echo "== Memory: compressed swap in RAM (zram), useful on 1 GB boards"
if [ -f /etc/default/zramswap ] && ! grep -q '^PERCENT=' /etc/default/zramswap; then
  printf 'ALGO=zstd\nPERCENT=50\n' >> /etc/default/zramswap
fi
systemctl enable --now zramswap.service 2>/dev/null || true

echo "== Services"
for unit in rigctld xvfb js8call ham-gateway; do
  install -m 644 "systemd/$unit.service" /etc/systemd/system/
done
systemctl daemon-reload
systemctl enable chrony rigctld ham-gateway

cat <<EOF

Done. Next:
  1. Set the radio's serial port in $ETC/rigctld.env  (docs/04-rigctld.md)
  2. Set MQTT login and your radio in $ETC/config.yaml  (docs/06-home-assistant.md)
  3. Install JS8Call and set it up once over VNC      (docs/05-js8call.md)
  4. sudo systemctl restart rigctld ham-gateway
     journalctl -u ham-gateway -f
EOF
