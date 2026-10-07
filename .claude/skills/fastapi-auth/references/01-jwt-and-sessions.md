# 01. JWT, Refresh Tokens and Sessions

## Lifetimes
| Token | Lifetime | Storage (server) |
|---|---|---|
| Access JWT | 5-15 min | stateless (+ optional `jti` denylist) |
| Refresh | 7-30 days (sliding, with absolute cap) | DB table, **hash only** |

## Claims (minimal)
`sub` (user id), `jti`, `type` (`access`|`refresh`), `iat`, `exp`, `sv` (user session version), optional `iss`/`aud`. Permissions: either look up per request or embed a version; see chapter 15.3. No email, name, or PII.

## Create / decode
```python
def create_access_token(user_id: int, sv: int, s: Settings) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "jti": uuid4().hex, "type": "access", "sv": sv,
               "iat": now, "exp": now + timedelta(minutes=s.access_ttl_min),
               "iss": s.jwt_issuer}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256", headers={"kid": s.jwt_kid})

def decode_token(token: str, expected_type: str) -> Claims:
    try:
        data = jwt.decode(token, key_for(token), algorithms=["HS256"],  # pinned list
                          issuer=settings.jwt_issuer, leeway=30,
                          options={"require": ["exp", "iat", "sub", "jti"]})
    except jwt.ExpiredSignatureError:
        raise AppException(ErrorCode.TOKEN_EXPIRED, status_code=401)
    except jwt.PyJWTError:
        raise AppException(ErrorCode.TOKEN_INVALID, status_code=401)
    if data.get("type") != expected_type:
        raise AppException(ErrorCode.TOKEN_INVALID, status_code=401)
    return Claims.model_validate(data)
```

## Refresh rotation with reuse detection
```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    family_id: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 hex
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
```
Refresh flow: look up by `sha256(token)`; if missing/expired -> 401. If `used_at` set (reuse) -> revoke the entire family, audit `token_reuse_detected`, 401. Else mark used, issue new pair in the same family. Do it in one transaction with `SELECT ... FOR UPDATE` to stop parallel races.

## Revocation
- Logout: revoke refresh family; put access `jti` in Redis `SETEX deny:{jti} <remaining ttl> 1`.
- Logout-all / password change / role change / deactivation: bump `users.session_version` (access tokens with old `sv` die immediately) and revoke all refresh rows.
- Redis down: fail closed for sensitive routes, or accept short access TTL as the bound; decide and document.

## Header vs httpOnly cookie
- **Header (Bearer)**: simple for mobile/API clients; token must be held by the client, XSS-exposed in browsers.
- **httpOnly cookie**: safer for browsers; set `Secure`, `HttpOnly`, `SameSite=Lax|Strict`, narrow `Path` (e.g. refresh cookie only on `/auth/refresh`). Cookie auth needs CSRF protection (SameSite + CSRF token/double-submit or Origin check) on state-changing routes.
- Common split: access in memory/Bearer, refresh in httpOnly cookie.
```python
response.set_cookie("refresh_token", token, httponly=True, secure=True,
                    samesite="strict", max_age=ttl, path="/api/v1/auth")
```

## JWT pitfalls
- Pin `algorithms=[...]`; never trust the header `alg`; reject `none`. Do not mix HS/RS key use (algorithm confusion).
- Secret >= 32 random bytes from env/secret manager. Rotate with `kid`: accept old and new keys during overlap, sign with new only.
- Clock skew: small `leeway` (<= 30-60 s); NTP on servers.
- Validate `iss`/`aud` where multiple services exist.
- JWTs are signed, not encrypted: nothing sensitive inside.
- Do not store tokens in localStorage if avoidable; never put them in URLs.
- Never use one token type for another (`type` check).

## Session invalidation matrix
| Event | Action |
|---|---|
| Password change/reset | bump `session_version`, revoke all refresh |
| Role/permission change | bump `session_version` (or permission version) |
| Deactivation/ban | status check in `get_current_user` + bump |
| Logout | revoke family + denylist jti |
| MFA reset | bump + revoke all |
