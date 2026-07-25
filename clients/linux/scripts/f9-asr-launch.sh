#!/usr/bin/env bash
# Подбор DISPLAY и XAUTHORITY для pynput (GNOME/GDM, :0 или :1)
set -euo pipefail
UID_NUM="$(id -u)"
if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]] && [[ -S "/run/user/${UID_NUM}/bus" ]]; then
  export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${UID_NUM}/bus"
fi
export XAUTHORITY="${XAUTHORITY:-/run/user/${UID_NUM}/gdm/Xauthority}"
if [[ ! -f "$XAUTHORITY" ]]; then
  export XAUTHORITY="${HOME}/.Xauthority"
fi
if [[ -z "${DISPLAY:-}" ]]; then
  for d in 0 1 2; do
    if [[ -S "/tmp/.X11-unix/X${d}" ]]; then
      export DISPLAY=:${d}
      break
    fi
  done
fi
export DISPLAY="${DISPLAY:-:0}"
cd "$(dirname "$0")/.."
exec uv run python -m f9_asr.main
