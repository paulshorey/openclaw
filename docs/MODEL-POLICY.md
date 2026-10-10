# Model policy and override inventory

Updated: 2026-10-08. Desired policy is versioned; live verification evidence is recorded separately. Never infer successful migration from this table alone.

| Role | Authority | Consumers | Desired behavior |
| --- | --- | --- | --- |
| Coordinator, scheduled launcher and visible heartbeat children | `config/agent-models.json:roles.coordinator` | `agent_policy.coordinator_patch`, `configure-agent-runtime.py`, OpenClaw main/default model entries | GPT-6.1 Sol, High, Standard; official Codex app-server, ChatGPT only |
| Direct small fixes | Coordinator role | Same coordinator turn in an isolated worktree | Same model as coordinator |
| Separate local coding | `roles.local_coding` | `local-codex.py`, invoked by `delegate-codex.sh` | Independently pinned GPT-6.1 Sol, High, Standard; CLI ChatGPT only |
| Cloud coding | `roles.cloud_coding` | `cloud_tasks.py`, `codex-cloud.py`, reviewed Cloud environment mapping | Requested GPT-6.1 Sol, High, Standard; remote control unverified; dispatch disabled |
| Map ingestion providers | Map repository configuration/runbook | Map normalization, embeddings, geocoder, matching/fusion | Independent of coordinator inference; preserve existing keys/authority |
| Map optional detached terminal summarizer | Map `codex-notify.ts`/supervisor configuration | Separate detached notification path | Existing map role, outside this migration; foreground watch performs no AI waiting |

## Every setting that can override a role

The model registry is the only executable model intent in this checkout. Templates and heartbeat prompts refer to it rather than repeating model IDs. `config/codex-runtime.json` owns explicit binaries, homes, selected versions and the coordinator subscription profile reference. It contains no tokens.

| Location | Treatment / check |
| --- | --- |
| `~/.openclaw/openclaw.json`: `agents.defaults` and `agents.entries.main` | Export explicit model primary, empty fallbacks, a strict `modelPolicy.allow` containing that model, `utilityModel=""` to disable implicit alternate utility inference, High thinking, `fastModeDefault=false`, canonical model entry `agentRuntime.id=codex`, `params.fastMode=false`; main/default heartbeat uses the same prompt and has no model/thinking override |
| Same file: `auth.order.openai` | Exactly the imported subscription profile; apply rejects an unverified credential type; no API backup |
| Same file: `models.providers.openai` | Authored custom route is a review blocker, not silently overwritten |
| Same file: Codex `appServer` | Agent home, API inference env removed, managed binary, forced ChatGPT; no service-tier override or cyber model escalation; custom command/transport requires review |
| Same file: subagent/other agent/utility model overrides | Review when adding agents or changing role inheritance; the current deployment has main only; do not silently redefine unrelated agent roles |
| Saved OpenClaw conversations | Model/runtime/thinking/Fast pins can beat new defaults. The checker audits all main sessions without editing them. `coordinator-sessions.py` previews legacy Fireworks pins; explicit `--apply` clears their model/runtime/thinking/Fast pins through guarded `sessions.patchMany` batches, retaining private metadata backups and all history. Other deliberate pins require supported model/thinking/speed controls or an identified new conversation |
| Agent-scoped Codex home | `~/.openclaw/agents/main/agent/codex-home` (verify resolved placement through plugin diagnostics); OpenClaw bridges profile tokens in memory; personal CLI auth is not automatically read |
| Personal CLI home/config | Explicit `cli_home` in runtime config; current `~/.codex/config.toml` uses GPT-6.1 Sol, XHigh, Standard. Wrapper supplies model/High/provider/forced ChatGPT/Standard after project env loads; personal defaults stay untouched |
| CLI project `.codex/config.toml`, profiles, requirements | CLI arguments override role fields; requirements can reject requested policy and must be reported, never bypassed. Launch checks reject authored OpenAI provider or ChatGPT base routes in the explicit personal home and relevant project config layers. Review provider definitions and workspace restrictions before upgrades |
| Environment | Remove `OPENAI_API_KEY`, `CODEX_API_KEY` and OpenAI route overrides at actual Codex boundary, including keys reintroduced by project-env. Preserve project provider credentials such as map Fireworks |
| Cloud UI/account/environment generation | Local CLI model flags do not configure the remote model. Exact task/UI/model evidence and user policy decision are required before enabling dispatch |
| Historical plan / old transcripts | Historical references are evidence, not active model sources; never rewrite private history to hide the migration |

