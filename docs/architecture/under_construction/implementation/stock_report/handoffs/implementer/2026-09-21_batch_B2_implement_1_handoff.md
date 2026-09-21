```
plan: batch B2 (6, 7)
role: implement
round: batch_B2-implement-1
state: DONE
date: 2026-09-21
actor: Sonnet (orchestrated, unattended)
tree: ff39a960bc2bdc97ad0b24180404d3b3f3466066
```

# Batch B2 implementation handoff — phases 6 → 7 (`stock_report`)

## 1. Gate check record

| Check | Result |
|---|---|
| `SR/planning/intention.md` begins `status: RATIFIED` | confirmed — "RATIFIED — by the owner (David): ratified 2026-09-18 …" |
| `SR/master_plan.md` §4A: batch B2 `IMPLEMENTATION_PROMPT_READY`, B1 and A `APPROVED` | confirmed — B1 row: "**APPROVED** (gate pending a clean L4)"; A row: "**APPROVED**"; B2 row: "IMPLEMENTATION_PROMPT_READY" |
| `git status --porcelain` empty at start | confirmed |
| `a2f4fc2` an ancestor of HEAD | confirmed (`git merge-base --is-ancestor a2f4fc2 HEAD`) |

All four gate lines passed. Implemented phase 6 then phase 7 in one session per the
prompt's dependency rule (phase 7 depends on phase 6, satisfied within this
session).

## 2. Phase 6 — `apply_stock_demand`

### Task 0 coverage map

