"""Shared policy and private state for native desktop project coordinators."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tomllib
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime" / "native"
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$", re.I)
SHA = re.compile(r"^[0-9a-f]{40}$")

def now():
    return datetime.now(timezone.utc).isoformat()

def identifier(value):
    if not isinstance(value, str) or not UUID.fullmatch(value):
        raise ValueError("An actual native thread/run UUID is required")
    return value

def read_json(path):
    return json.loads(Path(path).read_text())

def private_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Private state cannot be symlinked")
    temporary = path.with_name(path.name + "." + str(uuid4()) + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def projects():
    data = read_json(ROOT / "config/projects.json")
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported project registry")
    result = data.get("projects", {})
    if not result:
        raise ValueError("No reviewed projects")
    paths = set()
    for slug, item in result.items():
        if not re.fullmatch(r"[a-z][a-z0-9-]*", slug):
            raise ValueError("Invalid project slug")
        path = Path(item["path"])
        if not path.is_absolute() or str(path) in paths:
            raise ValueError("Project paths must be absolute and unique")
        paths.add(str(path))
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", item["repository"]):
            raise ValueError("Invalid reviewed GitHub repository")
        responsibility = (ROOT / item["responsibilities"]).resolve()
        if not responsibility.is_relative_to((ROOT / "config/coordinators").resolve()):
            raise ValueError("Responsibilities must be versioned coordinator instructions")
    return result

def role(name):
    data = read_json(ROOT / "config/agent-models.json")
    if data.get("schema_version") != 2 or set(data.get("roles", {})) != {"coordinator", "coding"}:
        raise ValueError("Unsupported native role policy")
    value = data["roles"][name]
    if value.get("runtime") != "codex_desktop" or value.get("authentication") != "chatgpt" or value.get("allow_api_fallback") is not False:
        raise ValueError("Native roles require desktop ChatGPT authentication without fallback")
    if value.get("reasoning_effort") not in {"low", "medium", "high", "xhigh", "max", "ultra"} or value.get("speed") != "standard":
        raise ValueError("Unsupported reasoning/speed policy")
    if not re.fullmatch(r"gpt-[a-zA-Z0-9.\-]+", value.get("model", "")):
        raise ValueError("Invalid model ID")
    return value

def project(slug):
    try:
        return projects()[slug]
    except KeyError as exc:
        raise ValueError("Project is outside the reviewed registry") from exc

def git(cwd, *arguments):
    result = subprocess.run(["git", "-C", str(cwd), *arguments], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise ValueError("Git verification failed: " + " ".join(arguments[:2]))
    return result.stdout.strip()

def verify_repository(slug, cwd=None):
    item = project(slug)
    path = Path(cwd or item["path"]).resolve()
    origin = git(path, "remote", "get-url", "origin")
    match = re.fullmatch(r"(?:git@github\.com:|https://github\.com/)([^/]+/[^/]+?)(?:\.git)?/?", origin)
    if not match or match.group(1).lower() != item["repository"].lower():
        raise ValueError("Checkout origin does not match the reviewed repository")
    return {"path": str(path), "repository": item["repository"], "head": git(path, "rev-parse", "HEAD")}

def state(slug):
    project(slug)
    path = RUNTIME / slug
    if path.is_symlink():
        raise ValueError("Private project state cannot be symlinked")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path

def connection(slug):
    path = state(slug) / "tasks.sqlite3"
    if path.is_symlink():
        raise ValueError("Private task ledger cannot be symlinked")
    db = sqlite3.connect(path, timeout=15, isolation_level=None)
    os.chmod(path, 0o600)
    db.row_factory = sqlite3.Row
    db.executescript("""
      CREATE TABLE IF NOT EXISTS passes (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, started_at TEXT NOT NULL,
        state TEXT NOT NULL, finished_at TEXT, evidence TEXT);
      CREATE UNIQUE INDEX IF NOT EXISTS one_pass ON passes(state) WHERE state='active';
      CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, scope TEXT NOT NULL UNIQUE, base TEXT NOT NULL,
        state TEXT NOT NULL, prompt_path TEXT NOT NULL, authority TEXT NOT NULL,
        acceptance TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        pass_id TEXT, thread_id TEXT UNIQUE, host_id TEXT, cwd TEXT, observed_status TEXT,
        observed_at TEXT, evidence TEXT);
    """)
    db.execute("BEGIN IMMEDIATE")
    if "admission" not in {row["name"] for row in db.execute("PRAGMA table_info(tasks)")}:
        db.execute("ALTER TABLE tasks ADD COLUMN admission TEXT")
    db.commit()
    return db

def begin(slug, owner):
    identifier(owner)
    db = connection(slug)
    try:
        db.execute("BEGIN IMMEDIATE")
        active = db.execute("SELECT * FROM passes WHERE state='active'").fetchone()
        if active:
            db.rollback()
            return {"status": "already_owned" if active["owner"] == owner else "blocked", "pass": dict(active),
                    "instruction": "Read the actual owner task before recovery; never reclaim on elapsed time alone."}
        value = {"id": str(uuid4()), "owner": owner, "started_at": now(), "state": "active"}
        db.execute("INSERT INTO passes(id,owner,started_at,state) VALUES (:id,:owner,:started_at,:state)", value)
        db.commit()
        return {"status": "claimed", "pass": value}
    finally:
        db.close()

def end(slug, pass_id, evidence, recovered=False):
    identifier(pass_id)
    if not evidence.strip():
        raise ValueError("A result/recovery evidence reference is required")
    db = connection(slug)
    try:
        cursor = db.execute("UPDATE passes SET state=?,finished_at=?,evidence=? WHERE id=? AND state='active'",
                            ("recovered" if recovered else "finished", now(), evidence, pass_id))
        if cursor.rowcount != 1:
            raise ValueError("No matching active pass")
    finally:
        db.close()

def pilot(slug, action, thread_id=None, child_id=None, evidence=None):
    directory = state(slug) / "pilot"
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / "result.json"
    if action == "claim":
        identifier(thread_id)
        fd = os.open(directory / "dispatch.claim", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(thread_id + "\n")
        result = {"project": slug, "owner_thread": thread_id, "status": "dispatching", "claimed_at": now()}
        private_json(path, result)
        return result
    if not path.exists():
        return {"project": slug, "status": "not_started"}
    result = read_json(path)
    if action == "attach":
        identifier(child_id)
        if result["status"] != "dispatching":
            raise ValueError("Pilot already dispatched; never retry")
        result.update(child_thread=child_id, status="created", created_at=now())
    elif action == "verify":
        identifier(thread_id)
        if result["status"] not in {"created", "verified"} or thread_id == result["owner_thread"]:
            raise ValueError("A different scheduled pass must witness the created task")
        if child_id != result.get("child_thread") or not evidence:
            raise ValueError("Exact child and native task evidence required")
        result.update(status="verified", observer_thread=thread_id, verified_at=now(), evidence=evidence)
    elif action != "status":
        raise ValueError("Unknown pilot operation")
    if action != "status":
        private_json(path, result)
    return result

def prompt(slug):
    item = project(slug)
    return (f"You are Paul's native desktop scheduled coordinator for {slug} only. "
            f"Project: {item['path']}; reviewed repository: {item['repository']}. "
            f"Coordinator tooling checkout: {ROOT}. "
            f"Read {ROOT / 'config/coordinators/common.md'} and {ROOT / item['responsibilities']} before acting. "
            f"Use {ROOT / '.venv/bin/python'} {ROOT / 'scripts/coordinator.py'} "
            f"with --project {slug} for private state and duplicate guards. "
            "Perform one bounded coordination pass; reconcile existing tasks before starting work. "
            "Keep source edits in separate native worktree coding tasks. "
            "End with a concise visible result, pending decisions and next action.")

def prepare_task(slug, scope, base, prompt_path, authority, acceptance):
    verify_repository(slug)
    if not scope.strip() or not authority.strip() or not acceptance.strip() or not SHA.fullmatch(base):
        raise ValueError("Stable scope, reviewed full base SHA, authority and acceptance checks required")
    item = project(slug)
    if git(item["path"], "rev-parse", base + "^{commit}") != base:
        raise ValueError("Reviewed base is not a local commit")
    source = Path(prompt_path).resolve()
    if not source.is_relative_to(state(slug).resolve()) or not source.is_file():
        raise ValueError("Task prompt must be in this project's private state")
    text = source.read_text()
    if not text.strip() or len(text.encode()) > 65536:
        raise ValueError("Task prompt must be nonempty and at most 64 KiB")
    db = connection(slug)
    try:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT * FROM tasks WHERE scope=?", (scope,)).fetchone()
        if existing:
            db.rollback()
            return {"status": "existing", "task": dict(existing)}
        task_id = str(uuid4())
        frozen = state(slug) / "prompts" / (task_id + ".txt")
        frozen.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(frozen, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
        row = {"id": task_id, "scope": scope, "base": base, "state": "prepared", "prompt_path": str(frozen),
               "authority": authority, "acceptance": acceptance, "created_at": now(), "updated_at": now()}
        db.execute("""INSERT INTO tasks(id,scope,base,state,prompt_path,authority,acceptance,created_at,updated_at)
                      VALUES(:id,:scope,:base,:state,:prompt_path,:authority,:acceptance,:created_at,:updated_at)""", row)
        db.commit()
        return {"status": "prepared", "task": row}
    finally:
        db.close()

def task(slug, task_id):
    identifier(task_id)
    db = connection(slug)
    try:
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown project task")
        return dict(row)
    finally:
        db.close()

def claim_task(slug, task_id, pass_id):
    identifier(task_id)
    identifier(pass_id)
    role("coding")
    binding = read_json(state(slug) / "desktop.json")
    if binding.get("path") != project(slug)["path"] or binding.get("host_id") != "local":
        raise ValueError("Refresh the native project binding before dispatch")
    if pilot(slug, "status").get("status") != "verified":
        raise ValueError("Scheduled delegation pilot must be verified before dispatch")
    db = connection(slug)
    try:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM passes WHERE id=? AND state='active'", (pass_id,)).fetchone():
            raise ValueError("Dispatch needs the current active coordination pass")
        changed = db.execute("UPDATE tasks SET state='dispatching',pass_id=?,updated_at=? WHERE id=? AND state='prepared'",
                             (pass_id, now(), task_id))
        if changed.rowcount != 1:
            raise ValueError("Task already claimed/started; ambiguous dispatch must never be retried automatically")
        db.commit()
    finally:
        db.close()
    return task(slug, task_id)

def bind_project(slug, project_id):
    verify_repository(slug)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", project_id):
        raise ValueError("Use an actual project ID returned by native list_projects")
    private_json(state(slug) / "desktop.json", {"project_id": project_id, "path": project(slug)["path"], "host_id": "local", "updated_at": now()})

def dispatch_plan(slug, task_id):
    row = task(slug, task_id)
    if row["state"] != "dispatching":
        raise ValueError("Claim the task once before obtaining creation arguments")
    settings = role("coding")
    binding = read_json(state(slug) / "desktop.json")
    if binding["path"] != project(slug)["path"] or binding["host_id"] != "local":
        raise ValueError("Refresh the native project binding")
    if pilot(slug, "status").get("status") != "verified":
        raise ValueError("Native scheduled dispatch/discovery pilot is not verified for this project")
    command = f"{ROOT / '.venv/bin/python'} {ROOT / 'scripts/coordinator.py'} --project {slug}"
    instructions = (
        f"Paul authorizes this scoped implementation in a separate native worktree. Intent {task_id}; "
        f"authority: {row['authority']}; reviewed base: {row['base']}. "
        f"Before editing run {command} task-start --task {task_id} --cwd YOUR_ACTUAL_CWD. "
        "Stop on a base/origin/worktree/cleanliness mismatch. Preserve the primary checkout and user changes. "
        "Read applicable project AGENTS.md. Product/release decisions outside this scope belong to Paul. "
        f"Acceptance: {row['acceptance']}. Complete relevant checks and create/update any PR required by the scoped task and project. "
        "Return the actual base, diff/check results, remaining decisions and PR URL. "
        "Use the project environment runner at the actual worktree/app path when credentials are needed; map uses --shell-only.\n\n"
        + Path(row["prompt_path"]).read_text()
    )
    return {"model": settings["model"], "thinking": settings["reasoning_effort"],
            "title": f"{slug}: {row['scope'][:80]}", "prompt": instructions,
            "target": {"type": "project", "projectId": binding["project_id"], "environment": {"type": "worktree"}}}

def attach_task(slug, task_id, thread_id, host_id):
    identifier(thread_id)
    if host_id != "local":
        raise ValueError("Attach only the exact ready local thread; resolve pending/unknown outcomes first")
    db = connection(slug)
    try:
        cursor = db.execute("""UPDATE tasks SET state='started',thread_id=?,host_id=?,updated_at=?
          WHERE id=? AND state IN ('dispatching','started') AND (thread_id IS NULL OR thread_id=?)""",
          (thread_id, host_id, now(), task_id, thread_id))
        if cursor.rowcount != 1:
            raise ValueError("Task is not admitted or belongs to a different thread")
    finally:
        db.close()
    return {"task": task(slug, task_id), "url": f"codex://threads/{thread_id}"}

def start_task(slug, task_id, cwd, thread_id):
    identifier(thread_id)
    row = task(slug, task_id)
    if row["state"] not in {"dispatching", "started"} or (row["thread_id"] and row["thread_id"] != thread_id):
        raise ValueError("Task is not admitted or is owned by another native thread")
    primary = Path(project(slug)["path"]).resolve()
    cwd = Path(cwd).resolve()
    # Save the actual identity first, including if worktree admission fails. The creator
    # may have received only a pending client ID; the ledger is its discovery path.
    db = connection(slug)
    try:
        cursor = db.execute("""UPDATE tasks SET state='started',thread_id=?,host_id='local',cwd=?,updated_at=?
          WHERE id=? AND state IN ('dispatching','started') AND (thread_id IS NULL OR thread_id=?)""",
          (thread_id, str(cwd), now(), task_id, thread_id))
        if cursor.rowcount != 1:
            raise ValueError("Task admission changed; stop before editing")
    finally:
        db.close()
    try:
        verify_repository(slug, cwd)
        if cwd == primary or git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir") != git(primary, "rev-parse", "--path-format=absolute", "--git-common-dir"):
            raise ValueError("Coding must use a linked worktree of this project, never the primary checkout")
        if git(cwd, "rev-parse", "HEAD") != row["base"] or git(cwd, "status", "--porcelain"):
            raise ValueError("Native worktree must start clean at the reviewed base")
    except (ValueError, OSError, subprocess.TimeoutExpired):
        db = connection(slug)
        try:
            db.execute("UPDATE tasks SET admission='blocked',updated_at=? WHERE id=? AND thread_id=?", (now(), task_id, thread_id))
        finally:
            db.close()
        raise
    db = connection(slug)
    try:
        db.execute("UPDATE tasks SET admission='verified',updated_at=? WHERE id=? AND thread_id=?", (now(), task_id, thread_id))
    finally:
        db.close()
    return {"task": task(slug, task_id), "admission": "verified", "instruction": "Read project instructions, then implement only the authorized scope."}

def observe_task(slug, task_id, observed_status, evidence, close=False):
    row = task(slug, task_id)
    if not row["thread_id"] or not evidence.strip():
        raise ValueError("Exact native thread and fresh observation evidence required")
    db = connection(slug)
    try:
        db.execute("""UPDATE tasks SET observed_status=?,observed_at=?,evidence=?,
          state=CASE WHEN ? THEN 'closed' ELSE state END,updated_at=? WHERE id=?""",
          (observed_status, now(), evidence, close, now(), task_id))
    finally:
        db.close()
    return task(slug, task_id)

def schedule_binding(slug, automation_id):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", automation_id):
        raise ValueError("Use the exact native automation ID")
    private_json(state(slug) / "schedule.json", {"automation_id": automation_id, "updated_at": now()})

def schedule_plan(slug, status=None):
    settings = role("coordinator")
    binding = read_json(state(slug) / "desktop.json")
    if binding.get("path") != project(slug)["path"] or binding.get("host_id") != "local":
        raise ValueError("Refresh native project binding")
    path = state(slug) / "schedule.json"
    existing = read_json(path)["automation_id"] if path.exists() else None
    result = {"mode": "update" if existing else "create", "kind": "cron", "name": f"{slug} project coordinator",
      "executionEnvironment": "local", "projectId": binding["project_id"],
      "model": settings["model"], "reasoningEffort": settings["reasoning_effort"],
      "rrule": project(slug)["schedule"], "prompt": prompt(slug), "status": status or "PAUSED"}
    if existing:
        saved = read_schedule(existing)
        result.update(id=existing, status=status or saved["status"])
        if "notification_policy" in saved:
            result["notificationPolicy"] = saved["notification_policy"]
    return result

def read_schedule(automation_id):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", automation_id):
        raise ValueError("Invalid automation ID")
    # Read only. Automation changes belong to native automation_update, never TOML writes.
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    with (home / "automations" / automation_id / "automation.toml").open("rb") as stream:
        return tomllib.load(stream)

def schedule_audit(slug):
    plan = schedule_plan(slug)
    if plan["mode"] != "update":
        return {"project": slug, "status": "missing", "drift": ["No registered native automation"]}
    saved = read_schedule(plan["id"])
    comparisons = {"name": plan["name"], "kind": "cron", "execution_environment": "local",
                   "model": plan["model"], "reasoning_effort": plan["reasoningEffort"],
                   "rrule": plan["rrule"], "prompt": plan["prompt"],
                   "target": {"type": "project", "project_id": plan["projectId"]}, "cwds": [project(slug)["path"]]}
    drift = [key for key, value in comparisons.items() if saved.get(key) != value]
    return {"project": slug, "automation_id": plan["id"], "status": saved["status"], "drift": drift,
            "configured_model": saved.get("model"), "configured_reasoning": saved.get("reasoning_effort"),
            "runtime_auth_and_speed": "Verify desktop account and Standard speed; not proved by automation TOML"}
