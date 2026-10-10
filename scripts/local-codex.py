#!/usr/bin/env python3
"""Run the independent local coding role in a verified isolated worktree."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid
from agent_policy import ROOT, PolicyError, cli_env, cli_prefix, fingerprint, load_policy, load_runtime, private_write, require_cli, verified_worktree


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repository", required=True)
    p.add_argument("--worktree", type=Path, required=True)
    p.add_argument("--base", required=True, help="Reviewed starting commit SHA")
    p.add_argument("--prompt", type=Path, required=True)
    p.add_argument("--launch", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    os.umask(0o077)
    policy, runtime = load_policy(), load_runtime()
    worktree = verified_worktree(args.repository, args.worktree, args.base)
    prompt = args.prompt.resolve(strict=True)
    if not prompt.is_file(): raise PolicyError("Prompt must be a file")
    role = policy["roles"]["local_coding"]
    command = cli_prefix(runtime) + ["exec", "--cd", str(worktree), "--model", role["model"],
        "-c", f'model_reasoning_effort="{role["reasoning_effort"]}"',
        "--dangerously-bypass-approvals-and-sandbox", "--json"]
    if args.dry_run:
        print(json.dumps({"schema_version": 1, "role": role, "command": command, "worktree": str(worktree), "auth_home": runtime["cli_home"]}, indent=2))
        return 0
    if not args.launch:
        env_command = [sys.executable, str(ROOT / "scripts/project-env.py"), "--cwd", str(worktree)]
        if args.repository == "paulshorey/map": env_command.append("--shell-only")
        env_command += ["--", sys.executable, str(Path(__file__).resolve()), "--launch",
            "--repository", args.repository, "--worktree", str(worktree), "--base", args.base, "--prompt", str(prompt)]
        # Reload project env, then strip API keys again at the actual Codex boundary.
        os.execvpe(env_command[0], env_command, cli_env(runtime))
    require_cli(runtime, cwd=worktree)
    run = str(uuid.uuid4())
    logs = Path(runtime["workspace"]) / "logs/local-codex" / run
    logs.mkdir(parents=True, mode=0o700)
    lock_path = Path(runtime["workspace"]) / "state/local-coding-locks" / (fingerprint(str(worktree)) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if lock_path.is_symlink(): raise PolicyError("Refusing symlinked coding lock")
    with lock_path.open("a") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise PolicyError("A coding process already owns this worktree")
        record = {"schema_version": 1, "run_id": run, "repository": args.repository,
            "worktree": str(worktree), "base": args.base, "role": role, "wrapper_pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(), "state": "starting",
            "event_log": str(logs / "events.jsonl"), "last_message": str(logs / "last.txt")}
        private_write(logs / "run.json", json.dumps(record, indent=2))
        with prompt.open("rb") as source, (logs / "events.jsonl").open("wb") as output:
            child = subprocess.Popen(command + ["--output-last-message", str(logs / "last.txt"), "-"],
                stdin=source, stdout=output, stderr=subprocess.STDOUT, cwd=worktree, env=cli_env(runtime))
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, lambda signum, frame: child.send_signal(signum) if child.poll() is None else None)
            record.update(state="running", child_pid=child.pid)
            private_write(logs / "run.json", json.dumps(record, indent=2))
            print(json.dumps(record), flush=True)
            code = child.wait()
        record.update(state="finished", exit_code=code, finished_at=datetime.now(timezone.utc).isoformat(), result_verified=False)
        private_write(logs / "run.json", json.dumps(record, indent=2))
        print(json.dumps(record))
        return code


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (PolicyError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema_version": 1, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(78)
