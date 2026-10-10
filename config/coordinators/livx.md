# LivX responsibilities

Own paulshorey/livx only: requested implementation, open PR feedback and checks,
backend/client/admin contract compatibility and evidenced deployment failures.
Read root and affected nested AGENTS before proposing work. Use pnpm from root;
commands needing credentials use the actual app path through project-env.py.

Understand main/dev versus prod/production before reviewing a release. Preserve
the one-time prepaid Stripe Checkout Session/Payment Element invariant. Database
and contract changes belong to lib/db-deals and all affected consumers. Never
reset, baseline or seed a database. Validate affected lint/tests/builds and the
required migration/generated contract checks under project instructions.

Native iOS/Android release work requires its specific authorization and release
guides. A failed check or available build is not authority to upload, publish or
change production. Do not start dev servers merely because a heartbeat runs;
inspect existing development work and preserve the primary checkout.

Delegate authorized implementation to visible native worktree coding tasks.
Keep product/release decisions in this project's private state and final summary.
No map ingestion, Notes task ownership or unrelated repository monitoring.
