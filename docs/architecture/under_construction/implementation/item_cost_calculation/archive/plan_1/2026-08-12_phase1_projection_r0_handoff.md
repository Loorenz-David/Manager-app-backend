---
plan: phase 1 (worker money redaction)
role: reviewer
session_doctrine: plan-projection (charter: reviewer role tables, round 0)
round: 0
date: 2026-08-12
state: COMPLETE
verdict: AMENDMENTS_REQUIRED
actor: Claude (plan-projection agent)
---

# Projection handoff — phase 1, round 0

## Opening (owner-readable)

The plan for closing the worker money leak is nearly right, but it undercounts the
problem. It names five places in the code where a step's cost number gets built into
a payload, and that count is correct — but two of those five places are shared
helpers used by more screens than the plan lists. Following the plan exactly would
close the leak on five endpoints and leave it open on two others that workers can
reach today. Nothing here needs a decision from you except one question about
timing, below: a second, different money leak (the item's price and purchase cost)
also reaches workers over the API today, and the current sequence closes it in
phase 6 rather than phase 1.

Nine issues are recorded for the coordinator to route. One is blocking (the census),
five are plan wording that two implementers would read differently, one is a
contract-drift item the coordinator must record before the implementer prompt is
compiled, and two are existing tests that will break and are not named anywhere.
No code was touched.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Do workers keep seeing item prices until phase 6?

**Question:** Close the item-price exposure now in phase 1 too, or leave it to
phase 6 as currently sequenced?

**Story:** A restorer opens a chair task on their phone. Phase 1 stops the app from
sending them what that step cost in salary — but the same response still carries what
you paid for the chair and what you expect to sell it for. No worker screen draws
those numbers today, so nobody sees them on-screen; they sit in the data the phone
receives. Phase 6 deletes those two fields from items entirely, which ends it for
good — but phase 6 is five phases away.

**Branches:**
- Leave it to phase 6 — no worker screen shows the numbers, and phase 6 removes the
  columns rather than hiding them, so nothing has to be written twice.
- Close it in phase 1 too — the API stops carrying item prices to workers within
  days, at the cost of code that phase 6 then deletes.

**Recommendation:** leave it to phase 6 — the numbers are not rendered anywhere a
worker looks, and a phase-1 patch would be removed again five phases later.

**On silence:** the gate holds on this question only; the rest of phase 1 proceeds
under the recommendation, and the coordinator records it either way.

**Trace:** intention §11A.1, §4.7, §10.2; phase 6 plan task 1; finding D9.

---

## Decision ledger

| # | Decision the artifacts do not determine | Class | Severity | Proposed routing |
|---|---|---|---|---|
| D1 | Whether the three endpoints reaching `serialize_step` through shared builders are in scope, and what their criteria rows are | intention gap (census) + plan gap (criteria) | **BLOCKING** | amend intention §11A.2 census; then amend plan criteria table |
| D2 | Where the flag is derived for the two shared builders (inside the builder from `ctx`, or threaded as a parameter from each query service) | plan gap | **BLOCKING** | plan amendment (task 2), decided together with D1 |
| D3 | What test harness the (endpoint × identity) rows are written against — route-level or query-service-level | plan gap | HIGH | plan amendment (criteria preamble) |
| D4 | Whether "money present" rows assert an exact value or only key presence | plan gap | MEDIUM | plan amendment (criteria preamble) |
| D5 | Whether site 5 hardcodes `True` or derives from identity like the others | plan gap (plan vs §11A.3) | MEDIUM | plan amendment (task 2) |
| D6 | Whether the predicate is written as an allow-list (`in {admin, manager}`) or a deny-list (`not in {worker, seller}`) | plan gap | MEDIUM | plan amendment (task 2 + one criteria row) |
| D7 | How to obey `46_serialization` (router-owned serialization) while implementing a query-layer redaction | contract gap | MEDIUM | coordinator records divergence (master plan §5 and/or `46_serialization_local.md`) before prompt compiles |
| D8 | Which existing tests change, and on whose authority the characterization key-set changes | plan gap | MEDIUM | plan amendment ("Files expected to change") |
| D9 | Whether the §11A.1 predicate's other live violation (item money) is in phase-1 scope | intention gap (scope) | LOW-MED | owner card 1, then record in the plan's Notes |

---

## Findings

### D1 — BLOCKING. The census counts call expressions; the exposure surface is endpoints

**Verified in the tree, 2026-08-12.** `serialize_step` has exactly five call
expressions in production code (six including a test) — §11A.2's count is correct.
But two of those five sit inside **shared payload builders** that more than one query
service calls, and the census maps each call expression to exactly one endpoint.

Re-derived caller graph:

| serialize_step call | Reached by | Endpoint | Roles admitted | In census? |
|---|---|---|---|---|
| `services/queries/tasks/tasks.py:702` | `get_task` | `GET /api/v1/tasks/{task_id}` | ADMIN, MANAGER, WORKER, SELLER (`routers/api_v1/tasks.py:543`) | yes (site 1) |
| `services/queries/tasks/list_task_steps.py:57` | `list_task_steps` | `GET /api/v1/tasks/{task_id}/steps` | ADMIN, MANAGER, WORKER, SELLER (`routers/api_v1/tasks.py:936`) | yes (site 2) |
| `services/queries/working_sections/steps_list_payload.py:320` (`build_steps_list_payload`) | `list_working_section_steps.py:281` | `GET /api/v1/working-sections/{id}/steps` | ADMIN, MANAGER, WORKER (`routers/api_v1/working_sections.py:148`) | yes (site 3) |
| ″ | `task_step_acknowledgments/list_reassigned_steps.py:85` | `GET /api/v1/task-step-acknowledgments/reassigned-steps` | ADMIN, MANAGER, **WORKER** (`routers/api_v1/task_step_acknowledgments.py:35`) | **NO** |
| `services/queries/working_sections/step_record_payload.py:208` (`build_step_record_payload`) | `get_user_last_active_step_record.py:63` and `:115` (two calls, one endpoint) | `GET /api/v1/working-sections/steps/user-last-active` | ADMIN, MANAGER, WORKER (`routers/api_v1/working_sections.py:113`) | yes (site 4) |
| ″ | `task_step_acknowledgments/list_pending_step_acknowledgments.py:75` | `GET /api/v1/task-step-acknowledgments/pending` | ADMIN, MANAGER, **WORKER** (`routers/api_v1/task_step_acknowledgments.py:74`) | **NO** |
| ″ | `worker_stats/list_workers_last_interacted_step.py:111` | `GET /api/v1/worker-stats/last-interacted-steps` | ADMIN, MANAGER (`routers/api_v1/worker_stats.py:30`) | **NO** |
| `services/queries/worker_stats/get_worker_daily_step_breakdown.py:436` | itself | `GET /api/v1/worker-stats/{user_id}/daily-steps` | ADMIN, MANAGER (`routers/api_v1/worker_stats.py:133`) | yes (site 5) |

Router prefixes verified in `routers/api_v1/__init__.py` (`/api/v1/task-step-acknowledgments`,
`/api/v1/worker-stats`).

**Consequences:**
1. `GET /task-step-acknowledgments/reassigned-steps` and `GET /task-step-acknowledgments/pending`
   are **live WORKER money exposures** of exactly the kind card 4 ordered closed, and
   neither the intention nor the plan mentions them.
2. The exposure matrix over (endpoint × admitted role) is **24 cells, not 16**: the
   three missing endpoints add 3 + 3 + 2 rows. Charter rule 2 (enumerate, never
   sample) is violated at the matrix level even though the plan's own 16 rows are a
   complete enumeration of the 5 endpoints it knows about.
3. `GET /worker-stats/last-interacted-steps` is an anti-blanket-redaction row like
   row 15 — money must stay — and nothing currently guards it.

**Routing:** the census lives in the intention (§11A.2), so the correction goes there
first (lettered amendment, no renumbering), then flows into the plan's criteria table
and named-mutation list. This must be resolved before the implementer prompt compiles:
under the plan as written, an implementer can finish every task, pass all 17 criteria,
and leave two worker leaks open.

### D2 — BLOCKING. Where the flag is derived for the shared builders is undetermined

Plan task 2 says *"Update all five call sites; each derives the flag from the request
identity at the query boundary"*. For sites 3 and 4 the "query boundary" is ambiguous
because two boundaries exist: the shared builder (which already receives `ctx`) and
the query services above it. Both readings are defensible and they differ in outcome:

- **(a) derive inside the builder** from `ctx.role_name` —
  `build_steps_list_payload` and `build_step_record_payload` compute the flag
  themselves. Perimeter matches the plan's declared file list exactly; the three D1
  endpoints inherit correct behaviour for free (workers redacted on both
  acknowledgment endpoints, money kept on `last-interacted-steps`, since that route
  admits ADMIN/MANAGER only).
- **(b) thread `include_monetary` into the builders** as a parameter — then
  `list_reassigned_steps.py`, `list_pending_step_acknowledgments.py` and
  `list_workers_last_interacted_step.py` must all change (or raise `TypeError` at
  runtime), and none of the three is in "Files expected to change". A reviewer running
  the charter's perimeter check would report those three edits as out-of-perimeter.

Both builders already take `ctx` as their first parameter
(`steps_list_payload.py:36`, `step_record_payload.py:32`), so (a) is mechanically
available. `build_step_record_payload` already carries the precedent of a keyword-only
presentation flag (`include_cases_summary: bool = True`, `:33`) — note that precedent
is *defaulted*, i.e. fail-open, and must not be copied for this flag.

**Recommendation:** (a), plus the pin that if (b) is chosen anyway, the builders'
`include_monetary` is keyword-only with **no default**, same as `serialize_step` —
otherwise charter rule 11's fail-closed guarantee stops one level below where the new
callers actually live.

### D3 — HIGH. The criteria table's harness is unpinned, and the wrong choice makes M2–M5 decorative

Rows 1–15b are stated as (endpoint × identity). The repo offers two harnesses and
only one of them can turn the named mutations red:

- **Route-level, the repo's existing router-test idiom** (`tests/unit/test_worker_shifts_router.py:16-45`):
  builds a bare `FastAPI()`, overrides `get_jwt_claims`, and **monkeypatches
  `run_service` to a stub**. The query never runs. Under this harness M2–M5
  (call-site mutations inside the query services) **sail through green** — the exact
  failure charter rule 11 exists to prevent (and the one plan 3 round 1 already paid
  for).
- **Query-service-level integration** (`tests/integration/.../test_list_working_section_steps_payload_characterization.py:106-116`):
  hand-builds `ServiceContext(identity={"role_name": ...})` and calls the query
  directly. This bites M2–M5, holds a real `TaskStep` ORM instance (charter rule 3),
  and matches `15_testing`'s "at least one integration test per query" rule
  (`architecture/15_testing.md:381`).

The service-level harness cannot prove *route admission* (that SELLER actually reaches
`GET /tasks/{id}`); that fact lives in `require_roles(...)` and I verified it by
reading. The plan should say which of the two is the criterion and how admission is
evidenced, rather than leaving "Endpoint" to imply an HTTP test.

Related first-hour reality: `15_testing`'s prescribed fixture backbone
(`db`, `workspace`, `admin_identity`) **does not exist here**. `tests/conftest.py`
provides only `initialize_database`, `isolated_redis_prefix`, `async_engine`,
`db_session`, `redis_client`, `count_queries`; `tests/factories/` and
`tests/fixtures/` contain only `.gitkeep`. There is also **no test anywhere in the
repo that calls `get_task` or `list_task_steps`** — rows 1–8, half the table, require
the first integration harness for those two services. `db_session` rolls back
(`conftest.py:46-50`), so charter rule 11½ is satisfied structurally by seeding with
`flush()` and never committing; the plan should say so rather than leave the
implementer to rediscover it.

### D4 — MEDIUM. "Money present" rows have no value assertion

The sole-predicate companion is stated only for redacted rows ("Each redacted row's
fixture gives the step a non-NULL `total_cost_minor`"). `total_cost_minor` is nullable
(`models/base/aggregate_metrics.py:41`), so a present-row fixture that leaves it NULL
yields `{"total_cost_minor": None}` — which satisfies "key present" under the plan's
own definition while proving nothing. An implementation bug that emitted `None` for
managers would pass rows 1, 2, 5, 6, 9, 10, 12, 13, 15, 15b — ten of sixteen rows.
**Proposed amendment:** present-rows seed a distinctive non-NULL value and assert
equality against it, not membership.

### D5 — MEDIUM. Site 5's flag source contradicts itself

Plan task 2 says every call site derives the flag from request identity, then says
"Site 5 (worker_stats, ADMIN/MANAGER-only route) **passes True**". Intention §11A.3
admits only the first form ("Each call site derives the flag from the request identity
at the query boundary"). Hardcoded `True` is a durable fail-open: if
`GET /worker-stats/{user_id}/daily-steps` ever admits WORKER, money ships and no test
notices. Rows 15/15b stay green under both forms, so **no criterion distinguishes
them** — it must be pinned in prose. Recommend uniform identity-derivation everywhere,
site 5 included.

### D6 — MEDIUM. Allow-list vs deny-list is unpinned, and nothing tests it

`RoleNameEnum` is closed at four values (`domain/roles/enums.py:5-8`) and
`require_roles` rejects any identity whose `role_name` is not in the route's set
(`routers/utils/jwt_dep.py:44-47`), so the predicate is total *today* under both
forms. But `role_name in {admin, manager}` and `role_name not in {worker, seller}`
diverge the moment a fifth role exists or a non-HTTP caller builds a `ServiceContext`
without `role_name` (`ServiceContext.role_name` returns `""` by default,
`services/context.py:40-41`) — the deny-list form then emits money.

**Proposed amendment:** mandate the allow-list form, and add one criterion row —
an identity with an absent/unknown `role_name` gets money absent — which is the only
row that can turn red on that mutation. The keyword-only signature protects the
*serializer* layer; nothing currently protects the *derivation* layer.

### D7 — MEDIUM. `46_serialization` contradicts the phase's whole design, and the local override is empty

`architecture/46_serialization.md` states, as binding rules: "Serialization … is a
presentation concern owned by the **router layer**, not the service layer";
"**Services never call serializer functions**"; "Services return **dataclass
instances**, never dicts for resource types". The repo's entire task /
working-section query layer does the opposite, and
`architecture/46_serialization_local.md` is an **unmodified template** — it records
no override, no local decision, nothing.

Under master plan §5's pattern-authority rule ("contracts say how to write code;
implementation files say only what exists"), an implementer who re-emits the contract
bundle before coding is being told to move step serialization into the routers —
which would blow the perimeter, and is the opposite of "derive the flag at the query
boundary". This is the second contract gap of the same shape as the `05_errors` one
already recorded in §5. **Routing:** the coordinator records the divergence (in
`46_serialization_local.md` per that file's own instruction, or in master plan §5)
with the explicit note that phase 1 keeps serialization where it is, before the
implementer prompt compiles.

Verified as *not* in conflict: `28_roles_permissions` blesses both the
`require_roles([...])` route dependency and the `role_name` JWT claim
(`architecture/28_roles_permissions.md:385`, and the route-level role dependency
section) — deriving the flag from `ctx.role_name` is contract-faithful. Backend
permissions are endpoint-level (method + path) and cannot express a per-field
audience, so they are the wrong carrier here.

### D8 — MEDIUM. Two existing tests break; neither is named

"Files expected to change" says only "existing step-payload tests updated for the
signature". The concrete list is:

1. `tests/integration/services/queries/analytics/test_ended_shift_bucket_collapse.py:1019`
   — `payload = serialize_step(step)`, positional, no keyword. Under the new signature
   this raises `TypeError`. It is criterion row 16's mutation applied by accident, and
   it is a characterization test of an earlier project's criterion 10 ("published names
   and meanings"), so the edit must be the minimum: add the keyword, change no
   assertion.
2. `tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py`
   — `_STEP_KEYS` (`:27-67`) contains `total_cost_minor`, the context is built with
   `"role_name": "worker"` (`:106-116`), and the assertion is set equality
   (`assert set(item) == _STEP_KEYS`, `:234`). After redaction this **fails**.

Item 2 is more than a signature update: it changes a published payload contract's
expected key set under a worker identity, i.e. it *is* criterion row 11 in a different
file. Recommend the plan name the file, require it to be re-parametrized by role
(worker → absent, manager → present) rather than simply deleting the key from the set,
and record the key-set change in the Review log so a reviewer does not read it as an
unauthorized characterization edit.

### D9 — LOW-MEDIUM. `total_cost_minor` is not the only §11A.1 violation on these endpoints

`GET /tasks/{task_id}` — WORKER- and SELLER-reachable — also returns
`item_value_minor`, `item_cost_minor` and `item_currency` via `serialize_item`
(`domain/tasks/serializers.py:104-106`, called at
`services/queries/tasks/tasks.py:696`). §11A.1's predicate ("a payload may carry
monetary fields iff the requesting identity's role is ADMIN or MANAGER") covers these;
phase 1 does not close them, and phase 6 does — by removing the columns
(`plans/phase_6_legacy_migration_api_bridge.md:55`). See owner card 1.

Two consequences regardless of the owner's answer:
- The plan's definition of "money absent" (`total_cost_minor` key absent) must stay
  exactly as written. An implementer who reads rows 3/4 as "no monetary keys in the
  payload" writes a test that fails for reasons unrelated to their change.
- **Forward note for phase 6's projection, not a phase-1 finding:** phase 6 line 55
  says "five embedding payloads". I count six `serialize_item` call expressions in
  five files — `services/queries/tasks/tasks.py:387` (`list_tasks`) and `:696`
  (`get_task`), `list_task_coordination_threads.py:224`,
  `upholstery/upholstery_order_needs.py:595`,
  `items/seat_tasks_pending_upholstery.py:335`,
  `upholstery/upholstery_orders_query.py:496`. Whether "five payloads" means five
  files or five payloads is worth pinning before phase 6, and it is the same
  call-expressions-vs-endpoints error class as D1.

---

## Reality checks

### Paths and citations in the plan

| Cited | Status |
|---|---|
| `domain/tasks/serializers.py::serialize_step` at `:152` | ✅ exact, `:152-178`; emits `total_cost_minor` at `:176` |
| `services/queries/tasks/tasks.py` call `~:702` | ✅ exact `:702`, inside `get_task` (`:579`) |
| `services/queries/tasks/list_task_steps.py` `~:57` | ✅ exact `:57` |
| `services/queries/working_sections/steps_list_payload.py` `~:320` | ✅ exact `:320`, inside `build_steps_list_payload` (`:36`) |
| `services/queries/working_sections/step_record_payload.py` `~:208` | ✅ exact `:208`, inside `build_step_record_payload` (`:32`) |
| `services/queries/worker_stats/get_worker_daily_step_breakdown.py` `~:436` | ✅ exact `:436` |
| `routers/api_v1/worker_stats.py:133` admits ADMIN + MANAGER (criteria fold for row 15b) | ✅ exact — `require_roles([ADMIN, MANAGER])` at `:133` |
| §11A.2 route/role columns for sites 1–5 | ✅ all five verified against `require_roles` in the routers (see D1 table) |
| §11A.2 "five call sites" | ✅ as call expressions; ❌ as endpoints (D1) |
| Intention §11A.3 keyword-only-no-default construction | ✅ implementable; `TypeError` on `serialize_step(step)` is the real CPython behaviour for a keyword-only parameter without default |
| Card 4 / R1-5, SELLER exclusion (R4-3) | ✅ `owner_decisions.md:115-141`, CLOSED; not revisitable — respected here |
| Master plan §10: `PYTHONPATH=. pytest --collect-only -q` → 1602 tests | ✅ re-verified 2026-08-12: **1602 collected in 1.14s** |
| Master plan §3: graph 116 nodes / 157 edges, revision `b0702c3c…`, 0 stale, permissionMode `review` | ✅ re-verified via `archgraph_status`; pendingReviewCount 244 |

### Named mutations M1–M5, simulated on paper

| Mutation | Site kind | Bites? |
|---|---|---|
| M1 — default `include_monetary=True` in `serialize_step` (definition) | definition | ✅ row 16 goes red, provided row 16's test calls the function directly rather than through a route |
| M2 — hardcode `True` at `tasks.py:702` | call site | ✅ rows 3, 4 — **only under the query-service harness** (D3) |
| M3 — hardcode `True` at `list_task_steps.py:57` | call site | ✅ rows 7, 8 — same condition |
| M4 — hardcode `True` at `steps_list_payload.py:320` | call site | ✅ row 11 — same condition |
| M5 — hardcode `True` at `step_record_payload.py:208` | call site | ✅ row 14 — same condition |
| complementary — blanket `False` at site 5 | call site | ✅ rows 15, 15b |

**Mutations no row catches** (each is a ledger item, listed here so the gap is visible
as a set):
- hardcoding `True` inside `list_reassigned_steps.py` or
  `list_pending_step_acknowledgments.py` under design (b) — D1 + D2;
- flipping the predicate from allow-list to deny-list — D6;
- hardcoding `True` at site 5 and later admitting WORKER to that route — D5;
- emitting `total_cost_minor: None` to ADMIN/MANAGER — D4.

### Criteria decidability, row by row

- Rows 1–15b: decidable **once D3 fixes the harness and D4 fixes the present-row
  assertion**; the identity column maps cleanly onto `ServiceContext.identity["role_name"]`
  and the route's `require_roles` set, and each row's expected outcome is a single
  exact value (charter rule 2 satisfied within the 5 endpoints the table covers).
- Row 16: decidable as written; unit test, no DB. Note charter rule 3 does not force
  an ORM instance here — a keyword-only parameter with no default raises before the
  body runs — but every payload row must hold a real `TaskStep`, which the
  query-service harness gives naturally.
- Row coverage: **incomplete against the real endpoint set** (D1) — 16 of 24 cells.
- Sole-predicate companion: satisfied for redacted rows as written; missing for
  present rows (D4).
- "key absent vs null": pinned correctly and unambiguously in the criteria preamble
  ("assert key ∉ dict, not `is None`") and in §11A.3. No ambiguity found.

### Environment and tooling

- Test command verified from `backend/app/`: `PYTHONPATH=. pytest --collect-only -q`
  → 1602 tests, 1.14s. Markers per `pytest.ini` (`unit`/`integration`/`e2e`, strict,
  `asyncio_mode = auto`). No suite run — the integration tier commits nothing but does
  touch the configured DB, and master plan §10 assigns the baseline to the phase-1
  implementer, not to this session.
- Archgraph: read-only. `archgraph_status` matches the planner's recorded state.
  `table-task-step` describes `total_cost_minor` as a column of the step's own
  analytics rollup — consistent with the code (`models/base/aggregate_metrics.py:41`);
  no discrepancy to file. No node exists for `serialize_step` or for the four
  step-payload endpoints; `endpoint-worker-daily-step-breakdown` and
  `projection-worker-daily-step-breakdown` exist and are unaffected by a redaction
  that keeps money on that route. The plan's "expected delta ≈ zero new nodes" holds;
  if D1 is routed, the three newly-named endpoints may be worth nodes, which is the
  implementer's close-of-phase call, not mine.

---

## Explicit delegation list (freedom granted on purpose)

1. **Test file placement and names**, within `15_testing`'s mirror layout — e.g.
   `tests/integration/services/queries/tasks/test_get_task_money_redaction_integration.py`.
   No plan row depends on the filenames.
2. **Fixture/factory design for seeding a step graph** (workspace, user, task,
   task_item, step, state record), including whether it lands in `tests/factories/`
   (currently empty) or as module-local helpers. Constraint, not delegation: seed with
   `flush()` on the rolled-back `db_session` fixture — do not commit — and any factory
   added must have a caller in this phase (charter rule 4).
3. **Whether the role→bool derivation is a shared helper or repeated inline.**
   Recommendation: one shared pure helper (e.g. in `domain/tasks/serializers.py`
   beside `serialize_step`) taking the role name and returning `bool`, so the
   allow-list form of D6 exists in exactly one place; but this is a free choice and is
   granted either way.
4. **Whether row 16's unit test builds a `TaskStep` or passes a stub** — the
   `TypeError` precedes the body. Delegated.
5. **Ordering of the implementation tasks** within the phase.

Not delegated, and not to be resolved silently in code: D1–D8. Each changes what
ships or what the tests prove.

---

## Session write perimeter

- **Documents written:** this file only —
  `handoffs/reviewer/2026-08-12_phase1_projection_r0_handoff.md`.
- **Code changed:** none.
- **Tests run:** collection only (`pytest --collect-only`), no execution, no DB writes.
- **Tool-recorded state:** none. Archgraph calls were `archgraph_status`,
  `archgraph_search_nodes` (×3), `archgraph_get_node` (`table-task-step`) — all
  read-only. No delta applied, no review item adjudicated.
- **Skeleton:** deliberately not attached. The projection's paper artifacts are
  discarded per doctrine; nothing here is guidance for the implementer beyond the
  ledger.

## Verdict

**AMENDMENTS_REQUIRED.** D1 and D2 must be routed before the implementer prompt is
compiled — the plan as written can be executed faithfully and completely while leaving
two worker-reachable money leaks open. D3 must be routed for the same reason at one
remove: under the repo's existing router-test idiom, four of the five named mutations
never bite. D7 needs a recorded contract divergence, or the implementer's first act
(re-emitting the §5 bundle) points the phase at the wrong layer.
