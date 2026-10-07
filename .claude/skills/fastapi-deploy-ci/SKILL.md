---
name: fastapi-deploy-ci
description: Containerize, configure, migrate, ship and roll back FastAPI services - Dockerfile, docker-compose, GitHub Actions / GitLab CI, pre-commit, Alembic in deploy, health/readiness, zero-downtime rollout, graceful shutdown, worker sizing, TLS, staging vs prod, release checklist. Use when adding or changing CI/CD, Docker, deploy config, env/secrets handling or release process of a FastAPI backend.
---

# FastAPI Deploy and CI

FastAPI backends only. Standards: [../fastapi-blueprint](../fastapi-blueprint/SKILL.md) - ch.7 DB/migrations
([07](../fastapi-blueprint/references/07-database-transactions-concurrency.md)), ch.9 performance/observability
([09](../fastapi-blueprint/references/09-performance-and-observability.md)), ch.12 Git
([12](../fastapi-blueprint/references/12-git-standard.md)). Logging/metrics: [../fastapi-observability](../fastapi-observability/SKILL.md).

## Templates (copy, then adjust `app.main:app`, python version, requirements files)

| File | Purpose |
|---|---|
| `templates/Dockerfile` | Multi-stage, non-root, gunicorn + uvicorn workers, healthcheck |
| `templates/.dockerignore` | Keeps secrets, tests, VCS out of the image |
| `templates/docker-compose.yml` | api + migrate job + Postgres (MySQL alt) + Redis, healthchecks |
| `templates/.github/workflows/github-actions-ci.yml` | ruff, pytest + DB/Redis services, migration check, image build |
| `templates/gitlab-ci.yml` | Same pipeline for GitLab |
| `templates/.pre-commit-config.yaml` | ruff, format, secret scan, hygiene |
| `templates/.env.example` | Variable names only, no real values |

## Rules

1. **One image, many environments.** Build once per commit (tag = git SHA), promote the same image
   staging -> prod. Only env vars differ. Never tag deploys `latest` only.
2. **Config** via `pydantic-settings` (`BaseSettings`), validated at startup; fail fast on missing vars.
   Secrets come from the platform secret store or CI masked variables - never in the image, repo, compose
   file, or logs. Commit `.env.example` only. See `references/config-and-secrets.md`.
3. **Migrations** run as a separate step *before* new app version starts (`alembic upgrade head` job),
   never from app startup in multi-replica setups. Use two-step (expand/contract) backward-compatible
   changes so old and new code both work during rollout. See `references/migrations-in-deploy.md`.
4. **Health**: `/health/live` (process up, no deps) and `/health/ready` (DB + Redis reachable). Liveness
   must not touch dependencies. Snippet in `references/rollout-and-runtime.md`.
5. **Graceful shutdown**: exec-form `CMD` so PID 1 gets SIGTERM; gunicorn `--graceful-timeout` < orchestrator
   kill timeout; readiness fails first, then drain. Dispose DB engine in lifespan shutdown.
6. **Workers**: containers = CPU limit based. Start with `workers = min(2*cores+1, 4)` per container for
   I/O-bound apps; scale replicas, not workers. Check `pool_size * workers * replicas < DB max_connections`.
7. **Proxy/TLS** terminated at the reverse proxy/ingress; run uvicorn with `--proxy-headers` and a trusted
   `--forwarded-allow-ips`. Details in `references/rollout-and-runtime.md`.
8. **CI gates (must pass to merge)**: `ruff check`, `ruff format --check`, pytest with coverage threshold,
   single Alembic head, upgrade/downgrade/upgrade, `alembic check` (no model drift), image build.
9. **Staging mirrors prod** (same image, same DB engine/version, same migrations path); prod deploys are
   manual-approval or tag-triggered. Differences listed in `references/environments-and-release.md`.
10. **Release**: follow the checklist and rollback plan in `references/environments-and-release.md`.

## Workflow

1. Copy the templates you need; replace placeholders.
2. Run `pre-commit install` locally; CI runs the same checks.
3. `docker compose up --build` to verify migrate -> api -> healthy locally.
4. Open PR per ch.12; CI green; deploy to staging; smoke test `/health/ready`; promote to prod.

## Do not

- Run migrations in the Docker `CMD` with multiple replicas; bake `.env` into images; run as root;
  use `--reload` in prod; put DB credentials in compose files; drop/rename columns in the same release
  that stops using them.
