# DB connection pool audit — ManagerBeyo backend

**Date:** 2026-09-29 · **Scope:** read-only static investigation of the repository. No code, config,
database, AWS or process was touched. **Revision audited:** `be98365` (local `HEAD` = local
`origin/main` ref; the GitHub remote was not fetched, so "production runs `be98365`" is INFERRED
from the last push in the local reflog at 2026-09-28 16:05 +0200).

Evidence labels used throughout:

- **OBSERVED**: read directly in repository code or config.
- **INFERRED**: strongly supported by the evidence.
- **HYPOTHESIS**: plausible but not proven.
- **UNKNOWN**: cannot be determined from the repository.

---

## 1. Executive summary

1. **Production is not Docker.** It is one EC2 host running **10 separate systemd services**. Each
   service is an independent Python process with its **own SQLAlchemy pool** (OBSERVED,
   `.github/workflows/deploy.yml`). The Compose stack in `../managerbeyo-deployment/` has a deliberate
   connection budget, but it is an in-progress migration that has not gone live ("legacy production"
   throughout its decision log).
2. **Every process uses the same pool configuration:** `pool_size = DB_POOL_SIZE` (default **10**),
   `max_overflow = DB_MAX_OVERFLOW` (default **20**), `pool_recycle = 1800`, `pool_timeout = 30`,
   `pool_pre_ping = True` (OBSERVED). None of it is tuned per process. The production values live in
   `/home/ubuntu/config/managerbeyo/.env` on the EC2 host and are **UNKNOWN**. `.env.example` ships
   `DB_POOL_SIZE=20 / DB_MAX_OVERFLOW=20`.
3. **The configured ceiling exceeds the database.** With defaults, 10 processes × (10 + 20) + 1 LISTEN
   connection gives **301 possible connections**, and the persistent ceiling alone is **101**. The
   deployment repo records RDS `max_connections` as **79**. Nothing in the configuration keeps the
   application inside the database's limit.
4. **Realistic steady state is much lower than the ceiling.** QueuePool opens connections lazily and
   keeps up to `pool_size` idle connections **forever**: sleep mode, `pool_recycle` and
   `pool_pre_ping` never reduce the count. Background processes are strictly sequential and hold
   ~1–2 connections each. The API holds its high-water mark of concurrent requests, capped at
   `pool_size`.
   - Defaults: **~19–30** application connections.
   - `DB_POOL_SIZE=20`: **~29–40**.
5. **The observed 31–33 is category B: plausible, not provable.** It fits the topology if production
   uses `DB_POOL_SIZE=20` (as `.env.example` does), or defaults plus the email watcher plus a few RDS
   internal connections. It sits at the upper edge if production uses pure defaults.
6. **No classic connection leak was found.** Every session is opened through `async with
   _session_factory()`. SQLAlchemy 2.0.40 closes sessions in a shielded task, so cancellation cannot
   skip the close. The QueuePool architecture also caps any leak at `pool_size + max_overflow` per
   process. A stable 31–33 plateau is the shape of pool high-water marks, not of a leak.
7. **Transaction lifetime is the real, confirmed problem:**
   - **~16 runtime sites** hold an open transaction, sometimes with **row locks** (`FOR UPDATE`),
     across Shopify, S3, SMTP/IMAP or Web Push calls.
   - Several of these calls are **synchronous** (boto3, pywebpush), so they block the whole event
     loop while the connection is checked out.
   - Web Push runs with **no timeout at all**.
   - **`TimeoutMiddleware` does not release anything.** The client gets a 504 at 30 s, but the
     handler keeps running and keeps its connection.
8. **Connections vs memory:** the repository shows *why ~30 connections exist*. It cannot show *how
   much memory each costs*. Per-backend memory depends on per-connection state: each pooled
   connection caches up to 100 server-side prepared statements (SQLAlchemy asyncpg default,
   OBSERVED), and long idle-in-transaction sessions add more. None of this is measured. The
   "~10.5 MiB per connection" figure should not be treated as a constant.

---

## 2. Database stack

```
HTTP:    uvicorn (1 process, INFERRED) → FastAPI 0.115.12 / Starlette 0.46.2 → Depends(get_db)
Workers: asyncio main() → init_db() → get_db_session() / task_db_session()
                         ↓
         SQLAlchemy 2.0.40 AsyncSession        owns: unit of work + the TRANSACTION (autobegin)
                         ↓
         AsyncEngine → AsyncAdaptedQueuePool   owns: pooled connection checkout/checkin
                         ↓
         asyncpg 0.30.0 Connection            owns: the PHYSICAL socket = 1 PostgreSQL backend process
                         ↓
         PostgreSQL on RDS (db.t4g.micro)
```

Versions come from the pinned `app/requirements.txt` and match the local `.venv` (OBSERVED).

**Who owns what, and why it matters for the RDS count:**

- An **AsyncSession** holds a pooled connection only from its first statement until
  `commit()`/`rollback()`/`close()`. After commit the connection goes back to the pool, and the next
  statement checks one out again.
- The **pool** keeps up to `pool_size` physical connections open while they are idle. Connections
  beyond that (overflow) are closed when they are checked back in.
- **Each physical connection is one PostgreSQL backend process.** RDS `DatabaseConnections` counts
  these whether they are idle, active or idle-in-transaction.
- **Therefore the RDS count ≈ the sum over processes of the idle pooled connections plus those
  currently checked out, plus the non-pooled asyncpg connections.** Sessions themselves do not show
  up in the count.

There is one non-pooled long-lived connection: the task router's `LISTEN task_open` connection
(`asyncpg.connect`, `services/infra/execution/task_router.py` `_listen_for_task_events`).

---

## 3. Engine configuration

**Single application engine:** `app/beyo_manager/models/database.py` `init_db()`, which is identical
at HEAD and in the working tree for every pool parameter.