## Changing only the coordinator model

1. Edit only `roles.coordinator` in `config/agent-models.json`. Keep the local/Cloud roles unchanged.
2. Run `scripts/agent-policy.py`, the offline test suite and `scripts/configure.sh --dry-run`. Verify account/model availability and selected plugin compatibility. `--validate` asks OpenClaw to validate without applying.
3. Reconcile active turns and durable map/Cloud/local jobs; inspect saved session pins using supported controls. Review the concrete patch, then `scripts/configure.sh --apply`. This command deploys and applies but does not install/start the service.
4. Intentionally restart when needed and verify a new native coordinator turn plus an independent local coding invocation. Reprove map callbacks after a restart; do not borrow old receipts.
5. Run `scripts/agent-policy.py --check`, update this log and the dated private evidence. Any unknown override or unsupported setting remains a blocker. Confirm local and Cloud settings are unchanged.

## Selected versions and compatibility

- OpenClaw / `@openclaw/codex`: 2026.9.9. The plugin's peer/API compatibility requires this host version. Its release notes explicitly add the requested 6.1 catalog support.
- Managed coordinator app-server: 0.160.0, selected by the plugin. Leave `appServer.command` unset.
- Independent local/Cloud CLI: 0.160.0 at the explicit versioned path in `config/codex-runtime.json`. It shares the user's CLI auth home, not the coordinator home.
- `service_tier="default"` and `features.fast_mode=false` are the selected CLI Standard controls; OpenClaw sends its own Standard run control. Login/version checks use the exact guarded launch context.
- Refresh compatibility on version/path/account/environment changes. Do not assume PATH, desktop-managed `current` or a remote Cloud generation follows this policy automatically.

## Change log

| Date | Change | Files / live paths | Verification / rollback |
| --- | --- | --- | --- |
| 2026-10-08 | Cut over coordinator Fireworks → official Codex app-server; independently pin local coding to GPT-6.1 Sol, High, Standard | Registry/runtime config, policy/exporter, guarded wrapper, routing templates, README; generated paths above | OpenClaw/plugin 2026.9.9, CLI 0.160.0; supported auth-only ChatGPT import; native coordinator/resume/direct coding and separate local coding passed. `agent-policy.py --check` reports no drift or differing saved session pins. Private full/config/template backups retained; no API/Fireworks fallback |
| 2026-10-08 | Clear 258 legacy Fireworks conversation pins; disable implicit alternate utility model and provider fallback | Scoped OpenClaw main/default config; `coordinator-sessions.py`; supported `sessions.patchMany` | 258 successful guarded resets, zero failures; history preserved. Private before/batch evidence under `~/Library/Application Support/OpenClaw Backups/codex-coordinator/session-reset-20261008T235528492498Z/` |
| 2026-10-08 | Validate native Gateway callbacks and fresh child discovery; enforce complete heartbeat launch receipts | Heartbeat prompt, `heartbeat-receipt.py`, UI config main/default prompt | Root and fresh visible child harmless map preflights automatically resumed their owners and passed alternate receipt checks under Gateway PID 20912. Evidence in ignored `runtime/coordinator/logs/codex-cutover/` and `state/codex-cutover/`; no production import launched |
| 2026-10-08 | Correct Cloud assumptions | Adapter/Cloud runbook/implementation plan | 0.160.0 source verifies stdin prompt and pending status exit 1. No remote model selector; no Cloud write/pilot yet |

Implementation commit: uncommitted on `codex-coordinator`; fill with the actual commit when committed. See `docs/CODEX-CLOUD.md` for Cloud gates and the implementation plan for rollout evidence.
