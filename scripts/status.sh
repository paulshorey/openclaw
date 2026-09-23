#!/usr/bin/env bash
set -u

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
echo 'OpenClaw gateway:'
openclaw gateway status 2>&1 | head -25
echo
echo 'Model:'
openclaw config get agents.defaults.model.primary 2>&1
echo
echo 'Codex authentication:'
/Applications/ChatGPT.app/Contents/Resources/codex login status 2>&1
echo
echo 'GitHub authentication:'
gh auth status 2>&1 | sed -E 's/(Token: ).*/\1[redacted]/'
echo
echo 'Open pull requests authored by paulshorey:'
gh search prs --author paulshorey --state open --limit 30 --json repository,title,number,url,updatedAt 2>&1
echo
echo 'Map ingestion process inventory:'
if [[ -d /Users/pshorey/git/map ]]; then
  root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
  "$root/.venv/bin/python" "$root/scripts/project-env.py" --cwd /Users/pshorey/git/map -- pnpm --silent --filter @lib/db-map ingest:control list --json 2>&1 | head -80
fi