| Parameter | Value | Class | Source |
|---|---|---|---|
| engine | `create_async_engine` (async) | EXPLICIT | `database.py` `init_db` |
| driver | `postgresql+asyncpg` (URL scheme) | ENV-DEPENDENT (`DATABASE_URL`) | `config.py` comment + URL |
| pool class | `AsyncAdaptedQueuePool` | DEFAULT (SQLAlchemy for async engines) | — |
| `pool_size` | `settings.db_pool_size`, default **10** | ENV-DEPENDENT (`DB_POOL_SIZE`) | `config.py` `db_pool_size` |
| `max_overflow` | `settings.db_max_overflow`, default **20** | ENV-DEPENDENT (`DB_MAX_OVERFLOW`) | `config.py` `db_max_overflow` |
| `pool_recycle` | `settings.db_pool_recycle`, default **1800 s** | ENV-DEPENDENT (`DB_POOL_RECYCLE`) | `config.py` |
| `pool_timeout` | **30 s** | EXPLICIT | `database.py` |
| `pool_pre_ping` | **True** | EXPLICIT | `database.py` |
| `pool_use_lifo` | False (FIFO) | DEFAULT | — |
| connect timeout | `connect_args.timeout = 5` s | EXPLICIT | `database.py` |
| server settings | `timezone=UTC` (+ `application_name` **only in the uncommitted working tree**) | EXPLICIT | `database.py` |
| `prepared_statement_cache_size` | **100 per connection** | DEFAULT (SQLAlchemy asyncpg dialect, `dialects/postgresql/asyncpg.py`) | — |
| asyncpg `statement_cache_size`, `command_timeout` | not set | DEFAULT | — |
| isolation level | not set → PostgreSQL default READ COMMITTED | DEFAULT | — |
| `echo` | `True` when `settings.environment == "development"` | ENV-DEPENDENT (`ENVIRONMENT`, default `"development"`) | `database.py` |
| sessionmaker | `async_sessionmaker(class_=AsyncSession, expire_on_commit=False)`, autobegin | EXPLICIT/DEFAULT | `database.py` |

**Configuration path.**
1. Environment, or an env file chosen by `APP_ENV`: `development→.env`, `production→.env.production`
   and so on (`config.py` `_resolve_env_file`).
2. → `Settings` (pydantic-settings, `env_ignore_empty=True`).
3. → `database.init_db()`.
4. → `_engine` + `_session_factory` (module globals).
5. → `get_db` (HTTP), `get_db_session` / `task_db_session` (background).

On EC2, the deploy script sources `/home/ubuntu/config/managerbeyo/.env` for migrations only. What
the systemd units load (`EnvironmentFile=`, or `.env.production` in the working directory) is
**UNKNOWN**. Dev/staging/prod **can** differ, because all three pool numbers are environment
variables.

Known values:

| Source | `DB_POOL_SIZE` | `DB_MAX_OVERFLOW` | `DB_POOL_RECYCLE` |
|---|---|---|---|
| code default | 10 | 20 | 1800 |
| `app/.env.example`, `app/.env` (dev) | 20 | 20 | 1800 |
| `.env.validation`, `.env.testing` | unset → defaults | unset → defaults | unset → defaults |
| legacy production | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** |
| future Compose (not live) | api 5, background 1, email watcher 1 | api 10, background 1, email watcher 2 | default |

Values never changed: the defaults 10/20/1800 have existed since the first commit, `89c5db1`
(2026-05-15).

**Other engines and connections (all transient):**

| Site | What | Lifecycle |
|---|---|---|
| `scripts/wait_for_services.py` `_check_db` | temp engine, `SELECT 1` | `dispose()` in `finally`; only when started via `run.py` |
| `migrations/env.py` | `NullPool` engine | 1 connection during `alembic upgrade`, disposed |
| `scripts/apply_db_triggers.py` | `asyncpg.connect` | closed in `finally`; runs at every deploy |
| `scripts/migrate.py` (untracked, Compose only) | ≤2 asyncpg connections | not in legacy prod |
| `scripts/create_db.py`, `wipe_all_data.py`, `seed_ws.py`, `test_history.py`, `operations/connecteam_dead_letter.py` | ad-hoc tools | manual only |

---

## 4. Process / container topology

**Legacy production (live).** `deploy.yml` SSHes to EC2, runs `git pull`, `pip install`,
`alembic upgrade head` and `apply_db_triggers.py`, then `systemctl restart` on these units. The
shopify-worker unit is listed twice, which makes **10 distinct units**:

| # | systemd unit | Entry point | Calls `init_db()` → own pool? | Concurrency model |
|---|---|---|---|---|
| 1 | managerbeyo-backend | uvicorn `beyo_manager.asgi:app` (ExecStart **UNKNOWN**) | yes, in FastAPI `lifespan` | concurrent requests + Socket.IO events |
| 2 | managerbeyo-task-router | `workers/task_router_process.py` | yes, **+1 dedicated asyncpg LISTEN conn** | sequential loop |
| 3 | managerbeyo-tasks-worker | `workers/tasks_worker.py` | yes | 1 task at a time |
| 4 | managerbeyo-notification-worker | `workers/notification_worker.py` | yes | 1 task at a time |
| 5 | managerbeyo-shopify-worker | `workers/shopify_worker.py` | yes | 1 task at a time |
| 6 | managerbeyo-analytics-worker | `workers/analytics_worker.py` | yes | 1 task at a time |
| 7 | managerbeyo-presence-worker | `workers/presence_worker.py` | yes | 1 task at a time |
| 8 | managerbeyo-delayed-scheduler | `workers/delayed_scheduler_runner.py` | yes | sequential poll, 10 s |
| 9 | managerbeyo-recurring-scheduler | `workers/recurring_scheduler_runner.py` | yes | sequential poll, 10 s |
| 10 | managerbeyo-email-idle-watcher | `workers/email_idle_watcher.py` | yes, but **exits immediately if `EMAIL_IDLE_ENABLED` is false** (default), before any connection | one task per mailbox |

