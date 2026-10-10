#!/usr/bin/env python3
"""Preview or apply the scoped coordinator patch; never starts the Gateway."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from agent_policy import ROOT, PolicyError, coordinator_patch, load_policy, load_runtime, private_write, read_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--validate", action="store_true", help="Validate the dry-run patch through OpenClaw")
    p.add_argument("--auth-profile", help="Explicit supported ChatGPT auth profile ID")
    args = p.parse_args()
    policy, runtime = load_policy(), load_runtime()
    if args.auth_profile:
        runtime["coordinator_auth_profile"] = args.auth_profile
        if not args.auth_profile.startswith("openai:"):
            raise PolicyError("Expected an OpenAI ChatGPT auth profile")
    patch = coordinator_patch(policy, runtime)
    if not args.apply and not args.validate:
        print(json.dumps({"schema_version": 1, "mode": "preview", "patch": patch}, indent=2))
        return
    config_path = Path(runtime["user_home"]) / ".openclaw/openclaw.json"
    config = read_json(config_path)
    if config.get("models", {}).get("providers", {}).get("openai"):
        raise PolicyError("Review/remove the authored OpenAI provider route before applying native Codex")
    app = config.get("plugins", {}).get("entries", {}).get("codex", {}).get("config", {}).get("appServer", {})
    if any(app.get(k) for k in ("command", "url", "headers", "authToken")):
        raise PolicyError("Review the existing custom Codex transport before applying")
    allow = config.get("plugins", {}).get("allow")
    if allow is not None and "codex" not in allow:
        patch["plugins"]["allow"] = [*allow, "codex"]
    command = [runtime["openclaw_binary"], "config", "patch", "--stdin"]
    for scope in ("agents.defaults", "agents.entries.main"):
        command.extend(["--replace-path", scope + ".model"])
        command.extend(["--replace-path", scope + '.models["' + patch["agents"]["defaults"]["model"]["primary"] + '"]'])
    command.extend(["--replace-path", "plugins.entries.codex.config.appServer"])
    checked = subprocess.run(command + ["--dry-run", "--json"], input=json.dumps(patch), text=True, capture_output=True, timeout=60)
    if checked.returncode:
        evidence = ROOT / "runtime/coordinator/logs/configuration-validation.txt"
        private_write(evidence, checked.stdout + checked.stderr)
        raise PolicyError(f"OpenClaw patch validation failed; private diagnostics: {evidence}")
    if not args.apply:
        print(json.dumps({"schema_version": 1, "validated": True, "changed_live_config": False}))
        return
    subprocess.run([sys.executable, str(ROOT / "scripts/deploy-workspace.py"), "--check"], check=True, timeout=15)
    auth = subprocess.run([runtime["openclaw_binary"], "models", "auth", "list", "--agent", "main", "--json"], text=True, capture_output=True, timeout=30)
    if auth.returncode: raise PolicyError("Cannot inspect OpenClaw auth profiles")
    profiles = json.loads(auth.stdout)
    profile_id = runtime["coordinator_auth_profile"]
    def contains_subscription(obj):
        if isinstance(obj, dict):
            identity = obj.get("id") or obj.get("profileId")
            if identity == profile_id and (obj.get("type") or obj.get("credentialType")) in ("oauth", "token"):
                return True
            return any(contains_subscription(v) for v in obj.values())
        if isinstance(obj, list): return any(contains_subscription(v) for v in obj)
        return False
    if not contains_subscription(profiles):
        raise PolicyError("Selected profile is not verified subscription auth; import/sign in with OpenClaw first")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = Path(runtime["user_home"]) / ".openclaw/backups/codex-coordinator" / stamp
    private_write(backup / "openclaw.json", config_path.read_bytes())
    for name in (".deployed-files.json", "AGENTS.md", "SOUL.md", "IDENTITY.md", "USER.md", "MAP-IMPORTS.md", "CODEX-CLOUD.md"):
        source = Path(runtime["workspace"]) / name
        if source.exists(): private_write(backup / "workspace" / name, source.read_bytes())
    private_write(backup / "manifest.json", json.dumps({"schema_version": 1, "created_at": stamp, "runtime": runtime, "config_target": str(config_path), "service_state": "Apply does not manage service; capture status before cutover"}, indent=2))
    applied = subprocess.run(command, input=json.dumps(patch), text=True, capture_output=True, timeout=60)
    if applied.returncode:
        private_write(backup / "apply-error.txt", applied.stdout + applied.stderr)
        raise PolicyError(f"Apply failed; private rollback evidence: {backup}")
    if args.auth_profile:
        private_write(ROOT / "config/codex-runtime.json", json.dumps(runtime, indent=2) + "\n")
    print(json.dumps({"schema_version": 1, "applied": True, "backup": str(backup), "service_started": False}))


if __name__ == "__main__":
    try: main()
    except (PolicyError, OSError, ValueError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        print(json.dumps({"schema_version": 1, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(78)
