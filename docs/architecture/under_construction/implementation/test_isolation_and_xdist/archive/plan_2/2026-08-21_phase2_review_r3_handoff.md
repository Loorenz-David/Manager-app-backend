---
plan: 2
role: review
round: 3
verdict: CHANGES_REQUESTED
date: 2026-08-21
actor: Opus 5 (independent review, NO-WRITE mode) — transcribed to disk by the coordinator
transcription_note: |
  Round 3 ran in NO-WRITE mode so two reviewer models could be compared on an identical
  repository. Neither session wrote to the repo; both delivered findings in their final
  message. This file is the coordinator's faithful transcription of the Opus review's
  layer-1 artifact, which is the adopted review. The Sonnet review is recorded in the
  comparison section at the end and did not contribute findings to the fix cycle except
  where noted (N9).
---

# Phase 2 review r3 (independent) — verdict CHANGES_REQUESTED

1 blocking · 5 should-fix · 9 notes. Session L4 count **0** against a stated budget of 0;
tree was `app/`-identical to `8429442`, so the closing stamps were consumed by citation and no
authorization line was needed.

## ⚠ OWNER DECISIONS REQUIRED (1) — ANSWERED

**Card 1 — should the test slot become a real setting, or stay an exported variable?**
**Answered 2026-08-21: settings field.** Recorded as **OD-7** in `planning/intention.md`.

## Blocking

### B1 — `BEYO_TEST_SLOT` is unreachable through the only surface that documents it

`resolve_test_slot` (`app/tests/database_isolation.py:33-40`) reads the slot with
`os.getenv(TEST_SLOT_ENV)`. The only operator-facing documentation of the variable in the
repository is `app/.env.example:8-10`. `app/.env` is consumed by pydantic-settings via
`Settings.model_config` (`app/beyo_manager/config.py:135-139`), which reads the file directly
and **does not populate `os.environ`**; only `app/run.py:6-7` calls `load_dotenv()`, and that is
the app runner, not pytest.

**Measured (reviewer, and independently re-measured by the coordinator):** with
`BEYO_TEST_SLOT=shopify` present in the `.env` that `settings` actually parsed,
`os.getenv("BEYO_TEST_SLOT")` is `None` and `resolve_worker_database_name()` returns
`beyo_test_main_main`.

**Consequence:** the concurrent-checkout hazard of intention §5 survives **in its original
form** for any operator who configures the slot where they were told to — and it survives
silently. The second run's startup drops the database the first run is using; the destroyed run
fails as flakiness.

**Violated authority:** `plans/plan_2.md` §4 task 2 ("document it where an operator running a
second worktree will find it"); §1 goal 2; charter rule 10 (config-gated behaviour must be
reachable through the shipped configuration surface).

**Correction (OD-7 selects shape (a)):** add a `BEYO_TEST_SLOT` field to
`app/beyo_manager/config.py` and resolve the slot from settings with an `os.environ` override,
so both `.env` and an exported variable work. Add a **C3 row that resolves the slot the way an
operator sets it**, not through the `slot=` keyword parameter — the existing rows all bypass the
surface that is broken.

### B2 — the legacy sweep destroys other checkouts' live databases, on every process

*Raised by the reviewer as S1; **escalated to blocking by the coordinator**, who executed the
destruction the reviewer described.*

`_sweep_legacy_databases` (`database_isolation.py:303-306`) is called from `start()` (`:170`),
so **every pytest process** drops every database matching `LEGACY_TEST_DATABASE_PATTERN`
(`:18`) — `beyo_test_template`, `beyo_test_main`, `beyo_test_gwN`. `assert_disposable_database`
(`:87-91`) permanently accepts those names.

**Measured (reviewer):** replacing the sweep body with `return` → `36 passed`. Removing the
legacy alternative from the guard's pattern check → `36 passed`. **Neither branch has a row.**

