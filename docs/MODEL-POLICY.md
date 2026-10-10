# Model policy and override inventory

Updated 2026-10-10. config/agent-models.json is the only executable model intent in
this checkout. No model IDs belong in coordinator or coding launch prompts.

| Role | Authority | Consumers | Initial request |
| --- | --- | --- | --- |
| Scheduled coordinator | roles.coordinator | native_coordinator.schedule_plan → native automation_update | GPT-6.1 Sol, High, Standard, ChatGPT account |
| Separate coding task | roles.coding | native_coordinator.claim_task/dispatch_plan → native create_thread | Independently GPT-6.1 Sol, High, Standard, ChatGPT account |
| Map pipeline providers | Map repository's own config and runbook | Normalization, geocoding, embeddings, matching/fusion | Independent of coordinator model and account |

The coordinator model can change without changing coding. Future tasks receive
the coding role's explicit model/thinking arguments; existing tasks retain their
own settings. The toolkit validates subscription/no-fallback intent but does not
force or prove the app's authentication and speed through a Python helper.

## Every setting that matters

| Location | Authority or override and verification |
| --- | --- |
| config/agent-models.json | Desired coordinator/coding model, reasoning, Standard speed and ChatGPT authentication. Two roles are independent. |
| config/projects.json | Schedule cadence and reviewed checkout/path, no model override. |
| scripts/native_coordinator.py | schedule_plan and dispatch_plan consume the respective roles. No fixed model IDs. |
| Native registered automation | Persisted model/reasoning, local project target, prompt, cadence and status can drift from registry. schedule-audit compares every managed field. IDs are private runtime/native/PROJECT/schedule.json. |
| Native child task | Explicit create_thread model/thinking overrides project/app defaults for new tasks. Read the actual task result/history after creation; a pending client ID is not a ready task ID. |
| Existing desktop tasks | Human model/speed changes and task settings remain local to that task. A registry edit does not migrate existing tasks. Do not silently reset unrelated human choices. |
| Desktop account and Fast/Standard UI | Must be reviewed in the app. Current native create/update tool arguments expose model/reasoning but no speed or auth selector. An automation TOML cannot prove these controls. |
| Personal/user/project Codex config and requirements | Can affect tools, permissions, providers, speed and model availability. Inspect authored overrides without printing tokens. Do not bypass administrator requirements. The user's CLI defaults are not rewritten here. |
| Scheduled process environment | Native task identity comes from actual CODEX_THREAD_ID and supported tools. Do not invent pipe/identity context. Project provider credentials are used only by project commands, never to launch fallback inference. |
| Diagnostic schedules | Paused proof runs preserve their original explicit models. They are evidence, not current production consumers, and must remain paused. |
| Private historical data / Git checkpoint | Evidence only. It is not an active model source and should not be erased to hide prior behavior. |

## Change only the coordinator

1. Edit only roles.coordinator. Leave roles.coding unchanged. Confirm the requested
   model/reasoning is available for the desktop account.
2. Run the tests and doctor for each project. Generate schedule-plan for each
   registered schedule; it preserves current status and notification policy.
3. Use native automation_update with those full arguments, then schedule-audit.
   Do not edit ~/.codex/automations/*/automation.toml directly. Do not touch unrelated
   account schedules. Preserve existing tasks and healthy imports.
4. Inspect a new scheduled run's native configuration and behavior. Recheck account,
   Standard speed and project requirements. Previously running tasks keep their model.
5. Record the change, affected automation IDs and actual verification here and in
   private evidence. A missing native capability remains a blocker, never a CLI/API fallback.

Changing only coding edits roles.coding. The next dispatch-plan uses it; coordinator
schedules need no update. Verify new child model/thinking through actual native
create_thread arguments and task history. Existing children do not change.

## Change log

| Date | Change | Evidence / recovery |
| --- | --- | --- |
| 2026-10-10 | Native per-project schedules replace the previous gateway/launcher architecture; coordinator and coding roles independently consume the registry | Baseline checkpoint ff8762f on codex-coordinator. New work on codex-native-coordinators. Three actual scheduled creation/discovery pilots passed, each paused afterward; see IMPLEMENTATION.md and private receipts. Standard/auth remain app controls to review. |
