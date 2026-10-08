# Codex coordinator and Cloud implementation plan

Date: 2026-10-08

Status: Approved. No runtime migration has been performed.

## 1. Recommendation and intended result

Move the OpenClaw coordinator from Fireworks DeepSeek to the official OpenClaw Codex app-server runtime on this Mac, authenticated through Paul's ChatGPT account. Start with `gpt-6.1-sol`, High reasoning, and Standard speed. Keep coordinator, delegated local coding, and Cloud coding settings independent.

Allow the coordinator to implement small, authorized fixes directly in an isolated worktree. Use a separate local coding process for work requiring this Mac's tools, credentials, or a longer execution window. Use Codex Cloud for suitable repository work that Paul should be able to continue directly in Cloud. Keep map ingestion and its completion callbacks on the local OpenClaw Gateway.

The Cloud integration has a supported CLI entry point and the installed CLI successfully authenticates to the Cloud task listing service. It is feasible to build a submission and monitoring adapter. Full compatibility with Paul's intended Cloud interface still needs one controlled task submission and human follow-up test. That is a release gate, not an assumption.

This document supersedes the earlier conversational plan where details differ. It is a proposal for implementation; its configuration examples are project policy, not commands to run against the live installation.

### Success criteria

- Coordinator turns demonstrably run through local Codex app-server with ChatGPT authentication and the requested model/effort. There is no automatic Fireworks or OpenAI API billing fallback.
- Changing the coordinator role changes new coordinator turns without changing the delegated local coding role or Cloud role.
- Every active model-setting consumer, external setting, and migration is documented and checked for drift.
- Small fixes can be completed directly with repository instructions, isolation, appropriate checks, and an actual reviewed diff.
- The coordinator can submit a Cloud task, retain its identity across restarts, monitor it, link its results, and reconcile its PR without relying on the local checkout's current branch.
- Paul can open the submitted task and continue that same task directly in his intended Cloud interface.
- Existing four-hour heartbeat behavior, GitHub responsibilities, map continuation, private state, and Gateway access remain operational after cutover.

## 2. Evidence and corrections to the earlier plan

### 2.1 What current documentation establishes

