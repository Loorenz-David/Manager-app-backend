# PLAN_user_online_status_20260516

## Metadata

- Plan ID: `PLAN_user_online_status_20260516`
- Status: `under_construction`
- Owner agent: `GitHub Copilot`
- Created at (UTC): `2026-05-16T00:00:00Z`
- Last updated at (UTC): `2026-05-16T00:00:00Z`
- Related issue/ticket: `—`
- Intention plan: `—` *(intent is embedded in scope below; no separate INTENTION file)*

## Goal and intent

- **Goal:** Write the `{prefix}:user_online:{user_id}` Redis key on WebSocket connect and delete it on WebSocket disconnect, enabling `GET /api/v1/users/live` (from `PLAN_user_app_view_records_20260515`) to report accurate online/offline status per workspace member.
- **Business/user intent:** Managers see a live snapshot of who is currently online in the workspace. A user is online if they have at least one active WebSocket connection; offline if they have none.
- **Non-goals:**
  - HTTP heartbeat or polling endpoint for online status
  - Exposing the online key via a dedicated REST endpoint (covered by the live endpoint in the view records plan)
  - Persistence of online/offline history in the DB
  - Support for multi-process uvicorn workers (socket.io has no Redis adapter; in-process tracking is the correct scope)

## Scope

- **In scope:**
  - `services/infra/presence/user_online_key.py` — async Redis helpers `set_user_online` and `delete_user_online`
  - `sockets/manager.py` — add `is_user_connected(user_id) -> bool` helper method
  - `sockets/handlers.py` — call `set_user_online` on connect; conditionally call `delete_user_online` on disconnect (only when no other active connection for same user)
  - `architecture/48_presence_local.md` — document the online/offline key pattern and multi-tab rule
- **Out of scope:**
  - Any changes to the view records plan or live endpoint — they already read this key correctly (absent = offline)
  - DB recording of connect/disconnect events
  - Heartbeat / TTL refresh mechanism (TTL is a crash-safety net only)
- **Assumptions:**
  - socket.io runs as a single in-process `AsyncServer` (confirmed — no Redis adapter in `sockets/__init__.py`)
  - `get_async_redis()` is available at `services/infra/redis/async_client.py` (confirmed existing)
  - `make_key(namespace, *parts)` is available at `services/infra/redis/keys.py` (confirmed existing)

## Clarifications required

*(none — all design decisions resolved)*

## Acceptance criteria

1. After a successful WebSocket connection, `{prefix}:user_online:{user_id}` exists in Redis with TTL ≤ 86400s and value `"1"`.
2. When all WebSocket connections for a user disconnect, the key is deleted from Redis.
3. When a user has two active connections and one disconnects, the key is **not** deleted (multi-tab guard).
4. When a user reconnects after the key was deleted (re-open app), the key is re-created correctly.
5. `48_presence_local.md` documents the key pattern, TTL, and multi-tab behavior.

## Contracts and skills

### Contracts loaded

- `backend/architecture/12_infra_redis.md`: key naming convention (`{prefix}:{namespace}:{parts}`), mandatory TTL, async client usage
- `backend/architecture/48_presence.md`: presence layer architecture; confirms Redis is the inline layer for real-time state
- `backend/architecture/13_sockets.md`: socket handler wiring pattern, `AsyncServer`, connect/disconnect lifecycle

### Local extensions loaded

- `backend/architecture/48_presence_local.md`: will be updated by this plan to document the online/offline key

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`12_infra_redis.md`, `13_sockets.md`, `48_presence.md`)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Permitted relational reads for this plan:
- `sockets/handlers.py` — understand existing connect/disconnect structure before modifying
- `sockets/manager.py` — understand `_connections` dict and `disconnect` return value
- `services/infra/presence/user_view_key.py` — pattern reference for the sister Redis key helper (same namespace)
- `services/infra/redis/async_client.py` and `keys.py` — confirm import paths

### Skill selection

- Primary skill: `—` *(no task-system skill; this is a direct implementation)*

---

## Implementation plan

### Step 1 — CREATE `services/infra/presence/user_online_key.py`

