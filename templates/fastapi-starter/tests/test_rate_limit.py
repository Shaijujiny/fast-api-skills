from app.core import rate_limit
from app.core.config import get_settings
from tests.conftest import PASSWORD, login, make_user


def test_login_rate_limited_with_retry_after(client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "login_rate_limit", 3)
    monkeypatch.setattr(get_settings(), "login_max_failed_attempts", 100)
    for _ in range(3):
        assert login(client, "x@example.com", "whatever1").status_code == 401
    r = login(client, "x@example.com", "whatever1")
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED_429"
    assert int(r.headers["Retry-After"]) >= 1
    # key is IP + email: another email is unaffected
    assert login(client, "y@example.com", "whatever1").status_code == 401


def test_refresh_rate_limited(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "refresh_rate_limit", 2)
    for _ in range(2):
        assert client.post("/auth/refresh", json={"refreshToken": "bad"}).status_code == 401
    r = client.post("/auth/refresh", json={"refreshToken": "bad"})
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_lockout_after_failed_attempts(client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "login_max_failed_attempts", 3)
    make_user(db, "a@example.com")
    unknown = login(client, "ghost@example.com", "whatever1")
    for _ in range(3):
        wrong = login(client, "a@example.com", "wrong-password")
    assert wrong.status_code == 401
    # locked: even the right password is refused, with the exact same response as an unknown user
    locked = login(client, "a@example.com", PASSWORD)
    assert locked.status_code == 401
    assert locked.json()["message"] == unknown.json()["message"] and locked.json()["code"] == unknown.json()["code"]


def test_lockout_expires_and_success_resets_counter(client, db, monkeypatch):
    from datetime import timedelta

    from app.utils import utc_now

    monkeypatch.setattr(get_settings(), "login_max_failed_attempts", 2)
    user = make_user(db, "a@example.com")
    login(client, "a@example.com", "wrong-password")
    assert login(client, "a@example.com", PASSWORD).status_code == 200  # counter reset
    db.refresh(user)
    assert user.failed_login_count == 0
    for _ in range(2):
        login(client, "a@example.com", "wrong-password")
    assert login(client, "a@example.com", PASSWORD).status_code == 401
    db.refresh(user)
    user.locked_until = utc_now() - timedelta(seconds=1)
    db.commit()
    assert login(client, "a@example.com", PASSWORD).status_code == 200


def test_memory_backend_window_resets(monkeypatch):
    b = rate_limit.MemoryBackend()
    assert b.hit("k", 60)[0] == 1 and b.hit("k", 60)[0] == 2
    t = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: t[0])
    b.reset()
    assert b.hit("k", 10)[0] == 1
    t[0] += 11
    assert b.hit("k", 10)[0] == 1


def test_redis_backend_with_fake_client():
    class Pipe:
        def __init__(self, store):
            self.s, self.ops = store, []

        def incr(self, k):
            self.ops.append(("incr", k))

        def expire(self, k, w, nx=False):
            self.ops.append(("expire", k, w))

        def ttl(self, k):
            self.ops.append(("ttl", k))

        def execute(self):
            k = self.ops[0][1]
            self.s[k] = self.s.get(k, 0) + 1
            return [self.s[k], True, 42]

    class Fake:
        def __init__(self):
            self.store = {}

        def pipeline(self):
            return Pipe(self.store)

    b = rate_limit.RedisBackend("redis://x", client=Fake())
    assert b.hit("a", 60) == (1, 42) and b.hit("a", 60) == (2, 42)