Notes on the topology:

- **The API worker count is UNKNOWN.** Several facts point to a single uvicorn process (INFERRED):
  - Socket.IO state is held in-process: `create_app` calls `mark_socket_server_process()`.
  - The deployment decision log (D6) says "Exactly one Uvicorn process".
  - Neither `run.py` nor the Dockerfile passes `--workers`.

  Against that, `architecture/02_app_factory.md` recommends `--workers 4`. If production followed
  that document, the API would have **4 independent pools**.
- **No Gunicorn, no Celery, no cron, no scheduled restart** exists in the repository (OBSERVED). `rq` is
  installed and `workers/runtime.py` defines an RQ worker, but no unit or Procfile line starts it.
  The Procfile's `worker: python worker.py` points at a **file that does not exist**.
- **No pools are shared between processes.** Each process calls `init_db()` in its own `main()` or
  lifespan.

**Future Compose stack (NOT live):** the same 10 roles as containers plus a `migrate` job. It pins
per-process pools: background processes 1+1, API 5+10 (D26 in `compose.yaml`). Its header says
**staging and production will share one RDS instance** (`max_connections 79`).

---

## 5. Connection budget

`P` = `pool_size` and `O` = `max_overflow`, per process.

### 5a. Theoretical (configuration capacity)

**Defaults, P=10, O=20:**

| Component | Processes | Pool size | Overflow | Persistent (proc×P) | Maximum (proc×(P+O)) |
|---|---|---|---|---|---|
| API | 1 (UNKNOWN; 4 if `--workers 4`) | 10 | 20 | 10 | 30 |
| task-router | 1 | 10 | 20 | 10 (+1 LISTEN) | 30 (+1) |
| queue workers (tasks, notification, shopify, analytics, presence) | 5 | 10 | 20 | 50 | 150 |
| schedulers (delayed, recurring) | 2 | 10 | 20 | 20 | 60 |
| email-idle-watcher | 0 (disabled) / 1 | 10 | 20 | 0 / 10 | 0 / 30 |
| **Total (email watcher on)** | **10** | | | **101** | **301** |
| **Total (email watcher off)** | **9** | | | **91** | **271** |

Summary lines:

- **Maximum persistent pooled connections:** 91–101.
- **Maximum overflow connections:** 180–200.
- **Theoretical application maximum:** 271–301.

**With `.env.example` values (P=20, O=20):**
- persistent 181–201
- overflow 180–200
- maximum 361–401

Any of these ceilings exceeds the RDS `max_connections` of 79 recorded in the deployment repo. That
value was not verified here.

### 5b. Expected steady state (what actually exists)

SQLAlchemy QueuePool behaviour (library behaviour, applied to this code):

- **Lazy.** `create_async_engine` opens **no** connections. The first checkout opens one.
- **High-water retention.**
  - Checked-in connections are kept, up to `P` of them.
  - Overflow connections (beyond `P`) are closed on checkin.
  - An idle pooled connection is **never closed because of time**: not by sleep mode, not by
    `pool_recycle` (checked only at checkout), not by `pool_pre_ping` (only at checkout).
  - So each process's idle count ≈ **min(its highest concurrent checkout since start, P)**, and it
    stays there until the process restarts.

Per-process high-water marks from the code:

| Component | Realistic high-water | Why |
|---|---|---|
| each background process (8 always-on) | **1**, sometimes **2** | Strictly one session at a time (`worker_base._process_task`: claim → handler → finalize, separate sessions). A 2nd appears when an event handler opens its own session inside a caller's (`services/infra/events/handlers/webhook_handler.py`), or when an `async for … get_db_session(): return` leaves the old session's close to the async-generator finalizer while the next session opens (§7). |
| task-router LISTEN | **1** | always open, reconnects on loss |
| email-idle-watcher | 0 if disabled; ~1–3 if enabled | one short session per mailbox event, several mailboxes concurrently |
| API | **min(peak concurrent DB-using requests/socket events, P)** | One session per request (`Depends(get_db)`, 344 uses; JWT auth uses Redis, not DB). Each Socket.IO view/leave/disconnect opens a session. SPA page loads that fire ≥P parallel API calls fill the pool once, and it stays full. |

**Expected steady-state application connections:**

| Scenario | API | 8 background | LISTEN | Email watcher | **Total** |
|---|---|---|---|---|---|
| Defaults (P=10), email off | ≤10 | 8–16 | 1 | 0 | **19–27** |
| Defaults (P=10), email on | ≤10 | 8–16 | 1 | 1–3 | **20–30** |
| P=20, email off | ≤20 | 8–16 | 1 | 0 | **29–37** |
| P=20, email on | ≤20 | 8–16 | 1 | 1–3 | **30–40** |
| API with `--workers 4`, P=10 | ≤40 | 8–16 | 1 | 0–3 | **up to ~60** |

Add RDS-internal sessions (`rdsadmin`; count UNKNOWN, typically a few). If staging or any other
application uses the same instance, add those as well (UNKNOWN; see §14).

---

## 6. Session lifecycle analysis