New Redis helper module. Owns the `user_online` key pattern.

```python
from beyo_manager.services.infra.redis.keys import make_key
from beyo_manager.services.infra.redis.async_client import get_async_redis

_USER_ONLINE_TTL_SECONDS = 86400


def _key(user_id: str) -> str:
    return make_key("user_online", user_id)


async def set_user_online(user_id: str) -> None:
    r = get_async_redis()
    await r.set(_key(user_id), "1", ex=_USER_ONLINE_TTL_SECONDS)


async def delete_user_online(user_id: str) -> None:
    r = get_async_redis()
    await r.delete(_key(user_id))
```

**Key pattern:** `{prefix}:user_online:{user_id}`
**Value:** `"1"` — existence means online; absence means offline
**TTL:** 86400s — crash-safety net only; the primary offline signal is key deletion on disconnect

---

### Step 2 — UPDATE `sockets/manager.py`

Add `is_user_connected(user_id: str) -> bool` to `ConnectionManager`.

This method inspects the in-process `_connections` dict (already the authority for single-process socket.io) to check whether any remaining connection belongs to the given user.

**Target location:** add after the `get` method, before the static methods.

```python
def is_user_connected(self, user_id: str) -> bool:
    return any(meta.user_id == user_id for meta in self._connections.values())
```

**Timing contract:** `manager.disconnect(sid)` pops the disconnecting sid from `_connections` **before** returning `meta`. Therefore, when `is_user_connected` is called inside `_handle_disconnect` after `await manager.disconnect(sid)`, the disconnecting connection is already absent — the result reflects only remaining connections. No race condition under single-process async I/O.

---

### Step 3 — UPDATE `sockets/handlers.py`

Two changes:

**3a — On connect:** after `await manager.connect(...)` succeeds, set the user online.

Add import at top:
```python
from beyo_manager.services.infra.presence.user_online_key import delete_user_online, set_user_online
```

Modify `_handle_connect` — add `await set_user_online(...)` after `manager.connect`:

```python
async def _handle_connect(sid: str, environ: dict, auth: dict | None = None):
    token = (auth or {}).get("token") or _query_token(environ)
    if not token:
        return False
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return False
    user_id = claims.get("user_id", "")
    await manager.connect(
        sid,
        ConnectionMeta(
            user_id=user_id,
            workspace_id=claims.get("workspace_id", ""),
            username=claims.get("username", ""),
        ),
    )
    await set_user_online(user_id)
    return True
```

**3b — On disconnect:** after `manager.disconnect` removes the sid, check if the user still has other active connections. Delete the key only if they do not.

Modify `_handle_disconnect`:

```python
async def _handle_disconnect(sid: str):
    meta = await manager.disconnect(sid)
    if meta:
        _cleanup_presence(meta)
        if not manager.is_user_connected(meta.user_id):
            await delete_user_online(meta.user_id)
```

**Multi-tab behavior:**
- User with 2 tabs: tab 1 disconnects → `manager.disconnect(sid_1)` pops sid_1 → `is_user_connected` finds sid_2 → key NOT deleted → user stays online.
- Last tab disconnects → `is_user_connected` finds no remaining connections → key deleted → user goes offline.

---

### Step 4 — UPDATE `architecture/48_presence_local.md`

Replace the stub file with documented local extensions:

