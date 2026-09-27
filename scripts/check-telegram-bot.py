#!/usr/bin/env python3
"""Check BotFather topic settings without displaying the bot token."""

import json
import os
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    env_file = Path.home() / ".openclaw" / ".env"
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token and env_file.is_file():
        for line in env_file.read_text().splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "TELEGRAM_BOT_TOKEN":
                token = value.strip().strip('"\'')
                break
    if not token:
        print("TELEGRAM_BOT_TOKEN is missing from ~/.openclaw/.env.", file=sys.stderr)
        return 78

    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getMe", timeout=15
        ) as response:
            result = json.load(response)
        bot = result["result"] if result.get("ok") is True else {}
    except (OSError, ValueError, KeyError):
        print("Could not verify the Telegram bot; check its token and network.", file=sys.stderr)
        return 69

    if not bot.get("has_topics_enabled"):
        print("Enable Topics/Threaded Mode for this bot in BotFather.", file=sys.stderr)
        return 78
    if not bot.get("allows_users_to_create_topics"):
        print("In BotFather, allow users to create topics for this bot.", file=sys.stderr)
        return 78
    print(f"Telegram bot @{bot['username']}: topics enabled; user-created topics enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
