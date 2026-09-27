#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[0-9]+$ ]]; then
  echo 'Usage: configure-telegram.sh <numeric-Telegram-user-id>' >&2
  exit 64
fi

export PATH="/opt/homebrew/bin:$PATH"
openclaw_bin=/opt/homebrew/bin/openclaw
env_file="$HOME/.openclaw/.env"
owner_id=$1

if [[ ! -f "$env_file" ]] || ! grep -q '^TELEGRAM_BOT_TOKEN=' "$env_file"; then
  echo 'Put TELEGRAM_BOT_TOKEN in ~/.openclaw/.env before configuring Telegram.' >&2
  exit 78
fi
python3 "$(dirname -- "${BASH_SOURCE[0]}")/check-telegram-bot.py"

"$openclaw_bin" config set channels.telegram.enabled true
"$openclaw_bin" config set channels.telegram.allowFrom "[\"$owner_id\"]" --strict-json
"$openclaw_bin" config set channels.telegram.dmPolicy allowlist
"$openclaw_bin" config set channels.telegram.groupPolicy disabled
"$openclaw_bin" config set channels.telegram.defaultTo "$owner_id"
"$openclaw_bin" config set commands.ownerAllowFrom "[\"telegram:$owner_id\"]" --strict-json
"$openclaw_bin" config set agents.defaults.heartbeat.target none
"$openclaw_bin" config validate
"$openclaw_bin" gateway restart
"$openclaw_bin" channels status --probe
