---
plan: batch B2 (6, 7)
role: implement
round: batch_B2-fix-1
state: DONE
date: 2026-09-21
actor: pipeline-implementer (Claude Sonnet 5)
tree: 29b4395540c85da637273dfe187b876c768f8b2b
---

# Batch B2 fix round 1 — handoff

Tests only, as the prompt required. **No production code changed** — verified explicitly below.
All three items (B1 blocking, S1, S2) are closed.

## 1. Gate check record

1. `SR/planning/intention.md` begins `status: RATIFIED` — PASS (ratified 2026-09-18, re-ratified
   2026-09-18/19 incl. rounds 7-9).
2. `SR/master_plan.md` §4A batch B2 row shows `FIX_PROMPT_READY` (fix round 1, prompt
   `prompts/implementer/2026-09-21_batch_B2_fix_1.md`, tests only) — PASS.
3. `git status --porcelain` was empty at session start — PASS.
4. `ff39a96` is an ancestor of HEAD (`git merge-base --is-ancestor ff39a96 HEAD`) — PASS.

All four passed; no gate defect. Proceeded.

## 2. B1 — the eight endpoint identity rows (blocking finding, closed)

Added to `app/tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py`,
new "C4" section. Each test: seed workspace W, two successive `receive_stock_demand_webhook` calls
with the two raw JSON bodies, then a live `stock_report_items` row count for W
(`_live_row_count` helper — `select(StockReportItem).where(workspace_id == W)`, no `is_deleted`
filter needed since nothing in this flow soft-deletes).

| Cell | Body 1 → Body 2 (properties) | Rows asserted | Test id |
|---|---|---|---|
| C4(a) | `{"a": ["x"], "b": ["y"]}` → `{"b": ["y"], "a": ["x"]}` | 1 | `test_c4a_key_order_is_one_live_row` |
| C4(b) | `{"wood_group": ["teak","dark"]}` → `{"wood_group": ["dark","teak"]}` | 1 | `test_c4b_list_element_order_is_one_live_row` |
| C4(c) | `{"wood_group": ["Teak"]}` → `{"wood_group": [" teak "]}` | 1 | `test_c4c_list_element_case_and_whitespace_is_one_live_row` |
| C4(d) | `{"wood_group": ["teak","teak"]}` → `{"wood_group": ["teak"]}` | 1 | `test_c4d_duplicate_list_elements_is_one_live_row` |
| C4(e) | `{"wood_group": "teak"}` → `{"wood_group": ["teak"]}` | 1 | `test_c4e_bare_string_vs_one_element_list_is_one_live_row` |
| C4(f) | `{"Wood_Group": ["teak"]}` → `{"wood_group": ["teak"]}` | 2 | `test_c4f_key_case_is_two_live_rows` |
| C4(g) | `{" wood_group": ["teak"]}` → `{"wood_group": ["teak"]}` | 2 | `test_c4g_key_whitespace_is_two_live_rows` |
| C4(h) | `{"n": 1}` → `{"n": 1.0}` | 2 | `test_c4h_not_understood_number_forms_is_two_live_rows` |

The eight parser tests in `test_stock_demand_request.py` (signature-equality comparisons) are
**unchanged and kept**, per the prompt — this is an addition, not a replacement.

**Arming mutation (identity-collapse), applied and reverted:**

