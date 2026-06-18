# PLAN_refresh_token_cookie_scope_collision_20260618

## Metadata

- Plan ID: `PLAN_refresh_token_cookie_scope_collision_20260618`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-18T00:00:00Z`
- Last updated at (UTC): `2026-06-18T11:08:23Z`
- Related issue/ticket: `HANDOFF_TO_BACKEND_refresh_token_cookie_scope_collision_20260618`
- Intention plan: `n/a — driven by frontend handoff bug report`

## Goal and intent

- Goal: Fix a silent session-corruption bug where two frontend apps authenticating against the same backend domain overwrite each other's `refresh_token` cookie, causing the first app's next token refresh to produce an access token with the wrong role scope.
- Business/user intent: A user who has both the manager app and the worker app open in the same browser can use both simultaneously without one app silently degrading the other's session. Adding a third app (seller) in the future requires zero backend changes.
- Non-goals: Changing the JWT access token structure, the `Authorization: Bearer` header flow, any database schema, or any frontend code beyond the `app_scope` field value sent at sign-in.

## Scope

- In scope:
  - Rename the refresh cookie from the single shared `refresh_token` to a per-scope name `{app_scope}_refresh_token` (e.g., `manager_refresh_token`, `worker_refresh_token`).
  - Add a `scope` query parameter to `POST /api/v1/auth/refresh` so the client tells the backend which cookie to read; validate the JWT `app_scope` claim matches.
  - Validate at sign-in that the client-supplied `app_scope` is permitted for the user's actual `role_name` via a static scope-to-allowed-roles mapping — prevents a worker-role user from claiming a manager scope while allowing `admin`-role users to sign into the manager app.
  - Clear the legacy `refresh_token` cookie on every sign-in and logout (backward-compat cleanup for existing browser sessions).
  - Fix `RefreshTokenRejected.http_status` from `403` to `401` so the frontend session-expired retry flow triggers correctly on all refresh failures.
  - Remove the `app_scope == "admin"` bypass from `BackendPermissionMiddleware` — the `role_name` fallthrough already handles it correctly; the bypass is now a dead code path after the scope rename.

- Out of scope:
  - Any Alembic migration (no schema changes).
  - Changing how `role_name` is resolved or stored.
  - Any frontend code changes (the frontend `app_scope` field value change from `"admin"` → `"manager"` is a one-line frontend change communicated via this plan's clarifications, not implemented here).
  - Introducing a separate refresh endpoint path per scope (e.g., `/auth/manager/refresh`).

- Assumptions:
  - The manager frontend already sends `app_scope: "manager"` — no coordinated frontend deploy required for this field. The `SignInBody` default `"admin"` is a backend artifact; the frontend overrides it explicitly.
  - The worker frontend already sends `app_scope: "worker"` — worker sessions are unaffected beyond the one-time forced re-login on first refresh after deployment.
  - Some manager-app users have `role_name: "admin"`. These users send `app_scope: "manager"` — the validation rule must allow this via a scope-to-allowed-roles mapping (not strict equality).
  - The `"admin"` scope is reserved for a future super-admin surface. No existing frontend sends it as `app_scope`; codex must not treat it as the manager scope.
  - Existing sessions (with the old `refresh_token` cookie) will break on their first refresh after deployment, forcing re-login. This is the acceptable cost of a security fix; the legacy cookie is cleared on next sign-in.
  - `RoleNameEnum` values (`"admin"`, `"manager"`, `"worker"`, `"seller"`) are the exhaustive allowed set for `app_scope`. Any other value is rejected at sign-in with a generic 403.
  - Adding a new frontend app (e.g., `"seller"`) in the future requires only adding an entry to the scope-to-allowed-roles mapping; no other backend changes needed.

## Clarifications required

_All clarifications resolved:_

- [x] **Manager frontend sends `"manager"`** — no coordinated deploy needed; backend change is self-contained.
- [x] **`admin`-role users exist in the manager app** — strict `app_scope == role_name` would break them. Resolved by the scope-to-allowed-roles mapping in Step 2.
- [x] **Worker frontend sends `"worker"`** — no disruption beyond forced re-login on first refresh.

## Acceptance criteria

1. `POST /api/v1/auth/sign-in` with `app_scope: "manager"` for a user with `role_name: "manager"` sets `Set-Cookie: manager_refresh_token=<jwt>; HttpOnly; Secure` and does not set `refresh_token`.
2. `POST /api/v1/auth/sign-in` with `app_scope: "worker"` for a user with `role_name: "worker"` sets `Set-Cookie: worker_refresh_token=<jwt>; HttpOnly; Secure` and does not set `refresh_token`.
3. `POST /api/v1/auth/sign-in` with `app_scope: "manager"` for a user with `role_name: "admin"` succeeds and sets `manager_refresh_token` cookie — `admin`-role users are permitted in the manager scope.
4. `POST /api/v1/auth/sign-in` with `app_scope: "worker"` for a user with `role_name: "manager"` returns `403 Forbidden` — a manager-role user cannot claim worker scope.
5. `POST /api/v1/auth/sign-in` with `app_scope: "manager"` for a user with `role_name: "worker"` returns `403 Forbidden` — a worker-role user cannot claim manager scope.
6. `POST /api/v1/auth/sign-in` with `app_scope: "unknown_scope"` returns `403 Forbidden` — invalid scope values are rejected.
7. `POST /api/v1/auth/refresh?scope=manager` with `manager_refresh_token` cookie present returns `200 OK` with a valid `access_token` whose `app_scope` claim is `"manager"`.
8. `POST /api/v1/auth/refresh?scope=manager` with only a `worker_refresh_token` cookie present (no `manager_refresh_token`) returns `401 Unauthorized` with `code: "auth_refresh_rejected"`.
9. `POST /api/v1/auth/refresh?scope=manager` with a `manager_refresh_token` cookie whose JWT has `app_scope: "worker"` (tampered or wrong cookie) returns `401 Unauthorized`.
10. `POST /api/v1/auth/refresh` with no `scope` query param returns `422 Unprocessable Entity`.
11. `POST /api/v1/auth/logout` deletes the scope-specific cookie (`manager_refresh_token` or `worker_refresh_token` depending on the `app_scope` in the access token claims) AND the legacy `refresh_token` cookie.
12. `POST /api/v1/auth/sign-in` deletes the legacy `refresh_token` cookie in the response (expired/zero max_age `Set-Cookie` header).
13. All existing `RefreshTokenRejected` error responses return HTTP `401`, not `403`.
14. `BackendPermissionMiddleware` no longer contains a special case for `app_scope == "admin"`.

## Contracts and skills

### Contracts loaded

- `../../../architecture/01_architecture.md`: baseline layered architecture rules
- `../../../architecture/04_context.md`: ServiceContext shape
- `../../../architecture/05_errors.md`: error imports and raising conventions
- `../../../architecture/06_commands.md`: command structure
- `../../../architecture/09_routers.md`: router handler wiring and response helpers
- `../../../architecture/10_auth.md`: JWT strategy, cookie contract, refresh flow, blocklist rules
- `../../../architecture/18_security.md`: security rules — never reveal internal failure reason to caller
- `../../../architecture/28_roles_permissions.md`: RoleNameEnum values and how role_name reaches the JWT

### Local extensions loaded

- `../../../architecture/06_commands_local.md`: `maybe_begin` session-call pattern (not directly used here but governs adjacent auth commands)

### File read intent — pattern vs. relational

Permitted reads (understanding what exists):
- `routers/api_v1/auth.py` — to understand current cookie-set, cookie-delete, and refresh request shape
- `services/commands/auth/sign_in_user.py` — to understand where `app_scope` is passed into `build_auth_response` and where `role_name` is available for validation
- `services/commands/auth/refresh_token.py` — to understand the current decode-and-reissue flow and where to insert scope validation
- `services/commands/auth/logout_user.py` — to confirm it does not read the cookie directly (cookie is passed in via `incoming_data` from the router)
- `errors/permissions.py` — to confirm `RefreshTokenRejected` structure and inheritance chain
- `routers/middleware/backend_permission.py` — to confirm exact line to remove
- `domain/roles/enums.py` — to confirm `RoleNameEnum` values used for scope validation set

### Skill selection

- Primary skill: `../../../architecture/10_auth.md` (token issuance, cookie management, refresh flow)
- Router trigger terms: `refresh_token`, `app_scope`, `sign-in`, `logout`, `refresh`
- Excluded alternatives: `30_migrations.md` — no schema changes; `06_commands.md` — no new command; `13_sockets.md` — no socket events

## Implementation plan

### Step 1 — Fix `RefreshTokenRejected.http_status` to `401`

File: `backend/app/beyo_manager/errors/permissions.py`

`RefreshTokenRejected` currently inherits `http_status = 403` from `PermissionDenied`. A failed token refresh means the session is expired or invalid — the client must re-authenticate. `401` is semantically correct and triggers the frontend's session-expired retry flow.

```python
class RefreshTokenRejected(PermissionDenied):
    http_status = 401

    def __init__(self, message: str, reason: str) -> None:
        self.reason = reason
        super().__init__(message, code="auth_refresh_rejected")
