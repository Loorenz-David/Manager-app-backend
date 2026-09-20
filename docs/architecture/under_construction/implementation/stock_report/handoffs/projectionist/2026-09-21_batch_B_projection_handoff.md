# Batch B projection — phases 4, 5 (B1) and 6, 7 (B2)

```
plan: 4, 5, 6, 7
role: projection (batch)
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-09-21
actor: pipeline-projectionist (Opus 5, plan-projection)
tree: e548d1f, clean (`git status --porcelain` empty)
intention gate: planning/intention.md status = RATIFIED (round 9) — PASS
write perimeter: this file only. No plan, master-plan, intention or code file touched. No commit.
                 No archgraph write. Three throwaway probe scripts in the session scratchpad
                 (outside the repo); one scratch table created and dropped in the dev DB (§6 below).
```

## Opening (for the orchestrator)

Batch B is implementable, but **not as written**. Seven blockers stop a literal implementer, and
one of them — the task-flag divergence — silently invalidates roughly **fifty** criterion rows of
plans 4 and 5 at once, because every row that ends with `assert_stock_report_clean` while a live
assignment sits on the seeded task will fail against the *shipped* consistency check. Batch A's
lesson L-17 is not a one-off in plan 3; it is the dominant shape in B1. The lesson fold produced
**38 cell replacements** (20 fixture, 18 mutation; counted from §3's four tables), **8 of which
close guards that are provably inert today** — plan 4 C1(g), C1(u), C6(a), C6(c); plan 6 C1(b),
C3(a), C3(g); plan 7 C1(e). One defect lives in an outcome cell and is listed separately. Zero
owner cards.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing in this projection needs the owner. Two items are judgment calls I have made and marked
**[escalate if you disagree]**: the `set_task_stock_flag` workspace predicate (§1.4 N-S3) and the
`write_repair_record` `delta` parameter (§5 B2). Both follow rulings the owner already made on
adjacent surfaces.

---

# 1. B1 projection — phases 4 and 5

## 1.1 Blockers (detail in §5; ids B1…B7)

| id | Where | One line |
|---|---|---|
| B1 | plan 4 §5 task 2 | `recompute_task_stock_flag(session, assignment.task_id)` — the shipped function takes **three** positional args |
| B2 | plan 4 C5(a), plan 5 C2(a) | the warning must carry the delta; shipped `write_repair_record` has no `delta` parameter and logs `delta=None` |
| B7 | plan 4 + plan 5, ~50 rows | `assert_stock_report_clean` reports a `task_flag` divergence whenever a live assignment sits on the seeded task |

## 1.2 Hazards the implementer must be told (B1)

**H1 — F0 is not what the kit returns.** Master plan §6.8 describes F0 as including row **R**, goal
record **G** and assignment **A**. `seed_stock_report_workspace` returns **only**
`SeededWorkspace(workspace, manager, worker, categories, item, task)`. R, G and A are built by each
test as ORM instances (precedent:
`app/tests/integration/services/queries/stock_report/test_consistency_check.py:70-93`). Do not look
for a kit helper that creates them.

**H2 — the seeded task's flag is `false` and nothing in phase 4 raises it.** `move_assignment` never
touches `tasks.is_stock_assignment`; only `remove_assignment` does, via
`recompute_task_stock_flag`. The consistency check compares every task in the workspace against
"does a non-deleted assignment name it" (`consistency.py:101-111, 223-245`). Rule: **a scenario that
ends with a live (non-deleted) assignment on T must seed `T.is_stock_assignment = true`; a scenario
that ends with A soft-deleted must leave it `false`.** See §3 F4-1 / F5-1 for the exact fixture text.

**H3 — the partial unique indexes bite in multi-assignment fixtures.**
`uix_stock_task_assignments_item_active` and `uix_stock_task_assignments_task_active` are unique on
`(workspace_id, item_id)` / `(workspace_id, task_id)` `WHERE is_deleted = false AND state IN
('in_queue','in_progress','awaiting')`. Two *active* assignments therefore need a second `Item` and
a second `Task` (plan 4 C4(b)). Terminal or deleted assignments are exempt (plan 4 C6(b), plan 5
C2(b), C2(d) work on the kit's single item+task — but plan 5 C2(d) must create A1, move it to
`resolved_early`, and only then create A2).

**H4 — `ck_stock_report_items_*_nonneg` fires immediately, not at commit.** That is what makes plan
4 C5(a)'s and plan 5 C2(a)'s "drop the guard" mutations redden as `IntegrityError`. Do not add
`DEFERRABLE`.

**H5 — the ORM instance is stale after every Core `UPDATE`.** `expire_on_commit=False`
(`bm/models/database.py:44-47`) and a raw `session.execute(text(...))` does not expire the identity
map. Read back with a fresh `SELECT` (or `populate_existing`), never from the instance. Plan 4
C4(c) and plan 6 C8(b) both *depend* on this staleness for their mutation to bite — do not "fix" it
by refreshing inside production code.

**H6 — `remove_assignment` writes `tasks` after the row and assignment locks, which inverts MC-1's
lock order (tasks are step 3).** MC-16's cascade resolves this by locking the tasks **first**, up
front, and only then issuing the flag UPDATE. `remove_assignment`'s contract is therefore *the
caller already holds the task lock*; plan 4 never says so. In phase 4's own tests take the task
`FOR UPDATE` before the row lock, so the test models the caller. Record the premise in the handoff.

**H7 — `Task.updated_at` carries `onupdate=lambda: datetime.now(timezone.utc)`**
(`bm/models/tables/tasks/task.py:92-94`). That is exactly why `set_task_stock_flag`'s
`values(is_stock_assignment=value, updated_at=Task.updated_at)` is a Core self-assignment and why
plan 4 C6(c)'s "write the flag via the ORM attribute" mutation bites. It also means **any** ORM
attribute write on a `Task` anywhere in phase 4 silently moves `updated_at`.

**H8 — `set_task_stock_flag` no-ops when the value already matches**
(`Task.is_stock_assignment.is_distinct_from(value)`). A fixture that leaves the flag at its target
value makes every flag mutation inert. This is H2 restated as a mutation-arming rule.

**H9 — the event `extra` may not carry an enum.** `RETURNING StockReportItem.priority` yields a
`StockReportPriorityEnum` member. `event_bus.dispatch` never serializes (handlers do), and phase 4's
tests monkeypatch dispatch away, so a non-JSON-serializable payload passes every test in this batch
and fails in production. **Emit `priority.value` (or `None`) in the `:updated` payload.** No
criterion pins this; declare the decision in the handoff as a candidate criterion.

**H10 — `_locks.py` helpers return `{}` for an empty id set and take `(session, workspace_id,
client_ids)`** — not keyword-only. `lock_*` already sorts and applies `ORDER BY client_id` +
`populate_existing`; do not re-sort at call sites.

**H11 — `apply_goal_effect`'s registered signature has no `workspace_id`**, but the repair record it
writes needs one. Use `assignment.workspace_id`. (Free choice → recorded here on purpose.)

**H12 — `build_workspace_event(entity, event_name, *, workspace_id, extra)` takes an *object* with
`.client_id`**, while §6.5 registers `_events.py`'s builders with a `client_id: str` parameter.
Construct `WorkspaceEvent(event_name=…, client_id=…, workspace_id=…, extra=…)` directly inside
`_events.py` (it is the event-building module and therefore the right home), and say so. Do not
invent a `SimpleNamespace` shim.

**H13 — never run `alembic upgrade` against the dev database, and add no revision.** §9 rule 12:
the schema is fixed in phase 1. Phases 4–7 need no schema change (verified: every column and index
they use exists at `e548d1f`).

## 1.3 Batch A facts phases 4/5 depend on — exact shipped signatures

All verified by reading the code at `e548d1f`.

| Symbol | Shipped signature | First caller |
|---|---|---|
| `recompute_row_counters` | `async def recompute_row_counters(session, stock_report_item_id: str) -> dict[str, int]` — keys exactly `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`; filters `is_deleted false` **and** `state.in_(ACTIVE_ASSIGNMENT_STATES)`; **no workspace filter** (keyed by row id) — `consistency.py:27-47` | **phase 4**, the inline counter self-heal |
| `recompute_goal_total` | `async def recompute_goal_total(session, history_record_id: str) -> int` — Σ `quantity` over `credited_history_record_id == id`, **no `is_deleted` filter, no state filter, no workspace filter** (this is what makes plan 5 C2(b) and C2(d) true) — `consistency.py:75-81` | **phase 5**, `apply_goal_effect`'s self-heal |
| `recompute_task_stock_flag` | `async def recompute_task_stock_flag(session, workspace_id, task_id) -> bool` — **three positional args** (`_task_flag.py:16-20`). §6.5 line 380 is correct; **plan 4 task 2 is wrong** (B1) | **phase 4**, `remove_assignment` |
| `expected_task_flag` | `async def expected_task_flag(session, workspace_id: str, task_id: str) -> bool` — "a non-deleted assignment of this workspace names this task"; **no state predicate** (a `resolved`/`failed`/`resolved_early` assignment keeps the flag `true`) — `consistency.py:101-111` | phase 3; phase 4 C6(b)'s mutation site |
| `set_task_stock_flag` | `async def set_task_stock_flag(session, task_id, value, *, require_update=False) -> None` — §6.5 registers `(session, task_id, value)`; the shipped form adds `require_update`. Predicate is `client_id` + `is_distinct_from(value)`; **no workspace predicate** (N-S3) — `_task_flag.py:6-14` | phase 3 (via repair); phase 4 decides N-S3 |
| `write_repair_record` | `async def write_repair_record(session, *, workspace_id, target_kind, target_client_id, field, stored_value, recomputed_value, trigger, created_by_id, now) -> StockReportRepairRecord` — **no `delta`**; the warning hardcodes `delta=%s` with `None` (`_repair_records.py:44-52`). `_text` maps `bool → "true"/"false"`, `None → None`, everything else → `str(...)` | phase 3; phase 4 (B2) |
| `_locks.py` | `acquire_stock_report_order_lock(session, workspace_id)`; `lock_stock_report_items` / `lock_stock_task_assignments` / `lock_stock_report_history_records` / `lock_items` / `lock_tasks`, each `(session, workspace_id, client_ids) -> dict[str, Model]` | phases 4/5 tests hold the locks manually; 8–13A use the helpers |
| `compute_stock_report_divergences` | `(session, workspace_id) -> list[Divergence]`, sorted by `(kind, client_id, field)`; eight kinds; `task_flag` values are `"true"`/`"false"` strings | `assert_stock_report_clean` |
| test kit | `seed_stock_report_workspace(session, *, suffix=None) -> SeededWorkspace(workspace, manager, worker, categories, item, task)`; `make_ctx(session, seeded, *, role_name="manager", user=None, incoming_data=None, query_params=None)`; `capture_dispatch(monkeypatch, import_site)`; `assert_stock_report_clean(session, workspace_id)`; `purge_stock_report_workspace(session, workspace_id)` | — |
| kit fixture values | item `quantity=4`, `properties {"wood_type": "Teak", "upholstery": "Down"}`, category[0] "Dining Chairs" (SEAT), category[1] "Coffee Tables" (WOOD), task `PENDING` with a PRIMARY `TaskItem`, `is_stock_assignment` **false** | — |
| `record_statements` / `count_writes` | `record_statements(session)` yields `list[str]` — **statement text only, parameters discarded**; `count_writes(statements, tables: set[str])` substring-matches. Engine-wide listener (`session.bind.sync_engine`) | phase 3; phase 6 (B3) |
| the four MC-9 tables | `stock_report_items`, `stock_task_assignments`, `stock_report_history_records`, **`tasks`** (intention §8B MC-9). §12A's instrument (d) adds `stock_report_repair_records` | plan 4 C2, plan 6 C1(c)/C4 |
| enums shipped | `StockTaskAssignmentStateEnum` (6 members), `ACTIVE_ASSIGNMENT_STATES`, `TERMINAL_ASSIGNMENT_STATES`, `StockReportPriorityEnum`, `StockReportHistoryRecordTypeEnum`, `StockReportRepairTargetKindEnum`, `StockCriteriaMismatchReasonEnum`. **Not shipped:** `StockDemandOutcomeEnum`, `StockDemandDeletedOutcomeEnum`, `ItemsProcessedOutcomeEnum`, `ItemsProcessedReasonEnum`, `REPAIR_TRIGGER_MANUAL`, `INLINE_REPAIR_TRIGGERS` (B4) | — |

## 1.4 Routed debt landing in B1

**N-S3 — `set_task_stock_flag` has no workspace predicate. Phase 4 decides it.**
Recommendation: **close it**, mirroring the owner's card-1 ruling on the read half. Concretely —
`async def set_task_stock_flag(session, workspace_id, task_id, value, *, require_update=False)`
with `Task.workspace_id == workspace_id` added to the `where`, and `recompute_task_stock_flag`
(the only caller, which already holds `workspace_id`) threading it. Cost: two lines, one call site,
zero behaviour change today. **Because no criterion pins it, plan 4 must declare it in its Review
log as a deviation *and* a candidate criterion** (charter trace-chain link 3): "the guard that
`set_task_stock_flag` cannot cross a tenancy line has no test". The orchestrator then folds a row
or refuses it with a recorded reason. Also amend master plan §6.5's `_task_flag.py` row in the same
act (lesson L-18 — N-S2 is still open on that row: it still registers
`recompute_task_stock_flag(session, task_id)`). **[escalate if you disagree]**

**N-R1 — the goal-total lock set is computed from the pre-lock read. Lands in phase 5.**
What the implementer must do: **nothing to `apply_goal_effect`, and explicitly not a lock on `R`.**
Intention §6A MC-5's round-7 re-check settles this: *no lock is taken on `R` itself*; what protects
`R` is the moving assignment's **row** lock, which every writer of any goal total of that row holds.
Phase 5 adds a second writer of goal totals, so the correct phase-5 obligation is to **prove the
premise, not to add a lock**: `apply_goal_effect` is unreachable except under the caller's row lock,
and plan 5's tests hold row + assignment `FOR UPDATE` before calling. The residual N-R1 window is a
defect in `repair_stock_report`'s lock-set computation (phase 3 code, outside B1's perimeter) —
carry it forward, do not fix it in phase 5, and say so in the handoff.

