#!/usr/bin/env bash
# Foreground, model-free process owner. Invoke with OpenClaw exec background=true.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ "${1:-}" == --check ]]; then
  "$root/.venv/bin/python" - <<'PY'
import json
from pathlib import Path
config = json.loads((Path.home() / '.openclaw/openclaw.json').read_text())
global_tools = config.get('tools', {})
agent_tools = config.get('agents', {}).get('entries', {}).get('main', {}).get('tools', {})
notify = agent_tools.get('exec', {}).get('notifyOnExit', global_tools.get('exec', {}).get('notifyOnExit', True))
if not notify:
    raise SystemExit('Blocked: native background exec completion notifications are disabled')
if 'process' in global_tools.get('deny', []) + agent_tools.get('deny', []):
    raise SystemExit('Blocked: OpenClaw process tool is denied')
print('Native notifyOnExit is enabled (configured or runtime default). Verify a harmless background exec completion in the owning conversation before importing.')
PY
  exit
fi
if [[ "${OPENCLAW_SHELL:-}" != exec ]]; then
  echo 'Launch this foreground wrapper through OpenClaw exec background=true; a terminal or detached shell has no native completion owner.' >&2
  exit 64
fi
if [[ $# -lt 3 || "$1" != --max-hours ]]; then
  echo 'Usage: run-map-import.sh --max-hours 1..168 -- <ingest:run arguments with explicit budgets>' >&2
  exit 64
fi
"$0" --check
exec "$root/.venv/bin/python" "$root/scripts/project-env.py" \
  --cwd /Users/pshorey/git/map --shell-only --require DB_MAP_URL -- \
  pnpm --silent --filter @lib/db-map ingest:supervise watch "$@"