| Pattern | Where | Cleanup on success / exception / cancel / early return | Verdict |
|---|---|---|---|
| `get_db`: `async with _session_factory() as session: yield session` | `database.py`, 344 route deps | FastAPI 0.115 closes the dependency's exit stack after the endpoint returns. `AsyncSession.__aexit__` runs `close()` in a **shielded task** (SQLAlchemy 2.0.40 `ext/asyncio/session.py`), so cancellation cannot skip it. | **Correct** |
| `get_db_session` via `async for session in get_db_session(): …` | workers, router, schedulers, sockets, email watcher, many handlers | Normal completion: deterministic close. `return`/`break`/exception inside the loop body: close is deferred to asyncio's async-generator finalizer (an `aclose()` task on the next loop tick). CPython refcounting makes that near-immediate. | **Correct but non-deterministic.** Not a leak. It can briefly overlap with the next session (high-water 2). |
| `get_db_session` via manual `anext()` + `finally: aclose()` | `routers/api_v1/bootstrap.py`, `reset.py` | explicit `aclose()` in `finally` | **Correct** (these endpoints are refused in production anyway) |
| `task_db_session()` `@asynccontextmanager` | `services/infra/execution/db.py` | `async with` | **Correct** |
| `session.begin()` / `maybe_begin` | services | commit/rollback on block exit. A session that has already autobegun makes `maybe_begin` subordinate, so the commit happens later. | Correct; affects lifetime, not leaks |
| Socket.IO handlers | `sockets/handlers.py` | short session per event, commit, close | **Correct** |
| Background `asyncio.create_task` | router (LISTEN, sleep monitor), email watcher | these tasks open their own short sessions; none captures a request session | **Correct** |
| Streaming / websocket-held sessions | — | no `StreamingResponse` with a DB session, no FastAPI websockets, no `BackgroundTasks` | **Not present** |
| Global/stored sessions | — | none found (`self.session =`, module-level sessions: no matches) | **Not present** |
| Direct `engine.connect()` / raw connections in app code | — | none, except the router's LISTEN asyncpg connection | — |
| Engine disposal | API `lifespan` → `close_db()`; **workers never call `close_db()`** | Process exit closes the sockets, so PostgreSQL backends end. There is no graceful `Terminate`, but no leak on the server either. | Acceptable |

---

## 7. Connection-leak audit

No site was found where a session or connection is acquired and never released.

| # | File / function | Concern | Status |
|---|---|---|---|
| L1 | every `async for session in get_db_session(): … return` (e.g. `worker_base._claim_task`, `delayed_scheduler_runner._get_next_scheduled_for`, `recurring_scheduler_runner._get_next_run_at`, `email_idle/connection_watcher._has_active_sync`, `_debounced_enqueue`, `handle_send_email_messages`) | Close is deferred to the async-generator finalizer, so the connection is released one loop tick later. If a reference cycle ever kept the generator alive, release would wait for cyclic GC. | **Requires investigation, low risk.** Not a leak in CPython. Runtime signal: SQLAlchemy warnings "garbage collector is trying to clean up non-checked-in connection" in journald. |
| L2 | `task_router._listen_for_task_events` | If an exception is raised while `conn` is still open (e.g. `add_listener` fails), the loop reconnects **without closing the old `conn`**. The old one lingers until GC or a server timeout. | **Requires investigation**, low risk. Most exceptions here mean the connection is already dead. |
| L3 | `TimeoutMiddleware` (`routers/middleware/timeout.py`) | `asyncio.wait_for(call_next(...))` in a `BaseHTTPMiddleware`. In Starlette 0.46.2 the endpoint runs in the middleware's outer task group, so the timeout cancels only the wait for the response. The client gets 504, and **the handler keeps running with its session and connection until it finishes**. | **Confirmed defect** (not a leak: the connection is returned eventually). It is the main way API checkouts can pile up past 30 s. |
| L4 | `asyncio.gather` over **one shared `AsyncSession`** (`domain/*/notification_targets.py`, `services/queries/items/lookup_item_by_article_number.py`) | Concurrent use of one session is unsupported. It can raise "another operation is in progress" and **invalidate** that connection. Not a count increase. | **Requires investigation** (correctness) |
| L5 | `worker_base.run_worker` / scheduler loops | DB errors in `_claim_task`, `_fail_task` or `_get_next_scheduled_for` are not caught, so **the process exits**. Under systemd this means restart and loss of all that process's connections. | **Confirmed behaviour.** Relevant to §14 (drops during RDS stalls), not a leak. |

**Why a leak is architecturally bounded here:** a checked-out connection that is never returned
still counts toward that process's `P + O`. A real leak would therefore show up as:

- rising **`idle in transaction`** rows in `pg_stat_activity`;
- then `QueuePool limit of size X overflow Y reached, connection timed out` errors after 30 s.

It would not show up as a stable plateau.

---

## 8. Long transaction / session findings

This comes from a delegated sweep of every session scope. The mechanism was verified independently,
and the top sites were spot-checked (§ marked ✔). Connection-hold rule: the connection is checked
out from the first statement to the next commit/rollback/close.

