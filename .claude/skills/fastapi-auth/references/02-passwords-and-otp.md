# 02. Passwords, Throttling, OTP, Reset, MFA

## Hashing
Use a maintained library; never roll your own, never SHA/MD5, never encrypt reversibly.
```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
ph = PasswordHasher()   # argon2id defaults; tune to ~100-250 ms

def hash_password(p: str) -> str: return ph.hash(p)
def verify_password(h: str, p: str) -> tuple[bool, str | None]:
    try: ph.verify(h, p)
    except VerifyMismatchError: return False, None
    return True, (ph.hash(p) if ph.check_needs_rehash(h) else None)  # upgrade on login
```
bcrypt acceptable (72-byte input limit; pre-validate). Password policy: min length 10-12, max 128, check against breached/common list, no composition silliness. Run hashing in a threadpool (`run_in_threadpool`) in async routes.

## Login without leaking existence
```python
DUMMY_HASH = ph.hash("dummy-password")
user = await repo.get_by_email(email)
ok, new_hash = verify_password(user.password_hash if user else DUMMY_HASH, password)
if not (user and ok and user.status == UserStatus.ACTIVE):
    await audit.log("login_failed", email_hash=sha256(email), ip=ip)
    raise AppException(ErrorCode.INVALID_CREDENTIALS, status_code=401)
```

## Throttling and lockout
- Per IP + per account counters in Redis (`INCR` + `EXPIRE`), e.g. 5 fails / 15 min per account, 20 / 15 min per IP.
- Prefer progressive delay or temporary lock (15 min) over permanent lock (avoids DoS of victims); notify user by email on lock.
- Apply the same limits to OTP verify, reset, and token-refresh endpoints. Respond `429` with `Retry-After`.
- Behind a proxy, take client IP only from trusted proxy headers.

## One-time tokens (verify email, reset, magic link)
Rules: `secrets.token_urlsafe(32)`; store only `sha256(token)`; store `purpose`, `user_id`, `expires_at`, `used_at`; single-use; short expiry (reset 15-60 min, magic link 10-15 min, verify 24 h); a new token invalidates older ones for the same purpose.
```python
class OneTimeToken(Base):
    __tablename__ = "one_time_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]

async def consume(db, raw: str, purpose: str) -> OneTimeToken:
    row = (await db.execute(select(OneTimeToken).where(
        OneTimeToken.token_hash == sha256_hex(raw), OneTimeToken.purpose == purpose,
        OneTimeToken.used_at.is_(None), OneTimeToken.expires_at > utcnow()
    ).with_for_update())).scalar_one_or_none()
    if row is None: raise AppException(ErrorCode.TOKEN_INVALID, status_code=400)
    row.used_at = utcnow()
    return row
```
Reset flow: `POST /auth/forgot` (always 200, send email if exists) -> `POST /auth/reset` {token, new_password}; on success set hash, bump session version, revoke refresh, audit, email "password changed". Never auto-login from a reset link without re-auth policy decision. Links go to the app's URL from config, not from the request `Host` header.

## Numeric OTP (SMS/email)
6 digits via `secrets.randbelow`, hashed (HMAC with server key) at rest, TTL 5-10 min, max 3-5 attempts then invalidate, resend cooldown (e.g. 60 s) and daily cap, compare constant-time. Never return the OTP in the API response outside local/dev.

## MFA basics
- TOTP (RFC 6238, `pyotp`): secret encrypted at rest, accept +/-1 step, block code replay within the window, show setup QR once.
- Issue 8-10 single-use recovery codes, stored hashed.
- Login with MFA: step 1 returns a short-lived (5 min) `mfa_pending` token (`type: mfa`, not usable as access); step 2 verifies code and issues the real pair.
- Require re-auth/MFA for sensitive actions (change email, password, payout details).
- Disabling or resetting MFA is itself audited and invalidates sessions.