**N-R3 — the three uncalled helpers.** `recompute_row_counters` gets its first caller in **phase 4**
(the inline counter self-heal); `recompute_task_stock_flag` in **phase 4** (`remove_assignment`);
`recompute_goal_total` in **phase 5** (`apply_goal_effect`'s self-heal). After B1 only
`set_task_stock_flag`'s direct use remains indirect. Charter rule 4 is discharged for two of the
three by plan 4 C5(a)/C5(c)/C6(a) and for the third by plan 5 C2(a)/C2(b)/C2(d). **Confirm the
discharge explicitly in the batch handoff** — L-8's proposal of one registry criterion per phase is
still unimplemented, so the discharge is otherwise invisible.

## 1.5 Lock order and transaction shape, phases 4–5

MC-1's global order is advisory → `items` → `tasks` → `stock_report_items` →
`stock_task_assignments` → `stock_report_history_records`, ascending `client_id` within a class.

| Phase | Who opens the transaction | Locks held on entry | Write order inside |
|---|---|---|---|
| 4 `move_assignment` | **nobody** — it never opens, commits or dispatches; the test transaction owns it | caller holds row (4) + assignment (5), state/`is_deleted` re-read | own columns + flush → guarded counter UPDATE → *(phase 5 inserts here)* → events |
| 4 `remove_assignment` | same | **plus the task (3), per H6** | `move_assignment(…, ASSIGNMENT_DELETE)` → `recompute_task_stock_flag` (writes `tasks`) |
| 5 `apply_goal_effect` | same | row (4) + assignment (5); **no lock on `R`**, by contract | memory clear is part of step 1's own-columns write and is flushed **before** any statement on `R` → guarded history UPDATE → self-heal |

**Mutually consistent?** Yes, with one gap: plan 4 does not state H6 (the task lock premise for
`remove_assignment`). Plan 5's insertion point ("after the counter statement, before the events") is
consistent with plan 4's step (4) placeholder and with MC-1's write order. Plan 5 note 4 correctly
derives `recomputed = 0` in C2(a) from the memory-clear-before-Σ ordering.

---

# 2. B2 projection — phases 6 and 7

## 2.1 Blockers (detail in §5)

| id | Where | One line |
|---|---|---|
| B3 | plan 6 C7(a) | `record_statements` discards parameters and the statement text carries `$1` — the row is unmeasurable with the shipped helper |
| B4 | plan 6 | `StockDemandOutcomeEnum` was never shipped by phase 1, and `enums.py` is outside plan 6's declared perimeter |
| B5 | plans 6 + 7 | `apply_stock_demand` refuses a session with an open transaction; `db_session` autobegins on the kit's first `flush()` |
| B6 | plan 7 C7(a) | the prescribed monkeypatch also freezes the command's own deadline computation, so the deadline can never be exceeded |

## 2.2 Rule-17 producibility pass — measured, not assumed

Everything plans 6 and 7 assert about a dependency was re-measured today against the installed
stack: **PostgreSQL 18.6** (`show server_version` = `18.6 (Debian 18.6-1.pgdg13+2)`, `localhost:5433`
from `app/.env`), SQLAlchemy **2.0.40**, asyncpg **0.30.0**, Starlette **0.46.2**, FastAPI
**0.115.12**, CPython **3.13.2**. The re-check handoff §2 measured on Postgres 17.9; these are the
18.6 confirmations the plan-6 note asks for.

| Claim | Plan row | Measured result on 18.6 |
|---|---|---|
| `SELECT set_config('statement_timeout', :ms, true), set_config('lock_timeout', :ms, true)` works parameterized | 6 task 2 step 1 | ✅ returns `('5s','5s')`; `SHOW statement_timeout` = `5s` |
| no leak to the next transaction on the same pooled connection | MC-9 | ✅ `SHOW` = `0` |
| equal limits on a lock wait → **57014** (statement timer first), as `sqlalchemy.exc.DBAPIError` with `.orig` = adapter `Error` | 6 C7(b) | ✅ `DBAPIError`, `orig` type `Error`, `sqlstate 57014`, elapsed 0.31 s at a 300 ms limit |
| `INSERT … ON CONFLICT (ws, cat, sig) WHERE is_deleted = false DO NOTHING RETURNING client_id` infers the **partial** unique index and returns only newly inserted rows | 6 task 2 step 5, C4(b), C5(a) | ✅ 2 VALUES, 1 conflicting → `RETURNING` = the one new id only |
| a waiting `SELECT … FOR UPDATE` re-evaluates its `WHERE` on the committed version and **drops** a row soft-deleted by the locker | 6 task 2 step 6, C5(c) | ✅ waiter blocked 0.4 s, then returned the set **without** the soft-deleted row |
| `dict(request.headers)` keys are lower-cased under `TestClient` | 7 C1(j), C5(c) | ✅ `{'host':…, 'x-api-key': 'k', 'x-weird-case': 'v', …}` |
| `hmac.compare_digest(str, str)` with non-ASCII raises `TypeError` | 7 C1(f) | ✅ `TypeError: comparing strings with non-ASCII characters is not supported` |
| `json.loads` keeps the **last** duplicate key | 7 note, MC-3 | ✅ `{"a":1,"a":2}` → `{'a': 2}` |
| `type(True) is int` is False | 7 C2(u) | ✅ |
| `json.loads(b"\xff\xfe")` raises **`JSONDecodeError`**, not `UnicodeDecodeError`; `b"\xff\xfe".decode("utf-8")` raises `UnicodeDecodeError` | 7 C2(a) | ✅ both — see H20 |
| `json.loads("5.0")` → `float`, `json.loads("true")` → `bool` | 7 C2(t)/(u) | ✅ |
| signature is key-order-insensitive; `{"n":1}` ≠ `{"n":1.0}`; keys are neither lowered nor stripped | 7 C4(a)/(f)/(g)/(h) | ✅ all four confirmed against the shipped `normalize_stock_criteria` |
| a repeated `:ms` bindparam compiles to **one** `$1` and **one** parameter | 7 —, **6 C7(a)** | ⚠️ `"… set_config('statement_timeout', $1, true), set_config('lock_timeout', $1, true)"` with `parameters = ('5000',)` — **one** parameter. See §4 O1 |

**Record these versions in plan 6's and plan 7's Review logs** (plan 7 note 2 requires it).

## 2.3 Hazards the implementer must be told (B2)

**H14 — every phase-6 and phase-7 integration test is a *committing* test.** `apply_stock_demand`
asserts `not session.in_transaction()`; `db_session` (`app/tests/conftest.py:107-111`) is a bare
session that autobegins the moment the kit flushes. Shape:
`seed → await db_session.commit() → AD(...) → assertions → finally: purge_stock_report_workspace +
commit`. This is B5. It also makes §9 rule 1 and charter rule 11½ binding on every row in plans 6
and 7 — there is no rollback safety net.

**H15 — `record_statements` listens on the *engine*, not the session.** Every statement of every
session on that engine lands in the list. Open the window **after** the seed commit, close it
before the purge, and in the two-session rows (C5(a), C5(b), C5(c)) keep the holder session's
writes outside the window.

**H16 — the statement budget is tight, not loose.** Derived from the plan's own step list:
all-new = steps 1,2,3,4,5,6,7,8 = **8** (the bound is exact, not slack); all-changed = 1,2,3,4,6,7,8
= 7; all-unchanged = 1,2,3,4,6 = **5** (matches C6(c)); unknown-category = one fewer where the
INSERT/UPDATE is skipped. Any extra `SELECT` anywhere — a stray `session.get`, an autoflush, a
lazy-load — breaks C6. Build the demand path with Core statements only and no ORM loads.

**H17 — step 6 must re-discover client_ids by *identity*, never reuse the ids generated for step
5's VALUES.** `ON CONFLICT DO NOTHING` returns nothing for a conflicting row, so the locally
generated ULID for that identity is not the row's id. Locking by identity is also what keeps two
concurrent requests on one lock order (C5(a), C5(b)).

**H18 — `set_config`'s returned text is `'5s'`, not `'5000'`.** Assert on the *bound parameter*, not
on the result and not on `SHOW`.

**H19 — patch the module *reference*, not the shared `time` module.**
`monkeypatch.setattr(apply_stock_demand.time, "monotonic", f)` mutates the real `time` module for
the whole process — including `asyncio`'s event-loop clock (`BaseEventLoop.time()` calls
`time.monotonic()`), which will corrupt any `asyncio.wait_for` running at the same moment. Use
`monkeypatch.setattr(apply_stock_demand, "time", <stub exposing monotonic>)`. For plan 7 C7(a) this
is not merely hygiene: the global form makes the row unachievable (B6).

