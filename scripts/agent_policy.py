"""Shared role policy and Codex launch boundary; never reads or prints tokens."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent.parent
INFERENCE_ENV = ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID", "OPENAI_PROJECT_ID")


class PolicyError(ValueError):
    pass


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise PolicyError(f"Cannot read valid JSON: {path}") from exc


def load_policy(root=ROOT):
    policy = read_json(root / "config/agent-models.json")
    if set(policy) != {"schema_version", "roles"} or policy["schema_version"] != 1:
        raise PolicyError("Unsupported model policy schema")
    roles = policy["roles"]
    if set(roles) != {"coordinator", "local_coding", "cloud_coding"}:
        raise PolicyError("Policy must define three independent roles")
    for name, role in roles.items():
        cloud = name == "cloud_coding"
        expected = {"runtime", "authentication", "allow_api_fallback"} | (
            {"requested_model", "requested_reasoning_effort", "requested_speed", "model_control", "attempts"}
            if cloud else {"provider", "model", "reasoning_effort", "speed"})
        if set(role) != expected:
            raise PolicyError(f"Unexpected or missing policy fields for {name}")
        if role["authentication"] != "chatgpt" or role["allow_api_fallback"] is not False:
            raise PolicyError(f"{name} must use ChatGPT without API fallback")
        if role["runtime"] != {"coordinator": "codex", "local_coding": "codex_cli", "cloud_coding": "codex_cloud"}[name]:
            raise PolicyError(f"Unsupported runtime for {name}")
        prefix = "requested_" if cloud else ""
        if not re.fullmatch(r"gpt-[a-zA-Z0-9.-]+", role[prefix + "model"]):
            raise PolicyError(f"Invalid model ID for {name}")
        if role[prefix + "reasoning_effort"] not in ("low", "medium", "high", "xhigh", "max", "ultra"):
            raise PolicyError(f"Unsupported reasoning effort for {name}")
        if role[prefix + "speed"] != "standard":
            raise PolicyError("Only verified Standard speed is supported")
        if not cloud and role["provider"] != "openai":
            raise PolicyError("Only official OpenAI routing is supported")
        if cloud and (type(role["attempts"]) is not int or role["attempts"] != 1 or role["model_control"] not in ("unverified_remote_setting", "verified_remote_setting")):
            raise PolicyError("Invalid Cloud control policy")
    return policy


def load_runtime(root=ROOT):
    runtime = read_json(root / "config/codex-runtime.json")
    expected = {"schema_version", "openclaw_binary", "openclaw_version", "plugin_package", "managed_app_server_version", "coordinator_home_scope", "coordinator_auth_profile", "cli_binary", "cli_version", "cli_home", "user_home", "workspace", "compatibility_checked_at"}
    if set(runtime) != expected or runtime["schema_version"] != 1 or runtime["coordinator_home_scope"] != "agent":
        raise PolicyError("Unsupported runtime configuration")
    for key in ("openclaw_binary", "cli_binary", "cli_home", "user_home", "workspace"):
        if not isinstance(runtime[key], str) or not Path(runtime[key]).is_absolute():
            raise PolicyError(f"Runtime {key} must be an explicit absolute path")
    if not re.fullmatch(r"openai:[\w@.+:-]+", runtime["coordinator_auth_profile"]):
        raise PolicyError("Invalid coordinator auth profile")
    return runtime


def private_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise PolicyError(f"Refusing symlink: {path}")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        f.write(data if isinstance(data, bytes) else data.encode())
    try:
        temp.chmod(0o600)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def cli_env(runtime, inherited=None):
    env = dict(os.environ if inherited is None else inherited)
    for key in INFERENCE_ENV:
        env.pop(key, None)
    env["HOME"] = runtime["user_home"]
    env["CODEX_HOME"] = runtime["cli_home"]
    return env


def cli_prefix(runtime):
    # These override user/project profiles; default is the CLI's Standard tier.
    return [runtime["cli_binary"], "-c", 'forced_login_method="chatgpt"',
            "-c", 'model_provider="openai"', "-c", 'service_tier="default"',
            "-c", "features.fast_mode=false"]


def require_cli(runtime, cwd=None):
    if not os.access(runtime["cli_binary"], os.X_OK):
        raise PolicyError("Configured Codex CLI is missing; run configure.sh --prepare")
    candidates = [Path(runtime["cli_home"]) / "config.toml"]
    if cwd is not None:
        directory = Path(cwd).resolve()
        base = Path(git(directory, "rev-parse", "--show-toplevel")).resolve()
        for parent in (directory, *directory.parents):
            candidates.append(parent / ".codex/config.toml")
            if parent == base: break
    for candidate in candidates:
        if candidate.exists():
            try: config = tomllib.loads(candidate.read_text())
            except (OSError, ValueError) as exc: raise PolicyError("Cannot audit Codex configuration") from exc
            if config.get("model_providers", {}).get("openai") or config.get("chatgpt_base_url"):
                raise PolicyError("Authored OpenAI/ChatGPT route in Codex config requires review; no custom inference route accepted")
    env = cli_env(runtime)
    version = subprocess.run([runtime["cli_binary"], "--version"], env=env, capture_output=True, text=True, timeout=15)
    if version.returncode or version.stdout.strip() != "codex-cli " + runtime["cli_version"]:
        raise PolicyError("Codex CLI version drift; compatibility check required")
    status = subprocess.run([runtime["cli_binary"], "login", "status"], env=env, capture_output=True, text=True, timeout=15)
    if status.returncode or "Logged in using ChatGPT" not in status.stdout + status.stderr:
        raise PolicyError("Configured Codex home needs ChatGPT sign-in; API credentials are rejected")
    return {"version": runtime["cli_version"], "binary": str(Path(runtime["cli_binary"]).resolve()), "home": runtime["cli_home"], "authentication": "chatgpt"}


def inventory(root=ROOT):
    rows = {}
    for line in (root / "config/managed-repositories.tsv").read_text().splitlines():
        if line and not line.startswith("#"):
            repo, checkout = line.split("\t")
            rows[repo] = Path(checkout).resolve()
    return rows


def git(path, *args):
    p = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, timeout=20)
    if p.returncode:
        raise PolicyError("Git validation failed: " + args[0])
    return p.stdout.strip()


def verify_origin(path, repository):
    origin = git(path, "remote", "get-url", "origin")
    if origin not in (f"git@github.com:{repository}", f"git@github.com:{repository}.git", f"https://github.com/{repository}", f"https://github.com/{repository}.git"):
        raise PolicyError("Origin does not match the reviewed repository")


def verified_worktree(repository, path, base, root=ROOT):
    rows = inventory(root)
    if repository not in rows:
        raise PolicyError("Repository is outside the managed inventory")
    canonical = rows[repository]
    path = Path(path).resolve(strict=True)
    verify_origin(canonical, repository)
    verify_origin(path, repository)
    if path == canonical or Path(git(path, "rev-parse", "--show-toplevel")).resolve() != path:
        raise PolicyError("Coding requires the root of a separate linked worktree")
    if git(canonical, "rev-parse", "--path-format=absolute", "--git-common-dir") != git(path, "rev-parse", "--path-format=absolute", "--git-common-dir"):
        raise PolicyError("Worktree belongs to a different Git repository")
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise PolicyError("Base must be the explicit reviewed 40-character commit SHA")
    if git(path, "rev-parse", "HEAD") != base or git(path, "status", "--porcelain"):
        raise PolicyError("New coding invocation requires a clean worktree at its reviewed base")
    branch = git(path, "symbolic-ref", "--short", "HEAD")
    if not branch.startswith("codex/"):
        raise PolicyError("Coding worktree needs a codex/ branch")
    return path


def coordinator_patch(policy, runtime, root=ROOT):
    role = policy["roles"]["coordinator"]
    ref = f"openai/{role['model']}"
    settings = {"model": {"primary": ref, "fallbacks": []},
                "modelPolicy": {"allow": [ref]}, "utilityModel": "",
                "thinkingDefault": role["reasoning_effort"], "fastModeDefault": False,
                "workspace": runtime["workspace"], "cwd": None,
                "models": {ref: {"agentRuntime": {"id": "codex"}, "params": {"fastMode": False}}}}
    heartbeat = {"every": "4h", "target": "owner", "isolatedSession": False,
                 "to": None, "accountId": None, "model": None, "thinking": None,
                 "prompt": (root / "config/heartbeat-prompt.txt").read_text().strip()}
    return {"agents": {"defaults": {**settings, "heartbeat": heartbeat}, "entries": {"main": {**settings, "heartbeat": heartbeat}}},
            "auth": {"order": {"openai": [runtime["coordinator_auth_profile"]]}},
            "plugins": {"entries": {"fireworks": {"enabled": False}, "codex": {"enabled": True, "config": {
                "sessionCatalog": {"enabled": False}, "appServer": {
                    "homeScope": "agent", "clearEnv": list(INFERENCE_ENV),
                    "cyberFailover": {"mode": "off"}, "serviceTier": None,
                    "args": ["app-server", "--listen", "stdio://", "-c", 'forced_login_method="chatgpt"']}}}}},
            "gateway": {"bind": "loopback"}, "memory": {"search": {"provider": "none"}},
            "env": {"shellEnv": {"enabled": True}}}


def merge_patch(existing, patch):
    result = json.loads(json.dumps(existing))
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict):
            result[key] = merge_patch(result.get(key, {}) if isinstance(result.get(key), dict) else {}, value)
        else:
            result[key] = value
    return result


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
