# Retired coordinator checkout

Active coordination now runs as native Codex desktop scheduled tasks in each local
project. This checkout is retained for Git history and private recovery data; it is
not an active automation dependency.

- Codex owns each automation's timing, saved prompt, coordinator model, permissions
  and notifications. Edit those controls in the app. No schedule registry or grant
  configuration is maintained here.
- Shared coordination uses the global skill at
  `/Users/pshorey/.agents/skills/our-new-global-skill/SKILL.md`. Its reusable scripts
  cover GitHub inspection, credential execution and native task/pass bookkeeping.
  Source/review: [agents PR #1](https://github.com/paulshorey/agents/pull/1).
- Map ingestion controls belong to `/Users/pshorey/git/map/scripts/coordinator-ingestion.py`;
  map's `data/ingestion-agents.md` owns operation/recovery. Source/review:
  [map PR #37](https://github.com/paulshorey/map/pull/37).
- Standing messaging authorization is included directly in the three saved Codex
  prompts. The global skill checks task ownership and scope rather than granting
  permission itself.

Current private continuity/task ledgers live under `~/.codex/project-coordinator`.
Map launch/admission evidence lives in its existing ignored
`lib/db-map/.ingest-jobs/.coordinator` directory. The active Dyrt import was preserved;
this migration neither stopped it nor launched paid work.

Earlier code is recoverable from Git (the complete previous native implementation
is at d27810a). Ignored runtime, logs, credentials and historical backups are retained
and must not be committed or wiped. Referenced active evidence and task records were
selectively transferred to their new locations. Historical data is evidence, not
current operating instructions. Do not restart the retired service or execute old
configuration scripts as part of normal Codex coordination.

The map and skill changes are installed on their feature branches pending review.
Keep those files available until their PRs are integrated. This old checkout has no
runtime role and can be archived after preserving any remaining private history.