| # | Site | Runs in | Held across | External timeout | Class |
|---|---|---|---|---|---|
| T1 ✔ | `services/tasks/notifications/send_push_notification.py` `handle_send_push_notification` | notification-worker | SELECT subscriptions, then a **synchronous** `send_web_push` loop, then DELETE + commit | **none**: `pywebpush.webpush` with no timeout (`services/infra/push/vapid.py`). It blocks the event loop, so the 300 s handler timeout cannot fire. | **CONFIRMED** (can hold 1 connection idle-in-transaction indefinitely) |
| T2 | `services/tasks/email_inbox_sync_handler.py` `handle_email_inbox_sync` | tasks-worker | inside `session.begin()`: reads, then IMAP login/search/fetch (`to_thread`) | 20 s per socket op | **CONFIRMED** |
| T3 | `services/commands/emails/_sync_email_threads_targeted_core.py` (from `handle_sync_email_threads_targeted`) | tasks-worker | reads, then IMAP `search_by_header_ids` per connection in a loop | 20 s per op | **CONFIRMED** |
| T4 | `services/commands/emails/test_email_connection.py` | API | SELECT, then SMTP test, then IMAP test | 15 s + 20 s (over the 30 s request limit) | **CONFIRMED** |
| T5 | `services/commands/shopify/handle_shopify_oauth_callback.py` | API | **SELECT … FOR UPDATE** (row lock), then OAuth token exchange, then shop-name fetch | 30 s each | **CONFIRMED** |
| T6 | `services/queries/shopify/get_shopify_locations.py` | API | SELECT, then `fetch_shop_locations` per shop (paginated) | 30 s per call | **CONFIRMED** |
| T7 | `services/queries/shopify/get_shopify_metafield_preferences.py` (+ `enrich_shopify_metafield_references.py`) | API | SELECTs, then several Shopify GraphQL calls per shop | 30 s per call | **CONFIRMED** |
| T8 | `services/queries/shopify/lookup_shopify_customers_by_product_identity.py` | API | SELECT, then up to 2 Shopify calls per shop | 30 s per call | **CONFIRMED** |
| T9 | `services/commands/shopify/create_shopify_metafield_preferences.py` | API | SELECTs, then a Shopify call per selection, then inserts | 30 s per call | **CONFIRMED** |
| T10 | `services/commands/shopify/sync_shopify_webhook_subscriptions_for_shop.py` | shopify-worker | `session.get`, then a remote list, then per-topic create/delete calls interleaved with flushes | 30 s per call | **CONFIRMED** |
| T11 | `services/commands/shopify/remove_shopify_webhooks_for_shop.py` | shopify-worker | same shape as T10 | 30 s per call | **CONFIRMED** |
| T12 | `services/tasks/shopify/_product_sync_orchestrator.py` `sync_one_product_sync_item` | shopify-worker | only when the payload has `image.image_id`: `SELECT Image`, then several GraphQL product calls | 30 s per call | **CONFIRMED (conditional)** |
| T13 | `services/commands/app_update_slide_media/add_slide_media.py` | API | **slide SELECT … FOR UPDATE**, then **synchronous boto3** `head_object` | botocore defaults (60 s connect / 60 s read + retries; `s3_client.py` sets only the signature version) | **CONFIRMED** (row lock + blocked loop) |
| T14 ✔ | `services/commands/images/confirm_upload.py` | API | inside `session.begin()`: **N sequential synchronous `head_object`** calls | botocore defaults | **CONFIRMED** (blocked loop) |
| T15 | `services/commands/files/confirm_upload.py` | API | `session.begin()` → SELECT → synchronous `head_object` | botocore defaults | **CONFIRMED** |
| T16 | `services/commands/images/soft_delete_image.py` `_run_hard_delete` | API | `session.begin()` → `session.get` → synchronous `delete_object` | botocore defaults | **CONFIRMED** |
| T17 | `services/queries/items/lookup_item_by_article_number.py` | API | `gather` of a DB lookup and a purchase-API GET sharing one session | 3 s / 8 s | **CONFIRMED** (short) |
| T18 | `task_router._route_open_tasks` | task-router | SELECT, then a **synchronous** `redis.rpush` per task, then commit | redis-py default | **CONFIRMED, low impact** |

**Why the synchronous calls (T1, T13–T16) matter twice:** they stall the **entire** event loop of
that process.

- In the API this freezes every other in-flight request, and those requests keep their checked-out
  connections too.
- It explains how the API can reach high concurrent checkouts (and a high-water mark) with modest
  traffic.

**Correctly designed sites (negative evidence):**

