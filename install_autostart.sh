#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_SOURCE="$SCRIPT_DIR/systemd/sensor-gps.service"
SERVICE_TARGET="/etc/systemd/system/sensor-gps.service"

if [ "${EUID}" -eq 0 ]; then
    SUDO=()
else
    SUDO=(sudo)
fi

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "$RUN_USER")"
HOME_DIR="$(getent passwd "$RUN_USER" | cut -d: -f6)"

escaped_project_dir=${SCRIPT_DIR//&/\\&}
escaped_project_dir=${escaped_project_dir//|/\\|}
escaped_home_dir=${HOME_DIR//&/\\&}
escaped_home_dir=${escaped_home_dir//|/\\|}
sed \
    -e "s|@PROJECT_DIR@|$escaped_project_dir|g" \
    -e "s|@RUN_USER@|$RUN_USER|g" \
    -e "s|@RUN_GROUP@|$RUN_GROUP|g" \
    -e "s|@HOME_DIR@|$escaped_home_dir|g" \
    "$SERVICE_SOURCE" \
    | "${SUDO[@]}" tee "$SERVICE_TARGET" >/dev/null

"${SUDO[@]}" systemctl daemon-reload
"${SUDO[@]}" systemctl enable --now sensor-gps.service

echo "Autostart installed: sensor-gps.service"
echo "Check status with: sudo systemctl status sensor-gps.service"
