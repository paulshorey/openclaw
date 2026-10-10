"""Supported Codex Cloud CLI adapter and private transactional task ledger."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
from urllib.parse import quote, urlparse
import uuid
from agent_policy import ROOT, PolicyError, cli_env, cli_prefix, fingerprint, inventory, private_write, read_json, require_cli, verify_origin

CAPABILITIES = {"submit": "gated", "list": True, "status": True, "diff": True,
    "follow_up": False, "cancel": False, "create_pr": False, "apply": False,
    "remote_model_selection": False, "completion_webhook": False, "prompt_stdin": True}


def now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None: raise ValueError("missing timezone")
        return parsed.astimezone(timezone.utc)
    except (ValueError, AttributeError) as exc:
        raise PolicyError("Invalid remote observation timestamp") from exc


def task_url(value):
    parsed = urlparse(value)
    if (parsed.scheme != "https" or parsed.netloc != "chatgpt.com" or parsed.query or parsed.fragment
            or not re.fullmatch(r"/codex/tasks/[A-Za-z0-9_-]+", parsed.path)):
        raise PolicyError("Unsupported Cloud task URL")
    return parsed.path.rsplit("/", 1)[-1], value


def parse_page(text):
    try: page = json.loads(text)
    except ValueError as exc: raise PolicyError("Malformed Cloud list JSON") from exc
    if not isinstance(page, dict) or not isinstance(page.get("tasks"), list) or "cursor" not in page:
        raise PolicyError("Unknown Cloud list schema")
    if page["cursor"] is not None and not isinstance(page["cursor"], str):
        raise PolicyError("Invalid Cloud pagination cursor")
    for task in page["tasks"]:
        if not isinstance(task, dict) or not isinstance(task.get("id"), str) or not isinstance(task.get("status"), str):
            raise PolicyError("Unknown Cloud task schema")
        if task_url(task.get("url", ""))[0] != task["id"]:
            raise PolicyError("Cloud task ID and URL disagree")
        if task.get("updated_at") is not None: timestamp(task["updated_at"])
    return page


class Ledger:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink(): raise PolicyError("Refusing symlinked task ledger")
        self.db = sqlite3.connect(path, timeout=5, isolation_level=None)
        path.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        # Default rollback journal: no unprotected long-lived WAL sidecars.
        self.db.execute("PRAGMA foreign_keys=ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1): raise PolicyError("Unknown ledger schema version")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, repository TEXT NOT NULL, scope TEXT NOT NULL,
            state TEXT NOT NULL, data TEXT NOT NULL, lease_owner TEXT, lease_until REAL,
            UNIQUE(repository, scope));
          CREATE TABLE IF NOT EXISTS observations (
            task_id TEXT NOT NULL REFERENCES tasks(id), observed_at TEXT NOT NULL,
            fingerprint TEXT NOT NULL, data TEXT NOT NULL);
          PRAGMA user_version=1;
        """)

    def close(self): self.db.close()

    def tasks(self):
        return [self.decode(row) for row in self.db.execute("SELECT * FROM tasks ORDER BY rowid")]

    @staticmethod
    def decode(row):
        data = json.loads(row["data"])
        return {**data, "id": row["id"], "state": row["state"], "lease_owner": row["lease_owner"], "lease_until": row["lease_until"]}

    def get(self, local_id):
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (local_id,)).fetchone()
        if row is None: raise PolicyError("Unknown local task ID")
        return self.decode(row)

    def prepare(self, data, local_id=None):
        local_id = local_id or str(uuid.uuid4())
        try:
            self.db.execute("INSERT INTO tasks(id,repository,scope,state,data) VALUES(?,?,?,'prepared',?)",
                (local_id, data["repository"], data["scope"], json.dumps(data)))
        except sqlite3.IntegrityError as exc:
            existing = self.db.execute("SELECT id FROM tasks WHERE repository=? AND scope=?", (data["repository"], data["scope"])).fetchone()
            raise PolicyError(f"Scope already tracked by {existing['id']}; reconcile it instead of duplicating") from exc
        return self.get(local_id)

    def claim(self, local_id, owner, seconds=180):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            task = self.get(local_id)
            if task["state"] != "prepared":
                raise PolicyError("Task is not prepared; uncertain/in-flight submissions cannot be retried")
            if task["owner"] != owner: raise PolicyError("Submission owner differs from prepared intent")
            if task["lease_until"] and task["lease_until"] > time.time():
                raise PolicyError("Another invocation owns the submission lease")
            self.db.execute("UPDATE tasks SET state='submitting',lease_owner=?,lease_until=? WHERE id=?",
                (owner, time.time() + seconds, local_id))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return self.get(local_id)

    def update(self, local_id, state=None, **fields):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            task = self.get(local_id)
            task.update(fields)
            for key in ("id", "state", "lease_owner", "lease_until"): task.pop(key, None)
            if state is None: state = self.get(local_id)["state"]
            self.db.execute("UPDATE tasks SET state=?,data=? WHERE id=?", (state, json.dumps(task), local_id))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return self.get(local_id)

    def observe(self, local_id, observation):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            task = self.get(local_id)
            prior = task.get("remote_observation")
            # Avoid overwriting a newer user continuation with delayed list data.
            observed_timestamp = observation.get("updated_at")
            previous_timestamp = (prior or {}).get("updated_at")
            if observed_timestamp and previous_timestamp and timestamp(observed_timestamp) < timestamp(previous_timestamp):
                self.db.execute("COMMIT")
                return {"changed": False, "stale": True, "id": local_id}
            changed = fingerprint(prior) != fingerprint(observation)
            raw = observation["status"].lower()
            state = {"pending": "running", "ready": "needs_review", "applied": "needs_review", "error": "failed"}.get(raw, "remote_unknown")
            if task["state"] == "verified" and not changed: state = "verified"
            task.update(remote_observation=observation, observed_at=now())
            for key in ("id", "state", "lease_owner", "lease_until"): task.pop(key, None)
            self.db.execute("UPDATE tasks SET state=?,data=? WHERE id=?", (state, json.dumps(task), local_id))
            if changed:
                self.db.execute("INSERT INTO observations VALUES(?,?,?,?)", (local_id, now(), fingerprint(observation), json.dumps(observation)))
            self.db.execute("COMMIT")
            return {"changed": changed, "state": state, "id": local_id, "remote_id": observation["id"], "url": observation["url"]}
        except Exception:
            self.db.execute("ROLLBACK")
            raise


