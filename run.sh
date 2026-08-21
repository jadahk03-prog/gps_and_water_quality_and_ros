#!/bin/bash
set -euo pipefail

# Backward-compatible manual launcher. The same startup path is used by systemd.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start_water_quality.sh"