**H20 — decode before `json.loads`.** `json.loads(b"\xff\xfe")` already raises `JSONDecodeError`, so
a parser that skips the explicit UTF-8 decode still passes C2(a). Implement MC-8 step 5 as written
(`raw.decode("utf-8")` in its own `try`), and catch `UnicodeDecodeError` **and**
`json.JSONDecodeError`.

**H21 — `uq_item_categories_workspace_name` is a plain UNIQUE on `(workspace_id, name)`,
case-sensitive and *not* partial on `is_deleted`.** So "Dining Chairs" + "dining chairs" in one
workspace is legal (plan 6 C2(c)/(d), plan 7 C3(d) depend on it), and a soft-deleted category still
holds its name (plan 6 C2(g)).

**H22 — two routers now share the `/api/v1/location-tracker` prefix.** The existing
`location_tracker.router` is mounted there (`routers/api_v1/__init__.py:137-141`) and exposes
`/items/location` only; no path collides with `/webhooks/stock-demand`. Add the new mount, do not
move the old one. `bm/services/infra/location_tracker/` **already exists** (`client.py`,
`constants.py`, `mapper.py`, `models.py`, `__init__.py`) — plan 7's "`__init__.py` (if absent)" is
already satisfied; add only `webhook_verifier.py`.

**H23 — `bm/errors/stock_report.py` does not exist.** Phase 6 creates it (plan 6's file list is
right). Bases available: `DomainError` (`errors/base.py`, `http_status = 500`), `ValidationError`
and `ConflictError` (`errors/validation.py`).

