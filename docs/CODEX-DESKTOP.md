# Desktop coding delegation: feasibility and proposed implementation

Updated: 2026-10-10. Status: research complete enough to choose a prototype;
unattended OpenClaw-to-desktop dispatch is **not implemented or verified**.

Paul prefers complex coding work in a new local Codex desktop project chat, with
the normal sidebar, direct follow-up, progress, approvals and stop controls.
Codex Cloud environments and a headless CLI process do not satisfy this request.
Inference may continue on OpenAI servers using the existing ChatGPT account.

## What is verified

| Interface | Verified behavior | Remaining boundary |
| --- | --- | --- |
| Native desktop task tools | This desktop conversation has `create_thread`, project discovery, task listing/reading, waiting and authorized follow-up tools. Existing map, livx, notes and openclaw projects are registered locally. The creation tool supports a local project and a native worktree. | Availability inside a desktop conversation does not establish availability to the isolated OpenClaw coordinator. No diagnostic chat was created during this investigation. |
| Bundled desktop tools MCP server | Installed `codex-app-tools` 0.1.5 requires a desktop-provided pipe and caller thread/turn metadata. It forwards requests to the desktop host. | This is a context-dependent app bridge, not a documented general-purpose OpenClaw endpoint. Do not copy this engineering chat's ephemeral pipe or impersonate its thread to obtain access. |
| Public Codex app-server | Its documented protocol can create threads, start turns, read state and interrupt turns. A read-only client successfully initialized against the existing local daemon. | A protocol thread is not, by itself, evidence of a native desktop project chat with live app controls. |
| Existing local daemon versus desktop server | The daemon read this engineering chat's stored ID/cwd/source but reported it `notLoaded` while the desktop conversation was active. The desktop has its own bundled app-server process. | Shared stored history is insufficient evidence of a shared live execution server. No new task, turn, resume or interruption was requested through the daemon. |
| Supported desktop deep links | `codex://new?prompt=...&path=...` opens a local composer with a prepared prompt; `codex://threads/<id>` opens an existing chat. | The documented new-chat link does **not** send the prompt. No documented model, worktree or automatic-send parameter should be invented. |
| SSH/remote control | Official clients can connect to host projects and app-server instances. | These features do not document an external OpenClaw call into the existing local desktop project/task tools. A localhost SSH connection would require a separate prototype and changes to connection setup. |

The read-only inspection found these distinct versions: desktop bundled CLI
0.159.2; the already-running shared daemon 0.155.1; its installed standalone
package 0.162.1; OpenClaw's independently selected CLI/app-server 0.160.0. These
are dated observations, not versions this project should automatically adopt.
Do not restart or upgrade the user's shared server to make a probe pass while
other desktop tasks are active.

The first daemon probes failed; a corrected WebSocket client with compression
disabled initialized successfully. Those initial failures are not evidence that
the daemon interface is unavailable. The successful read establishes stored
history access, not task creation, project association or native stop/control.

## Product choice before changing the route

The recommended next step is a **desktop dispatcher prototype**, keeping
OpenClaw as coordinator. A real desktop conversation would read a private local
queue and use the native app task tools to create visible project chats. This
avoids attributing desktop powers to OpenClaw that it does not currently possess.
First prove that the chosen scheduled desktop execution context actually has
these tools. A scheduled prompt is not proof of that capability.

This adds a component and dispatch latency. Scheduled dispatcher checks would
also consume some model usage when checking an empty queue; no supported local
Codex event subscription was established that eliminates that polling. The
polling interval and dispatcher model are product choices. Do not silently
create an automation or change the coordinator framework.

Alternatives:

1. Move the recurring coordinator into a native desktop scheduled conversation.
   Its native task tools are a better architectural fit, but migration would
   require re-proving map ownership, background completion and restart behavior.
   Existing OpenClaw callback receipts would not establish desktop acceptance.
2. Have OpenClaw prepare a desktop draft and let Paul send it. This uses the
   documented deep link and gives a normal app chat after submission, but does
   not satisfy unattended task creation.
3. Automate desktop UI submission. This would depend on the foreground session,
   Accessibility permissions and app layout. It would need explicit selection
   and a separate acceptance test. It is not the recommended default.

The requested default destination is now the desktop. Cloud remains disabled.
Until a route is accepted and verified, do not describe this document as an
enabled desktop integration or silently substitute a headless/Cloud task.
Existing direct small fixes and map process management are separate capabilities.

## Phase 1: capability pilot

After Paul selects the dispatcher approach:

1. Create a clearly named, project-bound desktop dispatcher with reviewed scope
   and a narrow task prompt. Use native app tools; do not manufacture desktop
   database rows or caller metadata. Inspect whether a scheduled run receives
   the native task tools, and whether it runs with the app open/closed/locked.
2. Have it create one explicitly identified read-only diagnostic task in a
   reviewed local project. The diagnostic must not change source, commit, push,
   create PRs, start imports or contact anyone. Set the intended coding model
   and reasoning explicitly where supported.
3. Confirm the returned **ready** task ID, local host, project and actual cwd in
   the app. A pending `clientThreadId` is not a usable completed task identity.
   Prove sidebar visibility and direct human continuation; prove native task
   reading/waiting and that the app controls the actual execution.
4. Separately test a native worktree. Verify origin, actual starting commit and
   isolation from the primary checkout. Do not invent a starting branch/ref or
   assume saved project defaults mean the reviewed base. Stop on mismatch.
