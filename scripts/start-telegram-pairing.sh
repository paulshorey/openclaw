#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:$PATH"
env_file="$HOME/.openclaw/.env"
openclaw_bin=/opt/homebrew/bin/openclaw

if [[ ! -f "$env_file" ]] || ! grep -q '^TELEGRAM_BOT_TOKEN=' "$env_file"; then
  echo 'Put TELEGRAM_BOT_TOKEN in ~/.openclaw/.env before starting Telegram pairing.' >&2
  exit 78
fi
python3 "$(dirname -- "${BASH_SOURCE[0]}")/check-telegram-bot.py"

"$openclaw_bin" config set channels.telegram.enabled true
"$openclaw_bin" config set channels.telegram.dmPolicy pairing
"$openclaw_bin" config validate
"$openclaw_bin" gateway restart
"$openclaw_bin" channels status --probe
echo 'Send a DM to the new bot. Its pairing reply includes your numeric Telegram user ID.'