- `worker_base._process_task` uses separate claim / handler / finalize sessions ("pool slot is free
  here").
- `handle_send_email_messages` and `handle_send_coordination_email_batch` close the session before
  SMTP.
- The Shopify product orchestrator commits before each stage (except T12).
- The IMAP IDLE watcher holds no session while idling.
- Location-tracker push has no session.
- The scheduler loops sleep outside sessions.

**Unverified side observation:** the delegated sweep reports that T10/T11 may **never commit**. The
first `session.get` autobegins, `maybe_begin` goes subordinate, and the `get_db_session` close rolls
back. That is a correctness question, not a connection one, and it is not verified here.

---

## 9. Engine / process lifecycle

- **API:** the engine is created **once per process in the FastAPI `lifespan`**, not at import
  (`beyo_manager/__init__.py`). It is disposed on shutdown via `close_db()`.
- **Background processes:** the engine is created **once per process** in each `main()`. It is
  never disposed; the process exit closes the sockets.
- **Not per request.** No code creates engines per request.
- **Independent per service:** 10 engines in legacy production.
- **Shutdown disposal** matters little for steady state. It only makes PostgreSQL see a clean
  `Terminate` instead of a socket EOF. Both end the backend.

### 9b. Forking / worker safety — NOT APPLICABLE

There is no Gunicorn and no pre-fork model. If uvicorn `--workers N` were used, uvicorn spawns
fresh interpreters. The engine is created inside `lifespan` (after the spawn), so no pool can be
inherited across processes. No module creates an engine at import time.

---

## 10. Connection recycling behaviour

- **`pool_recycle` = 1800 s** (default; env `DB_POOL_RECYCLE`).
  - It is checked **only at checkout**. A connection older than 30 min is closed and replaced 1:1
    at the moment it is next used.
  - It **does not reduce the count**.
  - It **does not close idle connections that nobody checks out**. With FIFO rotation and low
    traffic, such connections can stay open indefinitely.
  - Effect: periodic backend churn (a new PostgreSQL backend fork, fresh catalog caches, statements
    re-prepared). This may actually *bound* per-backend memory growth (HYPOTHESIS).
  - No comment explains the 1800 choice; it is the common "shorter than server/proxy idle timeouts"
    idiom.
- **`pool_pre_ping` = True:** one ping round-trip per checkout. It replaces dead connections (e.g.
  after an RDS restart) and **does not change the count**.
- **No idle reaper exists.** SQLAlchemy has no "close idle after N seconds" option, and sleep mode
  (`SLEEP_MODE_ENABLED`, 10 min idle threshold) pauses loops but **keeps every pooled connection
  open** (OBSERVED: no `dispose()` anywhere except `close_db`).

---

## 11. Explanation of the observed 31–33 connections

**Classification: B, plausible but not provable from the repository.**

The arithmetic, using the §5b steady-state numbers:

- **Defaults (10/20), single API process, email watcher off:**
  - API ≤ 10, background 8–16, LISTEN 1, giving **19–27**.
  - Plus rdsadmin (a few): **~20–30**.
  - 31–33 needs background high-water marks near 2 each **and** some non-app connections. This is
    possible, but it sits at the edge.
- **`DB_POOL_SIZE=20` (the `.env.example` value), single API process, email watcher off:**
  - API up to 20, plus 8–16, plus 1, giving **29–37**.
  - For example, 20 + 9 + 1 = 30, plus 1–3 rdsadmin, gives **31–33**, an exact fit with background
    processes at ~1.
- **API `--workers 4`:** this would usually exceed 33, so it is less likely (INFERRED).

It is **not category C or D**:

- A number that is stable over time, and resets to a lower level after restarts, matches pool
  high-water retention.
- A leak would climb toward `P + O` per process, produce `QueuePool limit … timed out` errors, and
  show as `idle in transaction` rows. None of that is predicted by the code.
- The long-transaction sites (§8) raise *peaks* and hold rows idle-in-transaction for tens of
  seconds. They do not create permanent extra connections.

**What settles it:** the production API logs its own pool size at every start (see §15). One
`pg_stat_activity` grouping by `client_port`→PID→unit (§15) then attributes every connection.

---

## 12. Confirmed problems

1. **Pool configuration is uniform and unbounded relative to RDS.** Every one of 10 processes gets
   `P=10, O=20` (or whatever the env sets). The theoretical maximum of 271–301 is far beyond
   `max_connections` ≈ 79. Background processes need ~1–2 connections but may *hold* up to P idle
   and *burst* to P+O.
2. **Idle connections are retained forever**, with no reaper and no dispose on sleep. The count is
   set by historical peaks, not current load.
3. **`TimeoutMiddleware` does not stop the handler** (L3). A 504 at 30 s releases nothing.
4. **Transactions are held across external I/O** at ~16 runtime sites (§8), including two with row
   locks (T5, T13), synchronous calls that block the event loop (T1, T13–T16), and one call with
   **no timeout** (T1, Web Push).
5. **Worker processes crash on transient DB errors** (L5), so an RDS stall turns into process
   restarts under systemd.
6. **Production connections are unattributable.** `application_name` is not set at HEAD (the fix is
   uncommitted), so `pg_stat_activity.application_name` is empty for every app connection.
7. **Security, found incidentally:** at HEAD the API startup log line prints `settings.database_url`
   and `settings.redis_url` **unredacted** (`beyo_manager/__init__.py` `lifespan`). The redaction fix
   (`core/logging/redaction.py`) is uncommitted, so production journald very likely contains the
   database password.

---

## 13. Potential problems requiring runtime evidence

- Actual `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_RECYCLE` / `ENVIRONMENT` in production.
- Whether the API runs more than one uvicorn worker.
- Whether `EMAIL_IDLE_ENABLED` is true in production (it is true in the local dev `.env`).
- Whether background high-water marks are 1 or 2.
- How often requests exceed 30 s (504s) and how long they actually run.
- Whether `idle in transaction` sessions appear, and for how long (T1 in particular).
- Deferred async-generator closes (L1) and the unclosed LISTEN connection (L2): look for SQLAlchemy
  GC warnings and duplicate router LISTEN backends.
- Per-backend memory. Relevant contributors: prepared statements (up to 100 per connection),
  catalog caches, `work_mem` usage, and long-lived versus recycled backends.
- Whether `ENVIRONMENT` is unset in production. That would enable SQL `echo` (log volume on EC2)
  and non-secure refresh cookies. This is not a DB-memory issue, but worth knowing.

---

## 14. Information that cannot be determined from code

- The systemd unit files: `ExecStart`, `Restart=`, `RestartSec`, `EnvironmentFile`,
  `TimeoutStopSec` (the decision log mentions a 90 s stop timeout), memory limits. They are not in
  any repository.
- The contents of `/home/ubuntu/config/managerbeyo/.env`.
- Whether **staging**, the **Scanner / Item-Scanner-Shopify** app, BI tools or humans (psql/DBeaver)
  connect to the same RDS instance. The Compose header plans for staging to share it.
- Actual RDS `max_connections`, `superuser_reserved_connections`, parameter group and `work_mem`.
  The "79" is from the deployment repo, not verified.
- Whether GitHub `origin/main` equals the local ref (it was not fetched), and whether pushes from
  other machines triggered deploys.
- Traffic concurrency (it determines the API high-water mark).

**Restart / mass-drop evidence (§14 of the brief):**

- **Deploy restart is OBSERVED.** Every push to `main` runs `systemctl restart` of all 10 units, so
  every app connection drops at once and then regrows lazily.
- **Pushes in the last 14 days**, from the local `origin/main` reflog, time +0200 with UTC in
  brackets. Restarts follow by roughly 1–3 min for Actions queueing, pip and migrations; that
  latency is an estimate.

  | Date | Times (UTC) |
  |---|---|
  | 09-16 | 07:55 (05:55Z) |
  | 09-18 | 16:15 (14:15Z) |
  | 09-22 | 14:06 (12:06Z), 20:34 (18:34Z) |
  | 09-26 | 15:57 (13:57Z) |
  | 09-28 | 13:28 (11:28Z), 15:25 (13:25Z), 16:01 (14:01Z), 16:05 (14:05Z) |

  Pushes from other machines would not appear here.
- **Process crash on DB error (L5)** is OBSERVED in code. During an RDS stall, the workers and
  schedulers exit and systemd (restart policy UNKNOWN, but INFERRED to exist from decision log D9)
  restarts them. That makes the drops a *consequence* of stalls, not a cause.
- **Not found:** cron, scheduled restarts, `RuntimeMaxSec`, worker recycling, health-check restarts.
  Sleep mode does not close connections.

---

## 15. Runtime measurements that would confirm or refute the remaining hypotheses

All read-only.

1. **The pool sizes production actually uses.** On EC2, run
   `journalctl -u managerbeyo-backend | grep 'startup |'`. It shows `env=`, `db_pool_size=`,
   `db_max_overflow=` and `db_pool_recycle=`. **⚠ The same line contains the unredacted
   `DATABASE_URL` and `REDIS_URL`: extract only the pool fields and do not paste the line.**
2. **The unit definitions:** `systemctl cat managerbeyo-*` (ExecStart, `--workers`, Restart=,
   EnvironmentFile).
3. **Attribute every connection to a process** without `application_name`:
   - On EC2: `sudo ss -tnp '( dport = :5432 )'` gives local port → PID.
   - Then `ps -o pid,cmd -p <PID>` gives the unit.
   - Join that to `pg_stat_activity.client_port`.
4. **Connection census** (RDS, read-only):
   ```sql
   SELECT datname, usename, application_name, client_addr, backend_type, state, count(*),
          min(backend_start) AS oldest, max(now() - state_change) AS longest_in_state
   FROM pg_stat_activity GROUP BY 1,2,3,4,5,6 ORDER BY count(*) DESC;
   ```
   This separates app, rdsadmin, staging and other databases, and idle versus active.
5. **Long transactions:**
   ```sql
   SELECT pid, client_port, state, now() - xact_start AS xact_age, left(query, 80)
   FROM pg_stat_activity WHERE state LIKE 'idle in transaction%' ORDER BY xact_age DESC;
   ```
   Sample it repeatedly.
6. **Journald greps (all units):**
   - `QueuePool limit` (pool exhaustion)
   - `garbage collector is trying to clean up` (L1)
   - `Request timed out` / 504 (L3)
   - `Handler timed out`, `task_failed`, `stale_task_recovered` (T1–T12)
   - `slow_query`
   - `LISTEN connection lost` (L2)
   - process start/stop times (compare with RDS drop times)
7. **Deploy correlation:** GitHub Actions "Deploy Backend" run times versus the RDS connection
   drops.
8. **Per-backend memory** (if the RDS role permits): `pg_log_backend_memory_contexts(pid)` on an
   old idle app backend versus a fresh one. Use Enhanced Monitoring's process list for RSS per
   backend.
9. **High-water per process:** the uncommitted `db_pool_peak` checkout logging in `database.py` would
   measure this directly once deployed.

---

## 16. Potential remediations to investigate — DO NOT IMPLEMENT

These are not findings; each needs its own decision.

- **Size pools per process role.** Background processes at P=1–2, O=1–2, which the code supports:
  they are sequential. The API sized from measured concurrency. The Compose D26 budget (API 5+10,
  background 1+1) is an existing proposal; it could be applied to the systemd units via per-unit
  `Environment=` without waiting for the container cutover.
- **Ship the uncommitted `application_name` + `db_pool_peak` changes** first, so every later decision
  is measured.
- **Fix `TimeoutMiddleware`** so a timeout actually cancels the handler, or remove the illusion of a
  bound.
- **Move external I/O out of transactions** (§8): load, then commit/close, then call out, then reopen
  to write. Add explicit timeouts to pywebpush and a botocore `Config`, and run boto3 via
  `to_thread`.
- **Database-side guard:** `idle_in_transaction_session_timeout` on the app role, which caps T1-style
  holds.
- **Make workers survive transient DB errors** instead of exiting.
- **Evaluate** `prepared_statement_cache_size` and `pool_recycle`, or NullPool for rarely active
  background processes, **against measured per-backend memory**, not assumptions.
- **Evaluate** an external pooler (PgBouncer, or RDS Proxy if supported for the instance class)
  only after per-process sizing. The asyncpg prepared-statement cache needs care behind
  transaction pooling.
- **Security:** rotate the DB and Redis credentials if journald holds the unredacted startup line,
  and ship the redaction change.

---

## 17. AWS ARCHITECTURE HANDOFF

### Established facts
- Production = **one EC2 host, 10 systemd services, each a separate Python process with its own
  SQLAlchemy `AsyncAdaptedQueuePool` over asyncpg**. There is no Docker, Gunicorn or Celery. The
  Docker Compose stack in `managerbeyo-deployment/` is **not live yet**.
- Every process uses identical pool settings from environment variables:
  - `DB_POOL_SIZE` (default 10)
  - `DB_MAX_OVERFLOW` (default 20)
  - `DB_POOL_RECYCLE` (default 1800 s)
  - fixed: `pool_timeout=30`, `pool_pre_ping=True`, connect timeout 5 s
- Connections open lazily. Idle pooled connections (up to `pool_size` per process) are **kept
  indefinitely**. Sleep mode, recycle and pre-ping never reduce the count.
- Every deploy (each push to `main`) restarts all 10 services at once.
- The HEAD code does not set `application_name`, so app connections look anonymous in
  `pg_stat_activity`.

### Connection topology
- **API:** 1 uvicorn process (INFERRED; ExecStart UNKNOWN). One session per HTTP request and per
  Socket.IO presence event. Persistent ≈ min(peak concurrency, pool_size).
- **8 always-on background processes:** task-router, tasks, notification, shopify, analytics,
  presence, delayed-scheduler, recurring-scheduler. All sequential, **~1–2 connections each**.
- **Task router:** +1 non-pooled asyncpg `LISTEN` connection.
- **Email IDLE watcher:** exits at start unless `EMAIL_IDLE_ENABLED=true` (production value
  UNKNOWN). If enabled, ~1–3 connections.
- **Deploy-time transients:** alembic (1, NullPool) and `apply_db_triggers.py` (1), sequential.

### Connection budget
- **Steady-state expected:** **19–30** with defaults (10/20); **29–40** if `DB_POOL_SIZE=20`. Add
  rdsadmin and any non-app clients on top.
- **Persistent pool ceiling:** 91 (email watcher off) / 101 (on) with defaults; 181–201 with
  `DB_POOL_SIZE=20`.
- **Overflow ceiling:** 180–200.
- **Theoretical maximum:** **271–301** with defaults; 361–401 with 20/20. This far exceeds
  `max_connections` ≈ 79 (from the deployment repo, unverified).

### Explanation for observed 31–33 connections
**Plausible, not provable (category B).** It is an exact fit for `DB_POOL_SIZE=20` (the
`.env.example` value): API 20 + 8–9 background + 1 LISTEN + 1–3 rdsadmin = 31–33. It is an
edge-of-range fit for defaults, where background processes would need to sit at ~2 each. The shape
(a stable plateau that drops at restarts) matches **pool high-water retention**, not a leak.
Confirm with the API startup log (`db_pool_size=`) and a `pg_stat_activity` census.

### Confirmed connection leaks
**None found.** All sessions use context managers, and SQLAlchemy 2.0.40 closes them in a shielded
task that cancellation cannot skip. A leak would also be capped at `pool_size + max_overflow` per
process and would surface as `QueuePool limit` errors.

### Suspected connection leaks
Both are low risk and need runtime evidence:

1. The task router's LISTEN reconnect loop does not close the old asyncpg connection on some
   exceptions.
2. `return` inside `async for … get_db_session()` defers session close to the async-generator
   finalizer. This is non-deterministic, but it is not a leak.

### Long-held transaction/session risks
~16 runtime sites hold a transaction across external I/O (Shopify, S3/boto3, SMTP/IMAP, Web Push):

- **2 hold row locks** (Shopify OAuth callback, slide media add).
- **Web Push has no timeout** and is synchronous, so the notification worker can sit
  **idle-in-transaction indefinitely**.
- boto3 calls are synchronous, so they block the API event loop while connections are checked out.
- **The 30 s request timeout returns 504 but does not stop the handler or release its connection.**

These inflate *peaks* and *idle-in-transaction time*, not the steady count.

### Relevant configuration
- **`pool_size`:** `DB_POOL_SIZE`, default 10 (dev/example: 20); production UNKNOWN.
- **`max_overflow`:** `DB_MAX_OVERFLOW`, default 20 (dev/example: 20); production UNKNOWN.
- **`pool_timeout`:** 30 s (hard-coded).
- **`pool_recycle`:** `DB_POOL_RECYCLE`, default 1800 s. Applied at checkout only; it does not close
  idle connections.
- **`pool_pre_ping`:** True. It validates connections and does not change the count.
- **Worker/process counts:** 10 systemd units (9 if the email watcher is disabled, since it exits at
  once); API uvicorn worker count UNKNOWN (1 INFERRED).
- **asyncpg settings:**
  - connect timeout 5 s; server setting `timezone=UTC`
  - SQLAlchemy `prepared_statement_cache_size` default **100 per connection** (server-side prepared
    statements live in each backend)
  - no `command_timeout`, no `statement_timeout`, no `idle_in_transaction_session_timeout` set by
    the app

### Unknown production values
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`, `ENVIRONMENT`, `EMAIL_IDLE_ENABLED`
- systemd `ExecStart` (uvicorn `--workers`), `Restart=`, `EnvironmentFile`
- whether staging, Scanner, or human/BI clients share the instance
- RDS `max_connections` / reserved slots / `work_mem`
- per-backend memory

### Recommended connection budget
Conceptual only; no sizing decision is made here.

- **Application steady state:** what the processes *need* is ~1 per background process + 1 LISTEN +
  API measured concurrency. That is roughly **15–20**, versus the ~30 they *hold*.
- **Application burst:** background ~2 each plus API P+O. The Compose D26 proposal is API 5+10 and
  background 1+1, which gives ≈ **32 max per environment**.
- **Reserve on top:**
  - RDS superuser/rdsadmin slots
  - monitoring
  - deploy transients (1–2 for migrations and triggers)
  - human admin sessions (2–3)
  - a **second environment** if staging will share the instance, which **doubles the app share**
    as planned in Compose
- **Size memory for connections × measured per-backend RSS**, not a per-connection constant.

### Evidence relevant to RDS sizing
- The app holds idle connections it rarely uses. Background processes are sequential, but each may
  keep up to `pool_size` idle connections, so the count is inflated by configuration rather than by
  demand.
- Connection count is driven by **historical peaks** and resets **only at deploy or crash**.
- Idle-in-transaction holds (external I/O inside transactions) keep backends and snapshots alive for
  tens of seconds, and indefinitely in the Web Push case.
- Each backend may cache up to 100 prepared statements (a per-backend memory contributor that has
  not been measured).
- Deploys, and RDS-stall-induced worker crashes, cause simultaneous drops and regrowth.
- **Security:** the HEAD startup log prints the unredacted `DATABASE_URL`. Handle journald carefully
  and consider rotating the credential.

### Remaining questions
1. What does `journalctl -u managerbeyo-backend | grep 'startup |'` report for `db_pool_size` and
   `db_max_overflow`? Extract those fields only.
2. What does `systemctl cat managerbeyo-backend` say: one uvicorn worker or several?
3. `pg_stat_activity` census by `datname`/`usename`/`client_addr`/`state`: are all ~31–33 from the
   EC2 host and the production database?
4. Do connection drops align with GitHub Actions deploy runs (§14 timestamps) or precede them (the
   stall causing worker crashes)?
5. Does any app backend sit `idle in transaction` for minutes (Web Push, IMAP, Shopify sites)?
6. What is the RSS of an old idle app backend versus a freshly recycled one?
