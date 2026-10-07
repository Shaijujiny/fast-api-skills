"""One test per global handler (blueprint ch. 18). Uses a throwaway app with routes that raise on purpose."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppException, ErrorCode
from app.main import create_app

ENVELOPE_KEYS = {"status", "statusCode", "code", "message", "data", "requestId"}


@pytest.fixture()
def client():
    app = create_app()

    @app.get("/boom/app")
    def _app():
        raise AppException(422, ErrorCode.BUSINESS_422_EMAIL_EXISTS, "custom message", data={"field": "email"})

    @app.get("/boom/integrity")
    def _integrity():
        raise IntegrityError("INSERT INTO users ...", {}, Exception("UNIQUE constraint failed: users.email"))

    @app.get("/boom/rate")
    def _rate():
        raise HTTPException(429, "slow down", headers={"Retry-After": "30"})

    @app.get("/boom/large")
    def _large():
        raise HTTPException(413)

    @app.get("/boom/unavailable")
    def _unavailable():
        raise HTTPException(503)

    @app.get("/boom/unhandled")
    def _unhandled():
        raise RuntimeError("secret internal detail: password=hunter2")

    # raise_server_exceptions=False so the 500 handler's response is returned instead of re-raised.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _assert_error(r, status, code):
    body = r.json()
    assert r.status_code == status
    assert set(body) == ENVELOPE_KEYS
    assert body["status"] == "0" and body["statusCode"] == status and body["code"] == code
    assert body["requestId"] == r.headers["X-Request-ID"]
    return body


def test_app_exception_keeps_code_message_and_data(client):
    body = _assert_error(client.get("/boom/app"), 422, "BUSINESS_422_EMAIL_EXISTS")
    assert body["message"] == "custom message" and body["data"] == {"field": "email"}


def test_unknown_route_404(client):
    _assert_error(client.get("/nope"), 404, "NOT_FOUND_404")


def test_wrong_method_405_keeps_allow_header(client):
    r = client.post("/boom/app")
    _assert_error(r, 405, "METHOD_NOT_ALLOWED_405")
    assert "GET" in r.headers["Allow"]


def test_validation_422_is_enveloped(client):
    _assert_error(client.get("/boom/app", params={}), 422, "BUSINESS_422_EMAIL_EXISTS")  # sanity: AppException path
    r = client.post("/auth/login", json={})
    _assert_error(r, 422, "VALIDATION_422")


def test_integrity_error_is_409_and_hides_sql(client):
    r = client.get("/boom/integrity")
    body = _assert_error(r, 409, "CONFLICT_409")
    assert "UNIQUE" not in r.text and "INSERT" not in r.text and body["message"]


def test_rate_limit_429_keeps_retry_after(client):
    r = client.get("/boom/rate")
    _assert_error(r, 429, "RATE_LIMITED_429")
    assert r.headers["Retry-After"] == "30"


def test_413_and_503_mapped(client):
    _assert_error(client.get("/boom/large"), 413, "PAYLOAD_TOO_LARGE_413")
    _assert_error(client.get("/boom/unavailable"), 503, "SERVICE_UNAVAILABLE_503")


def test_unhandled_exception_500_leaks_nothing(client):
    r = client.get("/boom/unhandled")
    body = _assert_error(r, 500, "SYSTEM_500")
    assert "hunter2" not in r.text and "Traceback" not in r.text and "RuntimeError" not in r.text
    assert body["message"] == "Something went wrong"


def test_error_message_is_localized(client):
    r = client.get("/nope", headers={"Accept-Language": "ar"})
    assert r.status_code == 404 and r.json()["message"] != "Resource not found"


def test_client_request_id_is_echoed(client):
    r = client.get("/nope", headers={"X-Request-ID": "abc123"})
    assert r.json()["requestId"] == "abc123" and r.headers["X-Request-ID"] == "abc123"
