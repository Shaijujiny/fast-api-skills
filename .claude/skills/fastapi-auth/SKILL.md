---
name: fastapi-auth
description: "Authentication patterns for FastAPI services (Pydantic v2, SQLAlchemy 2.x): access/refresh JWTs, rotation and revocation, password hashing, login throttling, OTP/magic-link/reset flows, MFA, OAuth2/OIDC/SSO, API keys and HMAC for service-to-service, session invalidation, audit logging. Use when adding or reviewing login, tokens, passwords, OTP, SSO, API keys or auth dependencies."
---

# FastAPI Auth

Authentication = who are you. Authorization (roles/permissions/scoping) lives in `../fastapi-blueprint/references/15-domain-users-roles-privileges.md` (chapter 15); transport/secrets rules in chapter 8. This skill covers the former and hands off to `require_permission(...)` for the latter.

Reference implementation: `templates/fastapi-starter/app/core/security.py` and `templates/fastapi-starter/app/api/auth/`. Copy its shape rather than inventing a new one.

## References
- `references/01-jwt-and-sessions.md` - access/refresh tokens, rotation, revocation, cookie vs header, JWT pitfalls, session invalidation.
- `references/02-passwords-and-otp.md` - hashing, throttling/lockout, OTP, magic links, email verification, reset, MFA.
- `references/03-oauth-and-sso.md` - OAuth2/OIDC login, SSO, API keys, HMAC service auth, audit logging.

## Non-negotiables
- [ ] Hash passwords with argon2id (or bcrypt); never custom crypto, never reversible, never logged.
- [ ] Access token short (5-15 min); refresh token longer (days), rotated on every use, stored server-side hashed.
- [ ] JWT verified with a pinned algorithm list; `alg: none` rejected; `exp`, `iat`, `sub`, `jti` required.
- [ ] Minimal claims: `sub`, `jti`, `type`, `exp`, optional `sv` (session version). No PII, no secrets.
- [ ] Reset/OTP/verify tokens: random, hashed at rest, single-use, short expiry.
- [ ] Login, OTP and reset endpoints rate-limited per account and per IP.
- [ ] Same response and similar timing whether or not the account exists.
- [ ] Password/role/status change invalidates existing sessions.
- [ ] Every auth event audit-logged (no secrets in the log).
- [ ] Secrets/keys from settings (env/secret manager), never in code; support key rotation.

## Shape of the code
- `core/security.py`: hash/verify, create/decode token, token generators. No FastAPI imports, no DB.
- `api/auth/` router: thin; calls `services/auth_service.py`.
- `deps.py`: `get_current_user` (decode, check denylist/session version, load user, check active), then `require_permission` from chapter 15.
- Errors: raise `AppException(ErrorCode.INVALID_CREDENTIALS)` / `TOKEN_EXPIRED` / `TOKEN_INVALID` / `ACCOUNT_LOCKED`; response is `ApiResponse[T]`.

```python
# schemas/auth.py
class LoginRequest(BaseSchema):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)

class TokenPair(BaseSchema):
    access_token: str
    refresh_token: str | None = None   # None when delivered via httpOnly cookie
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
```

```python
# deps.py
bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    if creds is None:
        raise AppException(ErrorCode.TOKEN_INVALID, status_code=401)
    claims = decode_token(creds.credentials, expected_type="access")  # raises AppException
    if await redis.exists(f"deny:{claims.jti}"):
        raise AppException(ErrorCode.TOKEN_INVALID, status_code=401)
    user = await db.get(User, claims.sub)
    if user is None or user.status != UserStatus.ACTIVE or user.session_version != claims.sv:
        raise AppException(ErrorCode.TOKEN_INVALID, status_code=401)
    return user
```

## Error messages
- Login failure: always `INVALID_CREDENTIALS` "Invalid email or password"; never "user not found" vs "wrong password".
- Forgot-password / resend-verification: always return 200 with a generic message.
- Registration: avoid enumeration where feasible (send "already registered" email instead of 409), or accept the leak and rate-limit.
- 401 for unauthenticated/expired, 403 for authenticated-but-forbidden. Do not leak internals.

## Review checklist
- [ ] No secret/token/password in logs, exceptions, or `ApiResponse`.
- [ ] Constant-time comparison for tokens/HMAC (`hmac.compare_digest`).
- [ ] Token `type` claim checked (refresh token cannot be used as access).
- [ ] Logout revokes refresh token and denylists access `jti`.
- [ ] Tests: expired, tampered, wrong type, revoked, reused refresh, locked account, inactive user.
