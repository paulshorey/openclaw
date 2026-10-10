#!/usr/bin/env python3
"""Validate policy and report safe effective settings and drift."""
import argparse
import json
from pathlib import Path
import sys
import subprocess
from agent_policy import ROOT, PolicyError, coordinator_patch, load_policy, load_runtime, read_json, require_cli


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true", help="Compare live config and exact CLI auth/version")
    p.add_argument("--config", type=Path)
    args = p.parse_args()
    policy, runtime = load_policy(), load_runtime()
    result = {"schema_version": 1, "roles": policy["roles"], "runtime": runtime, "drift": []}
    if args.check:
        config = read_json(args.config or Path(runtime["user_home"]) / ".openclaw/openclaw.json")
        patch = coordinator_patch(policy, runtime)
        for scope in ("defaults", "main"):
            actual = config.get("agents", {}).get("defaults", {}) if scope == "defaults" else config.get("agents", {}).get("entries", {}).get("main", {})
            desired = patch["agents"]["defaults"] if scope == "defaults" else patch["agents"]["entries"]["main"]
            for key in ("model", "modelPolicy", "utilityModel", "thinkingDefault", "fastModeDefault", "workspace", "cwd"):
                if actual.get(key) != desired.get(key):
                    result["drift"].append(f"agents.{scope}.{key}")
            ref = desired["model"]["primary"]
            if actual.get("models", {}).get(ref) != desired["models"][ref]:
                result["drift"].append(f"agents.{scope}.models.{ref}")
            for key in ("model", "thinking", "every", "isolatedSession", "target", "prompt", "to", "accountId"):
                if actual.get("heartbeat", {}).get(key) != desired["heartbeat"].get(key):
                    result["drift"].append(f"agents.{scope}.heartbeat.{key}")
        if config.get("auth", {}).get("order", {}).get("openai") != [runtime["coordinator_auth_profile"]]:
            result["drift"].append("auth.order.openai")
        app = config.get("plugins", {}).get("entries", {}).get("codex", {}).get("config", {}).get("appServer", {})
        desired_app = patch["plugins"]["entries"]["codex"]["config"]["appServer"]
        for key, value in desired_app.items():
            if app.get(key) != value:
                result["drift"].append(f"codex.appServer.{key}")
        for key in ("command", "url", "headers", "authToken"):
            if app.get(key): result["drift"].append(f"unknown codex.appServer.{key} override")
        entries = config.get("plugins", {}).get("entries", {})
        if entries.get("codex", {}).get("enabled") is not True:
            result["drift"].append("plugins.entries.codex.enabled")
        if entries.get("fireworks", {}).get("enabled") is not False:
            result["drift"].append("plugins.entries.fireworks.enabled")
        for key in ("sessionCatalog", "cyberFailover", "serviceTier"):
            if entries.get("codex", {}).get("config", {}).get(key) != patch["plugins"]["entries"]["codex"]["config"].get(key):
                result["drift"].append("codex." + key)
        if config.get("gateway", {}).get("bind") != "loopback":
            result["drift"].append("gateway.bind")
        provider = config.get("models", {}).get("providers", {}).get("openai", {})
        if provider:
            result["drift"].append("authored models.providers.openai route requires review")
        try:
            result["cli"] = require_cli(runtime)
        except PolicyError as exc:
            result["drift"].append(str(exc))
        sessions = subprocess.run([runtime["openclaw_binary"], "sessions", "--agent", "main", "--limit", "all", "--json"], capture_output=True, text=True, timeout=30)
        if sessions.returncode:
            result["drift"].append("Cannot audit saved session overrides")
        else:
            rows = json.loads(sessions.stdout)
            if rows.get("hasMore"): result["drift"].append("Incomplete saved session inventory")
            overrides = []
            role = policy["roles"]["coordinator"]
            for row in rows.get("sessions", []):
                wrong = []
                if row.get("providerOverride") not in (None, "openai"): wrong.append("provider")
                if row.get("modelOverride") not in (None, role["model"], "openai/" + role["model"]): wrong.append("model")
                if row.get("thinkingLevel") not in (None, role["reasoning_effort"]): wrong.append("thinking")
                if row.get("fastMode") not in (None, False): wrong.append("speed")
                if wrong: overrides.append({"session_key": row["key"], "fields": wrong})
            result["session_overrides"] = overrides
            if overrides: result["drift"].append(f"{len(overrides)} saved session override(s) differ from coordinator policy")
    print(json.dumps(result, indent=2))
    return 1 if result["drift"] else 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (PolicyError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema_version": 1, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(78)
