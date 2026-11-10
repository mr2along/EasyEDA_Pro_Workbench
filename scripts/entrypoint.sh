#!/usr/bin/env bash
set -euo pipefail

: "${WEB_PASSWORD:?Set WEB_PASSWORD as a Hugging Face Space Secret}"
: "${VNC_PASSWORD:?Set VNC_PASSWORD as a Hugging Face Space Secret}"
: "${APP_API_KEY:?Set APP_API_KEY as a Hugging Face Space Secret}"

if [[ ${#VNC_PASSWORD} -lt 6 ]]; then
  echo "VNC_PASSWORD must contain at least 6 characters" >&2
  exit 1
fi

mkdir -p /run/secrets /data/projects /data/automation "$EASYEDA_HOME"
x11vnc -storepasswd "$VNC_PASSWORD" /run/secrets/vnc.pass >/dev/null
chmod 600 /run/secrets/vnc.pass
printf 'eda:%s\n' "$(openssl passwd -apr1 "$WEB_PASSWORD")" > /run/secrets/novnc.htpasswd
chmod 600 /run/secrets/novnc.htpasswd

if [[ -n "${EASYEDA_INSTALLER_URL:-}" ]]; then
  python3 /opt/easyeda-workbench/scripts/install_easyeda.py "$EASYEDA_INSTALLER_URL" "$EASYEDA_HOME"
fi

BIN="$(command -v easyeda-pro || command -v lceda-pro || find "$EASYEDA_HOME" -maxdepth 6 -type f \( -name easyeda-pro -o -name lceda-pro \) -print -quit || true)"
if [[ -n "$BIN" ]]; then
  chmod +x "$BIN"
  ln -sf "$BIN" /usr/local/bin/easyeda-pro
  echo "EasyEDA executable found: $BIN"
else
  echo "WARNING: EasyEDA Pro executable not found. Starting diagnostic desktop without EDA." >&2
fi

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/easyeda.conf