The official OpenClaw `codex` plugin runs the native Codex app-server loop while OpenClaw retains its conversation and integration layer. Its managed binary is independent of the `codex` command on the shell PATH. Current documentation specifies managed Codex 0.160.0. [OpenClaw Codex harness](https://docs.openclaw.ai/plugins/codex-harness).

OpenClaw uses canonical `openai/*` model references. Runtime selection belongs on provider/model `agentRuntime` settings; selecting an `openai/*` model alone does not prove which runtime or credentials were used. [OpenAI runtimes and Codex auth](https://docs.openclaw.ai/providers/openai/runtimes).

Codex supports ChatGPT subscription authentication and API-key authentication. Cloud requires ChatGPT sign-in. Codex and ChatGPT Work share plan usage, so this design uses subscription allowance rather than assuming unlimited or separately discounted API usage. [Codex authentication](https://learn.chatgpt.com/docs/auth), [Codex pricing](https://learn.chatgpt.com/docs/pricing).

The CLI's experimental Cloud surface supports task submission and a paginated JSON task list. Current installed help additionally exposes status, diff, and apply commands, and an explicit submission branch. It provides the operations needed for an initial adapter. [Codex CLI reference](https://learn.chatgpt.com/docs/cli/reference).

Current Cloud tasks have isolated workspaces, can run while this Mac sleeps, and support direct user follow-ups and PR creation through the Cloud interface. [Codex Cloud](https://learn.chatgpt.com/docs/cloud).

There are separate current published Cloud environments and documented legacy environments. The legacy guide directs users to the current experience and continues to cover Code Review and GitHub/Linear integrations. The existence of both makes a real CLI-to-UI compatibility test necessary. Do not infer that either environment's ID will work with every CLI generation. [Current Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments), [Codex Cloud Legacy](https://learn.chatgpt.com/docs/environments/cloud-environment).

GPT-6.1 Sol is an appropriate initial choice for demanding agent work when the account and client have access. Keep the user's explicit High preference; confirm it in runtime evidence rather than substituting the model's default effort. [Codex models](https://learn.chatgpt.com/docs/models?surface=cli).

### 2.2 Verified local baseline

These observations were made on 2026-10-08 without changing live configuration or submitting a Cloud task:

| Surface                          | Observed state                                                                                                        | Consequence                                                                                                  |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| OpenClaw                         | `2026.9.5`, commit `ec9c1a1`                                                                                          | Validate the migration against this installation and any deliberately selected upgrade.                      |
| Codex plugin                     | `plugins inspect codex --json` reports plugin not found                                                               | Plugin installation and compatibility testing are required.                                                  |
| Installed OpenClaw documentation | Describes managed Codex `0.154.0`                                                                                     | Installed and current online documentation differ.                                                           |
| PATH Codex                       | `/opt/homebrew/bin/codex`, `0.156.1`                                                                                  | Do not assume it is the coding wrapper's binary.                                                             |
| Coding wrapper Codex             | `/Users/pshorey/.codex/packages/standalone/current/codex`, `0.155.1`                                                  | Record and verify this independently from app-server.                                                        |
| Coordinator model                | `fireworks/accounts/fireworks/models/deepseek-v4p1-flash`                                                             | The coordinator has not been switched.                                                                       |
| Delegated coding                 | Wrapper and USER template specify `gpt-6-sol`, High                                                                   | Migration to 6.1 must explicitly update this separate role.                                                  |
| CLI login                        | Both installed binaries report ChatGPT sign-in                                                                        | Subscription authentication exists in the current user context.                                              |
| Cloud read                       | Standalone CLI `cloud list --json --limit 1` succeeds with API-key environment variables removed; zero tasks returned | Confirms access to the listing service, not environment readiness or submission/UI compatibility.            |
| Parent environment               | An `OPENAI_API_KEY` variable is present; value was not inspected                                                      | Prevent inherited key-based inference fallback at each Codex launch boundary.                                |
| Workspace                        | `/Users/pshorey/git/openclaw/runtime/coordinator`; main agent `cwd` unset                                             | Keep the configured execution workspace.                                                                     |
| Schedule                         | Four-hour heartbeat                                                                                                   | Preserve this cadence. Earlier hourly descriptions are stale.                                                |
| Gateway binding                  | `loopback`                                                                                                            | Preserve loopback and the existing private access arrangement.                                               |
| Repository inventory             | `paulshorey/livx`, `paulshorey/map`, `paulshorey/notes`                                                               | Cloud eligibility is reviewed per repository; inventory membership alone is not a Cloud environment mapping. |

The current official changelog lists Codex CLI 0.161.0 and records the GPT-6.1 Sol catalog update in 0.159.1. The installed CLI versions predate those catalog updates. This does not by itself prove an explicit 6.1 request will fail, but makes model discovery and version compatibility an explicit prerequisite. [Codex changelog](https://learn.chatgpt.com/docs/changelog).

### 2.3 Important limits

The installed Cloud command has no dedicated remote model/effort selection, follow-up, cancellation, or PR-creation subcommand. Generic local `-c` options do not establish that remote model settings propagate. Initially, follow-ups and cancellation belong in the Cloud UI; the adapter exposes supported capabilities explicitly.

A successful empty list does not establish that an environment exists, that GitHub is connected to the intended account, or that tasks appear in the desired current Cloud experience. No paid inference or end-to-end Cloud pilot was run during this review.

Do not use the OpenAI Agents API as a transparent replacement for subscription Cloud tasks. It provides managed agent sessions, but its documented authentication requires a Platform key and its model usage is billed at API rates. It does not establish a shared consumer Codex task inbox. [Agents API quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart), [Agents API pricing](https://developers.openai.com/api/docs/guides/agents-api/overview#pricing).

Do not assume Codex desktop tools available in this engineering chat will exist inside OpenClaw. The coordinator's integration must use tools actually exposed by its installed runtime and the CLI adapter.

## 3. Target architecture

```text
OpenClaw dashboard/mobile and four-hour scheduler
    |
    v
Local OpenClaw Gateway -> official Codex app-server -> OpenAI inference
    |                       ChatGPT auth; coordinator role
    |
    +-- Direct small fix -> verified local worktree -> checks -> draft PR
    |
    +-- Local coding wrapper -> separate Codex process -> local-coding role
    |
    +-- Cloud adapter -> authenticated Codex CLI -> Cloud task/environment
    |                                             |
    |                                             +-> Paul follows up directly
    |                                             +-> result/PR independently checked
    |
    +-- gateway_exec/gateway_process -> map runner -> existing owner callbacks

Tracked policy and repository mappings -> validated configuration consumers
Ignored private task ledger -> restart recovery and bounded reconciliation
```

Use the official app-server integration rather than treating the text-only CLI backend as the primary coordinator runtime. The coordinator needs dynamic OpenClaw tools, durable continuation, and completion handling. Keep a separate ordinary CLI adapter for Cloud operations; app-server and Cloud CLI have different responsibilities and authentication contexts.

Do not add a custom OAuth proxy, private ChatGPT HTTP client, undocumented internal endpoint, or ACP bridge to solve this migration. If the official CLI cannot meet a required Cloud operation, record the missing capability and use the supported UI workflow pending a supported interface.

## 4. Independent model policy and change tracking

### 4.1 Canonical role registry

Add `/Users/pshorey/git/openclaw/config/agent-models.json`. It owns model intent, reasoning intent, speed intent, runtime, and billing policy. Keep deployment paths and credential references in a separate non-secret runtime configuration so changing a model does not require changing authentication.

Proposed project schema:

```json
{
  "schema_version": 1,
  "roles": {
    "coordinator": {
      "provider": "openai",
      "runtime": "codex",
      "model": "gpt-6.1-sol",
      "reasoning_effort": "high",
      "speed": "standard",
      "authentication": "chatgpt",
      "allow_api_fallback": false
    },
    "local_coding": {
      "provider": "openai",
      "runtime": "codex_cli",
      "model": "gpt-6.1-sol",
      "reasoning_effort": "high",
      "speed": "standard",
      "authentication": "chatgpt",
      "allow_api_fallback": false
    },
    "cloud_coding": {
      "runtime": "codex_cloud",
      "requested_model": "gpt-6.1-sol",
      "requested_reasoning_effort": "high",
      "requested_speed": "standard",
      "model_control": "unverified_remote_setting",
      "authentication": "chatgpt",
      "allow_api_fallback": false,
      "attempts": 1
    }
  }
}
```

The Cloud fields deliberately describe requested settings. Promote them to enforced settings only after a supported remote control and actual task evidence prove enforcement. If strict Cloud model selection cannot be verified, keep automatic Cloud dispatch disabled and report the exact limitation. A future deliberate acceptance of the service's available model must be recorded rather than implied.

Direct coding uses the coordinator model because it is the same agent turn. To use the separately pinned coding model, dispatch through the local coding wrapper or a verified Cloud setting. Do not imply that direct edits automatically switch models.

### 4.2 Consumers and effective configuration

Implement a small shared Python policy loader with schema validation and stable JSON output. The OpenClaw configuration script and local coding wrapper must read it. Do not copy model strings into executable shell logic or operating prompts.

The OpenClaw exporter should generate the canonical coordinator model reference, explicit model-scoped `agentRuntime.id: "codex"`, High thinking, and Standard speed settings accepted by the selected version. Prefer main-agent scoped settings where supported. Audit global defaults and inherited heartbeat/subagent settings so every coordinator entry path uses the coordinator role. Do not write legacy whole-agent runtime keys. [OpenClaw routing and deployment](https://docs.openclaw.ai/plugins/codex-harness/routing).

The local coding wrapper supplies its own explicit model, effort, provider, and verified Standard speed controls. Personal CLI defaults, project configuration, profiles, and rate-limit suggestions must not silently replace the role. Determine the supported CLI representation of Standard speed during compatibility tests; do not invent a service-tier string.

Scheduled coordinator children inherit the coordinator configuration. Keep model and thinking overrides out of the heartbeat prompt. Saved conversation overrides can take precedence over defaults; identify them explicitly and handle them when changing roles. [OpenClaw thinking levels](https://docs.openclaw.ai/tools/thinking).

### 4.3 Required tracking document

Add `/Users/pshorey/git/openclaw/docs/MODEL-POLICY.md` with:

- A table of each role, authoritative source, consumers, effective live paths, inherited defaults, and verified model/effort/speed/authentication.
- Every location that can override the role: OpenClaw global/main defaults and model entries, session overrides, heartbeat/subagent settings, plugin app-server arguments, CLI user/project/profile configuration, environment provider overrides, and remote Cloud UI/workspace settings.
- Resolved binary paths and versions, the managed app-server package version, last compatibility check, and upgrade procedure.
- Cloud control capabilities and a dated link to evidence showing the effective remote model, or a clear unverified/unsupported status.
- A dated change log: role, before/after, reason, changed files/live paths, verification, rollback reference, and Git commit when committed.
- Historical model mentions marked as historical rather than treated as current configuration.

The initial implementation must search the entire tracked checkout and inspect relevant external settings. The file inventory in section 12 is a starting map, not proof that no other overrides exist.

Add a read-only policy checker that compares desired policy with effective live configuration and wrapper invocation. Report safe fields only. It should flag unknown overrides and unsupported capabilities instead of rewriting them. Include role information in `scripts/status.sh` without dumping auth stores.

### 4.4 Future coordinator model change

1. Edit only the coordinator role in `agent-models.json`.
2. Run schema, availability, and compatibility checks; preview the generated main/default/model-entry changes.
3. Review saved coordinator session overrides and active turns. Preserve history and change their settings through supported operations or start new conversations; do not bulk-edit native thread databases.
4. Apply the scoped configuration. Perform a runtime check with a new coordinator turn and a separately verified local coding invocation.
5. Update `MODEL-POLICY.md`. Confirm local and Cloud coding policy is unchanged.

This makes a future role change a documented, bounded operation, independent of whether the roles currently use identical model IDs.

## 5. Runtime, authentication, and subscription billing

### 5.1 Version and installation strategy

Select a tested OpenClaw/plugin pair before installation. Inspect plugin compatibility metadata and the selected version's schema. If the current OpenClaw cannot safely load the current plugin, upgrade OpenClaw deliberately with a rollback copy and release-note review. Use the plugin-managed app-server for the coordinator; do not casually redirect it to the desktop-owned CLI binary.

Choose an explicit supported binary for local coding and Cloud operations. They may share a binary, but the deployment configuration must record that decision. Avoid selecting by interactive-shell PATH. Resolve managed `current` symlinks for diagnostics and require a compatibility check after package updates.

Installation/configuration can affect a running Gateway. Perform it in a maintenance window after reconciling active coding and map processes. Build and validate the implementation first; do not interrupt active imports simply to test a model.

### 5.2 Coordinator account

Use the default agent-scoped Codex home and the supported OpenClaw ChatGPT sign-in flow. Authenticate to the same intended ChatGPT account/workspace, select the resulting subscription profile explicitly, and exclude API profiles from this coordinator's auth candidates. Existing personal CLI login alone does not populate this isolated account context. [OpenAI runtimes and Codex auth](https://docs.openclaw.ai/providers/openai/runtimes).

Keep the app-server on local stdio. Clear `CODEX_API_KEY` and `OPENAI_API_KEY` from its inference process environment as an additional guard, then verify the selected account and prepared route. An explicit Codex runtime selects the harness; it does not alone guarantee subscription billing.

The agent-scoped home isolates native Codex state, while normal `HOME` remains inherited. User-home configuration and executable subprocesses remain accessible. Treat this as state separation, not an operating-system security boundary. `appServer.clearEnv` cannot be used to remove `HOME` or the selected `CODEX_HOME`. [Codex app-server policy](https://docs.openclaw.ai/plugins/codex-harness/app-server).

Do not copy tokens into the workspace, Git, prompts, or model policy. Do not enable broad credential migration as a convenience. If an account step requires interactive sign-in, finish the reviewable implementation first and have Paul complete the supported sign-in flow during cutover.

### 5.3 Local coding and Cloud CLI account

Configure an explicit authenticated CLI home for the coding/Cloud adapter. Initially prefer the already signed-in native user Codex home, selected by an explicit configured path, while keeping coordinator state separate. If a dedicated CLI home is desired later, sign in there through the supported flow; do not clone token files.

A CLI spawned from a coordinator's native shell may inherit its agent-scoped `CODEX_HOME`, which need not contain a usable ordinary CLI Cloud login. Both the local coding wrapper and Cloud adapter must construct their own launch environment rather than inherit that home accidentally. The Cloud adapter should normally run through `gateway_exec` with its verified CLI auth context.

Before dispatch, require ChatGPT authentication in that exact binary/home/environment context. Remove inference API-key environment variables immediately before launching Codex, including keys that a preceding dotenv runner could reintroduce. Use supported `forced_login_method = "chatgpt"` configuration where compatible and tested, and validate any intended workspace restriction. Do not modify Paul's global login configuration merely to configure the bot. [Codex authentication restrictions](https://learn.chatgpt.com/docs/auth#enforce-a-login-method-or-workspace).

Apply these guards at Codex launch boundaries only. Project tools still use `project-env.py` with the actual target project/app path, and map still requires `--shell-only`. Existing map provider keys and authorized pipeline spending are unrelated to coordinator inference routing.

On expired login, unavailable model, account mismatch, subscription exhaustion, or unsupported route, save the blocker and stop dependent dispatch. Do not change provider, buy credits, enable Fast mode, or substitute another model automatically. Permit bounded retries for transient read failures; task submission requires the ambiguity handling in section 7.

### 5.4 Configuration application

Refactor `scripts/configure.sh` so a normal policy/configuration apply does not install or start the Gateway unexpectedly. Provide explicit modes for dependency/plugin preparation, dry-run/validation, configuration application, and intentional service installation/start. Ordinary documentation/template deployment must remain safe while the operator intentionally leaves OpenClaw stopped.

Remove Fireworks as a coordinator prerequisite and automatic inference fallback. Preserve its existing key and private rollback configuration in `~/.openclaw/.env` with mode 0600. Preserve loopback binding, Tailscale access, existing device pairing, disabled Telegram state, memory search provider, and four-hour schedule. Use a scoped patch, never replace the entire live configuration.

## 6. Coding policy: direct, local delegated, and Cloud

| Work                                                                                   | Default route                                                                               | Required evidence                                                                              |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Small, clear code/doc/config fix that fits comfortably in the current pass             | Coordinator directly, isolated worktree                                                     | Verified repo/base, repository instructions, narrow diff, relevant checks, durable handoff/PR. |
| Larger implementation, broad refactor, or task requiring sustained independent context | Cloud when its environment is validated; otherwise explicit local delegation where suitable | Recorded authority, task ownership, acceptance criteria, isolated workspace, verified result.  |
| macOS/browser/computer-use work or access to local-only assets/services                | Local dedicated process or direct bounded local action                                      | Actual local tool availability and project instructions.                                       |
| Map import, resume, process control, and automatic continuation                        | Local Gateway execution path                                                                | Existing owner-specific preflight and map receipt/control evidence.                            |
| Map pipeline code repair                                                               | Direct small repair or delegated local/Cloud code task as suitable                          | No Cloud production import; merge/deploy/check locally before resuming the affected pipeline.  |
| GitHub publication, merge, deployment, or destructive cleanup                          | Existing authority and target project rules                                                 | Revalidated remote/PR/head/check state and concrete reviewable result.                         |

Do not force a second process merely because an action writes code. Isolation remains valuable even with a trusted model: it separates changes from Paul's checkout and keeps long tasks from blocking coordinator responsibilities.

“Small” is a scope/time judgment, not a permission to skip repository rules. If diagnosis broadens or the pass cannot finish within its budget, save the evidence and hand off the remaining task. Keep the heartbeat's five-minute target and 15-minute hard limit; do not turn every heartbeat into a long coding run.

Before any implementation, validate inventory/remote, read the target repository's `AGENTS.md`, inspect dirty state and existing worktrees/PRs, and acquire task ownership. Use `codex/` branches unless target instructions require otherwise. Never switch/reset Paul's working checkout to prepare a task.

Strengthen `delegate-codex.sh` or its shared helper to enforce a verified isolated worktree before starting the coding process. Currently the requirement exists mainly in prompts. Require an explicit base and reject an unrelated checkout/worktree; do not rely on the child to repair this later. Preserve the currently authorized execution policy rather than broadening it incidentally.

On completion, inspect the actual diff and checks. An exit code, task summary, or successful test run alone is insufficient to declare the intended change complete. Draft PRs remain drafts when work or required checks are missing. No new blanket approval requirement or automatic merge authority is introduced by this migration.

## 7. Cloud adapter and task lifecycle

### 7.1 Implement a narrow adapter

Add `/Users/pshorey/git/openclaw/scripts/codex-cloud.py`, using Python's standard library and the existing project environment infrastructure where needed. Invoke the configured CLI with argument arrays, explicit working directory, bounded timeout, and a private sanitized launch environment. Never interpolate prompts, task IDs, branches, or output into a shell command.

Expose project-level operations: `doctor`, `prepare`, `submit`, `list`, `status`, `diff`, `reconcile`, and `capabilities`. `prepare` records and validates intent without remote submission. `submit` performs one supported CLI submission. Local adapter output should be structured JSON with a schema version, success/error class, and stable IDs; do not promise upstream commands already have JSON output.

Initial capability report:

| Operation                       | Initial support policy                                                              |
| ------------------------------- | ----------------------------------------------------------------------------------- |
| Submit                          | Explicit environment, branch, one attempt; enabled per repository only after pilot. |
| List                            | Paginated JSON; preserve cursor and environment filtering.                          |
| Inspect                         | Known task status plus list metadata; unknown output stays unknown.                 |
| Diff                            | Read-only retrieval, explicit attempt when available.                               |
| Follow-up / cancel / create PR  | User follows up in Cloud UI; report CLI capability unavailable.                     |
| Apply diff                      | Automatic adapter path disabled; use verified PR workflow by default.               |
| Remote model selection / events | Unverified or unavailable until supported interface is demonstrated.                |

Do not scrape authentication tokens or call undocumented backend endpoints to fill capability gaps. Browser automation is acceptable for environment setup or an explicitly requested human-facing operation; it should not become a fragile unattended task API.

### 7.2 Environment registry and branch independence

Add `/Users/pshorey/git/openclaw/config/codex-cloud-environments.json`, separate from the reviewed local repository inventory. Each entry should record repository full name, reviewed remote, environment ID, environment generation, permitted base branch, auth-context reference, readiness status, verification date, tested CLI version, effective model-control capability, and setup/run-check references. No credentials belong here.

Start entries disabled/unverified. Choose the first pilot repository after checking its actual GitHub access, instructions, and setup. Do not create generic environments for every managed repository without reviewing suitability.

Never accept the CLI's current-local-branch default. Resolve the authorized remote base, query its current SHA, and pass an explicit branch. The registered repository and target environment must match. Cloud does not receive uncommitted local changes or private filesystem-only files; incorporate required committed changes through a reviewed branch or state that they are unavailable.

Record the expected remote SHA and require the Cloud task to report the actual starting commit before implementation. A branch name can move between lookup and dispatch; it is not an immutable commit guarantee. If exact base pinning is required, use a supported verified commit selector or a deliberately authorized dispatch branch. Do not assume a SHA passed to `--branch` is supported.

Never apply a Cloud diff to Paul's current checkout automatically. Prefer Cloud PRs. If PR publication requires a local step, fetch/apply only into a separate verified worktree, inspect the diff, run checks, and publish under existing authority. A patch must match the recorded base and must not overwrite local user changes.

### 7.3 Durable state, ownership, and duplicate prevention

Use a private SQLite task ledger at `/Users/pshorey/git/openclaw/runtime/coordinator/state/codex-tasks.sqlite3`. Python ships SQLite; transactions give multiple coordinator conversations a reliable way to claim work. Keep this implementation small: tasks, observations, ownership leases, and schema migrations. A readable JSON/Markdown snapshot may feed `state/ACTIVE.md`, but is not the concurrency authority.

Minimum task fields:

- Local task ID, route, repository, scope/key, owner conversation, and originating user/standing-authority reference.
- Environment ID/generation; explicit base branch; expected and verified starting SHA.
- Requested model-policy snapshot and separately verified effective model information.
- Prompt digest/private prompt path, acceptance criteria, decision constraints, and dispatch timestamp.
- Submission state, remote task ID/URL, attempt count, latest remote observation and timestamp.
- Lease owner/expiry, last action, next owner/action, PR URL/number/head SHA, checks, and evidence links.
- Error class, ambiguity/reconciliation record, terminal result verification, and notification fingerprint.

Use transactional claims and renewable bounded leases to prevent two heartbeats from submitting the same eligible task. An expired lease permits investigation; it does not prove the remote task stopped. Compare repository, issue/PR identity, scope, and base so a paraphrased prompt does not create duplicate work.

Suggested local lifecycle:

```text
prepared -> submitting -> submitted -> running -> needs_review -> verified
                   |
                   +-> submission_unknown -> reconciled / needs_user_action

Any non-final state -> blocked / failed / cancelled (only with evidence)
```

Cloud task completion and local work verification are different states. Preserve raw remote status separately. An unknown status value or unavailable API is not completion. Paul may resume a previously completed Cloud task; newer observations must reopen the relevant review state rather than treating a task as permanently immutable.

### 7.4 Submission ambiguity and recovery

Write the intent and `submitting` state transactionally before the remote call. Include a short non-secret local task marker in the prompt for reconciliation. After success, validate and store the returned task ID/URL before notifying the coordinator/user. Validate URLs against the supported service hosts and verified task-path format; never execute a returned URL as code.

The installed CLI does not expose a server-side idempotency key. Local markers and locks reduce duplication, but cannot guarantee exactly-once remote submission. A timeout, interrupted process, or lost success response must enter `submission_unknown`; never automatically resubmit an ambiguous request.

Reconcile using known IDs and a bounded paginated search around the dispatch time/environment. Recent-list absence, or a page limit, is not proof that submission failed or a task was deleted. If the available metadata cannot identify the task uniquely, retain the unresolved state and give Paul the concrete candidate links/context. Do not manufacture a failed state to justify retrying.

Read calls may retry with short exponential backoff and a total deadline. Rate limits and auth failures must not spin, resubmit tasks, or occupy the Gateway execution lane while waiting for a human.

### 7.5 Monitoring and direct user follow-up

After successful dispatch, publish the canonical Cloud task link with a brief purpose, environment/base, verification status, and local tracking ID in the owning OpenClaw conversation. Paul can continue directly in Cloud; the task should not need OpenClaw messaging to receive his follow-up.

Reconcile known tasks in the existing four-hour heartbeat, plus explicit user-requested checks. Poll with bounded calls and incremental observations. Monitor imported user-created Cloud tasks only when explicitly selected or covered by reviewed standing authority; do not take ownership of every task in the account.

Cloud continues while the Mac sleeps, but local OpenClaw dispatch, map work, and local monitoring do not. Four-hour scheduling also does not promise immediate completion notifications. If Paul later wants faster awareness, propose a separate lightweight status checker that wakes the coordinator only for meaningful changes; do not silently change the existing schedule.

The installed CLI supplies no verified completion webhook. Do not reuse map callback receipts as proof of Cloud events. Keep notifications in the owning dashboard/mobile conversation and avoid repeating unchanged progress or decisions.

On a Cloud PR, query GitHub independently: repository, PR identity, current head/base, actual diff, reviews, checks, and deployment state. Record the head reviewed. If Paul or another task changes the head, revalidate before publication/merge actions. Overlapping Cloud tasks can still conflict in Git even though their working files are isolated.

## 8. Cloud environment preparation and portability

Prepare environments through the current supported Cloud settings/setup flow, using the environment generation actually validated by the pilot. Review repository access, account/workspace identity, privacy/sharing, dependency setup, runtime versions, network policy, test commands, and PR workflow. Record reproducible setup in the appropriate repository when changes are needed; do not add machine-specific paths to a Linux Cloud bootstrap.

Keep environments lean. Start with coding and tests using fixtures or development services. Never transfer OpenClaw's runtime state, personal login files, production ingestion checkpoints, or blanket contents of local dotenv files. Required variables should be identified by name and supplied through the appropriate environment mechanism.

Current environments distinguish direct variables from proxy-substituted network secrets; the latter work for configured HTTPS destinations during setup and tasks. Legacy environment secrets are setup-only. Configure according to the chosen generation rather than copying legacy assumptions into current environments. [Current variables and network secrets](https://learn.chatgpt.com/docs/environments/cloud-environments#configure-environment-variables-and-network-secrets), [Legacy variables and secrets](https://learn.chatgpt.com/docs/environments/cloud-environment#environment-variables-and-secrets).

Current Cloud documentation also lists browser/computer use as unsupported, local personal skills as unsynced, and saved VM state recovery as limited to seven days after the latest turn/resume by default. Plan local routes for computer use, repository-owned portable instructions for Cloud, and PR/commit evidence for durable code output. [Cloud limitations and VM state](https://learn.chatgpt.com/docs/environments/cloud-environments#vm-specifications).

For this OpenClaw repository specifically, separate portable Python/unit checks from macOS LaunchAgent, Homebrew, live Gateway, and native callback integration checks. Cloud may implement portable code changes; this Mac verifies service installation and map callback behavior. Do not start a production Gateway or import pipeline in Cloud.

For map code tasks, read the map repository's instructions and environment rules. Tests must not launch production ingest or spend provider credits merely because the coordinator has standing local import authority. A Cloud coding task receives its own exact permitted scope.

Test cold environment setup and a new task after changes. Existing task state and published environment updates can differ; record the setup version used by each task. Review private package download hosts, test service access, resource limits, and large data requirements before calling an environment ready.

## 9. Preserve map process ownership and automatic continuation

This is the most important local regression risk. Current map operation depends on native OpenClaw background handles, owner-specific preflight proof, enqueue acknowledgements, exact terminal IDs, and continuation in the same owning conversation.

Under Codex app-server, ordinary native shell tools and OpenClaw Gateway execution are distinct. The eligible native runtime exposes `gateway_exec` and `gateway_process` for Gateway-owned execution; these remain subject to tool/host policy. Availability must be tested in the actual main agent and scheduled child. [Codex runtime behavior](https://docs.openclaw.ai/plugins/codex-harness/runtime-behavior).

Update operating templates so “native exec/process” in the map procedure unambiguously means the Gateway path under this runtime. Use Gateway execution for the map runner and its required environment/callbacks. Ordinary Codex native terminal completion is not equivalent map preflight proof.

Before accepting cutover:

1. Reconcile existing map control, active owner, and private action state. Do not abandon or duplicate an active import.
2. Verify actual Gateway tool availability and the configured exec host/sandbox/allow-deny policies. Do not solve a hidden tool by broadly disabling existing protections.
3. Launch the harmless map terminal preflight through `gateway_exec` in a controlled owner conversation.
4. End the turn after the background launch, let the automatic event resume that owner, and verify the exact callback/enqueue/terminal/exit evidence.
5. Record the witnessed receipt and run the existing receipt checker for that owner. Old receipts and another owner's success are insufficient.
6. Verify a controlled continuation/reconciliation path, including a duplicate event and queued callback case, before resuming normal continuous imports.

Preserve existing `--unlimited` full-run/resume semantics, shell-only project environment, one-active-import control, checkpoint recovery, and continuous standing authorization. This migration must not introduce new provider caps, deadline requirements, repeated preflights, or permission questions for already-authorized map work.

A Cloud coding task may repair the runner, but only locally deployed code and fresh local proof can establish restored production callback behavior.

### 9.1 CLI access and shell contract

The current unsandboxed default executes on the local Gateway host under Paul's macOS user, subject to OpenClaw's execution policy. It does not require a visible Terminal window. For map, the supported entry point remains the absolute `scripts/run-map-import.sh` path, launched through Gateway exec with `background=true`, `timeoutSeconds=0`, and no PTY. The zero timeout is essential: returning a background handle does not cancel the default command-lifetime timeout. [OpenClaw exec tool](https://docs.openclaw.ai/tools/exec).

The installed POSIX launcher chooses `SHELL` when available and otherwise resolves `sh`, then `bash`. It invokes a noninteractive command shell; Bash/zsh startup snapshots are a separate Gateway facility. This engineering session uses zsh, but the LaunchAgent does not explicitly pin `SHELL`, so do not infer the live Gateway shell from this terminal.

The actual map entry script declares Bash, immediately executes the project virtualenv Python runner, and starts the project environment helper. That helper explicitly uses `/bin/zsh -lc` to collect login environment privately, then replaces itself with the requested `pnpm` command. The supervisor launches the ingestion worker using the Node executable directly. The long-running job is a supervised Node process, not a shell or AI turn kept open to wait.

Document and test this execution chain with absolute entry paths and the map-required `--shell-only` environment behavior. Verify selected shell, working directory, executable paths, and variable availability through non-secret diagnostics during cutover. Do not depend on interactive aliases or a developer's open terminal.

### 9.2 Discovery must work outside the launching conversation

The installed OpenClaw 2026.9.5 implementation resolves process-tool scope in this order: explicit scope, session key, session ID, then agent ID. Process list/poll/control filter by that scope. This is narrower than the general documentation's per-agent description. A newly dated heartbeat conversation can therefore lack access to a prior owner's handle even when both use agent `main`. A restarted Gateway also loses its in-memory process handles. [OpenClaw background process tools](https://docs.openclaw.ai/gateway/background-process).

Keep the owning handle for immediate control and callback correlation, but use map's durable domain interfaces for independent discovery:

| Interface                                   | Purpose and limits                                                                                                             |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `ingest:supervise list`                     | Discover retained job IDs, run/execution IDs, status, and supervisor/child PID-presence hints. Presence is not identity proof. |
| `ingest:supervise status --job UUID`        | Read the private job manifest and terminal result, including health checks, logs, and pinned identities.                       |
| `ingest:control list --json`                | Inspect registered workers, admission/source locks, maintenance, local script candidates, and current quiescence.              |
| `ingest:status --run UUID --json --limit 5` | Inspect the exact managed run's progress, attempts, errors, verification, and resume evidence.                                 |
| Gateway `process`/`gateway_process`         | Manage the owning conversation's live handle while it exists; not the durable cross-conversation registry.                     |

Agents and humans use the same project CLI. Invoke these commands through `/Users/pshorey/git/openclaw/.venv/bin/python /Users/pshorey/git/openclaw/scripts/project-env.py --cwd /Users/pshorey/git/map --shell-only -- pnpm --silent --filter @lib/db-map ...`. They do not require the original model, chat, or a surviving Gateway handle. A future agent still needs authorized shell access to this Mac and the required project credentials; a Cloud coding task has no automatic access to these local controls.

The job directory is `/Users/pshorey/git/map/lib/db-map/.ingest-jobs/UUID/`. Preserve `job.json`, `result.json`, `worker.log`, `supervisor.log`, and notification/claim evidence. Keep the OpenClaw owner/native handle, job UUID, DB run UUID, execution UUID, Gateway generation, evidence paths, and next action in the existing private map ledger. Avoid ambiguous labels such as one generic “session ID” for all four identities.

### 9.3 Health and control belong to ordinary code

The existing Node supervisor detects exit immediately and probes database health hourly without invoking a model. Current checks stop its owned child for a heartbeat older than 120 seconds at the probe, a terminal execution with a still-live child, missing registration, a failed health query, or recorded progress idle for two hours. Preserve those checks initially; evaluate legitimate long stages and provider cooldowns before adjusting thresholds. Missing stdout is not a stall signal. A job can be silent and healthy.

For graceful managed pause, use `ingest:control stop --run UUID --wait-seconds 30 --json`. It requests the selected run to stop and waits for evidence; exit 2 means stop was not confirmed within the budget. For supervisor-owned termination, `ingest:supervise stop --job UUID` writes `stop.request`; the live supervisor signals its own child process group, allows ten seconds of grace, and forces termination if necessary. Neither command's request alone proves exit. Recheck control/locks, process evidence, and terminal outcome before resume or maintenance.

Never signal a saved PID solely because it appears in a manifest: it may have been reused. Do not kill all Node/pnpm processes. Use existing maintenance/quiescence rules before code/schema/input repairs. If the supervisor disappeared, use the runbook's evidence-based reconciliation; do not fabricate a terminal result or automatically relaunch an abandoned job claim.

A later heartbeat performs one bounded discovery snapshot, reconciles each known job with its pinned DB run/execution and progress, records meaningful changes or a concrete blocker, and ends. It does not stream logs or wait for healthy work. The owner callback provides immediate terminal continuation when verified; the four-hour heartbeat is an independent reconciliation opportunity, not the only health monitor.

### 9.4 Required additional acceptance tests

- Start a harmless supervised test in conversation A, then discover its job and inspect its state from a new heartbeat conversation B using map's durable controls. Do not borrow A's process scope or callback receipt.
- Discover the same job from a fresh human/developer shell using the documented project environment runner. Verify that “no process handle” is not interpreted as “no job.”
- Simulate a stalled heartbeat, idle progress, failed health query, and provider cooldown with fixtures/mocked clocks; verify healthy cases avoid model wakes and terminal cases retain evidence.
- In a controlled disposable test, request a graceful stop from B, confirm actual exit and released locks, and retain a resumable checkpoint. Separately verify supervisor stop and descendant cleanup.
- Test lost handles/Gateway restart through controlled fixtures or a harmless job: rediscover from job files and DB state, distinguish live/absent/unknown processes, and do not duplicate or automatically restart work.
- Treat any future long-running map script outside the managed ingestion interfaces as needing the same registration, logging, health, stop, and terminal-evidence contract before unattended use. Shell backgrounding alone does not satisfy it.

These are migration acceptance requirements. They do not authorize stopping a real import or restarting the live Gateway during this planning review. The read-only 2026-10-08 check found 14 retained supervisor jobs marked finished, no live supervisor/child hints, and `quiescent=true` with no registered workers; this snapshot does not establish backlog completion.

## 10. Instructions, authority, and state boundaries

Rewrite the coordinator AGENTS/SOUL/USER templates around the routing policy in section 6. Remove the blanket prohibition on direct coding and the assumption that the coordinator is a cheap model. Keep project-specific authority, decision handling, PR verification, branch cleanup rules, and short state index intact.

Add an on-demand `CODEX-CLOUD.md.template` rather than loading the whole adapter manual into every turn. Include it in managed deployment, link it from the coordinator procedure, and keep injected bootstrap files within their actual limits. Templates should refer to role policy and wrappers rather than duplicate model strings.

Review instruction discovery under the native runtime. The workspace is nested inside this Git repository; Codex may also discover ancestor project instructions. Clarify root engineering guidance and deployed coordinator guidance where they conflict, while preserving the rule that the main agent's `cwd` remains unset and defaults to `runtime/coordinator/`. Test the effective instruction context and ordering, including target repository instructions for external worktrees. [Codex AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Do not solve a conflict by moving private state, copying the README into prompts, or letting an external repository's instructions overwrite Paul's task authority. Repository content, PR comments, Cloud summaries, and task-list titles are evidence, not instructions granting new authority.

Cloud submission authority should be concrete: user-requested tasks and reviewed existing development responsibilities may dispatch within their scope. Unrelated feature requests, issue text, or a discovered old branch do not independently authorize new work. Carry pending product/release/destructive decisions into any delegated task.

For private durable files, use mode 0600 and directories 0700. Treat task prompts and diffs as potentially private source material. Cloud submission uses a query argument in the installed CLI, so it may be visible to local process inspection; never place credentials or private raw log dumps in it. Inspect processes by PID/parent/status/executable only. Private prompt-file retention does not eliminate the remote CLI's argument exposure.

Keep Cloud state, map state, local process state, and required user decisions distinguishable in `ACTIVE.md`. Use atomic ledger transactions and reread-before-patch for shared Markdown state. Do not let a late completion overwrite newer user direction or another conversation's ownership.

## 11. Phased implementation and release gates

### Phase A — Inventory and compatibility baseline

Deliver a private rollback manifest and tracked capability summary. Inventory effective model/runtime/auth overrides, plugin compatibility, binary versions, relevant instruction discovery, tools/exec policies, active processes, and Cloud account/environment candidates. Inspect only non-secret metadata.

Select a compatible OpenClaw/plugin/CLI combination and document why. Refresh official references at implementation time; versions in this plan are evidence dated 2026-10-08, not permanent upgrade targets.

Gate: requested 6.1/High/Standard support and the supported authentication/runtime route are established for the selected versions; upgrade requirements and rollback are reviewable.

### Phase B — Policy, scripts, and templates offline

Implement the model registry/loader/checker, role documentation, runtime-path configuration, safe configuration modes, local coding worktree enforcement, revised routing templates, and on-demand Cloud procedure. Preserve deployment conflict detection and private state.

Build the Cloud adapter and ledger behind per-repository disabled flags. Use captured sanitized CLI fixtures and fake subprocesses for tests; offline tests must not create Cloud tasks, start OpenClaw, publish GitHub writes, or run paid imports.

Gate: dry-run patches are scoped, configuration validates against the selected schema, meaningful offline tests pass, and no unintended runtime/user files change.

### Phase C — Local coordinator cutover

After the implementation is reviewed and migration is authorized, reconcile active work, back up only needed private config with restricted permissions, prepare the selected compatible plugin/runtime, complete supported ChatGPT sign-in, and apply the scoped configuration/templates.

Intentionally restart/start the Gateway only as part of this cutover. Record actual runtime, effective model/effort/speed, account type, tool availability, and a resumed conversation. Validate the dated heartbeat child and owning-dashboard reply behavior.

Run the harmless map callback preflight and cross-conversation discovery/control tests described in section 9. Exercise one small direct fix in a disposable verified worktree with an actual diff/check result. Verify a separate local coding invocation uses its role policy.

Gate: subscription-only Codex coordinator works, local coding is independently pinned, direct coding is isolated, and map callback/heartbeat behavior is witnessed. Cloud dispatch remains disabled if its separate gate has not passed.

### Phase D — One Cloud environment and end-to-end pilot

Prepare/review one eligible environment. Verify the exact CLI binary/home can read it and that it belongs to the intended account/repository. Submit one narrow task with one attempt, an explicit remote branch, a stable local marker, and clear acceptance checks.

Save its returned identity. Confirm the actual starting commit and effective remote model/effort/speed through supported evidence. Open the returned URL in Paul's intended Cloud interface. Have Paul continue that same task directly and confirm the CLI/adapter observes the resumed task and its output. This human follow-up is a necessary product-compatibility check, not permission to implement the adapter.

Retrieve the diff, review an actual PR or a controlled worktree publication, and verify the relevant checks. Exercise adapter restart recovery, a paginated reconciliation, and one safely simulated lost submission response. Do not deliberately create duplicate remote tasks to test deduplication.

Gate: direct user follow-up and result/PR reconciliation work for the actual service generation. Strict remote model policy is either proven or Cloud stays disabled pending an explicit recorded policy decision.

### Phase E — Routine coordination and incremental expansion

Enable only the validated environment mapping. Reconcile Cloud tasks alongside GitHub work while preserving map priorities and bounded heartbeat turns. Expand to another repository only after its setup and pilot checks pass.

Record initial operating evidence and failures in private notes. Verify stopped/sleeping/restarted Mac behavior: Cloud survives, local monitoring resumes and catches up, and local map processes are reconciled rather than duplicated. Add a faster model-free status monitor only if requested later.

Gate: routine dispatch and recovery are reliable, unchanged statuses stay quiet, independent user follow-ups are respected, and one broken environment does not stall unrelated local duties.

## 12. Planned file and configuration changes

All checkout paths in this table are relative to `/Users/pshorey/git/openclaw/`. Items marked “new” do not exist yet and are implementation deliverables.

| File or surface                                        | Planned change                                                                                                             |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `config/agent-models.json` — new                       | Canonical independent role settings and billing policy.                                                                    |
| `config/codex-runtime.json` — new                      | Non-secret binary/auth-home/profile references, selected compatibility versions, explicit path policy.                     |
| `config/codex-cloud-environments.json` — new           | Reviewed per-repository Cloud mappings, capabilities, readiness, and explicit base policy.                                 |
| `scripts/agent-policy.py` — new                        | Shared policy/path loader, schema validation, safe diagnostics, and export contract.                                       |
| `scripts/configure-agent-runtime.py` — new             | Scoped dry-run/apply generation and effective-policy comparison.                                                           |
| `scripts/configure.sh`                                 | Separate dependency preparation/config apply/service start; remove Fireworks coordinator prerequisite.                     |
| `scripts/delegate-codex.sh`                            | Load local coding role; enforce auth/binary context and isolated worktree; preserve private logs.                          |
| `scripts/codex-cloud.py` — new                         | Capability-aware Cloud adapter, task claims, submission recovery, and structured output.                                   |
| `scripts/status.sh`                                    | Report all role/runtime/auth contexts and known Cloud task state without exposing credentials.                             |
| `scripts/deploy-workspace.py`                          | Deploy on-demand Cloud procedure with current conflict protection and permissions.                                         |
| `config/coordinator/AGENTS.md.template`                | Direct/delegated/Cloud routing, ownership, verification, Gateway map tool names.                                           |
| `config/coordinator/SOUL.md.template`                  | Replace mandatory delegation language with scoped engineering judgment.                                                    |
| `config/coordinator/USER.md.template`                  | Reference role policy; preserve user preferences and four-hour communication.                                              |
| `config/coordinator/IDENTITY.md.template`              | Review role wording; edit only if it contradicts the final behavior.                                                       |
| `config/coordinator/MAP-IMPORTS.md.template`           | Clarify Gateway execution/callback semantics without changing ingestion authority.                                         |
| `config/coordinator/CODEX-CLOUD.md.template` — new     | On-demand dispatch, monitoring, recovery, and UI follow-up procedure.                                                      |
| `config/heartbeat-prompt.txt`                          | Reconcile Cloud work; preserve launcher classification/ownership and inherited coordinator model.                          |
| `scripts/configure-ui-workflow.py`                     | Preserve four-hour dashboard workflow; change only schema/runtime compatibility requirements.                              |
| `config/coordinator-skills.json`                       | Audit needed capabilities; add Cloud setup guidance only if genuinely used and available.                                  |
| Root `AGENTS.md`                                       | Clarify native instruction scope and reference role/Cloud documentation where needed.                                      |
| `docs/MODEL-POLICY.md` — new                           | Complete model-consumer inventory, effective settings, migrations, and future role-change procedure.                       |
| `docs/CODEX-CLOUD.md` — new                            | Operator environment setup, pilot evidence, CLI limits, recovery, and portability runbook.                                 |
| `README.md`                                            | Update actual architecture, file map, billing/auth explanation, configuration procedure, and limits.                       |
| Relevant test files — new or updated                   | Policy generation, wrapper isolation/auth, Cloud parsing/recovery/leases, deployment conflicts.                            |
| `~/.openclaw/openclaw.json` — private generated target | Scoped runtime/model/auth/tool policy apply; preserve unrelated settings.                                                  |
| OpenClaw subscription auth store — private             | Supported sign-in/profile selection only; no token values in Git or documentation.                                         |
| Native CLI home/config — private external setting      | Explicit adapter context; document any deliberate scoped profile/restriction without changing unrelated personal defaults. |
| `runtime/coordinator/` — ignored deployment/state      | Managed templates, private Cloud ledger/logs, existing memory/state; never commit or wipe.                                 |
| Cloud settings — external                              | Reviewed environment setup, account/repository access, supported remote model settings, and dated capability evidence.     |

Do not modify `scripts/run-map-import.py`, its shell wrapper, or project-env behavior unless the actual callback/environment validation reveals a concrete incompatibility. Preserve their established contracts and regression checks.

## 13. Verification plan

Write tests for consequential behavior and recovery, not for Markdown wording or trivial implementation mirrors.

| Area                   | Required checks                                                                                                                                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Role separation        | Coordinator-only registry edit changes only coordinator export; local role invocation and Cloud requested policy remain stable.                                                                                    |
| Runtime selection      | Selected schema accepts explicit canonical model/runtime; live turn identifies actual Codex runtime and requested model/effort/speed.                                                                              |
| Auth boundaries        | Exact CLI home/binary is used; inherited agent home and API keys cannot switch inference auth; dotenv reintroduction is handled; wrong/expired account blocks.                                                     |
| Configuration safety   | Dry-run causes no live writes/start; unrelated keys survive apply; malformed policy/config fails clearly.                                                                                                          |
| Local coding isolation | Dirty user checkout stays unchanged; unrelated repo/worktree rejected; explicit base and role arguments verified.                                                                                                  |
| Deployment             | Changed managed runtime file refuses overwrite; private state and permissions survive adding the Cloud procedure.                                                                                                  |
| Cloud parsing          | Paginated/empty/malformed/unknown-schema data, task URL validation, status drift, and attempt selection.                                                                                                           |
| Cloud dispatch         | Explicit environment/branch/one attempt; argument-array execution; private outputs; disabled/unverified environments reject submission.                                                                            |
| Recovery/concurrency   | Crash before/after submission, unknown outcome, duplicate owners, expired leases, stale observations, user-resumed task, and failed read retries.                                                                  |
| GitHub integration     | PR links verified independently; head changes invalidate stale checks; untrusted summaries do not authorize merge.                                                                                                 |
| Map continuation       | Existing project-env/map regression suites; actual same-owner Gateway preflight/callback receipt; queued events; fresh-heartbeat/human discovery; confirmed stop; lost-handle recovery without duplicate dispatch. |
| Scheduling             | Four-hour launcher, visible dated child, inherited coordinator role, bounded pass, no polling that blocks completion events.                                                                                       |
| Cloud environment      | Cold setup and new-task checks, Linux-compatible tools, allowed dependencies/services, correct secret mechanism, user follow-up.                                                                                   |

Use `git diff --check`, appropriate Python/shell checks, and existing `scripts/test-project-env.py` / `scripts/test-run-map-import.py` when their covered behavior changes or cutover needs regression evidence. Validate OpenClaw config without starting the service during offline phases. Run live runtime tests only in the deliberate cutover/pilot phases.

A Cloud “done” status is not acceptance. Completion requires the requested behavior, inspectable diff, relevant checks, and any required PR/deployment evidence. Document unverified requirements instead of marking a partial migration complete.

## 14. Rollback and failure handling

Before live application, record versions, changed config paths, deployment hashes, and service state. Keep private rollback copies outside Git with restrictive permissions. Preserve runtime databases, map checkpoints, user files, and native Codex history.

If coordinator runtime or map callback validation fails, disable new dispatch, reconcile active jobs, restore the reviewed prior coordinator configuration/templates, and intentionally restore service state. Fireworks remains available only as a deliberate rollback; its credentials must not become an automatic fallback.

If Cloud compatibility fails, keep the subscription Codex coordinator/local coding migration usable if its gates passed. Leave Cloud mappings disabled and retain the pilot task/ledger links. Do not cancel remote work, delete environments, or erase evidence to make the rollout appear clean.

The legacy provider's old conversations and native thread bindings may not translate to Codex runtime state. Preserve transcripts and private decision/task state; start a clearly identified new conversation when a supported continuation cannot be established. Do not edit history databases or rerun side effects to recreate context.

Rollback must account for jobs that already started. Changing a coordinator model does not stop a Cloud task or map process. Inventory those jobs before restoring ownership or permitting another dispatch.

## 15. Remaining questions to resolve through implementation evidence

These are technical gates, not reasons to stop the current planning work or ask Paul to repeat his preferences:

1. Which supported OpenClaw/plugin version pair provides the required model, tools, and continuation behavior on this Mac?
2. Does the selected CLI submit to an environment whose task opens and continues in Paul's intended current Cloud interface?
3. What supported control and observable evidence establish the effective Cloud model, effort, and speed? If none, what precise limitation remains?
4. Which first managed repository has a suitable portable Cloud environment and verified PR workflow?
5. Does the actual scheduled native runtime expose Gateway execution and preserve map owner callbacks under the current tool policy?
6. Which existing session-level model/thinking/speed overrides and ancestor instructions need explicit reconciliation?

Resolve each with a dated capability result and pilot evidence. Only ask for a user decision when the remaining issue depends on intent, account interaction, a deliberate policy change, or authority outside the already-agreed scope.

Research note: current official HTML documentation and installed version-specific documentation were used together. Direct Markdown downloads from several OpenClaw documentation URLs returned HTTP 403, so those downloads were not treated as evidence; official browser-retrieved pages and the installed bundled docs supplied the relevant facts. No search batch failed, no secrets were printed, and no Cloud task was submitted for this planning review.
