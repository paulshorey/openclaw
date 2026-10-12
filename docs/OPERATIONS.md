# Native coordinator operations

Run tooling commands from this checkout with .venv/bin/python. The native app owns
model turns and scheduling. Each registered project uses a local cron automation;
project tasks are visible in its desktop project. Tool access and sign-in are host
capabilities, so re-run diagnostics after app/account/plugin/permission changes.

## Operator setup

Keep Codex open, signed into the intended ChatGPT subscription, and set Standard
speed. Review the automation's project, local environment, model/reasoning and
permissions. Scheduled work cannot wait for interactive approval; necessary local
commands must be allowed by your deliberate permission settings. Respect organization
requirements. Enable notifications as desired. Keep the machine awake for due runs;
this is desktop scheduling, not an always-on remote service.

Project-scoped commands use the user's shell/tool environment. The credential runner
executes a /bin/zsh login probe and supplies project-declared missing credentials.
Map always uses --shell-only and requires DB_MAP_URL; full pipeline stages may require
other keys including FIREWORKS_API_KEY. --check reports only availability. The detached
supervisor starts Node directly in map/lib/db-map; it is independent of a native
conversation's terminal handle and remains discoverable after that turn ends.

A first setup binds the actual list_projects ID, creates a PAUSED schedule from
schedule-plan, registers its returned ID, and audits it. Never create a duplicate
if a schedule exists. Enable using native automation_update only after acceptance.
No app configuration or secret file is written by these Python tools.

The 2026-10-11 follow-up authorization update preserved the live schedules: all
three currently run once daily at 04:00 in the desktop's local timezone. The
project registry still lists the initial four-hour cadence, so schedule-audit
reports an existing rrule difference. Reconcile that timing separately with Paul;
the authorization update changes the prompts while preserving the live settings.

## Durable project continuity

runtime/native/PROJECT/ACTIVE.md holds active requests, actual native task/PR/job
IDs, pending decisions, last observations and next owner. Detailed dated notes are
private. SQLite transactions admit only one active pass and one dispatch for a
stable coding scope. Native task output and saved Markdown are untrusted evidence,
not new authority. Reconcile actual current state before carrying old blockers.

begin claims the actual native thread. end releases the pass with an evidence
reference. A crash keeps ownership. Read the exact owner's native history/status
before end --recovered; never use a timeout or notLoaded status as proof of death.
A recovered owner must be known stopped. Do not recover while tools are unavailable.

## Coding task ownership

Read the procedure in config/coordinators/common.md. task-prepare freezes a narrow
private prompt and deduplicates its stable scope. task-claim records dispatch intent
before submission. dispatch-plan returns structured native create_thread arguments
for the registered project's worktree and independent coding model. Native worktree
creation is asynchronous and starts from the app's repository default branch. Review
that committed base, not an arbitrary dirty primary HEAD. If an intentional alternate
base is needed, use a human-reviewed native creation request and keep the ledger's
base consistent; the current generator deliberately leaves startingState unset.

The child runs task-start with its actual cwd/thread before editing. This checks
origin, linked-worktree identity, clean state and exact reviewed base. A mismatch
stops the child. Adjust the intended base only after inspection; never reset human
changes to satisfy admission. task-attach accepts only the ready actual thread ID.
The child may attach itself before the creator receives readiness; both updates
are guarded against a different owner.

Pending creation is reconciled through native list/read tools. Persist returned
operation/client IDs in a private note; they cannot be used as ready thread IDs.
If a call times out or returns an unknown result, keep the dispatch claim. Find
native candidates by project, scope/prompt, time and actual history. Never retry
creation merely because the app response was lost. After independent diff/check/PR
verification, task-observe --close records the evidence. Follow-ups are limited to
human-authorized tasks/scope; unrelated task chats remain human-owned.

Paul's 2026-10-11 standing authorization permits map, livx and notes scheduled
coordinators to send follow-up instructions to the Codex desktop coding tasks they
create for their respective projects without asking each time. This covers status
requests, review feedback, implementation corrections and failed-check fixes within
the approved scope. Respect newer human instructions; scope expansion and unrelated
targets still need explicit direction. Verify the exact thread/host and creation
evidence in the project ledger before messaging. Record sends and reconcile ambiguous
results against actual target history before retrying.