**H24 — the envelope claims in plan 7 C5(c) are exact.** `build_ok(data)` →
`{"data": …, "ok": true, "warnings": []}`; `build_err(error)` → `{"error": error.message, "ok":
false}` with `status_code = error.http_status` (`routers/http/response.py`). `run_service` turns a
`DomainError` into `StatusOutcome(success=False, error=exc)` and anything else into a generic 500.

**H25 — C7(b) is the only sleeping test and it commits.** ~8 s wall time, its own file
(`test_apply_stock_demand_timing.py`), excluded from L1 loops **by file, never by `-k`** (§9 rules 8
and 10). The holder must hold for `default + 3000 ms` so that the 5 s statement timer fires first.

## 2.4 Batch A facts phases 6/7 depend on

Beyond §1.3: `normalize_stock_criteria(raw) -> dict` and
`compute_stock_criteria_signature(raw) -> str` (`domain/stock_report/criteria_normalization.py`,
`CRITERIA_NORMALIZATION_VERSION = 1`); the identity index
`uix_stock_report_items_identity_active` on `(workspace_id, item_category_id,
properties_signature) WHERE is_deleted = false`; `StockReportItem.quantity_requested` with
`server_default="0"`; `StockReportHistoryRecord` with
`ck_stock_report_history_records_quantity_awaiting_nonneg`; the three settings
(`config.py:67-69`, defaults `None`, `None`, `5000`) — read the timeout default as
`Settings.model_fields["stock_demand_webhook_timeout_ms"].default`, never as a literal (charter rule
13); `ServiceContext(identity, incoming_data, session, query_params, now)` with `now` defaulting to
`datetime.now(timezone.utc)` and `workspace_id` reading `identity.get("workspace_id", "")`.

## 2.5 Routed debt landing in B2

The three routed notes (N-S3, N-R1, N-R3) all land in B1. The one item routed to phase 6 by
re-review 1 is **"deleted `Settings` coverage (3 settings)"**: fix round 1 deleted
`app/tests/helpers/test_settings.py` (an orphan that also caused a basename collision), taking the
only coverage of the three new settings with it. Plan 6 C7(a) reads the timeout default from the
class and is the row that restores it; the two `str | None` settings are covered by plan 7 C1(a)–(c).
**Confirm the restoration in the batch handoff.** Related standing hazard, outside the perimeter:
`app/tests/helpers/test_settings.py` still exists as a test-named helper module (N-R9) — any future
`test_settings.py` under `tests/` re-creates the collection error. Do not rename it in batch B.

## 2.6 Lock order and transaction shape, phases 6–7

| Phase | Transaction | Locks | Consistent? |
|---|---|---|---|
| 6 `apply_stock_demand` | **owner mode**, one `maybe_begin`, refuses a pre-open transaction | `stock_report_items` only (MC-1 step 4), one sorted `FOR UPDATE ORDER BY client_id`; **no advisory lock**, no item/task locks; history is INSERT-only (step 6 of the order) | ✅ consistent with MC-1 (demand is not an ordering operation, so the advisory lock is correctly absent — phase 13A takes it because it cascades through ordering) |
| 7 `receive_stock_demand_webhook` | opens nothing; `apply_stock_demand` is the owner | — | ✅ — but the deadline is computed on the **first line** of the command, before verify and parse, so the 5 s budget covers the whole request |

Cross-batch: B1's transaction shape (subordinate, caller-owned) and B2's (owner mode) do not meet in
this batch — `move_assignment` has no demand-path caller until phase 8/9. No contradiction found.

---

# 3. Fold table — mutation and fixture cells (31)

Read `F` = fixture cell, `M` = mutation cell. "Replacement text" is verbatim cell content.

## 3.1 Plan 4

