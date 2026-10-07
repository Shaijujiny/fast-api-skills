# Environments, release checklist, rollback

## Staging vs prod
| Aspect | Staging | Prod |
|---|---|---|
| Image | Same SHA as prod candidate | Promoted from staging |
| Trigger | Auto on merge to main | Manual approval or release tag |
| DB | Same engine/version, masked or synthetic data | Real data, backups, PITR |
| Secrets | Separate set | Separate, restricted access |
| Debug/docs | Docs on | Docs off or protected |
| Replicas/limits | Smaller | Sized by load; min 2 replicas |
| Log level | INFO/DEBUG | INFO (WARNING for noisy libs) |
Never copy raw prod PII to staging.

## Release checklist
- [ ] PR merged, CI green (lint, tests, migration check, image built, scan clean)
- [ ] Migrations reviewed: backward compatible, lock-safe, backup taken if data-changing
- [ ] New env vars/secrets added in target environment BEFORE deploy
- [ ] Deployed to staging; `/health/ready` OK; smoke tests (login, main read/write path) pass
- [ ] Changelog/release notes and version tag created (see blueprint ch.12)
- [ ] Alerts and dashboards open; on-call aware of release window
- [ ] Prod: migrate job succeeds -> rolling deploy -> readiness green on all replicas
- [ ] Post-deploy: error rate, p95 latency, DB connections, queue depth normal for 15-30 min
- [ ] Mark release done; schedule contract migration for a later release

## Rollback plan
1. Trigger: error rate/latency SLO breach, failing readiness, or broken critical flow after deploy.
2. Redeploy previous image SHA (keep last N images; never delete them immediately).
3. Schema: expand migrations stay in place (compatible with old code). Do NOT downgrade unless the
   migration is proven reversible and data-safe; otherwise ship a roll-forward fix.
4. Feature flags: disable the new feature instead of redeploying when possible.
5. Verify health, error rate, key flows; announce; open an incident note and a follow-up fix PR.
6. Hotfix path: branch from the release tag, minimal fix, same CI gates, deploy via same pipeline.
