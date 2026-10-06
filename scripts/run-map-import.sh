#!/usr/bin/env bash
# Foreground, model-free process owner. Invoke with OpenClaw exec background=true.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec "$root/.venv/bin/python" "$root/scripts/run-map-import.py" "$@"