| Row | Lesson | Why the current cell is defective | Exact replacement text |
|---|---|---|---|
| **F4-1** — the `Fixture:` preamble above the table (§6, line 100) | L-17 / L-16 | Measured: `compute_stock_report_divergences` reports a `task_flag` divergence for any task with a live assignment and a `false` flag (`consistency.py:223-245`; shipped proof `test_consistency_check.py:97-112`, which asserts exactly this pair). The kit seeds `is_stock_assignment = false` and `move_assignment` never writes it. So **every row whose outcome says "clean", and every row that enumerates the check's exact output (C5(a), C5(b)), fails as written** — ~50 rows. Conversely, rows ending soft-deleted must *not* pre-set the flag. | `Fixture: **F0** with row R at `quantity_requested 10`, **no goal record**, assignment A `q = 4` in the stated state, counters pre-set to the consistent values for that state (e.g. A `in_queue` → R `quantity_in_queue = 4`). **Task flag:** `move_assignment` never writes `tasks.is_stock_assignment`, and MC-20 compares every task against "a non-deleted assignment names it". So a scenario that **ends with A non-deleted** seeds `T.is_stock_assignment = true` by raw SQL (`UPDATE tasks SET is_stock_assignment = true WHERE client_id = :t`, which bypasses `onupdate`), and a scenario that **ends with A soft-deleted** leaves it `false` — rows C1(g), C1(k), C1(p), C1(q), C1(r), C1(u), C5(c), C7(c). Every assignment added beyond A brings its own `Item` and `Task` when it is active (the two partial unique indexes), and each such task follows the same rule. `MV(from → to)` = call `move_assignment` for that pair. "counters" = the triple `(in_queue, in_progress, awaiting)` read back by a fresh `SELECT`.` |
| **F4-2** C4(b) | L-16 | "Two assignments on R: A `q = 3` `in_queue`, B `q = 5` `in_queue` (different items/tasks)" names the constraint but not the objects; the kit seeds one item and one task, so a literal implementer hits `uix_stock_task_assignments_item_active` / `…_task_active`. | `Two assignments on R: A `q = 3` `in_queue` on the kit's (I, T), B `q = 5` `in_queue` on a **second** item I2 and task T2 created in the same workspace (both partial unique indexes are on `(workspace_id, item_id)` and `(workspace_id, task_id)` over the active states, so two active assignments cannot share either); counters `(8,0,0)`; both T and T2 seeded `is_stock_assignment = true`; move A` |
| **F4-3** C6(a) | **L-10 (inert by construction)** | The mutation is "skip the recompute" and the outcome is `is_stock_assignment` **false**. The kit seeds the flag `false`, so with the recompute skipped the flag is *still* false and the row stays green. The mutation cannot fail. (Reinforced by `set_task_stock_flag`'s `is_distinct_from` no-op, `_task_flag.py:11`.) | `T with A only (A `in_queue`, live), and `tasks.is_stock_assignment` seeded **`true`** by raw SQL before the call — otherwise "skip the recompute" leaves the flag at the value the row asserts and the mutation cannot fail; `remove_assignment`` |
| **F4-4** C6(b) | L-16 | Same inertia risk in the other direction, plus the unnamed second item. B is `resolved`, so it is exempt from the active-state index and may share T. | `T with A (`in_queue`, item I) and B (`resolved`, a **second** item I2, same task T — legal because the partial unique indexes cover only the three active states), `tasks.is_stock_assignment` seeded **`true`**; remove A` |
| **F4-5** C6(c) | L-10 + L-5 | With the flag seeded `false` the Core UPDATE matches 0 rows and the ORM-attribute mutation writes an equal value, so nothing flushes and the mutation is inert. Separately, `tasks.updated_at`/`updated_by_id` are `NULL` on a fresh seed, so "byte-identical" compares `NULL == NULL` and cannot catch a write that *clears* the stamps. | `(a) again (flag seeded **`true`**), with `tasks.updated_at` and `updated_by_id` first set to known non-null values by raw SQL (`UPDATE tasks SET updated_at = :t_seed, updated_by_id = :u …`, which bypasses `onupdate`), both recorded before the call` |
| **F4-6** C7(d) | L-9 | "any move" is not a fixture; and with `R.updated_at`/`updated_by_id` `NULL` the row cannot distinguish "did not stamp" from "stamped NULL". | `C1(d)'s move (`MV(in_queue → in_progress)`, actor U, `now = t0`), with R's `updated_at` and `updated_by_id` first set to known non-null values (`t_seed`, X) by raw SQL` |
| **F4-7** C4(c) | L-5 | The row's bite depends on an unstated precondition — the ORM instance must stay stale. `expire_on_commit=False` and a raw `text()` UPDATE does not expire the identity map, but an `expire`/`refresh`/`populate_existing` anywhere in the test destroys the mutation. | `Load R into the session (`session.get(StockReportItem, R)`), then raw `UPDATE stock_report_items SET quantity_requested = 99 WHERE client_id = :r` in the same transaction — do **not** expire, refresh or re-select R afterwards, because the mutation's bite is exactly that the identity-mapped instance still reads 10; then `MV(in_queue → in_progress)`` |
| **M4-1** C1(a)–(c) | **L-12** | One mutation for a row with three sub-checks (counters, events, clean). "delta sign flipped" reaches only the *clean* sub-check: the self-heal repairs the counters back to `(4,0,0)` and the events are built from the repaired `RETURNING`, so the counter and event assertions stay green and only the repair-record half of the helper reddens. The counter sub-check has no mutation at all. | `enumerated, `_move_assignment.py` (definition site): (i) **skip the `+q` on the creation target** (`dq` vector all-zero for `is_creation=True`) → counters stay `(0,0,0)` → the counter assertion reddens; (ii) **flip the delta sign to `−q`** → the guard trips → self-heal repairs the counters, so (ii) reddens **only** the repair-record half of `assert_stock_report_clean`; (iii) **build the assignment event with kind `state-changed` instead of `created`** → the event assertion reddens. Record which of the three reddened which sub-check.` |
| **M4-2** C1(g) | **L-10 (equivalent mutant)** | "soft-delete after the counter statement" is *semantically identical* here. From `(4,0,0)` the guard is `4 − 4 ≥ 0` → the statement succeeds on the first try, so the recomputation is never reached and the write order is unobservable. Counters, stamps, events and the check are byte-identical under the mutant. The cell already concedes the real bite is C5(c). | `enumerated, `_move_assignment.py` (definition site): (i) **skip the `−q` for the `DELETE` target** (treat `DELETE` like a terminal target, which moves nothing) → counters stay `(4,0,0)` → red; (ii) **emit the assignment event with kind `state-changed` instead of `deleted`** → red; (iii) **write `updated_by_id`/`updated_at` instead of `deleted_by_id`/`deleted_at`** → `deleted_at` stays NULL → red. (The write-order mutation "soft-delete after the counter statement" is an **equivalent mutant on this row** — the guard never trips from a consistent counter — and is carried by C5(c), where drift makes it observable.)` |
| **M4-3** C1(u) | **L-10** | The cell names two mutations; the second, "subtract `q`", is inert. A `resolved_early` source has no active *from* counter, so a mutant that subtracts writes `0 − 4` into `quantity_awaiting`, trips the guard, self-heals to the recomputed `0`, and leaves "counters unchanged" true. The row asserts no repair record, so nothing observes it. | `enumerated, `_move_assignment.py` (definition site): (i) **emit the `stock_report_item:updated` event anyway** (drop the "no counter moved ⇒ no `:updated`" rule) → the event list has two entries → red; (ii) **classify `resolved_early` as active in the allowed-move/counter table** (i.e. include it in the set read from `ACTIVE_ASSIGNMENT_STATES`) → the `resolved_early → DELETE` cell becomes a counted move and `deleted_by_id`/the event kind change → red. ("subtract `q` from `quantity_awaiting`" is an **equivalent mutant** here: the guard trips and the self-heal restores `0`, leaving every assertion of this row true.)` |
| **M4-4** C5(b) | L-9 | "fire inline repair on any mismatch" names no site and no shape; the production code has no comparison to mutate — the self-heal block is reached only on a 0-row result. A literal implementer cannot apply it. | `run the self-heal block unconditionally instead of only on a 0-row result: in `_move_assignment.py` (definition site), after the guarded UPDATE returns **1** row, compare each `RETURNING` counter against `recompute_row_counters(session, R)` and, on any difference, write the repair record and the absolute UPDATE → one record appears and "**zero** repair records" reddens` |
| **M4-5** C2(a)–(f) | **L-12** | "write equal values" reaches the `count_writes == 0` sub-check (the all-zero counter UPDATE is still an UPDATE) but not the "no stamp change" sub-check independently, and not the `returns []` sub-check. Three sub-checks, one mutation. | `enumerated, `_move_assignment.py` (definition site): (i) **drop the `=`-cell early return** and fall through to the normal path (own-columns write + all-zero counter UPDATE) → `count_writes` over the four MC-9 tables becomes ≥ 1 → red; (ii) **stamp `updated_by_id`/`updated_at` before the `=` check** → the assignment's stamps move → the "no stamp change" assertion reddens; (iii) **return the event list instead of `[]`** → the return-value assertion reddens.` |

## 3.2 Plan 5

| Row | Lesson | Why the current cell is defective | Exact replacement text |
|---|---|---|---|
| **F5-1** — the `Fixture:` preamble (§6, line 68) | L-17 / L-16 | Identical to F4-1: "Every row ends with `assert_stock_report_clean` unless it plants drift" is unachievable while the seeded task's flag disagrees with the live assignment. Plan 5 additionally never says the row's counters must be pre-set consistently, which plan 4's preamble does. | `Fixture: **F0** with goal record **G** (type `quantity_requested_change`, `quantity_requested 10`, `quantity_awaiting 0`, `created_by NULL`) inserted as an ORM instance with an **explicit** `created_at`; where a second goal **G2** is named it is inserted with an **explicit, strictly greater** `created_at` (the current-goal rule orders by `(created_at, client_id)` and ULID client_ids do not order reliably inside one millisecond). R's three counters are pre-set to the values consistent with A's stated state, and `tasks.is_stock_assignment` follows plan 4's rule: seeded **`true`** wherever A ends non-deleted, left **`false`** for the rows that end with A soft-deleted — C1(i), C1(l), C1(q), C2(c), and step (6) of C3(a). Every row ends with `assert_stock_report_clean` unless it plants drift. `mem(A)` = `credited_history_record_id`.` |
| **F5-2** C1(j) | **L-14** | "then G2 inserted (awaiting 0)" leaves the two candidate current-goal keys able to agree *or* tie. `created_at` defaults to `datetime.now(timezone.utc)` at flush; two inserts in one test can share a timestamp, and the tiebreaker `client_id` is a ULID whose intra-millisecond ordering is random. The row's whole point — that the subtraction lands on the *credited* record, not the *current* one — is then non-deterministic. | `A `awaiting` `mem = G` (`G = 4`), G inserted with an explicit `created_at = t0`; then G2 inserted with an explicit `created_at = t0 + 1 s` (awaiting 0) so `current_goal_record_id` is unambiguously G2 regardless of ULID ordering; `MV(awaiting → in_progress)`` |
| **F5-3** C3(a) | **L-14** | Same defect inside the worked sequence: step (2) "G2 inserted (0)" must be strictly later than G1 or steps (4)–(6) credit the wrong record. | `The worked sequence, exact: row at 10 with G1 (0) inserted at an explicit `created_at = t0`; steps (1) A `q = 4` `∅ → awaiting`; (2) G2 inserted with an explicit `created_at = t0 + 1 s` (0); (3) `MV(awaiting → in_progress)`; (4) `MV(in_progress → awaiting)`; (5) `MV(awaiting → resolved)` with actor None; (6) `remove_assignment` (which needs the workspace id — `recompute_task_stock_flag(session, workspace_id, task_id)`). `tasks.is_stock_assignment` seeded `true` and left to the step-(6) recompute.` |
| **F5-4** C2(d) | L-16 / H3 | "A1 `resolved_early` … (via `MV(in_queue → resolved_early)`); A2 `awaiting`" is unordered. If A2 exists while A1 is still `in_queue`, both are active on the kit's single (I, T) and `uix_stock_task_assignments_item_active` rejects the second. The row also never says G reaches 5 legitimately before the drift is planted. | `In this order on the kit's (I, T): A1 `in_queue` `q = 2` → `MV(in_queue → resolved_early)` (G becomes 2, `mem(A1) = G`; A1 is now terminal so the active-state unique indexes free the pair); then A2 created `awaiting` `q = 3` with `mem = G` (G becomes 5); then raw `UPDATE stock_report_history_records SET quantity_awaiting = 0 WHERE client_id = :g` (truth 5); then `MV(A2: awaiting → in_queue)`` |
| **F5-5** C2(b) | L-16 | "A1 `resolved`, `mem = G`, `q = 2`, then soft-deleted (`is_deleted true`, memory kept)" does not say the soft-delete is written directly (no delete path exists in phase 5) nor that A1 must be terminal before A2 is active. | `A1 inserted `resolved` with `mem = G`, `q = 2`, then soft-deleted **by direct column write** (`is_deleted = true`, `deleted_at` set, `credited_history_record_id` left at G — there is no delete command in this phase); A2 then created `awaiting`, `mem = G`, `q = 3` on the same (I, T) (legal: A1 is neither active nor live); raw `UPDATE stock_report_history_records SET quantity_awaiting = 0 WHERE client_id = :g` (truth 5); `MV(A2: awaiting → in_queue)`` |
| **M5-1** C1(m) | L-12 | Cell is `—` with no mirror row to inherit from (unlike plan 4, plan 5 has no "mirror rows carry `—`" note). MC-5 row 8 — "`in_queue / in_progress / failed` → anything, memory NULL by construction, no history effect" — is the one MC-5 row with no armed mutation in this plan. | `credit on entering **any** terminal state (extend the credit test from `{awaiting, resolved_early}` to `TERMINAL_ASSIGNMENT_STATES ∪ {awaiting}`), `_goal_credit.py` (definition site) → `G` is credited 4 and a history write appears → red` |
| **M5-2** C1(c), C1(g), C1(h), C1(i) | L-12 | Four `—` cells in a plan with no stated mirror convention. They are genuine mirrors of C1(b) and C1(f), but nothing in the plan says so, and the batch-A ledger rule is `executed == declared`. | (C1(c)) `— (mirror of (b): the same credit statement with a different *from* state; declared as a mirror so the ledger's `declared` count is honest)` · (C1(g), C1(h), C1(i)) `— (mirror of (f): the same guarded subtraction and memory clear; declared as mirrors)` |
| **M5-3** C2(c) | L-9 | Same defect as plan 4 M4-4: "fire inline on any mismatch" names no site and no applicable code. | `run the self-heal block unconditionally instead of only on a 0-row result: in `_goal_credit.py` (definition site), after the guarded subtraction returns **1** row, compare `G`'s value against `recompute_goal_total(session, G)` and write a record + absolute UPDATE on any difference → a record appears on the first move and "no repair record from either move" reddens` |

## 3.3 Plan 6

| Row | Lesson | Why the current cell is defective | Exact replacement text |
|---|---|---|---|
| **F6-1** — the `Fixture:` preamble (§6, line 107) | L-17 (unachievable as written) | `AD(...)` cannot run on `db_session` once the kit has flushed: `apply_stock_demand` asserts `not session.in_transaction()` and the kit's `flush()` autobegins. Every row in this plan is affected. The preamble also never states the purge obligation that committing tests carry. | `Fixture: **F0**'s workspace W with categories K ("Dining Chairs") and K2 ("Coffee Tables"); entries are built with `DemandEntry` from raw dicts via `normalize_stock_criteria`/`compute_stock_criteria_signature`. **Every row in this plan is a committing test:** `apply_stock_demand` opens its own owner-mode transaction and refuses a session that is already in one, while the phase-1 kit autobegins on its first `flush()`. So each row runs `seed → await db_session.commit() → AD(...) → assertions → finally: await purge_stock_report_workspace(db_session, W); await db_session.commit()` (§9 rule 1, charter rule 11½). `AD(entries)` = `apply_stock_demand(session, workspace_id=W, entries, now=t0, deadline=+60 s, timeout_ms=<default>)`. "no write" = `count_writes` over the four MC-9 tables `== 0`; the `record_statements` window is opened **after** the seed commit and closed **before** the purge, because the listener attaches to the engine and would otherwise record both. Every non-timing row ends with `assert_stock_report_clean`.` |
| **F6-2** C3(g) | **L-16 (inert by construction)** | The mutation is "copy the counter", and the fixture sets only `priority` and `priority_order`. The row's `quantity_awaiting` is therefore `0`, which is exactly the value the outcome demands — the mutant writes `0` and the row stays green. Only a **non-zero live counter** can arm it, and the counter must be legitimate or `assert_stock_report_clean` reddens for the wrong reason. | `The row exists with `priority = high`, `priority_order = 2` (set by raw SQL) **and a live `awaiting` assignment of `q = 3` on the kit's (I, T)**, so the row's `quantity_awaiting` is legitimately **3** and the workspace is still clean (seed `tasks.is_stock_assignment = true` for T, per MC-20's task-flag rule); entry raises the quantity. Without the non-zero live counter the "copy the counter" mutation writes the same `0` the outcome asserts and cannot fail.` |
| **F6-3** C7(a) | L-17 / B3 | `record_statements` yields statement **text only** (`app/tests/helpers/statement_listener.py:6-17`); the parameters argument is discarded. Measured: the compiled statement is `SELECT set_config('statement_timeout', $1, true), set_config('lock_timeout', $1, true)` with `parameters = ('5000',)` — the value never appears in the text. The row is unmeasurable with the shipped helper. See §4 O1 for the parameter-count question, which is an outcome matter. | `setting unset (default); a parameter-capturing listener around `AD` — add `record_statement_calls(session)` to `app/tests/helpers/statement_listener.py`, an `asynccontextmanager` yielding `list[tuple[str, Any]]` of `(statement, parameters)` from the same `before_cursor_execute` hook, leaving `record_statements` and `count_writes` untouched so batch A's one caller (`test_repair_stock_report.py:333`) stays green. The value is never in the statement text: SQLAlchemy compiles the bind to `$1` and passes `('5000',)`, and `set_config` *returns* `'5s'`, so assert on the bound parameters only — never on the statement text, the result, or `SHOW`.` |
| **F6-4** C7(c) | L-17 / H19 | `monkeypatch.setattr(apply_stock_demand.time, "monotonic", …)` mutates the **shared `time` module**, including the asyncio event loop's clock. It happens to work here (the deadline is passed in), but the same form is fatal in plan 7 C7(a), and the two rows should not teach different things. | `monkeypatch.setattr(apply_stock_demand, "time", SimpleNamespace(monotonic=lambda: deadline + 1))` — replace the **module reference in `apply_stock_demand`'s namespace**, not the attribute on the shared `time` module, so the event-loop clock and every other module are unaffected (see the note)` |
| **F6-5** C5(c) | L-16 / H15 | The row asserts `count_writes` over the four tables `== 0` **during `AD`**, but the listener is engine-wide and session H's `UPDATE stock_report_items SET is_deleted = true` runs on the same engine. Whether the row is armed depends entirely on when the window opens — unstated. | `row R live at 5 (seeded and committed). Session H opened with `get_db_session()`: `SELECT … FOR UPDATE` on R, then `UPDATE stock_report_items SET is_deleted = true, deleted_at = now() WHERE client_id = R`, **held uncommitted**. The `record_statements` window opens **after** H's UPDATE has been issued (the listener attaches to the engine, so H's statements would otherwise be counted); then the main session starts `AD([R's identity, 7])` as a task` |
| **F6-6** C5(a), C5(b) | L-16 / H15 | Both open second sessions; §9 rule 9 names `get_db_session()` while the cited precedent (`test_phase7_concurrency.py:132-133`) uses `database._session_factory()`. Unstated which, and `get_db_session()` is an async **generator**, not a context manager. | append to each cell: `; the second session is opened as `async for s in get_db_session(): …` (it is an async generator, not a context manager) and is closed and purged in a `finally` (§9 rule 9). `pool_size` is 10, so two extra sessions are safe.` |
| **F6-7** C1(d) | L-5 | "row at 5 soft-deleted" does not say how, and an ORM soft-delete would leave the identity index free while a *hard* delete would too — the row cannot distinguish them. | `row at 5 **soft-deleted by direct column write** (`is_deleted = true`, `deleted_at` set; the row and its goal record stay in the table — the partial identity index excludes it, which is what lets the new row be inserted); entry with 3` |
| **M6-1** C1(b) | **L-10 (not implementable / equivalent)** | "insert a second row" cannot be written. Step 5 is guarded by `ON CONFLICT (…) WHERE is_deleted = false DO NOTHING`, and I measured on 18.6 that the conflicting VALUES row is silently dropped: a mutant that treats the existing identity as absent still inserts nothing and still updates the right row. The row stays green. | `enumerated, `apply_stock_demand.py` (definition site): (i) **drop the `ON CONFLICT … DO NOTHING` clause from step 5 and treat every entry as absent** (skip step 4's discovery result) → the INSERT violates `uix_stock_report_items_identity_active` → `IntegrityError` → red; (ii) **build a `stock_report_item:created` event for every identity in the request instead of only for step 5's `RETURNING` rows** → the event list gains a spurious `:created` and "events `[:updated …]`" reddens.` |
| **M6-2** C3(a) | **L-10 (equivalent mutant)** | "snapshot `quantity_awaiting` from the row" is an equivalent mutant on a **new** row: the row is created with `quantity_awaiting = 0` (`server_default="0"`), which is the value the outcome asserts. The mutant writes the same `0`. (It bites at C3(g), and only once F6-2 gives that row a non-zero counter.) | `enumerated, `apply_stock_demand.py` step 8 (definition site): (i) **snapshot `quantity_requested` from the row's pre-update stored value instead of the new value** → the record reads 0 instead of 5 → red; (ii) **let `created_at` fall to the column default instead of the operation's `now`** → `created_at != t0` → red. ("snapshot `quantity_awaiting` from the row" is an **equivalent mutant on this row** — a new row's counter is already 0 — and is carried by C3(g).)` |
| **M6-3** C1(f) | L-9 | The stated consequence is wrong. With step 2 skipped and no such workspace, step 3's category `SELECT` simply returns nothing, every entry becomes `category_not_found`, and no INSERT is ever attempted — there is no FK failure and no 500. The mutation still reddens (nothing raises), but the ledger would record a false mechanism. | `delete the step-2 workspace `SELECT` and its raise, `apply_stock_demand.py` (definition site) → the call returns normally with every entry `category_not_found` (step 3 finds no categories, so no row is ever inserted and the FK is never exercised) → `pytest.raises(LocationTrackerWebhookAuthError)` reddens` |
| **M6-4** C2(f) | L-5 / §9 rule 8 | "skip `strip()`" names neither the file nor definition-vs-call-site, and `strip()` appears in two places (the key computation and the exact-match comparison) with different effects. | `drop the `.strip()` from `item_category_key = item_category_raw.strip().lower()` in `stock_demand_entries.py` (`DemandEntry` construction, definition site) → the key is `"  sofas "`, `lower(name) IN (…)` matches nothing → outcome `category_not_found` → red` |

## 3.4 Plan 7

| Row | Lesson | Why the current cell is defective | Exact replacement text |
|---|---|---|---|
| **F7-1** C7(a) | **L-17 / B6** | The prescribed patch is global: `apply_stock_demand.time` **is** the `time` module, so patching its `monotonic` also freezes the clock the command uses on its own first line. `deadline = C + 5`, then step 9 tests `C >= C + 5` → **false**. The deadline can never be exceeded and the row cannot produce its own outcome as written. (It also freezes the asyncio event-loop clock.) | `` `receive_stock_demand_webhook` run through `run_service`, with **`monkeypatch.setattr(apply_stock_demand, "time", SimpleNamespace(monotonic=lambda: 10**9))`** — the module *reference inside `apply_stock_demand`* is replaced, not `time.monotonic` itself. Patching `apply_stock_demand.time.monotonic` mutates the shared `time` module, so the command's own first-line `deadline = time.monotonic() + timeout_ms/1000` would move with it and the deadline could never be exceeded (it would also freeze the asyncio event-loop clock) `` |
| **M7-1** C1(e) | **L-10 (declared inert)** | The cell itself records that `==` "passes only this row's literal" — a wrong header compares unequal under both `==` and `compare_digest`, so the mutation cannot redden C1(e). The row is left with no armed mutation. | `remove the comparison entirely from `verify_location_tracker_webhook` (`webhook_verifier.py`, definition site) — return the configured workspace id as soon as the header is present → this row's 401 assertion reddens. (Swapping `compare_digest` for `==` is **inert on this row** — a wrong value is unequal either way — and is carried by C1(f), where the non-ASCII input makes the two forms diverge.)` |
| **M7-2** C2(w) | L-9 | "drop the upper bound → DB error (500)" is wrong for this row: C2 is a **unit** test of `parse_stock_demand_body` (plan 7 §4 puts it in `tests/unit/services/commands/stock_report/test_stock_demand_request.py`), which never reaches a database. | `drop the `v <= 2147483647` bound from `parse_stock_demand_body` (`stock_demand_request.py`, definition site) → the parser returns an entry instead of raising → `pytest.raises(ValidationError)` reddens. (Downstream the value would overflow `stock_report_items.quantity_requested`, an `int4` column, and surface as a 500 — that consequence is not what this unit row observes.)` |
| **M7-3** C6(a) | L-9 | "read `ctx.workspace_id` in the command → FK failure" is wrong: `ctx.workspace_id` is `""` on a webhook path, so `apply_stock_demand`'s step-2 `SELECT 1 FROM workspaces WHERE client_id = ''` finds nothing and raises `LocationTrackerWebhookAuthError` (401). No FK is ever touched. | `pass `ctx.workspace_id` instead of the verifier's return value into `apply_stock_demand`, `receive_stock_demand_webhook.py` (call site) → `ctx.workspace_id` is `""` on a webhook path, so step 2's workspace `SELECT` finds nothing and a 401 is raised before any write → the "created row's `workspace_id == W`" assertion reddens` |
| **M7-4** C3(c) | L-12 | `—` on the row that proves the duplicate key includes the **category**; no other C3 row observes that half (C3(a)/(b) vary the properties, C3(d) varies the category spelling). | `key the duplicate check on `properties_signature` alone (drop `item_category_key` from the tuple), `stock_demand_request.py` (definition site) → these two entries collide → 422 instead of 200 → red` |
| **M7-5** C5(b) | L-12 | `—` on the only row that pins the response-entry key set. | `add a fourth key (e.g. `"index"`) to each result dict in `receive_stock_demand_webhook.py` (definition site) → the exact-key-set assertion reddens` |
| **M7-6** C4(a) | L-12 | `—` on the invariant (a) row. The key-order insensitivity is guaranteed by `compute_properties_signature`, which plan 1 armed — but nothing in plan 7 observes that the demand path actually routes through it. | `compute the identity from the **raw** dict's `json.dumps` instead of `compute_stock_criteria_signature(normalize_stock_criteria(raw))`, `stock_demand_request.py` (`DemandEntry` construction, definition site) → the two key orders produce different signatures → two rows → red` |

---

# 4. Outcome-cell defects — orchestrator cannot fix (1)

**O1 — plan 6 C7(a): "its two parameters both equal `str(Settings.model_fields[…].default)`".**

*What is wrong.* Measured on the installed stack: the statement the plan's own task 2 step 1
prescribes — one bind name `:ms` used twice — compiles to
`SELECT set_config('statement_timeout', $1, true), set_config('lock_timeout', $1, true)` and is
executed with `parameters = ('5000',)`. **One** parameter, not two. A faithful implementation of
task 2 step 1 cannot satisfy the outcome verbatim. (Secondary: `set_config` *returns* `'5s'`, so the
outcome cannot be read as being about the result either.)

*What the implementer should be told when it hits the contradiction.* Do not weaken the assertion
and do not silently reinterpret it. Bind **two distinct parameters** —
`SELECT set_config('statement_timeout', :statement_timeout_ms, true), set_config('lock_timeout',
:lock_timeout_ms, true)` with both bound to `str(timeout_ms)`. The compiled statement then carries
`$1` and `$2` and `parameters == ('5000', '5000')`, the outcome cell is satisfied word for word,
nothing about MC-9 changes, and the row gains real content: it now pins that **both** limits are
set, which a single shared bind could never show. Declare the choice in the phase-6 Review log
(charter rule 14) so the orchestrator can decide whether to write it back into task 2 step 1.

No other outcome cell in plans 4–7 was found unachievable. Plan 4 C5(a)'s and plan 5 C2(a)'s
"warning with the delta" **are** achievable once B2 is routed — that is a perimeter question, not an
acceptance-criterion change.

---

# 5. Blockers (7)

**B1 — plan 4 §5 task 2 calls `recompute_task_stock_flag` with the wrong arity.**
Plan text: "`recompute_task_stock_flag(session, assignment.task_id)`". Shipped
(`_task_flag.py:16`): `async def recompute_task_stock_flag(session, workspace_id, task_id)`. A
literal implementer writes a `TypeError`. Root cause is L-18 / N-S2: master plan §6.5 line 380 was
amended by the owner's card-1 ruling, but plan 4 was written before it.
**Resolution:** the batch prompt states the three-argument form verbatim and notes that
`remove_assignment` already receives `workspace_id` as a keyword argument, so it threads through
with no signature change to `remove_assignment`. Amend plan 4 task 2 in the same act.

**B2 — the inline repair warning must carry the delta; `write_repair_record` cannot.**
Intention §5A MC-1 ("one `logger.warning` per record naming the row, field, stored and recomputed
values **and the move's delta for that column**"), restated by the re-check ("the warning now
carries the delta"), and asserted by plan 4 C5(a) ("one warning whose message contains the delta
`-4`") and plan 5 C2(a) ("warning with delta `-4`"). Shipped `_repair_records.py:44-52` has no
`delta` parameter and passes a literal `None` into the `delta=%s` slot — phase 3's manual repair has
no delta, so the gap was invisible. But **`_repair_records.py` is not in plan 4's "Files expected to
change", which ends "Nothing else."**
**Resolution:** add `_repair_records.py` to phase 4's perimeter in the batch prompt. Change is
`delta=None` as a keyword-only parameter on `write_repair_record`, passed into the existing
`logger.warning` slot; phase 3's three call sites keep working unchanged (they omit it). Phase 4
passes the per-column delta of the statement that tripped; phase 5 passes `−q`. **[escalate if you
disagree]** — it is a signature change to a §6.5-registered function, so §6.5's `_repair_records.py`
row is amended in the same act (L-18).

**B3 — plan 6 C7(a) is unmeasurable with the shipped statement listener.** See F6-3 and O1.
`app/tests/helpers/statement_listener.py` is outside plan 6's declared file list.
**Resolution:** add that file to phase 6's perimeter and add `record_statement_calls`, leaving
`record_statements`/`count_writes` byte-identical so batch A's single caller cannot regress.

**B4 — six §6.1-registered names were never shipped by phase 1.** `enums.py` at `e548d1f` is 54
lines and defines five enums plus the two frozensets. Missing: `StockDemandOutcomeEnum`,
`StockDemandDeletedOutcomeEnum`, `ItemsProcessedOutcomeEnum`, `ItemsProcessedReasonEnum`,
`REPAIR_TRIGGER_MANUAL`, `INLINE_REPAIR_TRIGGERS`. Master plan §6.1 asserts "all shipped by phase
1"; plan 1 never mentions them (grep: zero hits), so batch A's 170/170 is not in question — the
claim in §6.1 is what is wrong. Phase 6 needs `StockDemandOutcomeEnum` for `DemandOutcome.outcome`
(C1(a) `applied`, C2(c) `category_not_found`), and `bm/domain/stock_report/enums.py` is not in plan
6's file list.
**Resolution:** add `enums.py` to phase 6's perimeter for `StockDemandOutcomeEnum` only; correct
§6.1's "all shipped by phase 1" to name the phase that ships each; leave the other four names to
their own phases (9, 13A) and `REPAIR_TRIGGER_MANUAL` / `INLINE_REPAIR_TRIGGERS` unshipped unless
the orchestrator wants phase 4 to introduce the frozenset as it becomes the first producer of
`inline:` triggers (my recommendation: **not** in batch B — charter rule 4 forbids adding a
constant with no test caller, and no criterion pins it).

**B5 — every phase-6/7 integration row must commit and purge.** `apply_stock_demand` asserts
`not session.in_transaction()` (plan 6 task 2) and `db_session` autobegins on the kit's first
`flush()` (`app/tests/conftest.py:107-111`, `helpers/stock_report.py:55`). Nothing in plan 6, plan 7
or master plan §6.8 says this. As written, **every** row in both plans raises
`RuntimeError` before reaching its assertion.
**Resolution:** F6-1 gives the fixture-preamble text; the batch prompt must repeat it as a standing
rule for both phases, together with §9 rule 1's purge obligation.

**B6 — plan 7 C7(a)'s prescribed monkeypatch makes its own outcome unreachable.** See F7-1. Closed
by the fixture-cell replacement.

**B7 — the task-flag divergence invalidates ~50 rows of plans 4 and 5.** See F4-1 / F5-1 and H2.
Measured, not inferred: `test_consistency_check.py:97-112` is a shipped, passing batch-A test that
asserts exactly this divergence for a kit-seeded task with one live assignment. Closed by the two
fixture-preamble replacements. **This is the single most important item in the projection** — it is
lesson L-17 recurring at ~25× plan 3's scale, and a Sonnet implementer following the plan literally
will either see a wall of red it cannot explain or "fix" it by weakening
`assert_stock_report_clean`, which would silently disarm §9 rule 2 for the rest of the project.

---

# 6. Anything I could not settle

1. **`recompute_goal_total` has no workspace predicate** (`consistency.py:75-81`), unlike its
   workspace-scoped twin `_recompute_goal_totals_for_workspace`. Phase 5 is its first caller, and it
   is keyed on a history-record `client_id` the caller already owns, so the exposure is the same
   shape as N-S3's write half — theoretical today, real if a future caller hands it an id it did not
   derive locally. No criterion pins it and MC-5's recomputation text does not mention a workspace.
   **Not settled;** I did not route it because the owner's card-1 ruling was about the *task-flag*
   boundary specifically, and widening it to a second function is a decision, not a transcription.
   Suggested destination: the same act as N-S3, or a backlog note. Flagging rather than deciding.
2. **The mutation cells in plans 4–7 name no file and no definition-vs-call-site.** Charter rule 11
   and §9 rule 8 require both, and batch A's fix round 1 lost five mutations to exactly this
   ambiguity ("delete the guard" being ambiguous between the function and its call). I supplied the
   site for every cell I replaced (12 of them), but the ~90 cells I did not touch still carry it.
   **I could not fix this at scale within the edit authority given** (it is a mutation-cell edit, so
   it is formally in scope, but rewriting ninety cells is a plan-authoring act, not a projection
   finding). Cheapest resolution: one standing line in the batch prompt — *"every named mutation is
   applied at the definition site of the function named in the plan's task section unless the cell
   says otherwise; record file and site in the ledger."*
3. **Whether `assert_stock_report_clean` should be called before *and* after each plan-4/5 move.**
   Plan 4 task 4 says "end every non-drift scenario with `assert_stock_report_clean`" — end only.
   With F4-1 that is coherent. A pre-call assertion would fail for every row that ends soft-deleted.
   I have assumed end-only; if the orchestrator wants both, F4-1's rule has to change and several
   rows become unsatisfiable. **Recorded as a delegation, not decided.**
4. **Postgres deadlock shapes for plan 6 C5(b)** were not measured — the row is already declared
   unable to force its interleaving and hands the check to the reviewer structurally. I confirmed
   the two facts the row's *correctness* rests on (sorted VALUES, and H17's identity-keyed re-lock),
   but not the negative claim that an unsorted implementation deadlocks.
5. **Scanner-side conformance** for phases 6/7 (v2 handoff §3.1–§3.4) was not re-derived; batch A's
   review discharged the criteria side and left the item side divergent (F-S1). Phase 7's C5(a)
   echo-as-received row is the surface where that would surface next; I read the plan's claim but
   did not open the Scanner tree.

---

## Appendix — non-authoritative

The skeleton I derived while projecting is discarded per doctrine. Probe scripts are in the session
scratchpad and are not part of the repo; the one scratch table created in the dev database
(`_sr_projection_probe_tmp`) was dropped in a `finally`, and `git status --porcelain` is empty.
