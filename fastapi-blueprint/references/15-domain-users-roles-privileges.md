# 15. Users, Roles & Privileges (RBAC pattern)

A reusable access-control pattern for any FastAPI app. Examples span portals: fintech (customer/accounts), assessment (candidate/exam/evaluator), interview (candidate/interviewer/panel), transport (driver/rider/dispatcher). Adapt names; keep the structure.

## 15.1 Users, roles, status

- Use **one `users` table** for every kind of person. Distinguish them with a `role` enum, not separate tables per login type.
- Columns: `id` (UUID), `email` (unique, normalized), `password_hash`, `role`, `status`, `organization_id` (tenant, nullable for platform staff), `last_login_at`, `created_at`, `updated_at`.
- Profile data that differs per kind (candidate résumé, driver licence, customer KYC) goes in a **linked profile table** keyed by `user_id`, not in extra nullable columns on `users`.
- `role` is a `str` Enum. Examples: fintech `SUPER_ADMIN, ADMIN, SUPPORT, CUSTOMER`; assessment `ADMIN, EVALUATOR, PROCTOR, CANDIDATE`; interview `ADMIN, RECRUITER, INTERVIEWER, CANDIDATE`; transport `ADMIN, DISPATCHER, DRIVER, RIDER`.
- `status` is a `str` Enum: `PENDING`, `ACTIVE`, `INACTIVE`, `LOCKED`, `DELETED` (soft delete). Store enums as strings, never ints.

## 15.2 Roles and permissions model

- A **role maps to a set of permissions**. A permission is `(resource, action)` with flags such as `view`, `create`, `edit`, `delete`, `export`.
- Tables: `roles` (id, name, is_system), `permissions` (id, resource, action), `role_permissions` (role_id, permission_id). Optionally `user_permission_overrides` for rare per-user exceptions.
- Keep `resource` names as a code-level enum (`CUSTOMER`, `ACCOUNT`, `EXAM`, `EVALUATION`, `INTERVIEW_PANEL`, `TRIP`) so typos fail at import time, not in production.
- Seed system roles and permissions through an idempotent migration or seed script; never rely on manual inserts.
- Prefer roles over per-user permissions. If you need many overrides, you need a new role.
- Examples: assessment `EVALUATOR` has `EVALUATION: view, edit` and `EXAM: view`; transport `DISPATCHER` has `TRIP: view, create, edit` but not `export`.

## 15.3 Permissions in the JWT vs looked up

| Approach | Pros | Cons |
|---|---|---|
| Permissions embedded in the JWT | No DB or cache hit per request; fast | Stale until the token expires; revocation is slow; token grows with permissions |
| Role in JWT, permissions looked up (cached) | Small token; permission changes apply within the cache TTL | One cache/DB read per request |
| Everything looked up per request | Always current; instant revocation | Highest load |

- Recommended default: put `sub`, `role`, `organization_id`, and a token `jti` in the JWT; resolve permissions from a cache (short TTL, for example 60 seconds) backed by the DB.
- Use short access tokens (5 to 15 minutes) plus refresh tokens. Permission or role changes take effect at the next refresh at the latest.
- For immediate revocation (user locked, role changed, logout), bump a per-user `token_version` or add the `jti` to a deny-list in the cache, and check it on each request.
- Always re-check `status == ACTIVE` against current data for sensitive actions, not only from the token.

## 15.4 Enforcement: `require_permission(resource, action)`

Enforce in a FastAPI dependency so every route declares what it needs and the check is not repeated inside services.

```python
def require_permission(resource: Resource, action: Action):
    async def checker(
        user: CurrentUser = Depends(get_current_user),
        perms: PermissionResolver = Depends(get_permission_resolver),
    ) -> CurrentUser:
        if user.status != UserStatus.ACTIVE:
            raise AppException(403, ErrorCode.USER_INACTIVE, "errors.user_inactive")
        if user.role != Role.SUPER_ADMIN and not await perms.has(user, resource, action):
            raise AppException(403, ErrorCode.FORBIDDEN, "errors.forbidden")
        return user
    return checker


@router.get("/exams/{exam_id}/results", tags=["Exams"])
async def exam_results(
    exam_id: UUID,
    user: CurrentUser = Depends(require_permission(Resource.EVALUATION, Action.VIEW)),
    service: ExamService = Depends(get_exam_service),
) -> ApiResponse[ExamResultsResponse]:
    return await service.results(exam_id, user)
```

- Every route has a permission dependency unless it is on an explicit public allowlist (login, health, password reset).
- Use `export` as its own action: viewing a list and downloading it are different privileges.
- Return 401 for missing/invalid tokens and 403 for authenticated-but-not-allowed. Do not leak whether a resource exists to users who lack access (prefer 404 for out-of-scope objects).
- A permission check answers "may this role do this kind of thing"; it does **not** answer "may this user touch this record". That is data scoping (15.5).