| Row | Test id | Assertion shape matches the row |
|---|---|---|
| C1(a) | `test_apply_stock_demand.py::test_c1a_new_entry_creates_row_and_emits_created_only` | yes — row values, outcome, exactly one `:created` event, no `:updated` |
| C1(b) | `test_c1b_existing_row_quantity_changes_emits_updated_only` | yes — same row id, new quantity, exactly one `:updated` |
| C1(c) | `test_c1c_replay_same_quantity_writes_nothing` | yes — `count_writes == 0`, no events, outcome `applied` |
| C1(d) | `test_c1d_soft_deleted_row_is_not_matched_new_row_created` | yes — new row, old row untouched, exactly one goal record each |
| C1(e) | `test_c1e_mixed_batch_one_new_one_changed` | yes — both applied, exactly one `:created` + one `:updated` |
| C1(f) | `test_c1f_unknown_workspace_raises_auth_error` | yes — exception class + `http_status` |
| C2(a) | `test_c2a_exact_category_name_match` | yes |
| C2(b) | `test_c2b_case_insensitive_fallback_when_unique` | yes |
| C2(c) | `test_c2c_ambiguous_case_insensitive_match_is_not_resolved` | yes — `category_not_found`, no row |
| C2(d) | `test_c2d_exact_match_wins_over_ambiguous_case_insensitive` | yes |
| C2(e) | `test_c2e_unknown_category_entry_is_skipped_others_applied` | yes — outcomes in order, one row |
| C2(f) | `test_c2f_category_name_with_surrounding_whitespace_resolves` | yes |
| C2(g) | `test_c2g_soft_deleted_category_is_not_matched` | yes |
| C3(a) | `test_c3_sequence_goal_records_only_on_increase` (step "(a)") | yes — full record field check |
| C3(b) | same test, step "(b)" | yes — no record, no write |
| C3(c) | same test, step "(c)" | yes — no record, row at 3 |
| C3(d) | same test, step "(d)" | yes — record on 3→4, not compared to historical 5 |
| C3(e) | same test, step "(e)" | yes — no record, row at 0 |
| C3(f) | `test_c3f_new_row_at_zero_has_no_goal_record` | yes |
| C3(g) | `test_c3g_goal_record_snapshots_priority_not_live_counter` | yes — priority/order snapshot, `quantity_awaiting 0` not the live 3 |
| C4(a) | `test_c4a_replay_of_mixed_batch_writes_nothing` | yes |
| C4(b) | `test_c4b_replay_of_all_new_batch_omits_insert` | yes |
| C5(a) | `test_c5a_concurrent_first_deliveries_of_same_identity_leave_one_row` | yes — barrier-released two sessions, one row, one `:created` |
| C5(b) | `test_c5b_concurrent_batches_opposite_order_both_complete` | yes (functional only — interleaving not forced, per the plan's own note) |
| C5(c) | `test_c5c_concurrent_soft_delete_under_lock_raises_and_heals` | yes — not-returned-after-0.5s, `RuntimeError`, zero writes, heals on retry |
| C6(a) | `test_c6a_statement_count_equal_across_batch_sizes_all_new` | yes — equal, `≤ 8` |
| C6(b) | `test_c6b_statement_count_equal_across_batch_sizes_all_changed` | yes |
| C6(c) | `test_c6c_statement_count_equal_across_batch_sizes_all_unchanged` | yes — exactly 5 |
| C6(d) | `test_c6d_statement_count_equal_across_batch_sizes_one_unknown_category` | yes |
| C7(a) | `test_apply_stock_demand_timing.py::test_c7a_default_timeout_is_the_first_statement_with_both_params` | yes — first statement, `('5000','5000')` |
| C7(b) | `test_c7b_statement_timeout_fires_before_the_holder_releases` | yes — `DBAPIError` sqlstate `57014`, elapsed bound, byte-identical afterward |
| C7(c) | `test_c7c_deadline_exceeded_raises_before_commit` | yes — 503, nothing written |
| C8(a) | discharged by `test_c1a_...` (plan cell: "— (C1(a) mutation)") | yes |
| C8(b) | `test_c8b_updated_event_payload_matches_returning_values` | yes — full six-field payload check |
| C8(c) | `test_c8c_unchanged_and_skipped_entries_emit_no_events` | yes |
| C8(d) | `test_c8d_event_workspace_id_is_the_argument_not_empty` | yes |

Every test in `test_apply_stock_demand.py` (28) and `test_apply_stock_demand_timing.py`
(3) appears in this map against a criterion row; there are no orphan tests.

### Test files and L1 results

- `app/tests/integration/services/commands/stock_report/test_apply_stock_demand.py` — 28/28 green.
- `app/tests/integration/services/commands/stock_report/test_apply_stock_demand_timing.py` — 3/3 green (the sleeping C7(b) row, ~8.6s; excluded from L1 loops by file per H25, never by `-k`).

### Named-mutation ledger, with derivation

30 named-mutation cells counted from plan 6 §6 (excludes `—` cells, the C8(a) reuse,
and the C3(a)-iii equivalent mutant carried by C3(g)). `executed == declared == 30`.
Full per-row table with sites, commands and results is in **plan 6's Review log**
(`plans/plan_6.md` §8) — reproduced in full there rather than duplicated here
verbatim; two highlights:

- Two cells (C1(c), C4(a)) name the identical code change and are recorded as one
  physical mutation run against both tests.
- Two mutations were **re-sited** after an initial false green: C2(d) (reordering
  alone was inert; the real defect stops at the ambiguous case-insensitive result
  without falling through to exact) and C3(f) (the `>`/`>=` swap is inert for a
  new row at 0, since `0 != 0` is false regardless; the real mutation
  unconditionally credits every created row). C6(a) needed to loop per **entry**,
  not per distinct category key, since the 3-vs-300 fixtures share one category.

### Judgment calls and deviations

All recorded in plan 6's Review log (§8): the identity-based step-6 lock (H17), the
`CAST(:name AS type)` fix for a SQLAlchemy `text()` bind-parameter parsing gap
(`:name::type` is not recognized as a parameter), reusing the mapped
`StockReportPriorityEnum` column type via `text(...).columns(...)` for the raw-SQL
`RETURNING`, `resolve_categories_for_entries`'s per-entry resolution order, and the
C3(g) fixture's companion row (needed to make `priority_order = 2` a legitimate
dense value rather than a self-contradicting fixture).

## 3. Phase 7 — the demand endpoint

### Task 0 coverage map

