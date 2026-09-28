#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'Usage: delegate-codex.sh <absolute-repo-path> <absolute-prompt-file>' >&2
  exit 64
fi

repo=$1
prompt=$2
if ! git -C "$repo" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Not inside a Git repository: $repo" >&2
  exit 64
fi
if [[ ! -f "$prompt" ]]; then
  echo "Prompt file missing: $prompt" >&2
  exit 64
fi

codex_bin=/Applications/ChatGPT.app/Contents/Resources/codex
if [[ ! -x "$codex_bin" ]]; then
  echo 'Codex CLI is unavailable at the configured path.' >&2
  exit 69
fi

umask 077
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin="$root/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo 'Project environment helper is missing; run scripts/configure.sh.' >&2
  exit 69
fi
mkdir -p "$root/runtime/coordinator/logs"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
run_id="${stamp}-$$"
event_log="$root/runtime/coordinator/logs/codex-${run_id}.jsonl"
last_message="$root/runtime/coordinator/logs/codex-${run_id}.last.txt"

echo "Codex Sol (high) started: $run_id"
echo "Events: $event_log"

set +e
"$python_bin" "$root/scripts/project-env.py" --cwd "$repo" -- "$codex_bin" exec \
  --cd "$repo" \
  --model gpt-6-sol \
  -c 'model_reasoning_effort="high"' \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  --output-last-message "$last_message" \
  - < "$prompt" > "$event_log" 2>&1
result=$?
set -e

echo "Codex exit code: $result"
echo "Events: $event_log"
if [[ -f "$last_message" ]]; then
  echo 'Last message:'
  tail -c 4000 "$last_message"
  echo
else
  echo 'No final message was written; inspect the event log.'
fi
exit "$result"
