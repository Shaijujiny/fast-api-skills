import json

from app.core.i18n import LOCALES_DIR


def test_health_ok_with_envelope_and_request_id(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "abc123"
    body = r.json()
    assert body["status"] == "1" and body["statusCode"] == 200 and body["code"] == "SUCCESS"
    assert body["data"] == {"database": "ok"}


def test_unknown_route_uses_error_envelope(client):
    r = client.get("/nope")
    assert r.status_code == 404
    assert r.json()["status"] == "0" and r.json()["code"] == "NOT_FOUND_404"


def test_locale_files_have_matching_keys():
    catalogs = {p.stem: set(json.loads(p.read_text(encoding="utf-8"))) for p in LOCALES_DIR.glob("*.json")}
    assert len(catalogs) >= 2
    base = catalogs["en"]
    for lang, keys in catalogs.items():
        assert keys == base, f"{lang} differs from en: {keys ^ base}"