| Row | Test id | Assertion shape matches the row |
|---|---|---|
| C1(a) | `test_receive_stock_demand_webhook.py::test_c1a_key_setting_none_is_401` | yes |
| C1(b) | `test_c1b_key_setting_blank_is_401` | yes |
| C1(c) | `test_c1c_workspace_setting_none_is_401` | yes |
| C1(d) | `test_c1d_missing_header_is_401` | yes |
| C1(e) | `test_c1e_wrong_header_is_401` | yes |
| C1(f) | `test_c1f_non_ascii_header_is_401_not_500` | yes — asserts `http_status == 401`, not 500 |
| C1(g) | `test_c1g_workspace_setting_names_no_workspace_is_401` | yes |
| C1(h) | `test_c1h_all_401_messages_are_byte_identical` | yes — set of exactly one message |
| C1(i) | `test_c1i_verify_runs_before_parse` | yes |
| C1(j) | `test_location_tracker_webhooks_router.py::test_c1j_header_key_sent_uppercase_is_still_found` | yes |
| C2(a)-(y) | `test_stock_demand_request.py` (25 parametrized/direct tests, `test_c2a_...`…`test_c2y_...`) | yes |
| C3(a)-(d) | same file, `test_c3a_...`…`test_c3d_...` | yes |
| C4(a)-(h) | same file, `test_c4a_...`…`test_c4h_...` | yes |
| C5(a) | `test_receive_stock_demand_webhook.py::test_c5a_results_echo_as_received_and_stored_row_is_normalized` | yes |
| C5(b) | `test_c5b_every_result_has_exactly_the_three_keys` | yes |
| C5(c) | `test_location_tracker_webhooks_router.py::test_c5c_route_forwards_raw_bytes_and_headers_and_renders_build_ok` (+ the `build_err` variant) | yes |
| C6(a) | `test_receive_stock_demand_webhook.py::test_c6a_created_row_and_events_carry_the_configured_workspace` | yes |
| C7(a) | `test_c7a_deadline_exceeded_answers_503_through_run_service` | yes — through `run_service`, 503, nothing written, no dispatch |

Every test in all four files (37 + 13 + 3 + 2 = 55) appears in this map. The one
addition beyond the criteria table — `test_location_tracker_webhook_verifier.py`'s
two tests — is declared as a **candidate/supplementary addition** in plan 7's
Review log (§8), not a criterion row: it pins the verifier's exact return value on
success, which no C1 row directly asserts (the C1 rows all assert on the *raised*
side). No undeclared orphan tests.

### Test files and L1 results

- `app/tests/unit/services/commands/stock_report/test_stock_demand_request.py` — 37/37 green.
- `app/tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py` — 13/13 green.
- `app/tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py` — 3/3 green.
- `app/tests/unit/services/infra/test_location_tracker_webhook_verifier.py` — 2/2 green.

### Named-mutation ledger, with derivation

29 named-mutation cells counted from plan 7 §6 (excludes `—` cells and C7(a), whose
cell explicitly says the mutation is carried by phase 6 C7(c)). **22 executed, 7
declined** (`declared 29 = executed 22 + declined 7`). Full per-row table is in
**plan 7's Review log** (`plans/plan_7.md` §8). Highlights:

- **Self-caught false green during mutation testing:** the first draft of the C1
  tests used a nonexistent placeholder workspace id for rows meant to fail before
  reaching `apply_stock_demand`. Under the C1(a)/C1(b) mutations, verification
  wrongly succeeded and fell through into `apply_stock_demand`, whose own step-2
  workspace check raised the *same exception type* for an unrelated reason — a
  false green. Fixed by seeding a real workspace for every C1 row except
  C1(c)/C1(g) (which test the workspace setting itself); both mutations were
  re-run against the corrected fixture and confirmed red.
