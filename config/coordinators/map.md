# Map responsibilities

Own paulshorey/map only: requested implementation, PR reviews/checks/deployment
failures and the continuous intended POI backlog. Read the project's root AGENTS,
data/poi-ingestion.md, data/ingestion-agents.md and applicable database/source
guides. Preserve Railway dev/prod distinctions and its reviewed IaC procedure.

Paul's standing continuous-ingestion direction covers intended captures, normal
provider stages and uncapped provider spending. Do not impose an allowance, ETA
or overall deadline. Request/cost telemetry is informational. Full runs use
`--unlimited`, including resumes of historically capped runs. Never confuse a
short smoke, extraction, report suffix or exclusion with whole-file completion.

Use `scripts/map-ingestion.py snapshot` once at the start of each scheduled pass.
Its database control and durable supervisor jobs are independent of conversation
handles. Reconcile existing workers first. Do not stop a healthy human-started
worker merely to assume ownership, and never duplicate its run. Inspect the exact
job/result, run/execution, maintenance, locks, heartbeat and progress before
deciding. Native task delegation does not own import waiting.

This migration uses durable detached supervision and reconciliation on normal
project passes. It does not promise an immediate app callback. Ordinary Node
owns hourly health checks, child groups, sleep assertion and terminal journals,
without AI waiting or an automatic ingestion relaunch. Native scheduled passes
can discover existing jobs and make the next decision after verified completion.

Starting a new full import requires this project's native dispatch/discovery pilot
and the map discovery acceptance receipt described in docs/OPERATIONS.md. When
admitted, use `map-ingestion.py start --owner ACTUAL_THREAD_ID -- <exact managed
arguments>`; it defaults uncapped resumes and uses the existing supervisor's
explicit local-only mode. Record its exact job UUID and end the turn. The local
journal plus database evidence is the completion path; no saved native shell
handle or PID is relied on. If admission is not verified, continue read-only
coordination and report the exact gate, not a spending question.

On verified whole-file completion choose the next eligible capture on this pass.
Reconcile the original Dyrt run first if it needs resumption; preserve checkpoint
and source/version scope. Source-specific blockers may permit independent files;
outage/schema/global-lineage blockers stop provider progression. Diagnose failed
or stalled work and dispatch a precise native coding repair, rather than repeatedly
resuming against an unresolved provider error. Maintenance and confirmed quiescence
are required before ingestion runtime/schema/data changes. Use targeted supervisor
or database control requests for stops; confirm actual worker/lock exit afterward.

Do not modify the running ingestion implementation during routine coordination.
Smoke tests follow project bounds. Production imports never run in a coding task's
worktree. Raw private logs and credentials stay out of prompts and Git.
