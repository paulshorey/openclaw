#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin="$root/.venv/bin/python"
[[ -x "$python_bin" ]] || python_bin=/opt/homebrew/bin/python3
mode=${1:---dry-run}
if [[ $# -gt 0 ]]; then shift; fi
case "$mode" in
  --dry-run) exec "$python_bin" "$root/scripts/configure-agent-runtime.py" "$@" ;;
  --validate) exec "$python_bin" "$root/scripts/configure-agent-runtime.py" --validate "$@" ;;
  --prepare)
    [[ $# -eq 0 ]] || { echo '--prepare takes no arguments' >&2; exit 64; }
    if [[ ! -x "$root/.venv/bin/python" ]]; then /opt/homebrew/bin/python3 -m venv "$root/.venv"; fi
    "$root/.venv/bin/python" -m pip install -r "$root/requirements.txt"
    policy_values=()
    while IFS= read -r value; do policy_values+=("$value"); done < <("$python_bin" -c 'import json,sys; c=json.load(open(sys.argv[1])); print(c["openclaw_version"]); print(c["plugin_package"]); print(c["cli_binary"]); print(c["cli_version"])' "$root/config/codex-runtime.json")
    /opt/homebrew/bin/openclaw update --tag "${policy_values[0]}" --no-restart --yes
    /opt/homebrew/bin/openclaw plugins install "${policy_values[1]}" --pin --force --accept-capabilities --no-enable
    cli_install_prefix=$(dirname -- "$(dirname -- "$(dirname -- "${policy_values[2]}")")")
    npm install --prefix "$cli_install_prefix" --no-audit --no-fund "@openai/codex@${policy_values[3]}"
    ;;
  --apply)
    "$python_bin" "$root/scripts/configure-agent-runtime.py" --apply "$@"
    "$python_bin" "$root/scripts/configure-ui-workflow.py"
    "$python_bin" "$root/scripts/deploy-workspace.py"
    /opt/homebrew/bin/openclaw config validate
    ;;
  --install-service) exec /opt/homebrew/bin/openclaw gateway install "$@" ;;
  --start) exec /opt/homebrew/bin/openclaw gateway start "$@" ;;
  --restart) exec /opt/homebrew/bin/openclaw gateway restart "$@" ;;
  *) echo 'Usage: configure.sh [--dry-run|--validate|--prepare|--apply|--install-service|--start|--restart]' >&2; exit 64 ;;
esac