## 15.5 Data scoping (tenant, ownership, assignment)

Scoping limits **which rows** a user can see or change. Apply it in **every** list, detail, update, export, and report path. A permission that passed never replaces a scope check.

- **Tenant/organization:** filter by `organization_id` taken from the authenticated user. Example: a fintech `ADMIN` of bank A never sees bank B's customers.
- **Ownership:** the record belongs to the user. Example: a rider sees only their trips; a candidate sees only their own attempts.
- **Assignment:** the record is assigned to the user. Examples: an evaluator sees only candidates assigned to them; an interviewer sees only interviews where they sit on the panel; a dispatcher sees trips in their assigned zones.
- Build scoping once, as a reusable function that returns a filter or a modified query (`scope_query(query, user, Model)`), and call it from repositories. Do not hand-write filters per endpoint.
- **Never trust the client for scope.** `organization_id`, `owner_id`, `assigned_to` come from the token/user record, never from query params or the body. Client-supplied filters may only narrow within the scope, never widen it.
- Detail and update routes check the scope too: load the row with the scope filter applied, and return 404 if it is outside scope (prevents IDOR).
- Exports, reports, dashboards, search, autocomplete, and scheduled emails are the usual places scope is forgotten. Review them explicitly.
- Scope checks also apply on write references: when a body contains `customer_id` or `panel_id`, verify the referenced entity is within the user's scope.

## 15.6 Field-level masking and restricted fields

- Some fields are visible only to some roles. Examples: customer national id and full account number (show last 4 unless `CUSTOMER_PII: view`), evaluator scores hidden from candidates until published, interviewer private notes hidden from the candidate, driver payout details hidden from riders.
- Implement masking in the **response schema layer** (an `Annotated` type or a role-aware serializer), not ad hoc inside services.
- Use a distinct response schema per audience when the shapes differ (`CandidateExamResult` vs `EvaluatorExamResult`) rather than one schema with many conditionals.
- Restricted fields in **writes**: reject, do not silently ignore, attempts to set fields the role may not edit (`role`, `status`, `organization_id`, `is_superuser`, scores).
- Masking applies equally to exports, logs, and error messages.
- Store sensitive values encrypted at rest; mask at the output boundary.

## 15.7 Super-admin handling

- A `SUPER_ADMIN` role bypasses permission flags, but **not** the active-status check and not audit logging.
- Keep super-admins few, platform-level (no tenant), and created by seed/CLI, never through the public API.
- Only a super-admin can create, promote, or demote another super-admin. Nobody can change their own role.
- Do not let a tenant admin grant permissions they do not hold themselves (no privilege escalation).
- Do not allow deleting or deactivating the last active super-admin.
- Audit-log every privileged action: actor, target, before/after, timestamp, request id.

## 15.8 Status rules

- Only `ACTIVE` users may authenticate and call protected routes. `PENDING`, `INACTIVE`, `LOCKED`, `DELETED` get a clear, localized error and no token.
- Status transitions are explicit (a small allowed-transition map), validated in the service under a row lock. Example: `PENDING -> ACTIVE -> LOCKED -> ACTIVE`; `DELETED` is terminal.
- Deactivating a user revokes their sessions/tokens (15.3) and unassigns or reassigns their open work (evaluations, interviews, trips).
- Soft-delete users referenced by history (transactions, evaluations, trips); never hard-delete them. Filter `DELETED` out of default queries.
- Automatic status changes (lock after repeated failed logins, dormant after inactivity) run in a scheduled job with a distributed lock and are audit-logged.
- Changing a user's status does not cascade silently to related entities or other users; make each change an explicit, separate operation.

## 15.9 Rules of thumb

1. One `users` table, a role enum, a status enum; per-kind data in profile tables.
2. Permissions are `(resource, action)`; roles own permissions; prefer roles to per-user overrides.
3. Enforce with a `require_permission(resource, action)` dependency on every non-public route.
4. Permission says what kind of action; scope says which rows. Do both, always.
5. Scope comes from the server-side user context, never from the client.
6. Scope every list, detail, update, export, report, and search path; return 404 for out-of-scope objects.
7. Mask at the schema boundary; use separate response schemas per audience when shapes differ.
8. Keep JWTs short-lived; plan revocation (version or deny-list) from day one.
9. Super-admin bypasses permissions, not status checks or auditing; no self-promotion, no last-admin removal.
10. Test authorization explicitly: for each role, an allowed case, a forbidden case, and an out-of-scope case.