```

### Step 2 — Add scope validation to `sign_in_user`

File: `backend/app/beyo_manager/services/commands/auth/sign_in_user.py`

After resolving `membership` and before calling `build_auth_response`, validate the client-supplied `app_scope` against a static scope-to-allowed-roles mapping. This prevents a lower-privilege user (worker, seller) from claiming a higher-privilege scope, while still allowing `admin`-role users to sign into the manager app — since `admin` is the highest privilege tier and the manager app is the admin surface.

The mapping is defined at module level so adding a new scope for a future app is a single-line addition here; no other file changes are needed.

```python
from beyo_manager.domain.roles.enums import RoleNameEnum

# module-level: maps each app_scope to the set of role_name values permitted to use it
_SCOPE_ALLOWED_ROLES: dict[str, set[str]] = {
    "manager": {RoleNameEnum.MANAGER.value, RoleNameEnum.ADMIN.value},
    "worker":  {RoleNameEnum.WORKER.value},
    "seller":  {RoleNameEnum.SELLER.value},
    "admin":   {RoleNameEnum.ADMIN.value},  # reserved — no frontend sends this today
}

# after membership is resolved, before build_auth_response:
actual_role = membership.workspace_role.role.name.value
requested_scope = data.get("app_scope", "")
allowed_roles = _SCOPE_ALLOWED_ROLES.get(requested_scope)