```markdown
# Presence - Local Extensions
> Extends: 48_presence.md

## Overridden Behaviour

### One active view record per user globally (auto-close)

Canonical contract 48 allows multi-tab concurrent views (multiple open `UserAppViewRecord` rows for the same user + entity pair). This app overrides that rule:

**Before inserting a new `UserAppViewRecord`, the `RECORD_VIEW_START` handler bulk-closes all open records for the user globally** (`WHERE ended_at IS NULL`, regardless of entity). This enforces a single-active-view invariant per user across the entire workspace.

*Reason: UX requirement — the live presence snapshot (`GET /api/v1/users/live`) shows one current view per user. Concurrent open records would make the current-view state ambiguous.*

### Payload timestamps for offline batch records

`RECORD_VIEW_START` and `RECORD_VIEW_END` handlers accept optional timestamp fields in the task payload:
- `RECORD_VIEW_START`: uses `payload["started_at"]` (ISO string) if present; falls back to `datetime.now(timezone.utc)`.
- `RECORD_VIEW_END`: uses `payload["ended_at"]` (ISO string) if present; falls back to `datetime.now(timezone.utc)`.

*Reason: the HTTP batch endpoint (`POST /api/v1/users/me/view-records`) sends buffered events after offline reconnect. These events carry the original client-side timestamps.*

## Local Decisions

### Redis key: `{prefix}:user_online:{user_id}`

**Owner:** `services/infra/presence/user_online_key.py` (written by `PLAN_user_online_status_20260516`)
**Written by:** WebSocket connect/disconnect handlers (`sockets/handlers.py`)
**Read by:** `GET /api/v1/users/live` live presence query (via Redis pipeline)

| Event | Action |
|---|---|
| WebSocket connect | `SET {prefix}:user_online:{user_id} "1" EX 86400` |
| WebSocket disconnect (last connection) | `DEL {prefix}:user_online:{user_id}` |
| WebSocket disconnect (other connections remain) | no Redis write (key persists) |

**Value:** `"1"` — key existence = online; key absence = offline.
**TTL:** 86400s — crash-safety net. Primary offline signal is explicit deletion on disconnect.
**Multi-tab rule:** the in-process `ConnectionManager._connections` dict is the authority for "is this user still connected?" After `manager.disconnect(sid)` pops the disconnecting sid, `is_user_connected(user_id)` checks remaining connections. Key is deleted only when no connections remain.

### Redis key: `{prefix}:user_view:{user_id}`

**Owner:** `services/infra/presence/user_view_key.py` (written by `PLAN_user_app_view_records_20260515`)
**Written by:** `POST /api/v1/users/me/view-records` HTTP endpoint (inline on each batch event)
**Read by:** `GET /api/v1/users/me/view-records/current` and `GET /api/v1/users/live`

Stores the user's most recent active view as a JSON object `{"entity_type": "...", "entity_client_id": "..."}`. TTL 86400s.
```

---

## Risks and mitigations

- **Risk:** Multi-process deployment — if multiple uvicorn processes serve socket.io connections, `is_user_connected` checks only the local process's `_connections`. A user connected to process B would appear offline to process A's manager on disconnect.
  **Mitigation:** socket.io runs as a single in-process `AsyncServer` with no Redis adapter (confirmed). This plan is correct for the current single-process deployment. If multi-process support is added in the future, `is_user_connected` must be replaced with a Redis counter or `sio.manager.get_participants()` via the Redis adapter.

- **Risk:** Crash leaves stale online key.
  **Mitigation:** TTL of 86400s ensures stale keys auto-expire. Worst case: a user appears online for up to 24h after a process crash. Acceptable for a manager presence snapshot.

- **Risk:** `set_user_online` called with an empty `user_id` string if JWT claims are missing.
  **Mitigation:** `_handle_connect` already returns `False` early if token is invalid. An empty `user_id` claim would produce a valid but user-less key. Add a guard: only call `set_user_online(user_id)` if `user_id` is non-empty. See Step 3a — `user_id = claims.get("user_id", "")` is extracted before the `manager.connect` call; add `if not user_id: return False` after extracting it, or guard `await set_user_online(user_id)` with `if user_id`.

## Validation plan

After implementation, verify with a Redis CLI and a WebSocket test client:

- `WS connect (valid token)` → `redis-cli GET {prefix}:user_online:{user_id}` returns `"1"`
- `WS disconnect` → `redis-cli GET {prefix}:user_online:{user_id}` returns `(nil)`
- **Multi-tab**: connect two clients for same user → disconnect one → key still `"1"` → disconnect second → key `(nil)`
- `GET /api/v1/users/live` with connected user → `is_online: true`; after disconnect → `is_online: false`
- `redis-cli TTL {prefix}:user_online:{user_id}` → value ≤ 86400 and > 0

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
