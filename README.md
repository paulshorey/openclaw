# OpenClaw development coordinator

This repository develops and stores the configuration for a local OpenClaw bot. Its active workspace is the ignored `runtime/coordinator/` directory. OpenClaw is configured as a macOS user LaunchAgent, uses Fireworks' DeepSeek V4.1 Flash for coordination, and delegates coding and computer use to the authenticated ChatGPT Codex CLI using `gpt-6-sol` with medium reasoning. It watches Paul Shorey's local projects and GitHub pull requests, then uses quiet time to coordinate ingestion for the `map` project.

## What is installed on this Mac

- OpenClaw CLI: `/opt/homebrew/bin/openclaw` (installed through npm with Homebrew Node 26)
- Gateway state and credentials: `~/.openclaw/`
- Repository and engineering workspace: `/Users/pshorey/git/openclaw`
- OpenClaw agent workspace: `/Users/pshorey/git/openclaw/runtime/coordinator`
- Fireworks provider plugin: `@openclaw/fireworks-provider`
- Fireworks model: `fireworks/accounts/fireworks/models/deepseek-v4p1-flash`
- GitHub CLI: logged in as `paulshorey`
- Codex CLI: `/Applications/ChatGPT.app/Contents/Resources/codex`, using the existing ChatGPT login

The Fireworks key is stored in `~/.openclaw/.env` with mode `0600`. It is deliberately absent from this repository. Rotate the key at Fireworks if it is exposed. Do not paste it into the config or a task prompt.

Memory search uses keyword indexing (`memory.search.provider: none`) because the host's unrelated OpenAI API credential is not valid for embeddings. This keeps workspace memory searchable without extra API calls.

## Instruction files and runtime data

The root `AGENTS.md` guides Codex and other engineering agents changing this repository. OpenClaw reads `runtime/coordinator/AGENTS.md` and the other bootstrap files in its configured workspace. Their versioned sources are `config/coordinator/*.template`; `scripts/deploy-workspace.py` copies them into the active workspace. The deployer refuses to overwrite an active instruction file that changed since its last deployment, so inspect and reconcile the difference before retrying. Edit the templates to make lasting operator changes. `config/heartbeat-prompt.txt` is separately applied to the local OpenClaw configuration by `scripts/configure.sh`.

`runtime/coordinator/` is ignored by Git. It contains deployed files plus private `state/`, `logs/`, and any memory OpenClaw writes. Do not remove it when updating the repository. The Fireworks key and Gateway state stay in `~/.openclaw/`. OpenClaw's workspace is also its default execution directory because agent `cwd` is unset. It can access `/Users/pshorey/git` using absolute paths and the current macOS user's filesystem permissions. The nested workspace location does not confine it to that directory; the Gateway has no sandbox configured.

```sh
./scripts/deploy-workspace.py
openclaw config get agents.defaults.workspace
openclaw config get agents.entries.main.workspace
```

## Project environment variables