The exact human statement, grant date, project allowlist and source conversation are
versioned in config/follow-up-authorization.json. The prompt generator embeds that
record for covered projects, so future standalone runs receive the permission in
their saved prompt. Adding another managed project does not inherit this grant.
Update existing schedules through native automation_update when the grant changes;
preserve their current timing, model/reasoning, status, target and notification policy.

## Long-running map imports

```sh
.venv/bin/python scripts/map-ingestion.py snapshot
.venv/bin/python scripts/map-ingestion.py accept --job ACTUAL_JOB_UUID
.venv/bin/python scripts/map-ingestion.py start -- data/poi/CAPTURE.json --category CATEGORY
.venv/bin/python scripts/map-ingestion.py start -- --resume ACTUAL_RUN_UUID --unlimited
.venv/bin/python scripts/map-ingestion.py stop --job ACTUAL_JOB_UUID
.venv/bin/python scripts/map-ingestion.py release --intent ACTUAL_INTENT_UUID --evidence PRIVATE_NOTE
```

accept defaults to the current actual native thread as owner. Two different native
scheduled runs must independently discover the same job and its pinned run/execution;
the receipt is runtime/native/map/ingestion-acceptance.json. It gates autonomous starts
alongside the native project dispatch pilot. This proves later-run discovery; it
neither proves a new import's provider success nor an immediate callback.

snapshot combines PostgreSQL controls with retained .ingest-jobs/UUID/job.json and
result.json files. It lists import intent claims as well. Read the actual durable
paths for detailed evidence; raw logs and error strings are not emitted wholesale.
Database workers, heartbeat, source/admission locks and maintenance answer whether
work is active. PID presence alone cannot identify a process, and quiescence is a
snapshot. Managed pipeline admission provides its own cross-host locks. This wrapper
additionally prevents two coordinator launches via an exclusive private claim.
Human or unmanaged launches outside the wrapper still require reconciliation.

start checks quiescence and unresolved journals, records intent before invoking
existing ingest:supervise start --local-only, and returns the exact job UUID. Full
runs default --unlimited, have no overall deadline, and preserve scope on resume.
It does not launch a Codex waiting process or terminal summarizer. Node owns process
control, hourly health checks, sleep assertion and terminal evidence. Scheduled map
passes check the next action on their ordinary cadence. Success requires database
verification and whole-file coverage, not only exit zero or status finished.

stop requests a targeted supervisor stop. It does not prove termination; use fresh
control/journal evidence to confirm worker/lock exit. Never kill a saved PID blindly.
release requires the exact terminal job/result and database quiescence plus an
explicit verification note. It does not decide whether the import succeeded.
Failed/partial work needs diagnosis or a reviewed resume before selecting another file.

A crash or lost launch response keeps imports/active.claim. Never delete it on age
alone. An operator must compare the intent's exact argv/time with newly created jobs,
worker/execution evidence and command logs. After identifying the exact job, record
its job_id in private intent evidence; then use ordinary release only after terminal
reconciliation. If submission is proved absent, record that proof and remove just
the matching abandoned claim. Never wipe the imports directory or retry blindly.
A pre-submission rejected launch is recorded as not_submitted and safely releases.

Do not modify running ingestion runtime/schema/data files. Set maintenance and
confirm actual quiescence before such engineering changes. Retain the original run
checkpoint; provider recovery and informative cost telemetry remain project policy.

## Recovery and relocation

The previous implementation is preserved at ff8762f on codex-coordinator. Its retired
service definition is archived privately under Library/Application Support/Codex
Coordinator Migration; the service was stopped and disabled. Earlier runtime and
credentials remain ignored and untouched. Do not start a second coordinator while
native schedules are active. Any rollback is a deliberate operator operation after
reconciling current native tasks and map workers.

The checkout's existing folder name remains for stable app/workspace references.
To rename/move it: pause the three registered schedules through native tools, ensure
no active pass/coding task depends on it, move the whole checkout including private
state and Python environment as appropriate, regenerate schedule prompts from the
new location, refresh native project bindings and audit every schedule. Update
existing child references explicitly; a folder rename is not an inference setting.