**Measured (coordinator, executing the consequence):** created `beyo_test_main`, then ran
`pytest -q tests/unit/test_items_router.py` — a three-test unit file, 1.30 s. Server membership
went `['beyo_test_main', 'beyo_test_main_template']` → `['beyo_test_main_template']`. **A
1.3-second unit run silently destroyed what, in the scenario, is another checkout's live worker
database.**

**Why blocking rather than should-fix:** plan_2 §1 goal 2 is *"two checkouts can run pytest at
the same time without destroying each other's databases."* This is a checkout destroying another
checkout's database. Together with B1 it means **worktrees are unsafe by two independent
mechanisms**, which is the capability this phase exists to deliver.

**Violated authority:** `plans/plan_2.md` §1 goal 2, §4 task 2 (the disposition's permanence was
declared but no criterion was attached); charter standing rule 11.

**Correction:** two criterion rows — one asserting a legacy-named database is accepted by the
guard and reclaimed by the sweep, one asserting a **slot-qualified name from another slot is not
swept** — and record in the plan whether unconditional permanence is still intended given the
consequence above. A sweep that runs on every process forever is a different mechanism from the
one-time disposition task 2 asked for.

## Should-fix

### S2 — C6(b) was never implemented
`plans/plan_2.md` C6 requires row (b): *"the teardown deletes keys under the prefix that was
actually written."* No test references `isolated_redis_prefix`'s teardown. **Measured:** deleting
the `scan_iter`/`delete` loop (`conftest.py:59-64`) leaves the criterion module at `36 passed`
and `test_logout_user_integration.py` at `2 passed`. The residue class this project exists to
kill would reappear in Redis instead of PostgreSQL, unobserved.
**Correction:** an explicit finalizer or session-scoped assertion that writes a key under the
process prefix and verifies it is gone after the prefix fixture finalizes.

### S3 — the Redis teardown makes a live Redis a hard requirement of every pytest session
`isolated_redis_prefix` (`conftest.py:51-65`) is session-scoped autouse (correct, per L16 and
charter rule 10), but its `finally` block opens a Redis connection **unconditionally**.
**Measured** on `tests/unit/test_items_router.py`: control `2 failed, 1 passed`; with
`REDIS_URL` pointed at a dead port, `2 failed, 1 passed, 1 error` — ERROR at teardown from
`redis.connection.Connection.connect`. Before this phase the fixture was neither autouse nor
Redis-touching.
**This makes the authoritative failing-ID set a function of Redis availability**, which lands
directly on plan 3's re-enumeration.
**Violated authority:** intention §1 scope discipline (the runner must not acquire undeclared
dependencies).
**Correction:** make the key sweep best-effort (catch `redis.exceptions.ConnectionError`, warn)
while keeping the prefix override unconditional — or declare Redis a required suite dependency in
the environment topology and add it to plan 3's preconditions.

### S4 — two `_parse_database_url` sub-checks have no row that tests them
**Measured (reviewer), criterion module at L1, each mutation applied alone and reverted:**

| mutation site | result |
|---|---|
| `_parse_database_url:66-67` — drivername check removed | `36 passed` (nothing reddens) |
| `_parse_database_url:68-69` — host/username/database completeness check removed | `36 passed` (nothing reddens) |

**Independently re-measured by the coordinator:** removing the drivername check →
**`36 passed in 4.41s`**, file restored byte-identical
(`046b1f27685bfca4781893cd845595107b77599ff73637b44ac83a997bec19da` before and after).