if allowed_roles is None or actual_role not in allowed_roles:
    raise PermissionDenied("Invalid credentials.")
```

Using the same `PermissionDenied("Invalid credentials.")` message for all failure cases avoids leaking which scope strings are valid to an attacker probing login.

### Step 3 — Add scope validation to `refresh_token` service

File: `backend/app/beyo_manager/services/commands/auth/refresh_token.py`

After decoding the JWT claims, assert that the `app_scope` embedded in the refresh token matches the `scope` the client declared in the request. This is the defense-in-depth layer — even if somehow a wrong-scope cookie arrives, the JWT claim check catches it.

```python
async def refresh_token(ctx: ServiceContext) -> dict:
    raw_refresh = ctx.incoming_data.get("refresh_token")
    if not raw_refresh:
        raise RefreshTokenRejected("Refresh token missing.", reason="refresh_cookie_missing")
    try:
        claims = jwt.decode(raw_refresh, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise RefreshTokenRejected("Invalid refresh token.", reason="refresh_token_invalid") from exc

    requested_scope = ctx.incoming_data.get("scope", "")
    if claims.get("app_scope") != requested_scope:
        raise RefreshTokenRejected("Refresh token scope mismatch.", reason="scope_mismatch")

    now = datetime.now(timezone.utc)
    claims.pop("exp", None)
    claims["jti"] = str(uuid4())
    access_token = jwt.encode(
        {**claims, "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    return {"access_token": access_token}
```

### Step 4 — Rewrite cookie logic in the auth router

File: `backend/app/beyo_manager/routers/api_v1/auth.py`

Replace the single `_REFRESH_COOKIE = "refresh_token"` constant with a helper and a legacy constant for cleanup. Update `SignInBody.app_scope` default from `"admin"` to `"manager"` so omitting the field in tests/curl behaves consistently with the manager app. Then update each route.

**`SignInBody` default update:**
```python
class SignInBody(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str
    app_scope: str = "manager"  # was "admin" — updated to match manager app
```

**Cookie name helpers (module-level):**
```python
_LEGACY_REFRESH_COOKIE = "refresh_token"

def _scope_cookie(scope: str) -> str:
    return f"{scope}_refresh_token"
```

**`sign_in_route`:** Use the scope-specific cookie name. Also expire the legacy cookie so existing browser sessions are cleaned up.

```python
@router.post("/sign-in")
async def sign_in_route(
    body: SignInBody,
    session: AsyncSession = Depends(get_db),
    _rate: None = Depends(ip_rate_limit(10, 60, "sign-in")),
):
    outcome = await run_service(sign_in_user, ServiceContext(identity={}, incoming_data=body.model_dump(), session=session))
    if not outcome.success:
        return build_err(outcome.error)
    data = dict(outcome.data)
    refresh_token_value = data.pop("_refresh_token")
    scope = body.app_scope
    json_response = build_ok(data)
    json_response.set_cookie(
        _scope_cookie(scope),
        refresh_token_value,
        httponly=True,
        secure=settings.auth_refresh_cookie_secure,
        samesite=settings.auth_refresh_cookie_samesite,
        path=settings.auth_refresh_cookie_path,
        domain=settings.auth_refresh_cookie_domain,
        max_age=settings.auth_refresh_cookie_max_age_seconds,
    )
    json_response.delete_cookie(
        _LEGACY_REFRESH_COOKIE,
        path=settings.auth_refresh_cookie_path,
        domain=settings.auth_refresh_cookie_domain,
    )
    return json_response
```

**`logout_route`:** Derive the cookie name from the scope in the access token claims. Delete both the scope-specific cookie and the legacy cookie.

```python
@router.post("/logout")
async def logout_route(
    request: Request,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    scope = claims.get("app_scope", "")
    cookie_name = _scope_cookie(scope)
    ctx = ServiceContext(
        identity=claims,
        incoming_data={"refresh_token": request.cookies.get(cookie_name)},
        session=session,
    )
    outcome = await run_service(logout_user, ctx)
    json_response = build_ok(outcome.data) if outcome.success else build_err(outcome.error)
    for name in (cookie_name, _LEGACY_REFRESH_COOKIE):
        json_response.delete_cookie(
            name,
            httponly=True,
            secure=settings.auth_refresh_cookie_secure,
            samesite=settings.auth_refresh_cookie_samesite,
            path=settings.auth_refresh_cookie_path,
            domain=settings.auth_refresh_cookie_domain,
        )
    return json_response
```

**`refresh_route`:** Add a required `scope` query parameter. Pass it into `incoming_data` so the service can validate the JWT claim.

```python
from fastapi import Query

@router.post("/refresh")
async def refresh_route(
    request: Request,
    scope: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        identity={},
        incoming_data={
            "refresh_token": request.cookies.get(_scope_cookie(scope)),
            "scope": scope,
        },
        session=session,
    )
    outcome = await run_service(refresh_token, ctx)
    if not outcome.success and isinstance(outcome.error, RefreshTokenRejected):
        return JSONResponse(
            content={
                "error": outcome.error.message,
                "ok": False,
                "code": outcome.error.code,
                "reason": outcome.error.reason,
            },
            status_code=outcome.error.http_status,
        )
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)
```

### Step 5 — Remove `app_scope == "admin"` bypass from `BackendPermissionMiddleware`

File: `backend/app/beyo_manager/routers/middleware/backend_permission.py`

The `if claims.get("app_scope") == "admin": return await call_next(request)` block is a dead code path after the scope rename (no sessions will carry `app_scope: "admin"` from a frontend app). More importantly, it's conceptually wrong — authorization decisions belong to `role_name`, not `app_scope`. The `role_name`-in-`_KNOWN_ROLE_NAMES` branch that follows already defers correctly to route-level `require_roles` dependencies.

Remove lines 40–41:
```python
# DELETE these two lines:
if claims.get("app_scope") == "admin":
    return await call_next(request)
```

The middleware logic becomes: if the token has a known `role_name`, defer to the route; otherwise fall through to granular `backend_permissions` check. This is already the correct behavior for all non-admin roles.

## Risks and mitigations

- Risk: The `SignInBody` default is `app_scope: str = "admin"`. No frontend sends the default — both manager and worker frontends explicitly override it. However, any internal test script or `curl` call that omits `app_scope` will silently pass `"admin"`, which is now in `_SCOPE_ALLOWED_ROLES` only for `role_name: "admin"` users. Tests using manager-role credentials without an explicit `app_scope` will fail with 403.
  Mitigation: Update the `SignInBody` default to `"manager"` so that omitting `app_scope` behaves consistently with the manager app. Add this to Step 4 (the router file is already touched there).

- Risk: Removing the `app_scope == "admin"` middleware bypass (Step 5) affects `admin`-role users who log into the manager app. After the rename they carry `app_scope: "manager"` and `role_name: "admin"` — `"admin"` is in `_KNOWN_ROLE_NAMES`, so the middleware correctly defers to route-level `require_roles`. No access regression.
  Mitigation: Verified: `_KNOWN_ROLE_NAMES = {"admin", "manager", "seller", "worker"}` in the current middleware file — admin-role users are covered by the role-name fallthrough.

- Risk: Existing browser sessions carry the old `refresh_token` cookie (not `manager_refresh_token`). After deployment, the first refresh attempt for those sessions will fail (`manager_refresh_token` cookie not present → 401 → frontend redirects to login). All active users are effectively logged out on the next access token expiry.
  Mitigation: This is the intended behavior for a security fix. Document as a known disruption in the release notes. The legacy `refresh_token` cookie is cleared on the next successful sign-in (Step 4).

- Risk: `RefreshTokenRejected.http_status` change from 403 → 401 (Step 1) affects the HTTP status returned by the existing `refresh_cookie_missing` and `refresh_token_invalid` reason codes too, not just `scope_mismatch`. If any other system is monitoring for 403s from the refresh endpoint, it will no longer see them.
  Mitigation: 401 is the semantically correct status for all refresh failures — the session needs re-establishment. The change is correct; update any monitoring dashboards accordingly.

## Validation plan

- `POST /api/v1/auth/sign-in` with `app_scope: "manager"`, valid manager credentials: response sets `manager_refresh_token` cookie; `refresh_token` cookie is expired (max_age=0 or delete header present)
- `POST /api/v1/auth/sign-in` with `app_scope: "worker"`, valid worker credentials: response sets `worker_refresh_token` cookie; `refresh_token` cookie is expired
- `POST /api/v1/auth/sign-in` with `app_scope: "manager"`, admin-role credentials: returns `200` with `manager_refresh_token` cookie — admin role is permitted in manager scope
- `POST /api/v1/auth/sign-in` with `app_scope: "worker"`, manager-role credentials: returns `403` — worker scope rejects manager role
- `POST /api/v1/auth/sign-in` with `app_scope: "manager"`, worker-role credentials: returns `403` — manager scope rejects worker role
- `POST /api/v1/auth/sign-in` with `app_scope: "admin"`, manager-role credentials: returns `403` — admin scope reserved; only admin-role permitted and no frontend sends it yet
- `POST /api/v1/auth/refresh?scope=manager` with `manager_refresh_token` cookie: returns `200` with `access_token`; decoded token has `app_scope: "manager"`
- `POST /api/v1/auth/refresh?scope=manager` with only `worker_refresh_token` cookie (simulating overwrite scenario): returns `401` with `reason: "refresh_cookie_missing"`
- `POST /api/v1/auth/refresh?scope=manager` with `manager_refresh_token` cookie manually overwritten with a worker-scope JWT: returns `401` with `reason: "scope_mismatch"`
- `POST /api/v1/auth/refresh` (no scope param): returns `422 Unprocessable Entity`
- `POST /api/v1/auth/logout` for a manager session: response deletes `manager_refresh_token` AND `refresh_token` cookies
- Import smoke test: no `ImportError` on startup after all changes

## Review log

_None yet._

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
