# Metrics and tracing

## RED metrics (Prometheus)
```python
import time
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

REQS = Counter("http_requests_total", "Requests", ["method", "route", "status"])
LAT = Histogram("http_request_duration_seconds", "Latency", ["method", "route"],
                buckets=(.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10))
INFLIGHT = Gauge("http_requests_in_flight", "In flight")

@app.middleware("http")
async def metrics_mw(request, call_next):
    INFLIGHT.inc(); start = time.perf_counter(); status = 500
    try:
        response = await call_next(request); status = response.status_code
        return response
    finally:
        route = getattr(request.scope.get("route"), "path", "unmatched")
        REQS.labels(request.method, route, str(status)).inc()
        LAT.labels(request.method, route).observe(time.perf_counter() - start)
        INFLIGHT.dec()

app.mount("/metrics", make_asgi_app())   # restrict at proxy / internal network
```
Under gunicorn multi-process, set `PROMETHEUS_MULTIPROC_DIR` and use multiprocess collector, or scrape per-worker via OTel/agent.
Alternative: `prometheus-fastapi-instrumentator`. Label cardinality: route template only, bounded values.

## DB pool and slow queries
```python
from sqlalchemy import event
DB_SLOW = Histogram("db_query_duration_seconds", "Query time", buckets=(.005,.01,.05,.1,.5,1,5))
POOL_OUT = Gauge("db_pool_checked_out", "Checked-out connections")

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _start(conn, cur, stmt, params, ctx, many): conn.info["t0"] = time.perf_counter()

@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _end(conn, cur, stmt, params, ctx, many):
    dt = time.perf_counter() - conn.info.pop("t0", time.perf_counter())
    DB_SLOW.observe(dt)
    if dt > 0.5:
        log.warning("slow_query", extra={"extra_fields": {"duration_ms": round(dt*1000), "stmt": stmt[:200]}})  # no params
```
Pool gauge: `POOL_OUT.set(engine.pool.checkedout())` in a periodic task or collector. Alert when checked-out near `pool_size + max_overflow`.
Also track: dependency call latency/errors (httpx, Redis), queue depth, job failures, cache hit ratio.

## OpenTelemetry basics
```
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install
OTEL_SERVICE_NAME=api OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317 \
OTEL_TRACES_SAMPLER=parentbased_traceidratio OTEL_TRACES_SAMPLER_ARG=0.1 \
opentelemetry-instrument gunicorn app.main:app -k uvicorn.workers.UvicornWorker
```
Or in code: `FastAPIInstrumentor.instrument_app(app, excluded_urls="health/.*,metrics")`, `SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)`, `HTTPXClientInstrumentor().instrument()`.
- Sample (5-10% + always on errors via tail sampling in the collector). Do not put PII in span attributes.
- Add `trace_id` to logs: read `trace.get_current_span().get_span_context().trace_id` in the formatter (`format(trace_id, "032x")`).
- Custom spans only around business-significant steps: `with tracer.start_as_current_span("capture_payment"):`.
- Collector (OTel Collector) sits between app and backend; keeps exporters out of app code.
