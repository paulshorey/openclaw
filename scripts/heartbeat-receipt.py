#!/usr/bin/env python3
"""Record an accepted visible heartbeat launch without waiting on its child."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
import uuid
from agent_policy import PolicyError, load_runtime, private_write, read_json


def record(workspace, child_session, run_id, session_url=None):
    if not re.fullmatch(r"agent:main:dashboard:[A-Za-z0-9_-]+", child_session):
        raise PolicyError("Heartbeat receipt requires the accepted visible main dashboard child key")
    try: run_id = str(uuid.UUID(run_id))
    except ValueError as exc: raise PolicyError("Heartbeat receipt requires the accepted run UUID") from exc
    if session_url:
        url = urlparse(session_url)
        if url.scheme not in ("http", "https") or not url.netloc or url.username or url.password:
            raise PolicyError("Invalid dashboard session URL")
    path = Path(workspace) / "state" / ("heartbeat-launch-" + run_id + ".json")
    identity = {"childSessionKey": child_session, "runId": run_id, "sessionUrl": session_url}
    if path.exists():
        existing = read_json(path)
        if any(existing.get(k) != v for k, v in identity.items()):
            raise PolicyError("Existing heartbeat receipt has different launch identity")
        return path
    private_write(path, json.dumps({"schema_version": 1, **identity,
        "recorded_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--child-session", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--session-url")
    args = p.parse_args()
    path = record(load_runtime()["workspace"], args.child_session, args.run_id, args.session_url)
    print(json.dumps({"schema_version": 1, "receipt": str(path), "child_waited": False}))


if __name__ == "__main__":
    try: main()
    except (PolicyError, OSError) as exc:
        print(json.dumps({"schema_version": 1, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(78)
