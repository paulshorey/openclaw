#!/usr/bin/env python3
"""Read supported Codex app-server account/model/config metadata without inference."""
import json
import argparse
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
from agent_policy import ROOT, PolicyError, cli_env, cli_prefix, load_policy, load_runtime, require_cli


def probe(runtime, model):
    require_cli(runtime, cwd=ROOT)
    p = subprocess.Popen(cli_prefix(runtime) + ["app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        cwd=ROOT, env=cli_env(runtime), bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(p.stdout, selectors.EVENT_READ)
    pending = b""
    sequence = 0
    def request(method, params):
        nonlocal pending, sequence
        sequence += 1
        p.stdin.write((json.dumps({"id": sequence, "method": method, "params": params}) + "\n").encode())
        end = time.monotonic() + 20
        while time.monotonic() < end:
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                response = json.loads(line)
                if response.get("id") == sequence:
                    if "error" in response: raise PolicyError("App-server metadata request failed: " + method)
                    return response.get("result")
            if selector.select(max(0, end - time.monotonic())):
                data = os.read(p.stdout.fileno(), 65536)
                if not data: raise PolicyError("App-server closed during metadata probe")
                pending += data
                if len(pending) > 4 * 1024 * 1024: raise PolicyError("Oversized app-server metadata")
        raise PolicyError("App-server metadata timeout: " + method)
    try:
        initialized = request("initialize", {"clientInfo": {"name": "openclaw-policy-check", "version": "1.0.0"}, "capabilities": {"experimentalApi": True}})
        p.stdin.write(b'{"method":"initialized","params":{}}\n')
        account = request("account/read", {"refreshToken": False})
        models = request("model/list", {"limit": 100, "includeHidden": False})
        config = request("config/read", {"includeLayers": False})
        selected = next((m for m in models.get("data", []) if m.get("model") == model or m.get("id") == model), None)
        if selected is None: raise PolicyError("Requested model absent from exact CLI account catalog")
        effort = [e.get("reasoningEffort") for e in selected.get("supportedReasoningEfforts", [])]
        safe_config = config.get("config", {})
        return {"schema_version": 1, "account_type": (account.get("account") or {}).get("type"),
            "model": model, "supported_reasoning_efforts": effort,
            "cli_config": {k: safe_config.get(k) for k in ("model_provider", "forced_login_method", "service_tier")},
            "inference_started": False}
    finally:
        selector.close()
        if p.poll() is None:
            p.terminate()
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=5)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--role", choices=("coordinator", "local_coding"), default="coordinator")
        args = parser.parse_args()
        policy, runtime = load_policy(), load_runtime()
        role = policy["roles"][args.role]
        result = probe(runtime, role["model"])
        result["role"] = args.role
        print(json.dumps(result, indent=2))
        if result["account_type"] not in ("chatgpt", "chatgptAuthTokens") or role["reasoning_effort"] not in result["supported_reasoning_efforts"]:
            raise PolicyError("Account/model reasoning capability does not satisfy selected role policy")
    except (PolicyError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema_version": 1, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(78)
