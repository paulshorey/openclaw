#!/usr/bin/env python3
"""Structured local interface to supported subscription Codex Cloud commands."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
from agent_policy import ROOT, PolicyError, load_policy, load_runtime, private_write, require_cli
from cloud_tasks import CAPABILITIES, Cloud, Ledger


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities")
    commands.add_parser("doctor")
    prepare = commands.add_parser("prepare")
    for flag in ("repository", "scope", "owner", "authority", "acceptance", "prompt"):
        prepare.add_argument("--" + flag, required=True)
    submit = commands.add_parser("submit")
    submit.add_argument("id")
    submit.add_argument("--owner", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--remote", action="store_true")
    listing.add_argument("--environment")
    listing.add_argument("--max-pages", type=int, default=5, choices=range(1, 6))
    commands.add_parser("reconcile")
    binding = commands.add_parser("bind", help="Resolve unknown submission after exact human UI identity review")
    binding.add_argument("id")
    binding.add_argument("--evidence", required=True, type=Path)
    for cmd in ("status", "diff"):
        c = commands.add_parser(cmd)
        c.add_argument("id", help="Local tracking ID")
        if cmd == "diff": c.add_argument("--attempt", type=int, default=1, choices=[1])
    args = p.parse_args()
    policy, runtime = load_policy(), load_runtime()
    cloud = Cloud(policy, runtime)
    if args.command == "capabilities": return {"capabilities": CAPABILITIES}
    if args.command == "doctor":
        auth = require_cli(runtime, cwd=ROOT)
        page = cloud.pages(max_pages=1, deadline_seconds=30)
        return {"cli": auth, "capabilities": CAPABILITIES, "environment_mappings": cloud.registry,
                "read_access": True, "recent_tasks": len(page["tasks"]), "dispatch_ready": False}
    if args.command == "list" and args.remote:
        require_cli(runtime, cwd=ROOT)
        return cloud.pages(args.environment, args.max_pages)
    db_path = Path(runtime["workspace"]) / "state/codex-tasks.sqlite3"
    # Read-only status of an unused adapter does not create private state.
    if args.command in ("list", "reconcile") and not db_path.exists():
        return {"tasks": [], "changes": [], "unresolved": [], "complete": True}
    ledger = Ledger(db_path)
    try:
        if args.command == "prepare":
            return {"task": cloud.prepare(ledger, args.repository, args.scope, args.owner, args.authority, args.prompt, args.acceptance)}
        if args.command == "submit": return {"task": cloud.submit(ledger, args.id, args.owner)}
        if args.command == "list": return {"tasks": ledger.tasks()}
        if args.command == "reconcile": return cloud.reconcile(ledger)
        if args.command == "bind": return {"task": cloud.bind(ledger, args.id, args.evidence)}
        task = ledger.get(args.id)
        if not task.get("remote_id"): return {"task": task, "remote_status": "unestablished"}
        require_cli(runtime, cwd=ROOT)
        if args.command == "status":
            # Upstream status exits 1 for healthy PENDING as well as ERROR.
            # Preserve text/exit separately; use list JSON for authoritative state.
            result = cloud.call(["status", task["remote_id"]])
            evidence = db_path.parent.parent / "logs/codex-cloud" / task["id"] / "status.txt"
            private_write(evidence, result.stdout + result.stderr)
            return {"task": task, "status_exit_code": result.returncode, "status_evidence": str(evidence), "state_source": "reconcile list JSON"}
        result = cloud.call(["diff", task["remote_id"], "--attempt", str(args.attempt)])
        evidence = db_path.parent.parent / "logs/codex-cloud" / task["id"] / "attempt-1.diff"
        if result.returncode: raise PolicyError("Diff unavailable; task may still be running")
        private_write(evidence, result.stdout)
        return {"id": args.id, "diff_path": str(evidence), "base_verified": bool(task.get("verified_starting_sha")), "result_verified": False}
    finally: ledger.close()


if __name__ == "__main__":
    try:
        result = main()
        print(json.dumps({"schema_version": 1, "ok": True, **result}, indent=2))
    except (PolicyError, OSError, ValueError, sqlite3.Error, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema_version": 1, "ok": False, "error_class": type(exc).__name__, "error": str(exc)}))
        raise SystemExit(78)
