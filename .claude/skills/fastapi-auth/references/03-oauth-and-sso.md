# 03. OAuth2 / OIDC / SSO, Service Auth, Audit Logging

## OAuth2 / OIDC login (Authorization Code + PKCE)
Use `authlib` (or a vetted OIDC client); do not hand-parse ID tokens.
1. `GET /auth/sso/{provider}/login`: generate `state` and `nonce` (and PKCE verifier), store server-side or in a signed short-lived cookie, redirect to provider.
2. `GET /auth/sso/{provider}/callback`: verify `state`, exchange code, validate ID token signature via provider JWKS, `iss`, `aud`, `exp`, `nonce`.
3. Map identity by `(provider, subject)`, **not** by email alone. Link to an existing local user by email only if the provider asserts `email_verified` and the user confirms/is already logged in; otherwise account takeover risk.
4. Issue your own access/refresh pair (file 01). Do not pass provider tokens to clients.
```python
class OAuthIdentity(Base):
    __tablename__ = "oauth_identities"
    __table_args__ = (UniqueConstraint("provider", "subject"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(255))
```
- Redirect URIs: exact-match allowlist from config; never accept a `redirect_to` param without allowlist check (open redirect).
- Enterprise SSO (SAML/OIDC per tenant): store per-tenant IdP config, enforce SSO-only for those domains, JIT-provision with a default least-privilege role, map IdP groups to roles via chapter 15 role table, never trust group claims to grant super-admin.
- Provider client secrets in the secret manager; rotate periodically.

## Protecting the API as a resource server
`OAuth2PasswordBearer`/`HTTPBearer` only extracts the token; you must still verify it (file 01). For third-party IdP tokens, verify against JWKS (cache with TTL, refresh on unknown `kid`) and check `aud`/scopes.

## Service-to-service
**API keys**
- Format `prefix_<random>`; show once; store `sha256` hash + prefix (for lookup/display) + owner + scopes + `expires_at` + `last_used_at` + `revoked_at`.
- Send in `Authorization: Bearer` or `X-API-Key` header, never query string.
- Scope per key (least privilege), per-key rate limit, rotation with two active keys during overlap.
```python
async def api_key_auth(key: str = Security(APIKeyHeader(name="X-API-Key")), db=Depends(get_db)):
    row = await repo.get_active_key_by_hash(db, sha256_hex(key))
    if row is None: raise AppException(ErrorCode.TOKEN_INVALID, status_code=401)
    return row
```
**HMAC-signed requests** (webhooks, partner calls): signature over `timestamp + "." + raw_body` (+ method/path), header `X-Signature`, `X-Timestamp`; reject if timestamp older than 5 min; compare with `hmac.compare_digest`; read raw body before JSON parsing; add nonce/idempotency key to stop replay.
```python
def verify(secret: bytes, ts: str, body: bytes, sig: str) -> bool:
    if abs(time.time() - int(ts)) > 300: return False
    expected = hmac.new(secret, f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
```
Internal-only services may prefer mTLS or short-lived signed JWTs from an identity provider; avoid sharing user tokens between services.

## Audit logging of auth events
Log (structured, append-only table or log stream): `login_success`, `login_failed`, `lockout`, `logout`, `token_refresh`, `token_reuse_detected`, `password_changed`, `reset_requested`, `reset_completed`, `email_verified`, `mfa_enabled/disabled`, `mfa_failed`, `role_changed`, `api_key_created/revoked`, `sso_login`.
Fields: timestamp, event, user_id (or hashed identifier when unknown), IP, user-agent, request id, outcome, reason code. Never: passwords, tokens, OTPs, full API keys. Alert on bursts of failures, reuse detection, and logins from new locations. Retention per compliance needs.