5. Check effective model, reasoning, speed, ChatGPT authentication and permissions.
   The native creation tool has model/reasoning controls but no explicit speed
   argument. Record whether supported app configuration enforces Standard;
   ask about any remaining policy gap rather than claiming an unverified setting.
6. Test one later scheduled pass reading the exact same task after its dispatcher
   launch turn ended. Test restart/sleep recovery without duplicate dispatch.
   A creation success alone does not pass this pilot.

If scheduling lacks native task tools or live control, stop the prototype and
report that precise boundary. Keep the queued request intact. Do not compensate
with private IPC, UI typing, additional providers or a headless coding launch.

## Phase 2: durable local dispatch

Only after the pilot passes, implement a small local queue/adapter:

- Keep intent, ownership and results in ignored `runtime/coordinator/state/`,
  using private permissions and SQLite transactional claims. A stable scope
  identifies repository, issue/request and reviewed base, not merely prompt text.
- Record local intent ID, authority, acceptance checks, project identity, base,
  queue state and owner. On creation, record exact ready desktop thread/host IDs,
  cwd/worktree and a `codex://threads/<id>` link. Treat titles as display text.
- Start with states `prepared`, `claimed`, `dispatch_unknown`, `started`,
  `running`, `needs_input`, `ready_for_review`, `failed` and `closed`. Separate
  intent state from observed native task state and the verification result.
- A crash/timeout after the creation call is ambiguous. Do not automatically
  retry, even if a recent task list is empty. Preserve the prompt/request ID and
  inspect native candidates; require explicit reconciliation if identity is
  still uncertain. Use a supported idempotency key if the interface gains one.
- Use one writer per task/worktree. An expired local claim does not prove the
  desktop task stopped. Reconcile the native task, process and Git evidence
  before releasing ownership or admitting another writer.
- Validate the managed inventory and registered project path/origin at dispatch.
  An app project ID is host/user configuration and must be refreshed after
  recreation. Never dispatch arbitrary paths from repository text.
- Prompts carry authorized scope, repository instructions, base checks, acceptance
  criteria, pending decisions and permitted publication actions. Queue data and
  coding outputs cannot grant new authority. Follow-up/cancellation requests
  require existing recorded authority or an explicit human instruction.

Prefer native managed worktrees to keep each implementation independent of
Paul's currently checked-out branch. Verify local setup behavior before enabling
it for a repository. Install dependencies with the target project's procedures;
do not transfer private runtime/auth files into worktrees. Commands needing
project credentials still use `project-env.py` at the actual worktree/app path;
map keeps `--shell-only`.

## Phase 3: independent models and operating procedures

- Keep the coordinator's model authority independent of desktop coding.
  Prefer using the existing `roles.local_coding` intent for both local coding
  backends; add a separate dispatcher role only if its own model is selected.
  Review the strict registry schema and every consumer before adding a role.
- Add the native launch controls, app/global/project overrides and observed
  speed/authentication behavior to `docs/MODEL-POLICY.md`. Never rely on the
  user's personal XHigh CLI default to implement the requested High coding role.
- Change coordinator templates only after the dispatch gate passes. Complex
  coding should prepare/dispatch through the desktop route; small scoped fixes
  remain available directly in an isolated worktree. Do not convert Cloud or
  headless CLI into an automatic fallback when desktop dispatch is unavailable.
- OpenClaw heartbeats reconcile the local ledger against fresh dispatcher/native
  observations and independently inspect actual diffs, checks and PR heads.
  They do not import all desktop account tasks or treat an agent's final text as
  acceptance. Human replies can reopen a task; timestamp observations to avoid
  stale status overwriting newer work.
- Leave durable map scripts and their existing supervisor/database discovery in
  place. Desktop coding delegation does not move production imports into a
  coding chat. If changing the coordinator framework later, test completion
  routing again before enabling paid import admission.
- Document app availability, dispatch latency, pending approvals, authentication
  exhaustion, version changes, sleep and restart recovery in operator status.
  A failure should retain recoverable intent and report its actual blocker.

## Release gates and verification

The route remains disabled until the pilot proves native creation, correct
project/worktree/base, effective role controls, direct human follow-up, native
execution control, later-pass discovery and duplicate prevention after ambiguity.
Verify offline state transitions and claims with meaningful tests once implemented;
test native integration with read-only diagnostics before a real coding task.

Update `README.md`, `docs/MODEL-POLICY.md`, the main implementation plan,
deployment file inventory and `scripts/status.sh` when consumers exist. Deploy
reviewed templates with `deploy-workspace.py` and validate config; documentation
changes alone do not start or restart OpenClaw. Preserve existing source changes,
runtime data and retained task/PR evidence.

## Primary references

- [Native desktop commands and deep links](https://learn.chatgpt.com/docs/reference/commands)
- [Codex app-server protocol](https://learn.chatgpt.com/docs/app-server)
- [Developer CLI commands and remote-control scope](https://learn.chatgpt.com/docs/developer-commands)
- [Remote connections and SSH projects](https://learn.chatgpt.com/docs/remote-connections)
- [Native Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)
- [Local environment setup](https://learn.chatgpt.com/docs/environments/local-environment)
- [Codex 0.160.0 daemon lifecycle and environment semantics](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/app-server-daemon/README.md)
- [Codex 0.155.1 daemon client transport](https://github.com/openai/codex/blob/rust-v0.155.1/codex-rs/app-server-daemon/src/client.rs)

Local evidence also includes the installed bundled desktop tools server and
read-only native project/task discovery. Those are dated implementation evidence,
not a promise of a public external task-creation API.
