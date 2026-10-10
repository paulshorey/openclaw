# Codex Cloud operations

Date: 2026-10-08. The local adapter is implemented. Automatic Cloud submission remains disabled while environment/UI compatibility and remote model policy are unverified. No Cloud task has been submitted during implementation so far.

## CLI and billing boundary

The adapter uses the versioned 0.160.0 CLI and explicit user CLI home from `config/codex-runtime.json`, verifies ChatGPT login, and removes API inference keys/route overrides. Cloud tasks use the subscription Cloud service; this is not an Agents API integration. Included usage is shared with ChatGPT/Codex and is not unlimited. Account exhaustion blocks dispatch instead of switching provider.

The selected CLI supports `cloud exec`, paginated `list --json`, text `status`, and read-only `diff --attempt 1`. Follow-up, cancellation, and PR creation belong in the supported Cloud UI. No verified completion webhook or remote model/effort/speed selector exists in this CLI. Do not treat local `-c model=...` as remote enforcement.

Implementation evidence from [upstream 0.160.0 Cloud source](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/cloud-tasks/src/lib.rs): `cloud exec ... -` reads the prompt from stdin; the adapter uses this so prompts stay off process argv. `cloud status` exits 1 for any status other than ready, including healthy pending tasks. The adapter preserves that code separately and uses JSON list metadata for reconciliation.

## Commands

Run from this checkout (absolute paths are suitable inside the coordinator):

```sh
.venv/bin/python scripts/codex-cloud.py capabilities
.venv/bin/python scripts/codex-cloud.py doctor
.venv/bin/python scripts/codex-cloud.py list
.venv/bin/python scripts/codex-cloud.py list --remote --max-pages 5
.venv/bin/python scripts/codex-cloud.py reconcile
```

`doctor` verifies read access and lists reviewed mappings. It does not create tasks or environments. Local list/reconcile of an unused adapter do not create a database.

Prepare a task only under actual user/standing authority:

```sh
.venv/bin/python scripts/codex-cloud.py prepare \
  --repository paulshorey/notes --scope 'issue:NUMBER:reviewed-base' \
  --owner ACTUAL_SESSION_KEY --authority USER_REQUEST_REFERENCE \
  --acceptance 'Exact checks and pending decision constraints' \
  --prompt /absolute/private/prompt.txt
.venv/bin/python scripts/codex-cloud.py submit LOCAL_TASK_UUID --owner ACTUAL_SESSION_KEY
.venv/bin/python scripts/codex-cloud.py status LOCAL_TASK_UUID
.venv/bin/python scripts/codex-cloud.py diff LOCAL_TASK_UUID --attempt 1
```

Preparation records intent even while dispatch is disabled. It verifies the reviewed local origin and resolves the registry's explicit remote branch through GitHub, independently of the local checked-out branch. Submission records the expected commit; the remote task must report the actual starting commit and stop on mismatch. A branch is not immutable pinning.

## Environment and policy gates

`config/codex-cloud-environments.json` starts with the three managed repositories disabled. Its base branch is proposed intent, not proof of readiness. Review the actual branch, repository instructions, GitHub/account access, published versus legacy environment generation, portable dependency setup, variables/secret mechanism, and checks before updating a mapping.

Use the supported [Cloud environment setup](https://learn.chatgpt.com/docs/environments/cloud-environments). Keep Linux setup separate from this Mac's Homebrew/LaunchAgent/Gateway tests. Never transfer personal CLI login files, OpenClaw private state or production map checkpoints. Map Cloud coding tasks may run fixtures/bounded tests within their exact scope; they do not inherit local production backlog execution authority. Current and legacy secrets have different lifetimes/mechanisms; use the guide for the chosen generation.

Before enabling a mapping, one narrow pilot must prove exact CLI → environment → intended UI task identity, actual base, direct user follow-up on that same task, result/diff/PR reconciliation and effective remote model/effort/speed policy. The current CLI cannot enforce the requested remote model. Merely changing `enabled` or `model_control` flags does not bypass this technical gate. A user decision about accepting the service-controlled model, or a new supported verifiable control, is required; any accepted limitation must be implemented and documented explicitly.

## Durable state and recovery

The private `runtime/coordinator/state/codex-tasks.sqlite3` stores tasks, observations and submission leases. Prompts/raw outputs/diffs live under `runtime/coordinator/logs/codex-cloud/UUID/`, with private permissions. ACTIVE.md is a readable index, not concurrency authority.

- A stable repository/scope key prevents duplicate preparation. A submission transaction moves prepared → submitting before contacting Cloud; one invocation owns the lease.
- Timeout, interrupted submission, malformed acceptance or lost response becomes `submission_unknown`. Crash recovery treats expired submitting claims as unknown. None of these states can be submitted again automatically.
- JSON list has bounded pagination. An absent task is not failed/deleted. Marker/title candidates are hints only because list does not expose the full prompt; inspect exact identity in UI before resolving ambiguity.
- Preserve raw remote status and update time. Unknown values remain unknown, late observations do not overwrite newer work, and user follow-up reopens review after earlier verification.
- Ready/applied means review is needed. Independently verify GitHub repository/PR/head/base/diff/checks. Never apply a diff to Paul's current checkout or mark a task verified from its summary/exit code.
- Four-hour reconciliation is bounded and quiet on unchanged work. Cloud runs while the Mac sleeps; local monitoring catches up afterward. Map owner callback proof does not establish Cloud event delivery.

Automatic apply, cancellation, follow-up messages, account-wide task adoption and merge/publication beyond existing authority are intentionally absent from this adapter. The implementation plan records the remaining pilot gates.

To resolve an ambiguous submission after an actual human UI review, save a private JSON evidence file containing `local_id`, `repository`, `environment_id`, `prompt_digest`, `remote_url`, `source: "human_ui_review"`, and `reviewed_at`. Each identity field must match the prepared intent and the reviewed remote task. Run `codex-cloud.py bind LOCAL_ID --evidence /absolute/private/evidence.json`; the adapter independently observes the remote ID in the intended environment before binding. A title match alone remains insufficient. Never fabricate human review evidence.

The first pilot is paused for Paul's decision on service-selected Cloud models. The current strict policy deliberately blocks submission even if registry flags are manually changed. Once that decision is recorded, implement an explicit controlled pilot path: reviewed environment/setup/account/base evidence permits one pilot before `readiness=ready`, while routine dispatch still requires the completed pilot. Do not remove the model gate or require a completed pilot as a prerequisite to starting that same pilot. No environment was changed and no Cloud task was submitted during the local cutover.
