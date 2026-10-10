#!/usr/bin/env bash
set -euo pipefail
coordinator_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec "$coordinator_root/.venv/bin/python" "$coordinator_root/scripts/status.py" "$@"