class Cloud:
    def __init__(self, policy, runtime, root=ROOT):
        self.policy, self.runtime, self.root = policy, runtime, root
        registry = read_json(root / "config/codex-cloud-environments.json")
        if registry.get("schema_version") != 1 or not isinstance(registry.get("repositories"), dict):
            raise PolicyError("Invalid Cloud environment registry")
        self.registry = registry["repositories"]

    def call(self, args, prompt=None, timeout=30):
        return subprocess.run(cli_prefix(self.runtime) + ["cloud", *args],
            input=prompt, capture_output=True, text=True, timeout=timeout,
            cwd=self.root, env=cli_env(self.runtime))

    def mapping(self, repository, submit=False):
        if repository not in inventory(self.root) or repository not in self.registry:
            raise PolicyError("No reviewed Cloud repository mapping")
        entry = self.registry[repository]
        if not isinstance(entry.get("base_branch"), str) or not entry["base_branch"]:
            raise PolicyError("Cloud mapping requires an explicit remote base branch")
        if submit:
            if entry.get("enabled") is not True or entry.get("readiness") != "ready" or not entry.get("environment_id"):
                raise PolicyError("Cloud dispatch disabled: environment and end-to-end pilot are unverified")
            role = self.policy["roles"]["cloud_coding"]
            if role["model_control"] != "verified_remote_setting" or entry.get("model_control") != "verified_remote_setting":
                raise PolicyError("Cloud dispatch disabled: remote model/effort/speed enforcement is unverified")
            if entry.get("tested_cli_version") != self.runtime["cli_version"] or not entry.get("pilot_evidence") or not entry.get("verified_at"):
                raise PolicyError("Cloud compatibility/pilot evidence is missing or stale")
            # No supported CLI remote model selector in the selected version.
            # A flag change must not accidentally promote unimplemented enforcement.
            if CAPABILITIES["remote_model_selection"] is False:
                raise PolicyError("Selected CLI cannot enforce requested remote model settings; a recorded user policy decision or supported new control is required")
        return entry

    def pages(self, environment=None, max_pages=5, deadline_seconds=90):
        tasks, cursor, seen = [], None, set()
        end = time.monotonic() + deadline_seconds
        for _ in range(max_pages):
            remaining = end - time.monotonic()
            if remaining <= 0: return {"tasks": tasks, "cursor": cursor, "complete": False}
            args = ["list", "--json", "--limit", "20"]
            if environment: args += ["--env", environment]
            if cursor: args += ["--cursor", cursor]
            result = self.call(args, timeout=min(30, remaining))
            if result.returncode: raise PolicyError("Cloud list unavailable; no task state inferred")
            page = parse_page(result.stdout)
            tasks.extend(page["tasks"])
            cursor = page["cursor"]
            if not cursor: return {"tasks": tasks, "cursor": None, "complete": True}
            if cursor in seen: raise PolicyError("Cloud list repeated a pagination cursor")
            seen.add(cursor)
        return {"tasks": tasks, "cursor": cursor, "complete": False}

    def prepare(self, ledger, repository, scope, owner, authority, prompt_path, acceptance):
        entry = self.mapping(repository)
        verify_origin(inventory(self.root)[repository], repository)
        branch = entry["base_branch"]
        result = subprocess.run(["gh", "api", f"repos/{repository}/commits/{quote(branch, safe='')}", "--jq", ".sha"],
            capture_output=True, text=True, timeout=20)
        if result.returncode or not re.fullmatch(r"[0-9a-f]{40}", result.stdout.strip()):
            raise PolicyError("Cannot establish the remote starting SHA")
        prompt = Path(prompt_path).read_text()
        if not prompt.strip(): raise PolicyError("Task prompt is empty")
        data = {"route": "cloud", "repository": repository, "scope": scope, "owner": owner,
            "authority": authority, "acceptance": acceptance, "prepared_at": now(),
            "environment_id": entry["environment_id"], "generation": entry["generation"],
            "base_branch": branch, "expected_sha": result.stdout.strip(), "verified_starting_sha": None,
            "policy": self.policy["roles"]["cloud_coding"], "prompt_digest": fingerprint(prompt),
            "remote_id": None, "remote_url": None, "result_verified": False}
        local_id = str(uuid.uuid4())
        private = Path(self.runtime["workspace"]) / "logs/codex-cloud" / local_id / "prompt.txt"
        private_write(private, prompt)
        data["prompt_path"] = str(private)
        # A crash before INSERT leaves only an unclaimed private prompt; a
        # prepared task always contains its complete immutable prompt reference.
        return ledger.prepare(data, local_id)

    def submit(self, ledger, local_id, owner):
        task = ledger.get(local_id)
        entry = self.mapping(task["repository"], submit=True)
        if task["policy"] != self.policy["roles"]["cloud_coding"] or task["environment_id"] != entry["environment_id"] or task["base_branch"] != entry["base_branch"]:
            raise PolicyError("Prepared policy/environment drift; review intent before dispatch")
        require_cli(self.runtime, cwd=self.root)
        prompt = Path(task["prompt_path"]).read_text()
        if fingerprint(prompt) != task["prompt_digest"]: raise PolicyError("Prepared prompt changed")
        task = ledger.claim(local_id, owner)
        marker = f"OPENCLAW_TASK:{local_id}"
        query = f"{marker}\nRepository: {task['repository']}\nExpected starting commit: {task['expected_sha']}\nReport actual starting commit before editing; stop on mismatch.\nAuthority: {task['authority']}\nAcceptance: {task['acceptance']}\nRead repository AGENTS.md; pending user decisions remain pending.\n\n{prompt}"
        ledger.update(local_id, dispatched_at=now(), marker=marker)
        evidence = Path(task["prompt_path"]).parent / "submission.txt"
        try:
            # Verified in upstream 0.160.0 source: '-' reads stdin. Prompt stays off argv.
            result = self.call(["exec", "--env", task["environment_id"], "--branch", task["base_branch"], "--attempts", "1", "-"], prompt=query, timeout=90)
            private_write(evidence, result.stdout + result.stderr)
            urls = re.findall(r"https://chatgpt\.com/codex/tasks/[A-Za-z0-9_-]+", result.stdout)
            if result.returncode or len(set(urls)) != 1: raise PolicyError("Cloud response did not establish one accepted task")
            remote_id, url = task_url(urls[0])
            return ledger.update(local_id, "submitted", remote_id=remote_id, remote_url=url, submission_evidence=str(evidence))
        except (OSError, subprocess.TimeoutExpired, PolicyError) as exc:
            ledger.update(local_id, "submission_unknown", error_class=type(exc).__name__, submission_evidence=str(evidence), next_action="Reconcile; do not resubmit")
            raise PolicyError("Submission outcome unknown; retained intent must be reconciled, never retried automatically") from exc

    def reconcile(self, ledger):
        tasks = ledger.tasks()
        if not tasks: return {"changes": [], "unresolved": [], "complete": True}
        require_cli(self.runtime, cwd=self.root)
        page = self.pages()
        by_id = {t["id"]: t for t in page["tasks"]}
        changes, unresolved = [], []
        for task in tasks:
            local_id = task["id"]
            if task["state"] == "submitting" and (task["lease_until"] or 0) < time.time():
                task = ledger.update(local_id, "submission_unknown", next_action="Expired submission lease is ambiguous; reconcile without retry")
            if task.get("remote_id") in by_id:
                observation = by_id[task["remote_id"]]
                if task["environment_id"] != observation.get("environment_id"):
                    unresolved.append({"id": local_id, "reason": "Remote environment mismatch"})
                    continue
                update = ledger.observe(local_id, observation)
                if update["changed"]: changes.append(update)
            elif task["state"] in ("submission_unknown", "submitting"):
                # CLI list exposes title, not full prompt. Marker candidates alone
                # cannot establish exact identity: retain ambiguity for UI inspection.
                candidates = [t["url"] for t in page["tasks"] if task.get("marker", "!missing!") in t.get("title", "") and t.get("environment_id") == task["environment_id"]]
                unresolved.append({"id": local_id, "reason": "Submission needs exact UI identity evidence", "candidates": candidates})
            elif task.get("remote_id"):
                unresolved.append({"id": local_id, "reason": "Absent from bounded list; absence does not prove deletion/failure", "remote_url": task["remote_url"]})
        return {"changes": changes, "unresolved": unresolved, "complete": page["complete"], "cursor": page["cursor"]}

    def bind(self, ledger, local_id, evidence_path):
        """Resolve an ambiguous submission only from explicit exact identity evidence."""
        task = ledger.get(local_id)
        if task["state"] not in ("submission_unknown", "submitting") or task.get("remote_id"):
            raise PolicyError("Only an unbound ambiguous submission can be reconciled by identity evidence")
        if task["state"] == "submitting" and (task["lease_until"] or 0) > time.time():
            raise PolicyError("A live submission lease must settle before binding")
        evidence = read_json(evidence_path)
        for key, expected in (("local_id", local_id), ("repository", task["repository"]),
                ("environment_id", task["environment_id"]), ("prompt_digest", task["prompt_digest"])):
            if evidence.get(key) != expected: raise PolicyError("Exact identity evidence mismatch: " + key)
        if evidence.get("source") != "human_ui_review" or not evidence.get("reviewed_at"):
            raise PolicyError("Binding requires recorded human UI identity review, not a title/list guess")
        remote_id, url = task_url(evidence.get("remote_url", ""))
        require_cli(self.runtime, cwd=self.root)
        page = self.pages(task["environment_id"])
        observed = next((t for t in page["tasks"] if t["id"] == remote_id), None)
        if not observed or observed.get("environment_id") != task["environment_id"]:
            raise PolicyError("Cannot independently observe the reviewed task in the intended environment")
        ledger.update(local_id, "submitted", remote_id=remote_id, remote_url=url,
                      identity_evidence=str(Path(evidence_path).resolve()), resolved_at=now())
        ledger.observe(local_id, observed)
        return ledger.get(local_id)
