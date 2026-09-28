#!/usr/bin/env python3
"""Apply dashboard-only heartbeat routing without changing Gateway access or keys."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent
OPENCLAW = "/opt/homebrew/bin/openclaw"
STATE = Path.home() / ".openclaw"
TOKEN_LINE = re.compile(rb"^\s*(?:export\s+)?TELEGRAM_BOT_TOKEN\s*=")


def write_private(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
        tmp.write(data)
    try:
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = json.loads((STATE / "openclaw.json").read_text())
    patch = {
        "agents": {"defaults": {"heartbeat": {
            "every": "1h",
            "target": "none",
            "to": None,
            "accountId": None,
            "isolatedSession": True,
            "prompt": (ROOT / "config/heartbeat-prompt.txt").read_text().strip(),
        }}},
        "channels": {"telegram": {"enabled": False}},
        "plugins": {"entries": {"telegram": {"enabled": False}}},
    }
    # Remove only retired Telegram owners; retain any other explicit owners.
    owners = config.get("commands", {}).get("ownerAllowFrom")
    if owners is not None:
        retained = [owner for owner in owners if not owner.startswith("telegram:")]
        if retained != owners:
            patch["commands"] = {"ownerAllowFrom": retained or None}
    command = [OPENCLAW, "config", "patch", "--stdin", "--replace-path", "channels.telegram"]
    if args.dry_run:
        command.append("--dry-run")
    subprocess.run(command, input=json.dumps(patch), text=True, check=True)
    if args.dry_run:
        print("Dry run only; credentials and runtime files were not changed.")
        return

    # Keep a private rollback copy; the active environment no longer has the bot key.
    env_file = STATE / ".env"
    if env_file.exists():
        original = env_file.read_bytes()
        cleaned = b"".join(line for line in original.splitlines(keepends=True)
                           if not TOKEN_LINE.match(line))
        if cleaned != original:
            backup_dir = STATE / "backups" / "ui-workflow"
            backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            backup_dir.chmod(0o700)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            write_private(backup_dir / f"env-{stamp}.backup", original)
            write_private(env_file, cleaned)
            print("Removed the Telegram token from the active .env; private rollback copy retained.")
        env_file.chmod(0o600)
    subprocess.run([OPENCLAW, "config", "validate"], check=True)
    print("Dashboard heartbeat routing configured; Telegram channel and plugin disabled.")
    print("Deploy coordinator templates, then restart the Gateway to apply the retired environment.")


if __name__ == "__main__":
    main()