Both URL-parsing rows in `test_destructive_guard_rejects_every_unsafe_case`
(`test_database_isolation.py:131-132`) use `None` and `"not-a-database-url"`, caught by `:60-61`
and `:62-65`. Nothing exercises `postgresql+psycopg://…`, `mysql://…`, or a URL missing a
username. The `target_database_url` parameter's failure paths have **no row at all** — every
parametrize row passes a well-formed target URL.
**Violated authority:** `plans/plan_2.md` C4 ("a sub-check whose disabling reddens nothing has no
row that tests it"). Fix r2's ledger treated URL parsing as one sub-check and disabled the parser
wholesale, which is why this survived.
**Correction:** three rows — non-PostgreSQL driver, URL missing username, malformed
`target_database_url` — plus a re-run of the per-sub-check mutation at the finer granularity.

### S5 — the earlier B1's mechanism is still unidentified; the repair prevents the symptom without explaining it
Fix r2 attributed the reversed-run `assert 0 == 2`
(`test_sku_templates_commands.py:132`) to a stale identity-mapped `SkuTemplate`. That mechanism
is the only one that can produce `0` — `allocate_sku_scalar_in_session` is a bulk
`UPDATE … RETURNING` (`_allocate_sku_scalar_in_session.py:25-41`), so the database certainly
holds `2` once `gather` returns, and READ COMMITTED guarantees a fresh statement sees it. But it
requires the ORM instance to still be in the session's identity map, which is a
`WeakInstanceDict`.
**Measured at L1/L2 with `refresh()` removed and a probe before the re-SELECT:** the
`SkuTemplate` is **absent from `db_session.identity_map`** in every configuration tried — alone;
whole file; whole file reversed; preceded by `test_clock_actions_integration.py`; and with the
identity map pinned immediately after `commit()`. The query constructs a fresh instance, reads
`2`, and passes **without** the repair.
**So the trigger is object lifetime, not collection order.** The coordinator's N1 is confirmed
and sharpened: `expire_on_commit=False` (`models/database.py:47`) is not the explanation, and
neither is ordering — this test's outcome was a function of garbage collection.
**Consequence for C2:** the closing pair proves the two runs agreed; it does **not** establish
that every test's outcome is a function of code and order alone. Bounded, and it lands on plan
3's mandate to re-enumerate the baseline.
**Class size, surveyed structurally:** 13 test files create a second session; the repository
already carries 89 `refresh()` calls and an explicit comment naming this hazard at
`tests/integration/services/tasks/shopify/test_shopify_worker_handlers_integration.py:250`. A
tail, not an epidemic.
**Correction:** record the corrected characterisation in the plan — **the fix-r2 handoff is
published and must not be rewritten** (§5A) — and carry to plan 3 a standing rule that a
single-occurrence failing-ID difference triggers re-measurement rather than attribution.

## Notes

- **N1** — `conftest.py:32-34`: `assert_configured_database_unchanged()` runs before
  `settings.database_url` is restored and before `isolation.stop()`. If it raises, the worker
  database is never dropped and the URL is never restored. Bounded (the next run's
  `DROP IF EXISTS` absorbs it), but the residue check's own failure produces residue.
- **N2** — `database_isolation.py:166-169`: `configured_row_counts_before_run` is only populated
  when the configured database name does **not** match the test pattern. If it does match, the
  value stays `None` and `assert after == None` fails at every session teardown. Edge
  configuration, fails loudly, worth a guard.
- **N3** — `_normalised_endpoint` (`:73-75`) maps only the literal string `"localhost"`.
  `LOCALHOST`, `::1`, `0.0.0.0` or a hostname alias mismatch and make **every** drop refuse, so
  the suite cannot start. Fail-closed and therefore safe, but the failure mode is total and the
  diagnosis non-obvious.
- **N4** (passing glance, phase-1 code at `da01592`) — `EXPECTED_HEAD = "c1d2e3f4a5b6"` and
  `EXPECTED_PUBLIC_TABLE_COUNT = 107` (`:25-26`) are hardcoded. **The next Alembic revision makes
  `_ensure_template` rebuild, and `_migrate_and_assert` then raises `RuntimeError` because the
  head no longer equals the constant — the suite wedges until a human edits the file.** Worth a
  follow-up phase, not this one.
- **N5** (lesson) — OD-6's closing clause, *"no factory may create a globally-unique row inside a
  test that commits"*, **contradicts adopt-or-create itself**: the first committing test to run on
  a fresh database must create the `Role`. `adopt_or_create_role` is right; the clause needs
  restating as **"never create unconditionally"**. `plans/plan_2.md` §4 task 1 bound 2 inherits
  the same wording. *(Coordinator-authored defect; corrected in the intention at this fold.)*
- **N6** — `test_add_task_steps_integration.py:90` still passes `worker_role` to
  `db_session.add_all([...])` after adopting it. Harmless (adding a persistent instance is a
  no-op), cosmetic residue of the repair.
- **N7** — C7(a)'s rewrite covers `create_pause_reason.py:36` only. The second production writer
  named by the plan, `seed_pause_reasons.py:102`, has no row; both write `False` today, so nothing
  is wrong, but the criterion's stated coverage is one writer narrower than its test name suggests.
- **N8** — this project has **no master plan** at the implementation-folder root, so the charter's
  environment-topology section (exact commands, DB safety rules, baseline caveats) has no home; it
  is distributed across plan files and prompts. Pre-existing across all three phases — a lesson for
  the coordinator.
- **N9** *(from the Sonnet review, adopted)* — `test_list_users_floor_identification.py:192-209`:
  the `roster` fixture now creates its own `Workspace` via `create_test_workspace`, but its
  `finally` block deletes only `UserWorkProfile`/`WorkspaceMembership`/`User` — never the
  `Workspace` or the `WorkspaceRole` that `seed_worker` creates — unlike
  `test_update_user_admin_clock_in_code.py`'s `admin_fixture`, which deletes everything it created.
  Verified structurally: `list_users` contains no write or commit, so the fixture's leading
  `rollback()` discards the uncommitted graph and today's omission is **harmless by accident
  rather than by design**. Align with the explicit-delete pattern (charter rule 11½).

## What the review verified correct

- **Gate.** `git diff 8429442 HEAD -- app/` empty; `git status --porcelain` clean at entry and
  exit; `import xdist` → `ModuleNotFoundError`; no `-n` in any pytest configuration. §7 carries
  all three rounds plus their consumptions.
- **C1 under a condition nobody had measured.** The repaired files run **preceded by the poisoning
  file** `tests/connecteam/test_clock_actions_integration.py`, in both collection orders: four
  files + poisoner → `91 passed` default and `91 passed` reversed; the remaining seven repaired
  files + poisoner reversed → `71 passed`. `adopt_or_create_role` correctly adopts an
  already-committed `WORKER` role rather than colliding — the exact composition OD-6 ratified.
- **P3 — S1's membership assertion bites.** Mutated to demand a sentinel → `36 passed, 1 error`
  with the assertion's own message and a non-zero exit. A real gate, not a warning.
- **The slot mechanism works when the variable is exported.** Mutating `resolve_test_slot` to
  ignore `os.getenv` produces `2 failed … 1 error`. **B1 is a documentation-surface defect, not a
  resolver defect.**
- **The guard, read structurally.** Endpoint confinement (`:97-98`) precedes the configured-tuple
  identity check (`:99-102`), so the pair is strictly stronger than phase 1's name-only comparison
  in both directions, exactly as L5 required. `beyo_manager` is refused twice over.
  `marker_present=False` with `public_table_count=None` refuses. `_quoted_identifier` remains
  ASCII-only behind the widened pattern.
- **Both wedge shapes clear.** `inspect` (`:195-220`) tolerates a missing `alembic_version` and a
  missing marker relation, catching `asyncpg.exceptions.UndefinedTableError` only — never a bare
  `except`. `_ensure_template` (`:308-337`) absorbs an unmarked template with zero public tables
  and refuses one carrying tables. F3/L3 discharged at the seam the projection identified.
- **C7(a) is honest.** `create_pause_reason` writes `is_system_managed=False` at `:36` and returns
  `serialize_pause_reason(pause_reason)` over the ORM instance, so the assertion reads a
  production-produced value, not a fixture literal.
- **C8.** The hook returns early on an unset variable, reverses exactly once on `reverse`, and
  raises `pytest.UsageError` on anything else — refused, not treated as off.
- **Perimeter and factories.** Implement r1 is eighteen code files, no production code; fix r2 is
  two. Both `phase2_row_factories.py` functions have callers (charter rule 4). Two repaired
  fixtures gained proper `finally` teardown of the workspace and workspace-roles they now create
  (charter rule 11½) — an improvement over what they replaced.
- **P2 — the L4 count reconciles at 5, all authorized.** Implement r1 took 3 against a budget of 3;
  fix r2 took 2, exactly the two authorized in the implement-r1 consumption. *"The first pair"*
  refers to implement r1's closing pair, not a fourth and fifth run. **The Sonnet review settled
  this more decisively:** checkpoints `0f08079` → `8429442` span **5m09s**, and the two recorded
  closing runs (~128 s + 129.26 s) already consume ~257 s of that 309 s window, leaving no room
  for an unrecorded second pair plus the SKU fix and its targeted rerun. No round is over budget;
  only the phrasing was ambiguous.
- **Boundary check** *(Sonnet, adopted)* — four files **outside** the declared eleven+one perimeter
  that still use bare `select(Role)`/populated-workspace lookups (`test_kiosk_floor_flow.py`,
  `test_worker_stats_endpoint_split_integration.py`, `test_get_worker_daily_step_breakdown.py`,
  `test_ended_shift_bucket_collapse.py`) are all safe: three inline their own adopt-or-create, and
  the kiosk file's three tests request the phase-1 `kiosk_reference_data` fixture
  (`phase1_reference_data.py:128-133`), which creates its own `Role`/`Workspace`/`PauseReason`.
  **The eleven-file perimeter is complete** — asserted by plan_2 §3, now proven.

## Mutation-probe declaration

Every probe applied one at a time, reverted from a pre-probe copy, checksum-verified
byte-identical. `git status --porcelain` empty at close. No file under `app/beyo_manager/` was
touched by any probe.

| file | SHA-256 before | after |
|---|---|---|
| `app/tests/integration/infrastructure/test_database_isolation.py` | `b94f1bb2457f9e2697de721185a9eba375e5b879dc3a1d256619e5c8e025825d` | identical |
| `app/tests/integration/services/commands/sku_templates/test_sku_templates_commands.py` | `ea0bcf6a0f606ace03ef16bf5a5aec35c8e8e67f6fa0029471c8874d126ac27c` | identical |
| `app/tests/database_isolation.py` | `046b1f27685bfca4781893cd845595107b77599ff73637b44ac83a997bec19da` | identical |
| `app/tests/conftest.py` | `85dd5fec7ccbcab6f88e3de7b4f6eb5280aae21bd8eaee738f3e01abb5aaa7f9` | identical |

**Database and state side effects.** Runs created and dropped the ordinary per-run worker
database `beyo_test_main_main` and the criterion module's own probes
(`beyo_test_main_gw993`–`gw999`, `beyo_test_phase2_*`), all reclaimed by the module's teardown.
Final server membership verified directly: `beyo_manager`, `beyo_test_main_template`,
`housing_parser_plan1_20260807`, `postgres` — identical to the settled-ground baseline. The
configured development database was never a target and was never written to. One probe ran with
`REDIS_URL` overridden to an unreachable port for a single command; no Redis state was written or
removed.

## Lessons for the plans

1. **An environment variable's documentation surface is part of its contract.** §4 task 2
   delegated the variable's name and said to document it; it did not say **where the read
   happens**. In a repo whose settings come from `.env` via pydantic, "document the env var in
   `.env.example`" is the natural and wrong answer. Future phases introducing an env-read
   mechanism carry a criterion row that resolves it **through the environment as an operator would
   set it**, not through a keyword argument.
2. **A criterion that groups sub-checks hides sub-sub-checks.** C4 named five sub-checks and got
   five mutations; the URL parser is four checks wearing one name, and two are uncovered. When a
   criterion says "one mutation per sub-check", the plan enumerates the sub-checks **from the
   code's branch points**, not from the prose description.
3. **Every destructive branch needs a row, including ones added for cleanup.** The legacy sweep is
   the widest destructive path in the module and was the only task-2 deliverable with no criterion.
   C4's enumeration was written before task 2's disposition existed and was never extended.
4. **"Invariant under collection order" and "the two runs agreed" are different claims.** One test's
   outcome depended on object lifetime rather than order. C2's wording should distinguish the
   measured claim from the general one, and plan 3 should treat a single-occurrence ID difference
   as a re-measurement trigger rather than something to attribute.
5. **OD-6's final clause is unsatisfiable as written** (N5) — restate in the intention as "never
   create unconditionally", so the next plan citing it does not re-derive the contradiction the
   projection already paid for once.
6. **This project has no master plan.** The charter's environment-topology section has nowhere to
   live, which is why the exact test commands, the Redis dependency and the database-safety rules
   are scattered across three plan files and every prompt. Worth creating before plan 3, which is
   almost entirely environment measurement.
7. **State L4 run counts as an explicit number in every handoff** *(Sonnet)* — not something
   inferable from a sentence like "the first pair". Two reviewers spent real effort disambiguating
   what should have been a one-line fact.
8. **A root-cause writeup that cites "passes alone" as supporting evidence must first check its own
   stated mechanism is consistent with that alone-passing result** *(Sonnet)* — here the two
   contradicted each other, and the contradiction was cheap to find but easy to miss.

## Appendix — reviewer-model comparison (the round's second purpose)

Both models received an identical prompt on an identical tree and wrote nothing to the repo.

| | Opus 5 | Sonnet 5 |
|---|---|---|
| Verdict | **CHANGES_REQUESTED** | **APPROVED** |
| Findings | 1 blocking, 5 should-fix, 8 notes | 0 blocking, 1 should-fix, 2 notes |
| B1 (slot inert via `.env`) | **found** | missed |
| B2 (sweep destroys other checkouts) | **found** | missed |
| S4 (two uncovered sub-checks) | **found** | **asserted the opposite** — "every named sub-check … is independently mutation-tested", citing the implementer's ledger rather than testing the branch points |
| S5 / P1 (SKU mechanism) | refuted the diagnosis **and** reclassified the cause as object lifetime, bounding the class at 13 files | refuted the diagnosis; left the cause unknown |
| L4 budget (0) | honoured | honoured |
| Probe hygiene | 4 files, checksummed | 3 files, checksummed; self-reported one over-evidence lapse |
| Unique contributions | the two blocking findings; the structural class survey | **the boundary check** (proved the eleven-file perimeter complete); the **timestamp-window** L4 reconciliation; N9 |

**Coordinator adjudication.** Three findings were independently re-measured by the coordinator:
B1 (`.env` slot inert → `beyo_test_main_main`), B2 (a 1.30 s unit run dropped `beyo_test_main`),
and S4's drivername row (`36 passed` with the check removed, file restored byte-identical). All
three confirm Opus. **Sonnet approved a phase carrying an inert safety switch and a silent
database-destruction path**, and affirmed coverage that does not exist by trusting the
implementer's ledger — the exact failure mode C4 was written to prevent.

Sonnet's two unique contributions were real and both are adopted above. The conclusion is that
Sonnet is a capable *second* reviewer and an unsafe *only* one: on this pipeline the reviewer is
the last gate before an approval baseline that three other projects consume, and a missed
`DROP DATABASE` is not a cost the model delta covers. **Recommendation: keep Opus on the review
role.**