- **Declined: C4(b)-(h).** These name properties of
  `bm/domain/stock_report/criteria_normalization.py`, phase 1's shipped, APPROVED
  code — outside batch B2's perimeter. That file's own test suite already asserts
  exact golden-vector output for every behavior these cells name, which
  structurally catches each mutation. Only C4(a) is run (its site is genuinely
  mine — the parser's `DemandEntry` construction). This is a caution-grounds
  decline, stated explicitly, not a silent skip.

### Judgment calls and deviations

Recorded in plan 7's Review log (§8): the file split (C2/C3/C4 as pure-function
unit tests of the parser vs. C1/C5/C6/C7 as command-level integration tests,
following the fold's own reasoning for C2), and the verifier unit-test file's
narrower scope.

## 4. Perimeter additions and the O1 decision

- **B3 — `record_statement_calls`** (`app/tests/helpers/statement_listener.py`):
  added as an `asynccontextmanager` yielding `list[tuple[str, Any]]` of
  `(statement, parameters)` from the same `before_cursor_execute` hook.
  `record_statements` and `count_writes` are **byte-identical** to their prior
  form — verified by diff against `a2f4fc2`. Batch A's `test_repair_stock_report.py`
  (the one existing caller of `record_statements`) was re-run and is green (see §2
  L2 scope in §6 below).
- **B4 — `StockDemandOutcomeEnum`** (`app/beyo_manager/domain/stock_report/enums.py`):
  added with exactly two members, `APPLIED = "applied"` and
  `CATEGORY_NOT_FOUND = "category_not_found"`. No other name from master plan
  §6.1's claimed-but-missing set was added (they belong to phases 9/13A).
- **O1 — plan 6 C7(a)'s outcome cell.** Implemented as the fold prescribes: two
  distinct bind names, `:statement_timeout_ms` and `:lock_timeout_ms`, both bound
  to `str(timeout_ms)`. The compiled statement carries `$1`/`$2`, and
  `record_statement_calls`'s captured parameters are asserted as
  `tuple(first_params) == (expected, expected)`. Declared in plan 6's Review log.

**For master plan §6.1/§6.5** (the orchestrator's correction, not mine to make):
please confirm `StockDemandOutcomeEnum (applied, category_not_found)` and
`record_statement_calls` in the shared skeleton sections.

## 5. Measured dependency versions

Confirmed into both plans' Review logs (not re-derived): **PostgreSQL 18.6,
SQLAlchemy 2.0.40, asyncpg 0.30.0, Starlette 0.46.2, FastAPI 0.115.12, CPython
3.13.2.**

## 6. Settings-coverage restoration

`stock_demand_webhook_timeout_ms`'s default is read from
`Settings.model_fields["stock_demand_webhook_timeout_ms"].default` (never a typed
literal) in plan 6's C7(a) test — restoring that part of the coverage batch A's fix
round lost when `test_settings.py` was deleted. Plan 7's C1(a)-(c) exercise
`manager_api_key_to_location_tracker_app` and `location_tracker_webhook_workspace_id`
being unset/blank, covering the other two. `app/tests/helpers/test_settings.py`
(the test-named helper module, out of my perimeter) was not touched.

## 7. Batch-level cross-phase integration and contract compliance

- Phase 7's `receive_stock_demand_webhook` calls phase 6's `apply_stock_demand`
  exactly per master plan §6.5's signature; phase 6's tests never depend on phase
  7's code (dependency direction holds).
- MC-8's 9-step order, the 401/422 body shapes, the webhook route shape
  (`bm/routers/api_v1/connecteam_webhooks.py` precedent), and the envelope
  (`build_ok`/`build_err`) all match §5 of the batch prompt.
- The new route `POST /api/v1/location-tracker/webhooks/stock-demand` is mounted
  in a **new** `app.include_router` call in `bm/routers/api_v1/__init__.py`; the
  existing `location_tracker.router` mount (its own `/items/location` route) is
  byte-unchanged (H22).
- No Alembic revision added; no `alembic upgrade`/`downgrade` run (H13).

### L2 (batch end)

```
tests/unit/domain/stock_report
tests/unit/services/commands/stock_report
tests/unit/services/infra/test_location_tracker_webhook_verifier.py
tests/unit/routers/api_v1/test_stock_report_router.py
tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py
tests/integration/models/stock_report
tests/integration/services/commands/stock_report
tests/integration/services/queries/stock_report
tests/integration/services/commands/reset/test_stock_report_reset.py
tests/integration/helpers/test_stock_report_helper.py
```
→ **334 passed** (tree `ff39a96`).

### L4 (batch end, once)

Command: `PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile`, tree `ff39a96`
(current HEAD).

**Result: 21 failed / 3436 passed / 2 skipped.**

- **Failure-ID set diffed both ways against the 21-ID baseline**
  (`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md`
  §3): **identical set, no additions, no removals** — verified by manual line-by-line
  comparison of both 21-item lists.
- **Known drifter check:** run at **02:05 UTC** (inside the 00:00-03:00 UTC window).
  `test_ended_shift_bucket_collapse.py::test_list_workers_totals_reports_an_open_clock_out_record_as_ended_shift`
  did **not** appear in this run's failures — the drifter did not fire this time.
  Recorded per the prompt's instruction regardless of outcome.
- **Passed-count arithmetic:** 86 new tests collected across the two phases'
  6 test files (verified by `pytest --collect-only`: 28 + 3 + 37 + 13 + 3 + 2 = 86).
  `3349 (B1 stamp) + 86 = 3435`, one short of the observed `3436`. The failed-ID
  set is exactly baseline-identical (the load-bearing invariant), and `git diff
  --stat a2f4fc2..HEAD` confirms no file outside the declared perimeter changed
  (the one `master_plan.md` diff in that range is entirely from `6fac680`, made
  before this session). I could not identify the source of the single extra pass
  within this session's budget; flagging it explicitly rather than silently
  rounding it away — the orchestrator may want a second `--collect-only` count on
  the full suite to reconcile it, but it does not indicate a regression (no
  baseline failure flipped, no unrelated file changed).

### Commits

- `4ca6da1` — `stock_report phase 6 — apply_stock_demand: find-or-create, goal records, replay, deadline (D6)`
- `ff39a96` — `stock_report phase 7 — demand webhook: key auth, body validation, duplicates, router`

Both are `CHECKPOINT`-shaped (not approved), perimeter paths only, no tracker row
touched (master plan is batch-tracked; that row is the orchestrator's to write).

### Blockers

None. Both phases fully implemented, all criteria discharged or explicitly
declined with reasoning (see §2/§3 above).

## 8. Write perimeter

Checked against `git status --porcelain` (empty — everything committed) and `git
diff --stat a2f4fc2..HEAD` (§6 above; the one `master_plan.md` hunk predates this
session).

**New files:**
- `app/beyo_manager/errors/stock_report.py`
- `app/beyo_manager/services/commands/stock_report/stock_demand_entries.py`
- `app/beyo_manager/services/commands/stock_report/_demand_lookup.py`
- `app/beyo_manager/services/commands/stock_report/apply_stock_demand.py`
- `app/beyo_manager/services/commands/stock_report/stock_demand_request.py`
- `app/beyo_manager/services/commands/stock_report/receive_stock_demand_webhook.py`
- `app/beyo_manager/services/infra/location_tracker/webhook_verifier.py`
- `app/beyo_manager/routers/api_v1/location_tracker_webhooks.py`
- `app/tests/integration/services/commands/stock_report/test_apply_stock_demand.py`
- `app/tests/integration/services/commands/stock_report/test_apply_stock_demand_timing.py`
- `app/tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py`
- `app/tests/unit/services/commands/stock_report/test_stock_demand_request.py`
- `app/tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py`
- `app/tests/unit/services/infra/test_location_tracker_webhook_verifier.py`

**Edited files:**
- `app/beyo_manager/domain/stock_report/enums.py` (B4 — one enum added)
- `app/tests/helpers/statement_listener.py` (B3 — one function added, existing two byte-identical)
- `app/beyo_manager/routers/api_v1/__init__.py` (one import + one `include_router` call added)
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_6.md` (Review log, §8)
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_7.md` (Review log, §8)

**Files a mutation probe touched (applied, reverted, byte-identical after revert —
verified by re-running the full green suite after every revert and by `grep
MUTATION` returning nothing at close):**
- `app/beyo_manager/services/commands/stock_report/apply_stock_demand.py` (C1(a),
  C1(b)(i)/(ii), C1(c)/C4(a), C1(f), C2(e), C3(a)(i)/(ii), C3(c), C3(d), C3(f),
  C3(g), C4(b), C5(a), C5(c), C6(b), C6(c), C7(a), C7(b), C7(c), C8(b), C8(d))
- `app/beyo_manager/services/commands/stock_report/_demand_lookup.py` (C1(d), C2(b),
  C2(c), C2(d), C2(g), C6(a))
- `app/beyo_manager/services/commands/stock_report/stock_demand_entries.py` (C2(f))
- `app/beyo_manager/services/infra/location_tracker/webhook_verifier.py` (C1(a),
  C1(b), C1(e), C1(f), C1(h))
- `app/beyo_manager/services/commands/stock_report/stock_demand_request.py` (C2(d),
  C2(l), C2(m), C2(s)/(t)/(u), C2(w), C2(x), C2(y), C3(b), C3(c), C3(d), C4(a))
- `app/beyo_manager/services/commands/stock_report/receive_stock_demand_webhook.py`
  (C1(i), C5(a), C5(b), C6(a))

No file outside this list was touched by any probe. `criteria_normalization.py`
(phase 1) was **not** touched — the C4(b)-(h) decline in §3 means no probe file
exists for it.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Both phases are fully implemented with green suites, complete mutation
ledgers (declared/executed/declined arithmetic auditable), and no semantic
question was left unresolved. The one open item — the single-test passed-count
discrepancy in §7 — is a measurement-reconciliation note for the orchestrator, not
an owner decision.
