#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:1
export XDG_RUNTIME_DIR=/tmp/runtime-root
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

dbus-launch --exit-with-session startxfce4 &
sleep 5

BIN="$(command -v easyeda-pro || command -v lceda-pro || true)"
if [[ -n "$BIN" ]]; then
  "$BIN" --no-sandbox --disable-gpu --disable-dev-shm-usage >/tmp/easyeda-pro.log 2>&1 &
  echo "EasyEDA Pro launch attempted: $BIN"
else
  echo "EasyEDA Pro not installed; XFCE desktop is available for diagnostics."
fi
wait
