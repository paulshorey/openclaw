# Retired coordinator checkout

Active coordination now runs as native Codex desktop scheduled tasks in each local
project. This checkout is retained for Git history and private recovery data; it is
not an active automation dependency.

- Codex owns each automation's timing, saved prompt, coordinator model, permissions
  and notifications. Edit those controls in the app. No schedule registry or grant
  configuration is maintained here.
- Shared handoff instructions use the global skill at
  `/Users/pshorey/.agents/skills/automation-memory/SKILL.md`. It reads native
  automation memory and previous chats, then updates the same memory file.
  Project responsibilities remain in the saved automation prompts.
  Source/review: [agents PR #1](https://github.com/paulshorey/agents/pull/1).
- Map ingestion controls belong to `/Users/pshorey/git/map/scripts/coordinator-ingestion.py`;
  map's `data/ingestion-agents.md` owns operation/recovery. Source/review:
  [map PR #37](https://github.com/paulshorey/map/pull/37).
- Standing messaging authorization is included directly in the three saved Codex
  prompts. Those prompts require native creation history and recorded ownership
  before follow-ups; memory supplies context rather than permission.

Current handoffs live in Codex's per-automation `memory.md`, whose path is supplied
with each scheduled run. Old ignored project continuity/task ledgers are historical
recovery data; active scheduled prompts no longer use them or the retired helpers.
Map launch/admission evidence lives in its existing ignored
`lib/db-map/.ingest-jobs/.coordinator` directory. The active Dyrt import was preserved;
this migration neither stopped it nor launched paid work.

Earlier code is recoverable from Git (the complete previous native implementation
is at d27810a). Ignored runtime, logs, credentials and historical backups are retained
and must not be committed or wiped. Referenced active evidence and task records were
selectively transferred to their new locations. Historical data is evidence, not
current operating instructions. Do not restart the retired service or execute old
configuration scripts as part of normal Codex coordination.

The memory skill is installed on its feature branch pending review. This old
checkout has no runtime role and can be archived after preserving any remaining
private history.
