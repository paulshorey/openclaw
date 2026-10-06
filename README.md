# OpenClaw development coordinator

Local OpenClaw bot (macOS LaunchAgent). Coordinator: Fireworks DeepSeek V4.1 Flash. Coding/computer use: Codex CLI, `gpt-6-sol`, high reasoning. Manages the repositories listed in `config/managed-repositories.tsv`; considers `map` ingestion when development is quiet.

## Installed

- OpenClaw CLI: `/opt/homebrew/bin/openclaw` (npm, Homebrew Node 26)
- Gateway state + credentials: `~/.openclaw/`
- Agent workspace: `runtime/coordinator/` (ignored; also default exec dir, agent `cwd` unset)
- Provider plugin: `@openclaw/fireworks-provider`
- Model: `fireworks/accounts/fireworks/models/deepseek-v4p1-flash`
- `gh`: logged in as `paulshorey`
- Codex: `~/.codex/packages/standalone/current/codex` (ChatGPT login)
- Memory search: keyword only (`memory.search.provider: none`; host OpenAI key invalid for embeddings)
- No sandbox: Gateway can reach all of `~/git` with user permissions.

## Secrets

- `~/.openclaw/.env` (mode `0600`): `FIREWORKS_API_KEY`. Telegram is retired; its token is removed from the active environment.
- Never in Git, config, or prompts. Rotate at Fireworks if exposed.
- `env.shellEnv.enabled: true` → imports missing expected keys from login shell (`~/.zprofile` → `~/.shortcuts.sh` → `~/.secrets.sh`). See [environment precedence](https://docs.openclaw.ai/help/environment).

## Development Files

| Path                                         | Purpose                                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `AGENTS.md`                                  | Rules for agents engineering **this repo**                                                   |
| `config/managed-repositories.tsv`            | GitHub/local checkout inventory for the standing coordination queue                          |
| `scripts/deploy-workspace.py`                | Templates → workspace; keeps state; refuses to overwrite changed runtime copies              |
| `scripts/configure.sh`                       | Applies model/workspace/heartbeat/Gateway settings, installs LaunchAgent (may start Gateway) |
| `scripts/delegate-codex.sh`                  | Runs Codex Sol in a repo with project env; logs to `logs/`                                   |
| `scripts/project-env.py`, `requirements.txt` | Project-scoped env runner + its dependency                                                   |
| `scripts/run-map-import.sh`, `scripts/run-map-import.py` | Native import wrapper, completion/ownership checks and optional explicit limits               |
| `scripts/status.sh`                          | Read-only Gateway/auth/PR/ingestion snapshot                                                 |
| `scripts/configure-ui-workflow.py`           | Applies dashboard heartbeat routing, disables Telegram, removes its active bot token         |

## OpenClaw Coordinator Files

| Path                                      | Purpose                                                                                                   |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `config/heartbeat-prompt.txt`             | Hourly heartbeat trigger; applied by `configure.sh`                                                       |
| `config/coordinator-skills.json`         | Small skill catalogue exposed to the coordinator; applied by `configure-ui-workflow.py`                  |
| `config/coordinator/AGENTS.md.template`   | OpenClaw procedure: pass checklist, priorities, delegation/review, GitHub + map workflows, when to notify |
| `config/coordinator/MAP-IMPORTS.md.template` | Map execution details read on demand; keeps the injected AGENTS below the bootstrap limit |
| `config/coordinator/SOUL.md.template`     | Mission, style, autonomy, review principles (broad)                                                       |
| `config/coordinator/IDENTITY.md.template` | Name, role, voice                                                                                         |
| `config/coordinator/USER.md.template`     | Stable facts/preferences about Paul (no secrets, no task state)                                           |
| `runtime/coordinator/state/`              | Private ledger: task IDs, PR URLs, decisions, blockers                                                    |
| `runtime/coordinator/state/ACTIVE.md`     | Short index of current work, pending decisions and evidence links; updated each pass                      |
| `runtime/coordinator/logs/`               | Codex run logs from `delegate-codex.sh`                                                                   |

## Where rules go:

- Engineering this setup → root `AGENTS.md`
- OpenClaw coordination → `config/coordinator/AGENTS.md.template` (enduring role → `SOUL.md.template`)
- Coding inside a project → that project's `AGENTS.md`
- One-off task / run status → `runtime/coordinator/state/`
- Edit templates, not runtime copies, then deploy. Deploy does not start the Gateway.

### Map import runner

Paul authorized continuous uncapped ingestion of all intended map captures on 2026-10-06. Normal provider stages, including normalization, Jina embeddings, geocoding, matching and fusion, are covered. The coordinator resumes interrupted full runs, verifies their database coverage, and advances eligible files until the intended backlog is complete or has documented technical blockers. Cost/request telemetry remains informational; unknown costs require no further approval. The old MAP-IMPORT-BUDGET decision and artificial deadlines are superseded. Full imports have no default completion deadline or ETA; finite limits remain available when explicitly requested later. Map's [ingestion runbook](/Users/pshorey/git/map/data/poi-ingestion.md) owns the command catalog and recovery details.

`./scripts/run-map-import.sh --check` checks completion configuration and returns the current Gateway PID/start time without starting ingestion. Use the owner's effective heartbeat `isolatedSession=false` and `target="owner"` for same-conversation delivery with internal dashboard projection. Isolated routing sends exec completion to a separate heartbeat session and loses the original conversation/process scope; `target="none"` removes raw completion details from the generated prompt and disables that dashboard projection. The wrapper rejects both failure settings. This configuration-only check explicitly does not prove wake-up.

The installed Gateway can defer ordinary native exec events until the next one-hour heartbeat. A callback formatted as `Exec completed (...)` can also lose its details after a heartbeat resets delivery to `none`. Spawned heartbeat sessions intentionally cannot send CLI chat messages. The runner therefore uses the supported targeted `openclaw system event --session-key <owner> --mode now --json` completion path with a generic payload beginning `INTERNAL_MAP_TERMINAL_EVENT`. It identifies the local wrapper and carries the stable event ID plus private evidence paths. The heartbeat prompt handles this marker in its owning conversation before considering scheduled launch logic. Waiting and health checks remain ordinary code; only terminal decisions start model turns. Never clear the subagent execution flag to bypass CLI restrictions.
Before unattended imports, run `./scripts/run-map-import.sh --preflight --owner-session <actual-dashboard-session-key>` through native `exec` with `background=true`, `timeoutSeconds=0`, then end the turn. This mode accepts no import arguments, deadline, credentials or existing completion receipt. It waits a fixed 12 seconds in ordinary code, writes private preflight terminal evidence with a unique marker, and attempts one targeted internal system-event callback. Verify the **automatic continuation with that exact marker in the same dashboard conversation after the initiating turn ends**. A CLI acknowledgement proves acceptance only; it does not prove that a model turn ran. Hidden `agent:main:subagent:...` owners are rejected. Repeat actual proof after a Gateway restart or notification/configuration change.

Each terminal callback must preserve its generic marker through the Gateway's prompt construction even when the conversation's delivery route is `none`. Test automatic preflight-to-import-to-terminal continuation without an intervening human message; one successful wake after a manual chat is insufficient. Native exec ownership and same-owner verification still apply. The wrapper does not start an external channel, independent server or detached import.
A heartbeat with eligible map work must establish its own missing preflight rather than defer it. It saves the chosen action and standing continuous authorization in private `state/map-import-action.json`, launches preflight and ends the turn; the automatic preflight callback records witnessed proof and launches that action. Resume The Dyrt's original campground run `4dda8606-9c20-4275-bae6-c14cdea9e38c` first with `--unlimited`, after fresh control and compatibility checks. After whole-file verification, the same proven owner continuously advances the next eligible intended capture. Fresh hourly conversations reconcile active ownership before selecting work; unchanged deferred PRs do not prevent ingestion progress. A quiet summary is appropriate only when no independently authorized action remains.

Record `runtime/coordinator/state/map-native-completion.json` only after witnessing that targeted callback. It uses `schema_version: 1`, `notification_kind: "internal_system_event"`, the exact `owner_session`, `gateway` object from `--check` (`pid` and timezone-aware `started_at`), timezone-aware `completed_at` and later `checked_at`, the actual native exec `native_process_id`, the preflight marker as `completion_event_id`, `completion_status: "succeeded"`, and an absolute `evidence_path` to a nonempty private transcript/note in `runtime/coordinator/` documenting the observed continuation. The preflight never creates this proof automatically. Do not fabricate a receipt, use acceptance as delivery proof, or borrow another conversation's evidence. Check it with `./scripts/run-map-import.sh --check --owner-session <actual-dashboard-session-key>`. The wrapper rejects legacy native-exit-only, structured exec-event and rejected chat-transport proof, missing evidence, another owner, stale PID/start time, hidden sessions and invalid timestamps. A current private alternate receipt can be passed with `--completion-receipt /absolute/private/path`.

Launch through OpenClaw native `exec` with `background=true` and `timeoutSeconds=0`. Pass `--owner-session <actual-dashboard-session-key> --`, then the exact compatible managed run arguments and `--unlimited`. Omit `--max-hours` and finite provider caps for the standing backlog. The wrapper injects `--unlimited` when provider caps are absent; on resume it clears saved `maxLlmRequests`, `maxCostUsd` and `geocodeLimit` while retaining the original cohort, stages and completed checkpoints. The supervisor's full-run timeout defaults to no deadline. Optional `--max-hours` and finite provider limits are for later explicit requests, and finite caps cannot be combined with `--unlimited`. The wrapper refuses ordinary terminals, uses shell-only project credentials, and requires `DB_MAP_URL`. It requires `FIREWORKS_API_KEY` except for an explicit **new** file/category run with exactly one `--from report` or `--from verify`, all three budgets zero, and no resume, conflicting stage options or consolidation. A resume preserves its original stage scope and cannot be converted into a report suffix by adding `--from`. Keep scope/authorization/telemetry/handles/event IDs in private `state/map-imports.md`; PostgreSQL remains progress truth. Waiting never invokes a Codex model.

For the first full continuation, after this owner has witnessed its preflight and control is quiescent:

```sh
/Users/pshorey/git/openclaw/scripts/run-map-import.sh \
  --owner-session <actual-dashboard-session-key> -- \
  --resume 4dda8606-9c20-4275-bae6-c14cdea9e38c --unlimited
```

Zero budgets alone do not make an arbitrary file or resume provider-free: request/cost limits bound normalization, and `--geocode-limit` bounds geocoder work; embedding, matching and fusion are not hard-capped by those flags. All normal provider stages are already authorized for full ingestion. A new `source.json --category campground --from report --max-llm-requests 0 --max-cost-usd 0 --geocode-limit 0` is a provider-free suffix, but can still perform deterministic extraction and database writes. Use such a suffix only for a compatible verification action; it does not replace the full import or prove whole-file completion. Require the file's `coverage="complete"` from `ingest:inventory --json` and `action="complete"` from `ingest:queue --json`; raw `ingestion_files.status="complete"` means extraction completed.

Failures still need diagnosis and checkpoint-preserving recovery. Delegate code/script, source-mapping and provider-control repairs to the connected Codex CLI with the exact run/execution/stage IDs and logs. Engineers validate with bounded smoke tests; the cheap OpenClaw runner owns full continuations and backlog advancement. Preserve maintenance ownership and verify quiescence before runtime/schema/source repairs. Do not repeatedly resume against an unresolved outage, resend ambiguous callbacks, or use new sample runs to replace an interrupted full run. Unknown cost telemetry does not block an otherwise healthy authorized run.

The wrapper owns one foreground `project-env.py → ingest:supervise watch` child, forwards its launch/terminal stdout, and retains bounded receipt capture plus raw stdout/stderr privately under `runtime/coordinator/logs/map-import-runner/`. Before a normal terminal callback, it verifies the canonical map `.ingest-jobs/<uuid>/job.json` and `result.json`, exact scope, event/job/run/execution identities, and terminal outcome. The callback uses the exact `ingestion:<job-uuid>:terminal` ID; deduplicate a later delayed native event against it. Pre-job failures and invalid journals send a distinct `map-import-wrapper:<uuid>:terminal` blocker with private wrapper evidence, without inventing a map run/job or advancing the queue. Callback claims and `callback.json` preserve the stable event ID, actual `{ok:true}` enqueue acknowledgement or failed/uncertain delivery. The wake API does not return a model run ID or provide transport idempotency; claims and event reconciliation prevent duplicate decisions. An exit-zero-only response is not acceptance. There are no automatic callback retries or import relaunches. Callback failure returns a blocker even when map succeeded; inspect owner history and evidence before any repair or queue advance.

Map now defaults to Fireworks DeepSeek V4.1 Flash with bounded thinking. Before provider work, check required shell variables through the env runner and verify the effective provider/model/endpoint against map's [Fireworks runbook](/Users/pshorey/git/map/data/poi-ingestion.md). Stale DeepInfra overrides need an engineering repair. Sharing OpenClaw's key does not establish map's model compatibility or successful ingestion; retain bounded pipeline test evidence separately from native completion proof.

Provider-free wrapper checks:

```sh
.venv/bin/python scripts/test-project-env.py
.venv/bin/python scripts/test-run-map-import.py
bash -n scripts/run-map-import.sh
```

### Context and run lifetime

OpenClaw injects the runtime `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, and `USER.md`, in that order, into both the launcher and visible heartbeat session. AGENTS owns the procedure; SOUL covers role/style; USER records preferences. The heartbeat prompt only launches the conversation and selects the procedure. The coordinator then reads `state/ACTIVE.md`, the repository inventory, and relevant linked evidence. Historical state/log directories are not loaded wholesale. Map actions explicitly read deployed `MAP-IMPORTS.md`; the detailed procedure is not added to every heartbeat bootstrap. Keep injected AGENTS below the installed 20,000-character per-file default rather than relying on truncation or raising the limit.

The built-in `[Subagent Context]` wrapper comes from OpenClaw's `buildSubagentTaskMessage` implementation. `depth 1/5` is nesting depth, not progress. `sessions_spawn` uses `runtime="subagent"` even for `visible=true` dashboard conversations; check the actual session key. A visible `agent:main:dashboard:...` session keeps a saved, replyable conversation and can receive automatic native background-exec continuation after its run ends. A hidden `agent:main:subagent:...` session cannot provide that owner. Visibility does not keep a model or worker running indefinitely: later messages/completions start another turn. Idle conversations retain history without generating tokens. The Gateway/scheduler service remains running independently.

Heartbeat passes aim for five minutes with a 15-minute hard execution limit. Required decisions are written to ACTIVE.md and asked in the final reply; dependent work stays pending until an actual answer arrives. Heartbeats do not block on `ask_user`, whose wait consumes the run budget and expires. Enable **Agent finished** notifications to see these summaries/questions; they are ordinary conversation messages, not pending question cards. Background specialist work uses completion events in its owning conversation.

The coordinator's skill allowlist keeps research, GitHub, UI/Gateway/node diagnostics, Railway, and migration reconciliation. Other installed skills remain on disk. The bundled coding-agent skill is excluded because its required external-channel notification workflow conflicts with our dashboard/background-exec workflow; the local wrapper is the delegation procedure. Codex has its own skill context.

The standing queue starts with `paulshorey/livx`, `paulshorey/map`, and `paulshorey/notes`. To add another repository, verify its GitHub remote and local `AGENTS.md`, then add a GitHub slug and absolute checkout path to `config/managed-repositories.tsv`. Other repositories remain available for explicit one-off requests. The coordinator checks all open PRs and issues in each managed repository, regardless of author; the status script uses paginated GitHub API queries for its snapshot. Open PRs, checks, reviews, and in-flight work take priority over new issue work.

```sh
./scripts/deploy-workspace.py
openclaw config get agents.defaults.workspace
openclaw config get agents.entries.main.workspace
```

## Project env runner

```sh
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/map --shell-only --check --require DB_MAP_URL --require FIREWORKS_API_KEY   # names only
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/map --shell-only -- pnpm --filter @lib/db-map ingest:status
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/example/apps/web -- npm run dev
```

- Imports login-shell vars named in the project's env files/examples, then `.env` + `.env.local` from Git root down to `--cwd`.
- Deeper dir wins; `.env.local` wins within a dir; blanks can be filled by other sources.
- `--shell-only`: do not read `.env`/`.env.local`; use injected/login-shell values and example declarations. Required for map.
- `--require NAME`: import an undeclared shell var and refuse execution when that explicit requirement is absent/empty. `--check` reports all missing declarations but returns failure only for missing explicit requirements; optional `.env.example` names remain optional.
- Use for anything needing project config (python, node, db, containers, dev servers, deploy CLIs). Not needed for `git`/`rg`/`gh`.
- `delegate-codex.sh` wraps with this automatically; pass the nested app path when relevant.
- `map` root uses shell-provided credentials; `.env.example` is reference only. `map/apps/map` unset: `NEXT_PUBLIC_API_URL`, `THUNDERFOREST_API_KEY` (as of 2026-09-23).

## Operate

```sh
export PATH="/opt/homebrew/bin:$PATH"
openclaw gateway status
openclaw health
openclaw config validate
openclaw models status
./scripts/status.sh
openclaw gateway start        # or restart after config/key changes
openclaw cron list --all      # heartbeat schedule
openclaw dashboard            # http://127.0.0.1:18789/
```

- Gateway currently **running** as a LaunchAgent. Loopback only.
- LaunchAgent runs only while logged in and awake.
- Heartbeat: every `1h` (`agents.defaults.heartbeat.every`); lives in the scheduler, no `HEARTBEAT.md`. Keep `agents.defaults.heartbeat.isolatedSession=false` and `target="owner"`: exec-event wakes inherit these settings. Isolation routes events into an owner `:heartbeat` suffix, and `target="none"` removes the completion details from the model prompt. Owner routing permits the dashboard conversation to receive its own event; external Telegram delivery remains disabled. Each scheduled launcher creates one persistent dashboard conversation with `sessions_spawn visible=true`, in the `Heartbeats` group. The new conversation runs the bounded coordination pass and always leaves a readable summary, including when nothing changed. The launcher records a receipt and returns `NO_REPLY` after dispatch.
- Dashboard auth is tied to the browser profile that ran `openclaw dashboard`.

## Dashboard and mobile conversations

Open the [private dashboard](https://pauls-macbook-pro.taila9173b.ts.net/chat) on a paired desktop or phone connected to the tailnet. The Gateway remains bound to loopback, with Tailscale Serve providing private HTTPS. The Android app also connects to this Gateway.

- Each hourly heartbeat starts a **new dated conversation**, even when it revisits an existing workload. Find it in the **Heartbeats** sidebar group and reply there to follow up. Earlier conversations remain replyable.
- Use **New conversation** (or **New** in the Android sidebar) for an unrelated request. The web shortcut is [New conversation](https://pauls-macbook-pro.taila9173b.ts.net/new?agent=main).
- Human replies and background completions stay in the conversation that owns their run. `state/ACTIVE.md` indexes stable task IDs, owning/latest sessions, active runs, pending decisions and evidence notes so a fresh chat does not duplicate ongoing work.
- Messages have **Copy as markdown** in the web UI.
- For browser/PWA alerts, open **Settings → Notifications**, enable notifications, opt into **Agent finished**, **Agent questions**, and desired failure categories, and use **Send test** on each device. Native mobile notifications are configured separately. Verify an actual completion while the phone UI is closed; Gateway delivery acceptance alone does not prove a phone displayed it.

Telegram's channel and plugin are disabled. Its destination/allowlist configuration and owner-command entry are removed, and its token is removed from active `~/.openclaw/.env` (a mode-0600 rollback copy remains under `~/.openclaw/backups/ui-workflow/`). The old provisioning scripts are retired. Historical topic sessions are archived and their transcripts/private notes retained as history; they must never be used as delivery destinations. `state/ui-migration.md` records the historical cutover; `state/ACTIVE.md` owns current work.

To reapply the workflow after changing its prompt or templates:

```sh
./scripts/deploy-workspace.py
python3 scripts/configure-ui-workflow.py --dry-run
python3 scripts/configure-ui-workflow.py
openclaw config validate
openclaw channels status --probe
```

The Gateway reloads prompt/skill configuration; runtime templates are used on subsequent turns. Restart only when needed for environment/service changes. The configure helper preserves the Fireworks key, Gateway binding, Tailscale Serve, and device pairing. To verify the scheduler path, find **Heartbeat (main)** with `openclaw cron list --all`, run its ID with `openclaw cron run <id>`, and confirm a new visible conversation and a dated `state/heartbeat-launch-*.json` receipt. Check the summary, ACTIVE.md update and successful task termination. A follow-up should use the same session after the original run has ended. The launcher uses `expectsCompletionMessage=false` to skip the child report handoff. OpenClaw can still wake the launcher for session-state changes (including human replies in children); the prompt routes these to event handling with `NO_REPLY`, never another launch. The visible child's report remains in its own conversation. Do not edit the system-owned heartbeat automation directly; its desired state comes from `agents.defaults.heartbeat`.

## Delegate

```sh
./scripts/delegate-codex.sh /Users/pshorey/git/example /absolute/path/to/prompt.txt
```

- Put prompts outside tracked files or in `runtime/coordinator/state/`.
- Codex runs with full local access: trusted prompts only.
- Verify diff, tests, PR state; the final message is not proof.

## Work cycle

- Hourly: resume ledger work; check the managed repositories' branches, PRs, reviews, CI, and issues; delegate selected tasks to Sol; record priorities and deferrals; no duplicates.
- Sol handles code/GitHub mutations and process repairs. The coordinator may launch the reviewed native map runner and make audited inventory metadata edits as described in its AGENTS template.
- Quiet: reconcile interrupted full runs, then continuously advance eligible intended files from map's `ingest:queue --json` after whole-file verification. OpenClaw is the cheap runner; Node handles waiting and hourly health. Native background exec owns the process, and the verified targeted terminal callback continues the owning conversation. Delegate technical blockers to Sol, preserve checkpoints, and use `--unlimited` with no overall deadline unless Paul later requests limits. Read map's `data/ingestion-agents.md#native-openclaw-runner`.

## New Mac setup

1. Node 26 + OpenClaw ([install](https://docs.openclaw.ai/install)); install `@openclaw/fireworks-provider`.
2. `FIREWORKS_API_KEY=...` in `~/.openclaw/.env`, `chmod 600`.
3. `./scripts/configure.sh` (deploys, applies settings, installs LaunchAgent), or manually: deploy, set both workspace keys to `runtime/coordinator/`, set model + heartbeat, `openclaw config validate`.
4. Auth `gh` as `paulshorey`; auth `codex` via ChatGPT; confirm `gpt-6-sol` access.
5. `openclaw gateway install`, `status`, `health`, one manual agent check.

## References

- OpenClaw: [install](https://docs.openclaw.ai/install), [macOS Gateway](https://docs.openclaw.ai/platforms/mac/bundled-gateway), [workspace](https://docs.openclaw.ai/agent-workspace), [heartbeat](https://docs.openclaw.ai/heartbeat), [Fireworks provider](https://docs.openclaw.ai/providers/fireworks)
- Dashboard workflow: [session tools](https://docs.openclaw.ai/concepts/session-tool), [sessions and sidebar](https://docs.openclaw.ai/web/control-ui/sessions-and-sidebar), [notifications](https://docs.openclaw.ai/web/notifications)
- [DeepSeek V4.1 Flash](https://fireworks.ai/models/deepseek-ai/deepseek-v4p1-flash), [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol)
