# 12. Git Standard

Applies to every FastAPI service. Use whatever ticketing tool the team has; `<TICKET-ID>` below is a placeholder for its id format.

## 12.1 Branch naming

```
main                              production-ready
feature/<TICKET-ID>-<short-slug>  new behaviour
fix/<TICKET-ID>-<short-slug>      bug fix
hotfix/<TICKET-ID>-<short-slug>   urgent production fix, branched from the production branch
chore/<TICKET-ID>-<short-slug>    tooling, dependencies, refactor, docs
```

- Lower-case, hyphen-separated slug: `feature/<TICKET-ID>-exam-attempt-autosave`.
- Branch from the up-to-date integration branch the team uses (`main`, or `develop` if the team runs one).
- Keep branches short-lived. Merge or rebase the base into your branch to resolve conflicts locally, then re-run lint and tests.
- Delete the branch after merge.

## 12.2 Commit messages (Conventional Commits)

```
<type>(<optional scope>): <short description>

<optional body: the why>

<optional footer: Refs <TICKET-ID>, BREAKING CHANGE: ...>
```

| Type | Use for |
|---|---|
| `feat` | new behaviour or endpoint |
| `fix` | bug fix |
| `refactor` | internal change, no behaviour change |
| `perf` | performance improvement |
| `test` | tests only |
| `docs` | documentation only |
| `chore` | tooling, config, dependencies, housekeeping |

Examples:

```
feat(payments): add partial refund endpoint
fix(interviews): prevent double booking of the same slot
refactor(trips): extract seat availability into repository
```

Rules:

- Imperative mood, lower-case after the colon, no trailing period, subject of 72 characters or fewer.
- Add a body when the **why** isn't obvious (business rule, incident, trade-off). Wrap at about 100 characters.
- Reference the ticket in the footer (`Refs <TICKET-ID>`) or the branch name, per team convention.
- Mark breaking API changes with `!` (`feat(api)!: ...`) or a `BREAKING CHANGE:` footer.
- One logical change per commit; no `wip`, `fix`, or `update` messages. Don't mix a refactor, a formatting sweep, and a feature.

## 12.3 Pull requests

- Small PRs: a few hundred changed lines is a good size. Split unrelated work.
- Title follows Conventional Commits and includes the ticket id: `feat(payments): add partial refund endpoint [<TICKET-ID>]`.
- Use this template:

```markdown
## Summary
What changed and why; link to the ticket.

## Impact
Endpoints, modules, and consumers affected; breaking or not.

## DB / Migration
Alembic revision id, what it changes, backfill, downgrade tested (yes/no). "None" if no schema change.

## Env / Config
New or changed environment variables, feature flags, secrets to provision. Also added to `.env.example`.

## Tests run
Exact commands and results; manual checks; what was NOT tested.

## Risks
What could go wrong, blast radius, assumptions not yet verified.

## Rollback
How to revert: redeploy previous image, `alembic downgrade <rev>`, flag off.
```

## 12.4 What every functional change must include

- [ ] Code plus tests (section 10.3)
- [ ] Alembic migration **in the same PR** as the model change (see the database reference), with a working `downgrade` where feasible
- [ ] New env vars documented in `.env.example` and the PR; no real values
- [ ] Message keys added to every supported locale
- [ ] OpenAPI-visible changes (new/changed endpoints, schemas) described in the PR
- [ ] Release-notes or changelog entry if the project keeps one

## 12.5 Safety rules

- **Never** force-push to `main`, `develop`, or any shared branch, and don't rewrite history others have pulled.
- Don't use `git reset --hard`, `git clean -fd`, or `--no-verify` to get past a problem; fix the cause.
- **No secrets in git:** `.env` files with real values, credentials, keys, tokens, database dumps, `__pycache__`, `.pytest_cache`, `logs/`, `tmp/`, exported files. Keep them in `.gitignore`. If a secret is committed, rotate it immediately; deleting the commit is not enough.
- Check `git status` and `git diff --staged` before every commit; look for stray debug code and PII.
- Edit data files in their own format so the diff shows only the real change.

## 12.6 Pre-commit routine

```bash
git status
git diff --staged                 # read the diff, look for secrets/PII/debug
ruff check <changed files>
pytest <relevant tests>
git commit -m "fix(payments): reject capture of already captured payment"
```

Use `pre-commit` hooks (ruff, secret scan, large-file check) so this runs automatically.

## 12.7 Review and merge rules

- Protected branches: no direct push to `main` (or `develop`); changes arrive by pull request.
- At least one approval; for money, auth, permission-scope, or migration changes, a second approval from a senior reviewer.
- CI must pass (lint, type check, tests, security scan; see 11.14). Don't bypass required checks or use admin override to merge.
- No unresolved review threads; the author responds to or resolves every comment.
- Authors don't merge their own PR without a reviewer's approval.
- Prefer squash merge (one Conventional Commit per PR) unless the team keeps meaningful per-commit history.

## 12.8 Hotfixes and releases

- Hotfix: `hotfix/<TICKET-ID>-...` from the production branch, PR into it, then back-merge into the integration branch so the fix isn't lost.
- Release: tag the production branch with a semantic version (`v1.4.2`); apply Alembic migrations before (or as the first step of) the new version rolling out, and keep migrations backward-compatible with the previous version so rollback is safe.
- Confirm which CI/CD pipeline a branch triggers before pushing.