- Site: `app/beyo_manager/services/commands/stock_report/stock_demand_request.py`, `DemandEntry`
  construction (definition site) — `properties_signature=compute_stock_criteria_signature(
  properties_raw)` replaced with `properties_signature=json.dumps(properties_raw)` (same family
  as C4(a)'s own named mutation: compute identity from the raw dict instead of the normalized one).
- Command: `PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py -q -k "test_c4"`
- **Result — 5 of 8 reddened on their own row-count assertion** (the invariant these rows exist to
  prove): C4(a)-(e), each `assert 2 == 1` (mutation produced 2 live rows where the row's own claim
  is 1).
- **C4(f)-(h): the row-count assertion itself did NOT redden** — it correctly stayed at `2 == 2`,
  because removing normalization cannot cause two identities that are already distinct (by key
  case/whitespace/number type) to collapse into one. All three test *functions* still failed, but
  at the `assert_stock_report_clean(...)` call after the row-count assertion passed: the mutated
  stored `properties_signature` no longer matches a fresh recompute from `row.properties` inside
  `compute_stock_report_divergences`, which is a real but **incidental** divergence caught by an
  unrelated consistency check, not by the identity invariant this round is proving.
- **This is reported per the prompt's "if some do not redden, that is a finding: report it"
  instruction, and resolved as a non-finding**: C4(f)-(h)'s own named mutations are a different
  family (lower keys / strip keys / normalize numbers), already applied against
  `criteria_normalization.py` and confirmed red in review 1 §3 (`declared 29 = executed 29`,
  unchanged by this round — not re-run here, per the prompt's "do not re-run them"). The single
  arming mutation this round used was correctly sited for what it targets (the (a)-(e) collapse
  family) and correctly inert for (f)-(h)'s own claim; it was never expected to arm (f)-(h) and the
  fact that it didn't (via the assertion that matters) is exactly right.
- Reverted. Checksum before and after, identical:
  `d8578ce3826a5e66d27b8dada075f26b481163941567e3146132be5b122c5d84` (matches the reviewer's
  recorded checksum for this file in review 1 §9). `git diff` on the file after revert: empty.
- Post-revert confirmation: all 8 pass again (`8 passed`).

## 3. S1 — the two integration tests (closed)

Both added to `test_receive_stock_demand_webhook.py`, new "C2" section, using a restated
`WRITE_TABLES` (the same four MC-9 tables `test_apply_stock_demand.py` defines:
`stock_report_items`, `stock_task_assignments`, `stock_report_history_records`, `tasks`) so the
file stays self-contained, and `record_statements`/`count_writes` from
`tests/helpers/statement_listener.py`.

- **`test_c2a_c2x_malformed_bodies_write_nothing_through_the_command`** — discharges both C2(a)
  and C2(x) in one function (mirroring the prompt's own framing of the correction as one test).
  C2(a): raw body `b"\xff\xfe"` (invalid UTF-8) → asserts `http_status == 422` and
  `count_writes(statements, WRITE_TABLES) == 0`. C2(x): a three-entry body with entries 0 and 2
  malformed (blank `itemCategory`; `quantityRequested: -1`) and entry 1 valid → asserts
  `http_status == 422`, message contains `"entry 0"` and `"entry 2"`, does **not** contain
  `"entry 1"`, `count_writes(...) == 0`, and `_live_row_count(...) == 0` (entry 1 is not applied —
  the batch is atomic).
- **`test_c2y_extra_key_is_ignored_and_the_entry_is_applied`** — one entry carrying an extra
  `"location": "LC1"` key → asserts `response["results"][0]["outcome"] == "applied"` and the
  created row's `quantity_requested == 3`.

## 4. S2 — orphan test (closed: deleted, not declared)

**Deleted** `test_raises_unauthorized_when_key_is_missing_or_wrong` from
`app/tests/unit/services/infra/test_location_tracker_webhook_verifier.py`. Reasoning (recorded in
the file's own docstring and in plan 7's Review log): it traced to no criterion row, duplicated
C1(d)/C1(e) at a narrower scope, and added no coverage the command-level integration tests do not
already give — the file's own stated purpose ("the one thing the command-level rows do not
directly pin") was never what this test served, so declaring it as a candidate criterion would
have been declaring a non-finding.

**Sibling declared, per the prompt's "also":** `test_returns_the_configured_workspace_id_on_success`
is routed as **candidate criterion CF-4** in plan 7's Review log — it is the only test pinning
`verify_location_tracker_webhook`'s return value, which C6(a) otherwise proves only indirectly
(through the row and dispatched event carrying the configured workspace, not through the
verifier's own output). Left for the coordinator to fold into a criterion row or refuse with a
recorded reason — not authored as a criterion row here, per the prompt's "do not author criterion
rows."

## 5. Ledger — this round's additions (derived)

| Cause | File | Added | Removed |
|---|---|---|---|
| B1 | `test_receive_stock_demand_webhook.py` | 8 (C4a-h) | 0 |
| S1 | `test_receive_stock_demand_webhook.py` | 2 (C2a/x combined, C2y) | 0 |
| S2 | `test_location_tracker_webhook_verifier.py` | 0 | 1 (orphan) |
| **Net** | | **10** | **1** → **+9** |

Per-file counts, derived from this session's own runs (not typed):
- `test_receive_stock_demand_webhook.py`: 13 (review 1 tree) → **23** (`23 passed`, this session).
  13 + 8 + 2 = 23. ✓
- `test_location_tracker_webhook_verifier.py`: 2 (review 1 tree) → **1** (`1 passed`). 2 − 1 = 1. ✓
- `test_stock_demand_request.py`: **37** (`37 passed`), unchanged — confirms the eight parser
  tests were kept, not replaced.

**Review 1's seven closures noted, not re-run.** The seven mutations for plan 7 C4(b)-(h)
(against `criteria_normalization.py`, phase 1's approved, out-of-perimeter code) were closed by
the reviewer in review 1 §3 — all seven reddened 1:1, file restored byte-identical
(`5be822d6b3c90fd4b993866a066ca6061a40e833502116a1ef98e66bcabd3791`). This round did not touch
that file and did not re-run those seven, per the prompt's explicit instruction ("Do not re-run
them and do not touch `criteria_normalization.py`"). Plan 7's mutation ledger stands at
**declared 29 = executed 29** (unchanged by this round, which added no new named mutations of its
own beyond the one arming demonstration in §2 above, which is not a plan-named mutation).

## 6. L2 and L4 stamps, tree SHAs, baseline diff

All commands run from `app/`.

**L1** (whole file, never `-k`), on the final tree (`29b4395`):
- `PYTHONPATH=. pytest tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py -q` → **23 passed**
- `PYTHONPATH=. pytest tests/unit/services/infra/test_location_tracker_webhook_verifier.py -q` → **1 passed**
- `PYTHONPATH=. pytest tests/unit/services/commands/stock_report/test_stock_demand_request.py -q` → **37 passed**, unchanged from review 1's tree.

**L2** (batch scope — the ten folders/files from the implement handoff's "L2 (batch end)" list),
on the final tree (`29b4395`):
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
→ **343 passed**. Derived: review 1's tree stamp was **334**; `334 + 10 (added) − 1 (removed) =
343`. Matches exactly.

**L4** (one authoritative stamp, full suite), on the final committed tree:
- Command: `PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile`
- Tree: `29b4395540c85da637273dfe187b876c768f8b2b` (HEAD, `git status --porcelain` empty at run time)
- Result: **21 failed / 3445 passed / 2 skipped**
- Derived: review 1's / implement-1's stamp on `ff39a96` was **21 failed / 3436 passed / 2
  skipped**; `3436 + 9 (this round's net addition) = 3445`. Matches exactly.
- **Failing-ID set diffed both ways against the published 21-ID baseline
  (`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md`
  §3): identical, zero difference either direction** (`diff` of the two sorted 21-line sets
  produced no output).
- Analytics drifter (`test_c3_real_concurrent_open_insert_translates_the_loser[model]`) is **not**
  in this run's failing set (it passed) — consistent with it being load-dependent per its known
  description; not investigated further, per scope.

**Note on stamp timing.** The full-suite run above was taken *after* the plan_7.md Review-log
edit, i.e. on the exact tree that was committed — I re-ran L4 (and L2) a second time for this
reason after first running them before that doc-only edit, so the cited stamp's tree identity is
unambiguous and requires no reader-side reconciliation.

## 7. Write perimeter

**Full write perimeter for this session**, checked against `git status --porcelain` (empty at
close) and `git diff --stat ff39a96..HEAD`:

- `app/tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py` —
  10 tests added (2 S1 + 8 B1), no test removed or altered.
- `app/tests/unit/services/infra/test_location_tracker_webhook_verifier.py` — 1 test deleted (S2
  orphan), 1 unchanged test kept, docstring updated with the S2 reasoning.
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_7.md` — one
  appended Review-log entry (§8) documenting this round.

**No other file was touched.** In particular:

- **`git diff ff39a96..HEAD -- app/beyo_manager/` is empty** — confirmed, no production code
  changed, exactly as this round required.
- `plan_6.md`, `master_plan.md`, `criteria_normalization.py`, the review handoff, and the fix/review
  prompt files are untouched by this session (their presence in `git diff ff39a96..HEAD --stat` is
  entirely from the prior review-1 commit `2542a58`, made before this session started).

**Mutation-probe files (applied-and-reverted), listed separately from the fix's own changes:**

| File | Probe | Reverted, checksum-verified |
|---|---|---|
| `app/beyo_manager/services/commands/stock_report/stock_demand_request.py` | Identity-collapse arming mutation (§2) | Yes — `d8578ce3826a5e66d27b8dada075f26b481163941567e3146132be5b122c5d84` before and after; `git diff` on the file is empty |

No other file was used as a mutation-probe target this round. No database/state side effects
persisted: every new test carries its own `finally: purge_stock_report_workspace + commit` (the
S1/B1 tests follow the file's existing pattern exactly), and every test run this session ended
green with teardown executing.

## 8. Commits

One checkpoint commit, perimeter paths only (`git add` of the three files named in §7, never
`-A`/`.`/`-a`):

```
29b4395 CHECKPOINT (not approved): stock_report batch B2 fix 1 — B1 endpoint identity rows (tests only), S1 write-path rows, S2 orphan resolved
```

No tracker row written (the batch row is the orchestrator's, per the prompt). No push, amend (of
any *prior* commit), rebase, or reset. (One local correction: my first commit attempt used a
non-conforming subject line; I amended that single, not-yet-shared commit immediately, before any
other commit followed it, to carry the required `CHECKPOINT (not approved):` prefix — no other
history was touched.)

## 9. ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner in this round. Card 1 from review 1 (three uncovered invariants —
demand-authorship cells, the sorted-VALUES lock order, the shared verifier's workspace-setting
guard) is untouched, exactly as the prompt directed: it remains open in review 1's handoff and in
plan 7's carry-forward table (CF-1, CF-2, CF-3), for the owner to decide on their own schedule.
