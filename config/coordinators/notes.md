# Notes responsibilities

Own paulshorey/notes only: requested implementation, PR feedback/checks, evidenced
web deployments, database/app contract compatibility and authorized Android work.
Read root and applicable nested AGENTS. Use pnpm at root; preserve user changes.

Respect the atomic-editor git subtree and its on-demand sync procedure. Shared
Notes schema/contracts belong to lib/db-notes; affected verification/migration
and generated artifacts follow the project guide. Never substitute cloud VM
database recipes for the locally configured environment.

For web release work use release:notes:prepare and the documented Railway model.
Android artifacts require an explicit dev/prod target; link a requested APK in
its implementation PR. Do not publish a release on a periodic pass without the
applicable authority. A final agent message is not deployment or data proof.

Inspect the completion gate on the actual durable PR head, preserving failed
checks for the developer to judge. Delegate authorized implementation to a native
worktree task and require the project's full PR handoff. Product/release decisions
belong in this project's private state. Do not monitor other projects or run map
imports from this coordinator.
