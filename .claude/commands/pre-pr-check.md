---
description: Run lint and tests, summarize impact, and fill the PR template
---
Pre-PR check. Extra context: $ARGUMENTS

1. Inspect the diff against the base branch (`git diff`, `git log`).
2. Run the project's lint/format/type checks and the test suite. Report actual results; never claim tests passed unless you ran them.
3. Review against `fastapi-blueprint` chapter 14 (red flags, Definition of Done): money as Decimal, single commit, no secrets in logs, i18n keys, permissions and data scoping on lists/exports, migrations reversible.
4. Summarize impact: endpoints, DB/migrations, config/env, background jobs, risks, rollback.
5. Fill the PR title, branch/commit naming and description using the template in `fastapi-blueprint` chapter 12 (git standard). List what was not tested.
