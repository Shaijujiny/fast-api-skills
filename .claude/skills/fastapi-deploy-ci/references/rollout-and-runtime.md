# Rollout and runtime

## Health endpoints
```python
from fastapi import APIRouter, Response, status
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"], include_in_schema=False)

@router.get("/live")
async def live():
    return {"status": "ok"}          # no dependency calls

@router.get("/ready")
async def ready(response: Response, session=Depends(get_session), redis=Depends(get_redis)):
    try:
        await session.execute(text("SELECT 1"))
        await redis.ping()
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}   # no error details to callers
    return {"status": "ready"}
```
Add a short timeout (1-2s) on each check. Add `/health/startup` only if boot is slow.

## Graceful shutdown
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    app.state.ready = True
    yield
    app.state.ready = False          # readiness returns 503 first
    await engine.dispose()
    await redis.aclose()
```
- Orchestrator sends SIGTERM -> gunicorn finishes in-flight requests up to `--graceful-timeout`.
- Set orchestrator grace period > graceful-timeout (compose `stop_grace_period: 40s`, k8s `terminationGracePeriodSeconds`).
- Optional preStop sleep (5-10s) so the load balancer deregisters before workers stop.
- Background tasks/jobs must be idempotent; long jobs belong in a worker queue, not request workers.

## Zero-downtime rollout
Rolling update: `maxUnavailable: 0`, `maxSurge: 1`; new pods must pass `/health/ready` before receiving traffic.
Order: migrate (expand) -> roll app -> verify -> later contract. Blue/green or canary (5-10%) for risky releases.
Keep N and N-1 API-compatible (additive response fields, no removed fields without versioning).

## Workers and pool sizing
- CPU-bound: workers ~ cores. I/O-bound async: 2-4 workers per container; scale replicas.
- `WEB_CONCURRENCY` overrides gunicorn workers if you remove the flag from CMD.
- Total DB connections = replicas x workers x (pool_size + max_overflow); keep below ~70% of DB limit.
- Use `--max-requests 1000 --max-requests-jitter 100` to contain slow memory leaks.
- Blocking sync work in `async def` stalls the loop; use `def` endpoints or a threadpool.

## Reverse proxy and TLS
- Terminate TLS at proxy/ingress/LB (nginx, Traefik, cloud LB); redirect 80 -> 443; HSTS on.
- Pass `X-Forwarded-For/Proto/Host`; run `--proxy-headers --forwarded-allow-ips=<proxy ip/cidr>` (not `*` on public networks).
- Proxy timeouts >= app timeout (`--timeout 60`); set body size limit and rate limits at the edge.
- Do not expose the app container port publicly; only the proxy is reachable. Restrict CORS to known origins.
