#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:$PATH"
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace="$root/runtime/coordinator"
openclaw_bin=/opt/homebrew/bin/openclaw

if [[ ! -x "$openclaw_bin" ]]; then
  echo 'OpenClaw is missing; install it with Node 26 first.' >&2
  exit 69
fi
if [[ ! -f "$HOME/.openclaw/.env" ]] || ! grep -q '^FIREWORKS_API_KEY=' "$HOME/.openclaw/.env"; then
  echo 'Put FIREWORKS_API_KEY in ~/.openclaw/.env before configuring.' >&2
  exit 78
fi

if [[ ! -x "$root/.venv/bin/python" ]]; then
  /opt/homebrew/bin/python3 -m venv "$root/.venv"
fi
if ! "$root/.venv/bin/python" -c 'import dotenv' >/dev/null 2>&1; then
  "$root/.venv/bin/python" -m pip install -r "$root/requirements.txt"
fi

if ! "$openclaw_bin" plugins inspect fireworks --json >/dev/null 2>&1; then
  "$openclaw_bin" plugins install @openclaw/fireworks-provider
fi
"$root/scripts/deploy-workspace.py"
"$openclaw_bin" config set agents.defaults.workspace "$workspace"
"$openclaw_bin" config set agents.entries.main.workspace "$workspace"
"$openclaw_bin" config set agents.defaults.model.primary fireworks/accounts/fireworks/models/deepseek-v4p1-flash
"$openclaw_bin" config set agents.defaults.heartbeat.every 1h
"$openclaw_bin" config set agents.defaults.heartbeat.target none
"$openclaw_bin" config set agents.defaults.heartbeat.isolatedSession true
"$openclaw_bin" config set agents.defaults.heartbeat.prompt "$(< "$root/config/heartbeat-prompt.txt")"
"$openclaw_bin" config set memory.search.provider none
"$openclaw_bin" config set env.shellEnv.enabled true
"$openclaw_bin" config set gateway.bind loopback
"$openclaw_bin" config validate
"$openclaw_bin" gateway install
"$openclaw_bin" gateway status
