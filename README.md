# OpenClaw development coordinator

Local OpenClaw bot (macOS LaunchAgent). Coordinator: Fireworks DeepSeek V4.1 Flash. Coding/computer use: Codex CLI, `gpt-6-sol`, medium reasoning. Manages the repositories listed in `config/managed-repositories.tsv`; considers `map` ingestion when development is quiet.

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

- `~/.openclaw/.env` (mode `0600`): `FIREWORKS_API_KEY`, `TELEGRAM_BOT_TOKEN`
- Never in Git, config, or prompts. Rotate at Fireworks if exposed.
- `env.shellEnv.enabled: true` → imports missing expected keys from login shell (`~/.zprofile` → `~/.shortcuts.sh` → `~/.secrets.sh`). See [environment precedence](https://docs.openclaw.ai/help/environment).

## Development Files

| Path                                                                 | Purpose                                                                                      |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `AGENTS.md`                                                          | Rules for agents engineering **this repo**                                                   |
| `config/managed-repositories.tsv`                                    | GitHub/local checkout inventory for the standing coordination queue                         |
| `scripts/deploy-workspace.py`                                        | Templates → workspace; keeps state; refuses to overwrite changed runtime copies              |
| `scripts/configure.sh`                                               | Applies model/workspace/heartbeat/Gateway settings, installs LaunchAgent (may start Gateway) |
| `scripts/delegate-codex.sh`                                          | Runs Codex Sol in a repo with project env; logs to `logs/`                                   |
| `scripts/project-env.py`, `requirements.txt`                         | Project-scoped env runner + its dependency                                                   |
| `scripts/status.sh`                                                  | Read-only Gateway/auth/PR/ingestion snapshot                                                 |
| `scripts/start-telegram-pairing.sh`, `scripts/configure-telegram.sh` | Telegram owner pairing + allowlist                                                           |

## OpenClaw Coordinator Files

| Path                                      | Purpose                                                                                                   |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `config/heartbeat-prompt.txt`             | Hourly heartbeat trigger; applied by `configure.sh`                                                       |
| `config/coordinator/AGENTS.md.template`   | OpenClaw procedure: pass checklist, priorities, delegation/review, GitHub + map workflows, when to notify |
| `config/coordinator/SOUL.md.template`     | Mission, style, autonomy, review principles (broad)                                                       |
| `config/coordinator/IDENTITY.md.template` | Name, role, voice                                                                                         |
| `config/coordinator/USER.md.template`     | Stable facts/preferences about Paul (no secrets, no task state)                                           |
| `runtime/coordinator/state/`              | Private ledger: task IDs, PR URLs, decisions, blockers                                                    |
| `runtime/coordinator/logs/`               | Codex run logs from `delegate-codex.sh`                                                                   |

## Where rules go:

- Engineering this setup → root `AGENTS.md`
- OpenClaw coordination → `config/coordinator/AGENTS.md.template` (enduring role → `SOUL.md.template`)
- Coding inside a project → that project's `AGENTS.md`
- One-off task / run status → `runtime/coordinator/state/`
- Edit templates, not runtime copies, then deploy. Deploy does not start the Gateway.

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

- Gateway currently **stopped** (post workspace migration). Loopback only.
- LaunchAgent runs only while logged in and awake.
- Heartbeat: every `1h` (`agents.defaults.heartbeat.every`); lives in the scheduler, no `HEARTBEAT.md`.
- Dashboard auth is tied to the browser profile that ran `openclaw dashboard`.

## Telegram (planned)

1. Create bot via `@BotFather`; add `TELEGRAM_BOT_TOKEN=...` to `~/.openclaw/.env`.
2. `./scripts/start-telegram-pairing.sh`, DM the bot, note your numeric user ID.
3. `./scripts/configure-telegram.sh <user-id>` (owner-only DM, heartbeat alerts to owner).
4. Verify: `openclaw channels status --probe` + test message.

Alerts only for blockers, failures, decisions.

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
- [DeepSeek V4.1 Flash](https://fireworks.ai/models/deepseek-ai/deepseek-v4p1-flash), [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol)
