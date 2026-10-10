# Engineering instructions for Codex

This repository develops native Codex desktop project coordinators. Read README.md
for the file map and docs/OPERATIONS.md for recovery. The root file guides engineers
working on this tooling; scheduled operating procedures live in config/coordinators.

## Working judgment

Check consequential assumptions against the environment, project guides and current
authoritative documentation. Explain discrepancies. Correct obvious reversible
mistakes and proceed; ask Paul when plausible interpretations materially change
scope, cost or product behavior. Continue independent useful work while waiting.

## Layout and changes

- config/projects.json owns reviewed repositories, primary checkout paths, schedules
  and responsibility files. Review origin and project instructions before adding one.
- config/agent-models.json independently owns coordinator and coding model intent.
  Update docs/MODEL-POLICY.md whenever consumers or overrides change. Keep model IDs
  out of executable prompts.
- config/coordinators/common.md and project files own operating procedures. Generated
  schedule prompts point to these files; procedure edits need no prompt deployment.
- runtime/native/PROJECT contains private continuity, SQLite task/pass ledgers,
  frozen coding prompts and diagnostic receipts. Never commit, wipe or bulk import it.
  Preserve earlier ignored runtime/history and credentials as recovery evidence.
- scripts/coordinator.py prepares native tool arguments and durable state. It does
  not launch an agent. Use supported native app tools for schedules and tasks;
  never edit automation TOMLs or desktop databases, spoof thread context or bridge
  private desktop endpoints from external processes.

Use one bounded local scheduled pass per project. Scheduled source changes belong
in separate visible native worktree tasks. Preserve primary checkout changes and
human ownership. Never reclaim a pass or redispatch work based on age alone.
Unknown/pending dispatch is reconciled using actual native IDs, never retried blindly.
No headless agent, remote coding environment or external inference fallback.

Native scheduled context discovers the project's own parent/nested AGENTS files.
Read them and preserve their maintenance, credentials, testing and PR requirements.
Do not redefine target project engineering rules in this root file. Model-free
scripts own long-running processes; ordinary scheduled passes reconcile them.

For commands needing project credentials, use:

```sh
.venv/bin/python scripts/project-env.py --cwd ACTUAL_PROJECT_OR_APP -- COMMAND
```

Map always requires --shell-only; do not load its dotenv files. --check prints
names and availability without values; --require NAME adds a required shell value.
Ordinary git/rg/gh reads need no runner. Never put secrets in Git, prompts or output.
Independent map provider keys remain necessary even though coordination uses the
Codex desktop account. Do not modify a running ingestion implementation; observe
maintenance and actual database/process quiescence before such changes.

Inspect the diff and run meaningful checks relevant to changes. Current validation:

```sh
.venv/bin/python scripts/test-native-coordinator.py
.venv/bin/python scripts/test-project-env.py
./scripts/status.sh
```

Use the app's automation_update for any schedule mutation, preserve unrelated
schedules and notification preferences, and audit the saved fields afterward.
Do not start services or imports for a documentation change. Record release evidence
and unknowns honestly; an intended account/speed policy is not proof of runtime use.
