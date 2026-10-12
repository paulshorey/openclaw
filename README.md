# Native Codex project coordinators

One native Codex desktop scheduled coordinator manages each reviewed local project:
map, livx and notes. Each run appears in the app, reads its project's instructions,
reconciles existing work and records the next action. Coding goes to a separate
visible native task in a linked Git worktree. This preserves the primary checkout
and lets Paul inspect, steer and take over implementation in the desktop app.

Coordinator and coding model settings are independent in
[config/agent-models.json](config/agent-models.json). Both initially request GPT-6.1
Sol with High reasoning and Standard speed using the signed-in ChatGPT account.
Inference runs on OpenAI servers. This toolkit neither launches headless agents
nor configures an API inference provider. Account limits are shared; expired
sign-in or exhausted allowance is reported as a blocker. Independent map ingestion
providers remain part of that project's pipeline.

## Project schedules

The intended cadence is every four hours in the desktop's local timezone:

| Project | Minutes past 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 | Responsibilities |
| --- | --- | --- |
| map | 00 | Requested development, PRs/checks, durable import recovery and intended POI backlog |
| livx | 05 | Requested development, PR feedback, checks and deployment failures |
| notes | 10 | Requested development, PR feedback, editor integrity and checks |

The registry owns cadence and checkout scope. Each scheduled pass has a fresh
conversation and persistent private continuity. A healthy import continues between
passes; completion is reconciled on the next ordinary map pass. There is no promised
immediate agent callback. Keep the desktop app open and the computer awake for
scheduled work. Review account, speed, permissions and notifications in the app.

## File map

| File | Purpose |
| --- | --- |
| [config/projects.json](config/projects.json) | Reviewed repository/path/schedule inventory |
| [config/agent-models.json](config/agent-models.json) | Independent coordinator and coding roles |
| [config/follow-up-authorization.json](config/follow-up-authorization.json) | Paul's standing permission for scoped messages to coordinator-created tasks |
| [config/coordinators/common.md](config/coordinators/common.md) | Claims, reconciliation, delegation and verification |
| [config/coordinators/map.md](config/coordinators/map.md) | Map and continuous ingestion responsibilities |
| [config/coordinators/livx.md](config/coordinators/livx.md), [notes.md](config/coordinators/notes.md) | Project-specific development responsibilities |
| [scripts/coordinator.py](scripts/coordinator.py) | Private ledger and structured native schedule/task arguments |
| [scripts/map-ingestion.py](scripts/map-ingestion.py) | Durable map discovery, admission, stop and terminal reconciliation |
| [scripts/project-env.py](scripts/project-env.py) | Project-scoped credential environment, with explicit map shell-only mode |
| [scripts/status.sh](scripts/status.sh) | Read-only native schedule/task/project/map snapshot |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Installation, task ownership, long job control and recovery |
| [docs/MODEL-POLICY.md](docs/MODEL-POLICY.md) | All model consumers/overrides and change procedure |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | Migration decisions, acceptance evidence and limitations |

Private state is ignored under runtime/native/PROJECT. It contains ACTIVE.md,
tasks.sqlite3, native project/schedule bindings, frozen prompts, import intent
claims and pilot receipts. Map's own .ingest-jobs directory and PostgreSQL control
state remain authoritative for ingestion processes. Historical private data is
preserved separately and is not loaded wholesale into scheduled prompts.

## Setup and inspection

Python 3.11+ and the native desktop app are required. Existing project tools such as
git, gh and pnpm must be available in scheduled execution. If rebuilding the Python
environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/test-native-coordinator.py
.venv/bin/python scripts/test-project-env.py
./scripts/status.sh
```

The app owns schedules. Inside a native conversation, call list_projects, verify
the exact local project/path, then bind it:

```sh
.venv/bin/python scripts/coordinator.py --project map bind --project-id ACTUAL_ID
.venv/bin/python scripts/coordinator.py --project map schedule-plan
```

Pass the emitted structured arguments to native automation_update. A new schedule
starts PAUSED. Register its exact returned ID with schedule-register --id ID, then
run schedule-audit. Enable through the same native tool after acceptance. Repeat
for each registered project. These scripts never write the app's automation files.
Changing operating Markdown takes effect next run; changing model, cadence, project
path or generated launch prompt requires updating the registered native schedule.

For models, follow [MODEL-POLICY.md](docs/MODEL-POLICY.md). For process/thread recovery,
follow [OPERATIONS.md](docs/OPERATIONS.md). Folder relocation is an explicit separate
operator operation because native prompts and private bindings contain absolute
paths. Keep this checkout at its current location until those references are updated.

Official background: [native automations](https://learn.chatgpt.com/docs/automations),
[local environments](https://learn.chatgpt.com/docs/environments/local-environment),
[Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees).
