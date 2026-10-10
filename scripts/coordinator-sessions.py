#!/usr/bin/env python3
"""Inspect/reset legacy Fireworks pins through supported session RPCs, preserving history."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from agent_policy import PolicyError, load_runtime, private_write


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    runtime = load_runtime()
    listed = subprocess.run([runtime["openclaw_binary"], "sessions", "--agent", "main", "--limit", "all", "--json"], capture_output=True, text=True, timeout=30)
    if listed.returncode: raise PolicyError("Cannot read supported session metadata")
    snapshot = json.loads(listed.stdout)
    if snapshot.get("hasMore"): raise PolicyError("Incomplete session inventory; no pins changed")
    rows = snapshot["sessions"]
    targets = [{"key": r["key"], "agentId": "main", "expectedSessionId": r["sessionId"]}
               for r in rows if r.get("providerOverride") == "fireworks" and r["key"].startswith("agent:main:")]
    if not args.apply:
        print(json.dumps({"schema_version": 1, "legacy_fireworks_pins": len(targets), "total_sessions": len(rows), "changed": False}))
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = Path(runtime["user_home"]) / "Library/Application Support/OpenClaw Backups/codex-coordinator" / ("session-reset-" + stamp)
    private_write(evidence / "before.json", listed.stdout)
    patch = {"model": None, "agentRuntime": None, "thinkingLevel": None, "fastMode": None}
    completed, failures = 0, []
    for offset in range(0, len(targets), 100):
        params = {"targets": targets[offset:offset + 100], "patch": patch}
        result = subprocess.run([runtime["openclaw_binary"], "gateway", "call", "sessions.patchMany", "--params", json.dumps(params), "--json", "--timeout", "60000"], capture_output=True, text=True, timeout=70)
        private_write(evidence / f"batch-{offset}.json", result.stdout + result.stderr)
        if result.returncode: raise PolicyError(f"Session reset did not complete; reconcile private evidence: {evidence}")
        outcomes = json.loads(result.stdout).get("outcomes", [])
        if len(outcomes) != len(params["targets"]): raise PolicyError("Unexpected session reset result schema")
        completed += sum(o.get("ok") is True for o in outcomes)
        failures.extend(o for o in outcomes if o.get("ok") is not True)
    print(json.dumps({"schema_version": 1, "reset": completed, "failures": failures, "evidence": str(evidence), "history_preserved": True}))
    if failures: raise PolicyError("Some sessions were busy/replaced; reconcile before further changes")


if __name__ == "__main__":
    try: main()
    except (PolicyError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema_version": 1, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(78)
