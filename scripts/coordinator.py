#!/usr/bin/env python3
"""Prepare and reconcile native desktop coordinator work; never start headless agents."""
import argparse
import json
import os
import sys
import sqlite3
import subprocess
from native_coordinator import project, projects, role, verify_repository, state, connection, begin, end, pilot, prompt, prepare_task, claim_task, bind_project, dispatch_plan, attach_task, start_task, observe_task, schedule_binding, schedule_plan, schedule_audit

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=tuple(projects()), required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("prompt")
    b = sub.add_parser("begin")
    b.add_argument("--thread", default=os.environ.get("CODEX_THREAD_ID"))
    e = sub.add_parser("end")
    e.add_argument("--pass-id", required=True)
    e.add_argument("--evidence", required=True)
    e.add_argument("--recovered", action="store_true")
    p = sub.add_parser("pilot")
    p.add_argument("action", choices=("claim", "attach", "verify", "status"))
    p.add_argument("--thread", default=os.environ.get("CODEX_THREAD_ID"))
    p.add_argument("--child")
    p.add_argument("--evidence")
    sub.add_parser("tasks")
    binding = sub.add_parser("bind")
    binding.add_argument("--project-id", required=True)
    schedule = sub.add_parser("schedule-plan")
    schedule.add_argument("--status", choices=("ACTIVE", "PAUSED"))
    register = sub.add_parser("schedule-register")
    register.add_argument("--id", required=True)
    sub.add_parser("schedule-audit")
    prepare = sub.add_parser("task-prepare")
    for option in ("scope", "base", "prompt", "authority", "acceptance"):
        prepare.add_argument("--" + option, required=True)
    claim = sub.add_parser("task-claim")
    claim.add_argument("--task", required=True)
    claim.add_argument("--pass-id", required=True)
    plan = sub.add_parser("dispatch-plan")
    plan.add_argument("--task", required=True)
    attach = sub.add_parser("task-attach")
    attach.add_argument("--task", required=True)
    attach.add_argument("--thread", required=True)
    attach.add_argument("--host", default="local")
    start = sub.add_parser("task-start")
    start.add_argument("--task", required=True)
    start.add_argument("--cwd", required=True)
    start.add_argument("--thread", default=os.environ.get("CODEX_THREAD_ID"))
    observe = sub.add_parser("task-observe")
    observe.add_argument("--task", required=True)
    observe.add_argument("--status", required=True)
    observe.add_argument("--evidence", required=True)
    observe.add_argument("--close", action="store_true")
    args = parser.parse_args()
    if args.command == "doctor":
        result = {"project": args.project, "checkout": verify_repository(args.project), "roles": {n: role(n) for n in ("coordinator", "coding")},
                  "state": str(state(args.project)), "native_thread": os.environ.get("CODEX_THREAD_ID"),
                  "desktop_bridge_available": bool(os.environ.get("CODEX_APP_TOOLS_PIPE_PATH")), "pilot": pilot(args.project, "status")}
    elif args.command == "prompt":
        print(prompt(args.project))
        return 0
    elif args.command == "begin":
        result = begin(args.project, args.thread)
    elif args.command == "end":
        end(args.project, args.pass_id, args.evidence, args.recovered)
        result = {"status": "released", "pass_id": args.pass_id}
    elif args.command == "pilot":
        result = pilot(args.project, args.action, args.thread, args.child, args.evidence)
    elif args.command == "bind":
        bind_project(args.project, args.project_id)
        result = {"project_id": args.project_id, "status": "bound"}
    elif args.command == "schedule-plan":
        result = schedule_plan(args.project, args.status)
    elif args.command == "schedule-register":
        schedule_binding(args.project, args.id)
        result = {"status": "registered", "automation_id": args.id}
    elif args.command == "schedule-audit":
        result = schedule_audit(args.project)
    elif args.command == "task-prepare":
        result = prepare_task(args.project, args.scope, args.base, args.prompt, args.authority, args.acceptance)
    elif args.command == "task-claim":
        result = claim_task(args.project, args.task, args.pass_id)
    elif args.command == "dispatch-plan":
        result = dispatch_plan(args.project, args.task)
    elif args.command == "task-attach":
        result = attach_task(args.project, args.task, args.thread, args.host)
    elif args.command == "task-start":
        result = start_task(args.project, args.task, args.cwd, args.thread)
    elif args.command == "task-observe":
        result = observe_task(args.project, args.task, args.status, args.evidence, args.close)
    else:
        db = connection(args.project)
        try:
            result = {"tasks": [dict(r) for r in db.execute("SELECT * FROM tasks ORDER BY created_at DESC")],
                      "active_passes": [dict(r) for r in db.execute("SELECT * FROM passes WHERE state='active'")]}
        finally:
            db.close()
    print(json.dumps(result, indent=2))
    return 3 if result.get("status") == "blocked" else 0

if __name__ == "__main__":
    os.umask(0o077)
    try:
        raise SystemExit(main())
    except (ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        raise SystemExit(78)
