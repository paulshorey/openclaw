#!/usr/bin/env bash
set -u

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
inventory="$root/config/managed-repositories.tsv"
snapshot_failed=0
echo 'OpenClaw gateway:'
openclaw gateway status 2>&1 | head -25
echo
echo 'Role policy and effective configuration:'
"$root/.venv/bin/python" "$root/scripts/agent-policy.py" --check || snapshot_failed=1
echo
echo 'Tracked Codex Cloud work:'
"$root/.venv/bin/python" "$root/scripts/codex-cloud.py" list || snapshot_failed=1
echo
echo 'GitHub authentication:'
gh auth status 2>&1 | sed -E 's/(Token: ).*/\1[redacted]/'
echo
echo 'Managed repository snapshot:'
while IFS=$'\t' read -r repo checkout || [[ -n "${repo:-}" ]]; do
  [[ -z "${repo:-}" || "$repo" == \#* ]] && continue
  if [[ -z "${checkout:-}" ]] || ! git -C "$checkout" rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "$repo: checkout missing or invalid: ${checkout:-[unset]}"
    snapshot_failed=1
    continue
  fi
  origin=$(git -C "$checkout" remote get-url origin 2>/dev/null || true)
  case "$origin" in
    "git@github.com:$repo"|"git@github.com:$repo.git"|"https://github.com/$repo"|"https://github.com/$repo.git") ;;
    *) echo "$repo: origin does not match inventory: $origin"; snapshot_failed=1; continue ;;
  esac
  echo
  echo "$repo ($checkout):"
  git -C "$checkout" status --short --branch 2>&1
  if pulls=$(gh api --paginate "repos/$repo/pulls?state=open&per_page=100" 2>&1); then
    echo 'Open PRs (all authors):'
    printf '%s\n' "$pulls" | jq -s 'add | map({number, title, url: .html_url, author: .user.login, draft, updated_at})'
  else
    printf 'Open PR query failed: %s\n' "$pulls"
    snapshot_failed=1
  fi
  if issues=$(gh api --paginate "repos/$repo/issues?state=open&per_page=100" 2>&1); then
    echo 'Open issues:'
    printf '%s\n' "$issues" | jq -s 'add | map(select(.pull_request == null) | {number, title, url: .html_url, updated_at})'
  else
    printf 'Open issue query failed: %s\n' "$issues"
    snapshot_failed=1
  fi
done < "$inventory"
echo
echo 'Map ingestion process inventory:'
if [[ -d /Users/pshorey/git/map ]]; then
  if supervisor=$("$root/.venv/bin/python" "$root/scripts/project-env.py" --cwd /Users/pshorey/git/map --shell-only -- pnpm --silent --filter @lib/db-map ingest:supervise list 2>&1); then
    printf '%s\n' "$supervisor" | head -80
  else
    printf 'Map supervisor discovery failed: %s\n' "$supervisor"
    snapshot_failed=1
  fi
  if controls=$("$root/.venv/bin/python" "$root/scripts/project-env.py" --cwd /Users/pshorey/git/map --shell-only -- pnpm --silent --filter @lib/db-map ingest:control list --json 2>&1); then
    printf '%s\n' "$controls" | head -80
  else
    printf 'Map control discovery failed: %s\n' "$controls"
    snapshot_failed=1
  fi
fi
exit "$snapshot_failed"
