# Native per-project coordinator implementation

Implemented 2026-10-10 on codex-native-coordinators. The prior uncommitted
implementation and research were checkpointed as ff8762f on codex-coordinator
before this branch was created. No private runtime/credential history was removed.

## Architecture and scope

Three standalone native desktop cron schedules bind to reviewed map, livx and
notes projects. Every run has a fresh conversation, precise project responsibilities,
private continuity and transactional pass ownership. Coding requests become separate
visible native worktree tasks with frozen scope, explicit independent model/reasoning,
reviewed committed base and admission before any edit. There is no external coordinator
service, headless implementation agent, remote coding environment or API fallback.

The previous gateway is stopped and disabled; its LaunchAgent definition is archived
privately. Active source/configuration/docs and service launch wrappers have been
replaced. The physical checkout name, old Git history and ignored runtime remain
for recovery and stable app references. Renaming the folder is a deliberate separate
operation, documented in OPERATIONS.md.

Model intent stays in two independent roles in config/agent-models.json. Native
schedule-plan and dispatch-plan are their only model-setting consumers. Native
saved schedules are audited against all managed fields. Operating prompts contain
no model IDs. The app's account and speed selectors remain operator controls;
model/reasoning tool arguments cannot prove runtime authentication or Standard speed.

## Verified native acceptance

These are actual desktop scheduled tool executions, not assumptions from a local
script or an app pipe. All one-minute diagnostic schedules are paused after proof.

| Project | Creator scheduled thread | Exact child | Later scheduled observer |
| --- | --- | --- | --- |
| notes | 01a12716-6fc9-79e0-a039-a6b8d2bd1b5d | 01a12716-c10a-7d50-a915-f8b915cb965d | 01a12717-5a2e-76c0-b5c0-e1a35f262c30 |
| map | 01a1271a-195e-7d42-8c8c-f37d9c31fe8e | 01a1271a-6b82-7641-9066-db1c8eb991b5 | 01a1271b-78f5-77e2-866c-859b28150988 |
| livx | 01a1271a-195b-7c43-840d-5136f798e050 | 01a1271a-7be9-7842-ad09-8f5f002f8596 | 01a1271b-03c0-7641-abc7-8c49ef9644de |

Each creator used native list_projects and create_thread with the coding role's
explicit model/High arguments. Each observer used native read_thread to verify a
completed child with exact NATIVE_COORDINATOR_CHILD_OK. No project source changes,
commits, PRs or providers were involved. Private receipts live under
runtime/native/PROJECT/pilot/result.json and native automation memory/history.

A separate Notes worktree pilot created native thread
01a12723-9e0d-7a40-941d-14a66c152e58 in a clean linked worktree, admitted it at reviewed
base 22ac3e0e004d5eea77df3bb7b91a3b9bf014fd1d, and returned
NATIVE_WORKTREE_ADMISSION_OK. The root independently verified clean status/base,
closed that diagnostic intent and released its pass. The clean worktree is retained
for inspection. Its creation returned only a pending client ID; the child registered
its actual ready thread through task-start. Production discovery therefore uses the
private ledger first, including on a failed admission, rather than relying only on
Recents or a transient creation response. Unknown dispatch never triggers a retry.

## Map long-job acceptance

The existing detached Dyrt job f6c1a95e-7759-4c42-a8dc-a48af1e2d8df remained running.
Its original run is 4dda8606-9c20-4275-bae6-c14cdea9e38c and pinned execution is
7561fd60-9f00-4ecd-965c-55b168c53623. Two different native scheduled threads,
01a12721-6c6f-7f40-b476-75090c2b9c45 and 01a12722-56d5-7ad2-a9c8-c47cc964a208,
rediscovered its durable journal and matched the run/execution to fresh database
worker evidence. The later run verified acceptance and paused its diagnostic schedule.
No import was started/stopped and no ingestion runtime/schema/source code was changed.

The new map wrapper uses the existing detached supervisor's explicit local-only mode.
It records intent before submission, holds an exclusive claim across unknown outcomes,
requires quiescence plus resolved journals, defaults full work to --unlimited and
provides targeted stop/terminal reconciliation. Database locks are the pipeline's
cross-host admission truth; a quiescence snapshot cannot serialize unrelated human
or unmanaged starts. The wrapper serializes coordinator launches and all callers
must reconcile other ownership. PID presence never proves process identity.

Healthy waiting is ordinary Node code with hourly probes and durable job/result/log
files. Future map passes discover existing jobs without a conversation handle.
Advancement waits for verified whole-file completion on the next ordinary scheduled
pass, up to roughly four hours later while the app is available. No immediate desktop
callback or process-level relaunch is promised. A new paid import was not launched
solely to test the migration while the existing job was healthy.

Map AGENTS.md and the two ingestion operating documents were aligned with this
explicit scheduled-reconciliation exception. These documentation-only changes
preserve the active worker and unrelated primary-checkout edits. They are saved as
map commit 1568a08 on codex/native-coordinator-docs, separately from this toolkit.
The reviewed documents are also present in the primary working tree so scheduled
context uses the new procedure; its branch and unrelated dirty files were preserved.

## Validation and operator limits

The offline suite tests concurrency, no age-based ownership recovery, scope deduplication,
ambiguous dispatch retention, independent models, guarded thread attachment, worktree
admission, notification preservation, schedule drift, origin/auth intent, uncapped
resume scope, busy-map rejection and two distinct job discovery observers. The existing
project environment suite tests credential scope/precedence without exposing values.
All 14 lifecycle tests and 8 environment tests passed. Diff whitespace, live
origin/schedule audits and fresh map control/journal checks passed. Every managed
schedule matched its registry model/reasoning, project, prompt and cadence before
activation. Private pilot receipts and native histories retain detailed evidence.

Production automation IDs are map-project-coordinator, livx-project-coordinator and
notes-project-coordinator. Only these three are registered as managed schedules.
Unrelated existing account test schedules were preserved. Operator action is to
review desktop ChatGPT account/Standard speed, deliberate local permission settings,
notifications and host availability. No cloud environment or API billing setup is
needed for native coordinator/coding model turns. Map pipeline provider charges
remain separate and unchanged.

The native scheduled capability is verified for the current desktop/account/plugin
configuration. Re-test after relevant upgrades or access changes. A full coding
implementation/PR and a newly launched paid full import are outside the diagnostic
proof; project checks and provider/result verification remain mandatory per actual task.
