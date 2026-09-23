# Engineering instructions for Codex

This repository develops and configures the local OpenClaw coordinator. This root `AGENTS.md` guides engineering agents. OpenClaw's operating instructions are versioned in `config/coordinator/` and deployed to the ignored `runtime/coordinator/` workspace.

## Layout and workflow

- `config/coordinator/*.template`: source for OpenClaw's `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, and `USER.md`.
- `config/heartbeat-prompt.txt`: scheduled coordinator prompt.
- `runtime/coordinator/`: active OpenClaw workspace, with deployed instructions and private `state/`, `logs/`, and memory. Do not commit or wipe it.
- `scripts/deploy-workspace.py`: deploy templates while preserving runtime data; refuses to overwrite a changed managed file.
- `scripts/configure.sh`: applies settings and installs the LaunchAgent; it may start the Gateway.

Edit the templates for coordinator behavior, deploy them, and validate OpenClaw config. Inspect the diff and run checks relevant to software changes. Preserve the Fireworks key in `~/.openclaw/.env` with mode `0600`; never put credentials in Git, prompts, or tool output. Keep the Gateway on loopback.

The configured OpenClaw workspace is `runtime/coordinator/`. Leave agent `cwd` unset so its default execution directory is that workspace. OpenClaw loads bootstrap files there. Codex may read this root file while engineering the repository; OpenClaw's own `AGENTS.md` comes from its nested workspace. Do not assume OpenClaw discovers parent instructions.

For commands needing credentials from another project, use `.venv/bin/python scripts/project-env.py --cwd <project-or-app-path> -- <command>`. Choose the actual project or nested app path. `--check` reports names and availability without values; `--require NAME` adds a required shell variable absent from dotenv files. Ordinary `git`, `rg`, and `gh` inspection does not need the runner. Respect the target repository's instructions. Examples:

```sh
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/map -- pnpm --filter @lib/db-map ingest:status
.venv/bin/python scripts/project-env.py --cwd /Users/pshorey/git/livx -- pnpm --filter apps/client-app dev
```

Do not start OpenClaw for a documentation or template edit unless requested. The operator may intentionally leave it stopped.