OpenClaw's own provider credentials belong in `~/.openclaw/.env`. This Gateway also has `env.shellEnv.enabled: true`, so OpenClaw may import missing expected keys from the login shell. On this Mac, `~/.zprofile` sources `~/.shortcuts.sh`, which sources `~/.secrets.sh`. OpenClaw's shell import does not guarantee that arbitrary application variables reach every project command. [OpenClaw's environment precedence](https://docs.openclaw.ai/help/environment) explains these separate paths.

Use the project-scoped runner for commands that need a project's credentials:

```sh
# Names and availability only; values are never printed.
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/map --check

# Run a command in the project's environment.
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/map -- pnpm --filter @lib/db-map ingest:status

# Select a nested app directory when its own .env or .env.local applies.
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/example/apps/web -- npm run dev
```

The runner imports exported login-shell variables whose names appear in the project environment files or examples, then loads `.env` and `.env.local` from the Git root through the selected working directory. Nonempty app values override repository values; `.env.local` has final precedence within a directory. Blank values can be filled by another source. Pass `--require NAME` when a project needs a shell variable that it has not declared in an environment file. The Codex delegation wrapper uses this runner automatically for the path you give it. For work in a nested app, pass that app's path to the delegation wrapper, or wrap a later command separately if Codex changes directories. Follow that repository's `AGENTS.md`; map's root specifically uses shell-provided credentials and treats `.env.example` as a reference.

This applies to any executable that needs project configuration, including `python` or `pytest`, `node` or `npm`, database clients and migration commands, container commands, development servers, and deployment CLIs. Pure repository inspection such as `git`, `rg`, or `gh` usually needs only its own authentication and does not need the runner. Use `--check` before a credential-dependent operation when availability is uncertain; it reports names, not values or whether an optional feature is needed.

The 2026-09-23 audit found 30 active `.env` files across 17 project trees, plus 27 `.env` and 12 `.env.local` files in `_archive_2025_12`. No active `.env.local` file was present at that time; the runner will load one when added. Across active projects, 31 variable names have different values in different files, so project scope matters. A variable listed in an example file may be optional, so `--check` reports *declared but unset names*, not proof that a command will fail. The active `map` root resolved its database and ingestion provider credentials from the login-shell chain; `map/apps/map` resolved 12 of 14 declared names. Its two unset names were `NEXT_PUBLIC_API_URL` and `THUNDERFOREST_API_KEY`; confirm whether those features need values before running commands that depend on them.

## Start and inspect

```sh
export PATH="/opt/homebrew/bin:$PATH"
openclaw gateway status
openclaw health
openclaw config validate
openclaw models status
./scripts/status.sh
```

The Gateway is currently stopped after the workspace migration. Start it explicitly when ready. When running, it binds to loopback. Open `openclaw dashboard` for the local UI. The LaunchAgent starts at login and keeps the Gateway alive while the Mac user session is active. Keep the Mac awake and connected if work must continue. A LaunchAgent does not guarantee work while the Mac sleeps or before login.

To start after an intentional stop, or restart after editing config or rotating the key:

```sh
openclaw gateway start
# Use openclaw gateway restart when it is already running.
```

To inspect the scheduled heartbeat, use `openclaw cron list --all`. Current OpenClaw keeps heartbeat state in its automations scheduler; it does not read a `HEARTBEAT.md` file. The cadence is **1 hour** (`openclaw config set agents.defaults.heartbeat.every 1h`). The active instructions live in `runtime/coordinator/AGENTS.md` and `runtime/coordinator/SOUL.md`; edit their templates under `config/coordinator/`. Once Telegram owner pairing is complete, actionable heartbeat alerts go to the owner's DM; routine checks stay quiet.

## Dashboard and owner messages

Run `openclaw dashboard` on this Mac to open the authenticated Control UI at `http://127.0.0.1:18789/`. It is the local admin interface for chatting with OpenClaw, checking agents and scheduled work, and inspecting configuration. The browser pairing created by this command grants access to that browser profile; a plain URL in a different browser may ask for authentication. The Gateway remains bound to loopback.

Telegram is the planned owner notification channel. Create a bot through the verified `@BotFather` account. Put its token in `~/.openclaw/.env` as `TELEGRAM_BOT_TOKEN=...`, never in Git. Run `./scripts/start-telegram-pairing.sh`, then DM the bot; its pairing reply includes your numeric Telegram user ID. Run `./scripts/configure-telegram.sh <user-id>` to set an owner-only DM allowlist and route heartbeat alerts to the owner. Verify with `openclaw channels status --probe` and a test message. Once linked, the bot contacts Paul about concrete blockers, failures, or decisions and suppresses routine all-clear messages.

## Delegating work

Create a prompt file outside tracked content or under ignored `runtime/coordinator/state/`, then call:

```sh
./scripts/delegate-codex.sh /Users/pshorey/git/example /absolute/path/to/prompt.txt
```

The wrapper pins Codex `gpt-6-sol` and `model_reasoning_effort=medium`. It starts Codex with the selected project's environment and writes private JSONL and final-message logs under ignored `runtime/coordinator/logs/`. The Codex process has full local tool access to avoid unattended approval stalls; only run prompts you trust. The coordinator must check the resulting diff, tests, and PR state. A Codex final message alone is insufficient proof of completion.

## Work cycle

At each hourly heartbeat, OpenClaw resumes outstanding work, checks relevant branches, open PRs, review comments, and CI in the `paulshorey` account, and delegates needed changes to Sol. It avoids duplicate tasks and keeps a small private ledger in `runtime/coordinator/state/`. Sol performs all repository and GitHub mutations, including branch cleanup, after checking merge and worktree state; unmerged branches require review.

When development is quiet, it inspects `/Users/pshorey/git/map` for one eligible JSON or CSV source, then delegates ingestion launch and supervision to Sol. The map repository owns the exact ingestion command, provider budgets, maintenance checks, and recovery rules. Start with its `AGENTS.md`, `data/poi-ingestion.md`, and `data/ingestion-agents.md`. A long run is managed by its supervisor; verify database completion and delegate failures to Sol. Do not start an overlapping import or silently expand scope.

## Setup on a replacement Mac

1. Install Node 26 and OpenClaw from the [official install guide](https://docs.openclaw.ai/install), then install `@openclaw/fireworks-provider`.
2. Put `FIREWORKS_API_KEY=...` in `~/.openclaw/.env` with mode `0600`.
3. Run `./scripts/deploy-workspace.py`; set `agents.defaults.workspace` and `agents.entries.main.workspace` to this checkout's `runtime/coordinator/` directory. Leave agent `cwd` unset. Set the Fireworks model and heartbeat settings shown above. Run `openclaw config validate`.
4. Authenticate `gh` as `paulshorey` and `codex` through ChatGPT. Confirm Codex accepts `gpt-6-sol` for this account.
5. Run `openclaw gateway install`, then `openclaw gateway status`, `openclaw health`, and a single manual agent check.

After steps 1–2, `./scripts/configure.sh` deploys the workspace files, applies tracked secret-free settings, and installs the LaunchAgent. Run it only when you intend to start or maintain the Gateway service. It can be rerun after changing `config/heartbeat-prompt.txt`; `scripts/deploy-workspace.py` alone updates the instruction files without starting OpenClaw.

## References

- [OpenClaw installation](https://docs.openclaw.ai/install), [macOS Gateway](https://docs.openclaw.ai/platforms/mac/bundled-gateway), [workspace files](https://docs.openclaw.ai/agent-workspace), [heartbeats](https://docs.openclaw.ai/heartbeat)
- [OpenClaw Fireworks provider](https://docs.openclaw.ai/providers/fireworks), [Fireworks V4.1 Flash model](https://fireworks.ai/models/deepseek-ai/deepseek-v4p1-flash)
- [Official OpenAI GPT-6 Sol documentation](https://developers.openai.com/api/docs/models/gpt-6-sol)
