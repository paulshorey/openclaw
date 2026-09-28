# OpenClaw development coordinator

Local OpenClaw bot (macOS LaunchAgent). Coordinator: Fireworks DeepSeek V4.1 Flash. Coding/computer use: Codex CLI, `gpt-6-sol`, high reasoning. Manages the repositories listed in `config/managed-repositories.tsv`; considers `map` ingestion when development is quiet.

## Installed

- OpenClaw CLI: `/opt/homebrew/bin/openclaw` (npm, Homebrew Node 26)
- Gateway state + credentials: `~/.openclaw/`
- Agent workspace: `runtime/coordinator/` (ignored; also default exec dir, agent `cwd` unset)
- Provider plugin: `@openclaw/fireworks-provider`
- Model: `fireworks/accounts/fireworks/models/deepseek-v4p1-flash`
- `gh`: logged in as `paulshorey`
- Codex: `/Applications/ChatGPT.app/Contents/Resources/codex` (ChatGPT login)
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
| `scripts/status.sh`                          | Read-only Gateway/auth/PR/ingestion snapshot                                                 |
| `scripts/configure-ui-workflow.py`           | Applies dashboard heartbeat routing, disables Telegram, removes its active bot token         |

## OpenClaw Coordinator Files

| Path                                      | Purpose                                                                                                   |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `config/heartbeat-prompt.txt`             | Hourly heartbeat trigger; applied by `configure.sh`                                                       |
| `config/coordinator-skills.json`         | Small skill catalogue exposed to the coordinator; applied by `configure-ui-workflow.py`                  |
| `config/coordinator/AGENTS.md.template`   | OpenClaw procedure: pass checklist, priorities, delegation/review, GitHub + map workflows, when to notify |
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

### Context and run lifetime

OpenClaw injects the runtime `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, and `USER.md`, in that order, into both the launcher and visible heartbeat session. AGENTS owns the procedure; SOUL covers role/style; USER records preferences. The heartbeat prompt only launches the conversation and selects the procedure. The coordinator then reads `state/ACTIVE.md`, the repository inventory, and relevant linked evidence. Historical state/log directories are not loaded wholesale.

The built-in `[Subagent Context]` wrapper comes from OpenClaw's `buildSubagentTaskMessage` implementation. `depth 1/5` is nesting depth, not progress. `visible=true` keeps a saved, replyable conversation after its run ends. It does not keep a model or worker running indefinitely: later messages/completions start another turn. Idle conversations retain history without generating tokens. The Gateway/scheduler service remains running independently.

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
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/map --check   # names only
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/map -- pnpm --filter @lib/db-map ingest:status
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/example/apps/web -- npm run dev
```

- Imports login-shell vars named in the project's env files/examples, then `.env` + `.env.local` from Git root down to `--cwd`.
- Deeper dir wins; `.env.local` wins within a dir; blanks can be filled by other sources.
- `--require NAME`: require an undeclared shell var. `--check` flags declared-but-unset (may be optional).
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
- Heartbeat: every `1h` (`agents.defaults.heartbeat.every`); lives in the scheduler, no `HEARTBEAT.md`. Each isolated launcher creates one persistent dashboard conversation with `sessions_spawn visible=true`, in the `Heartbeats` group. The new conversation runs the bounded coordination pass and always leaves a readable summary, including when nothing changed. The launcher records a receipt and returns `NO_REPLY` after dispatch.
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
- Sol does all repo/GitHub mutations, including branch cleanup (unmerged → review).
- Quiet: consider one eligible JSON/CSV source in `~/git/map`. Sol makes the orchestration decision and follows map's `AGENTS.md`, `data/poi-ingestion.md`, and `data/ingestion-agents.md`; a long import uses the runbook's cheap runner and model-free supervisor. Verify DB completion; no overlapping imports.

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
