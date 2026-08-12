---
plan: phase 4 (configuration services)
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-12
actor: Claude
---

# Phase 4 review r1 handoff

**Verdict: CHANGES_REQUESTED** — 2 blocking, 3 should-fix, 11 notes.

The configuration surface itself is substantially correct and was re-derived
independently against the configured development database, not read from the
implementer's log: every §7A.4 admission row, both chain races on the genuine
two-session DB-conflict path, all twelve §6A.4 term cells, the group guards, the
§7A.5 classifier through the status query, the audit vocabulary and the 13
registered routes all behave exactly as the authorities specify. What does not
hold is the **evidence**: 7 test nodes were shipped against a criteria set that
enumerates roughly 60 rows, and the two seams that carry the most silent-failure
risk (the API request boundary, the whole router surface) have no arbiter at all
— removing `MANAGER` from a route or deleting the mandated OpenAPI wording leaves
the entire 1779-node suite byte-identical.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing on this round needs an owner answer. B2 looks like a semantic question
but is not: §6A.4 already decided that an invalid term is rejected at request
time, and registry §6.2 already decided that no upper-bound CHECK exists — the
implementation simply does not carry the decision. If the coordinator disagrees
that the request layer owns those bounds, that becomes a card next round.

## Probe results

### P4-1 — criteria coverage arithmetic (THE probe)

**Measured, not accepted.** Collection at `3075fc3` (pre-phase-4) = 1772 selected;
at HEAD = 1779. Delta **+7 exactly**. Suite: pre-phase-4 1749 passed / 23 failed /
1 deselected; HEAD 1756 / 23 / 1; failure sets **byte-identical** (`diff` clean).
The handoff's "1755 passed / six net phase tests" is off by one, and its
"phase-focused suites: 72 passed" counts phase-3's calculator tests — the
coordinator's P-L reading is confirmed with numbers.

The 7 nodes:

| # | node id |
|---|---|
| N1 | `tests/unit/domain/item_economics/test_configuration.py::test_configuration_classifier_uses_explicit_failure_order_and_same_basis_identity_for_gap` |
| N2 | `tests/unit/domain/item_economics/test_configuration.py::test_is_applicable_is_half_open_and_excludes_deleted_versions` |
| N3 | `tests/unit/services/commands/item_economics/test_item_economics_requests.py::test_basis_request_canonicalizes_numeric_columns_before_command_derivation` |
| N4 | `…/test_item_economics_requests.py::test_model_request_canonicalizes_percentage_terms_to_three_places` |
| N5 | `…/test_item_economics_requests.py::test_integrity_translation_preserves_registered_and_unknown_paths` |
| N6 | `tests/integration/services/commands/item_economics/test_configuration_commands.py::test_configuration_commands_canonicalize_chain_and_status` |
| N7 | `…/test_configuration_commands.py::test_basis_admission_ignores_a_soft_deleted_open_row` |

Uncovered-row inventory (the blocking finding B1):

| Criterion | Required | Covered | Gap |
|---|---|---|---|
| C1 admission | 20 (10 rows × 2 chains) | 2 (basis+model "no open row / NULL" accept via N6/N7; N7 realizes it through a soft-deleted open row as pinned) | **18** — every rejection identity on both chains, and 3 of 4 accept rows |
| C2 adjacency | ≥8 (3 `is_applicable` rows + theorem row × 2 chains) | 0 | **all** — N2 exercises `is_applicable` on `SimpleNamespace`, never on a chain a command built (charter rule 3), and nothing asserts that creating v2 closes v1 |
| C3 conflict path | 2 (one per chain, concurrent) | 0 | **all** — N5 is the hand-built `IntegrityError` the harness block explicitly excludes |
| C4 rate rows | 5 row groups | 3 (canonicalize-then-derive; persisted rate verbatim; derived-never-accepted) | underflow (command **and** DB CHECK, 2 rows); the S4-forward parse row "distinct from the B1 row" (the same `173.456` fixture serves both) |
| C5 terms | 12 cells + 4 dual-path rows + router-surface immutability | 0 | **all 12 cells**, both dual paths, the A6 assertion |
| C6 guard race | 2 rows + 2 mutations | 0 | all (honestly declared) |
| C7 INV-G1 & group guards | 5 (dual-path + 3 delete rows) | 0 | all |
| C8 §7A.5 | 6 fixtures via the **status query** + structural probe | ~1 (N6 covers row 6 incl. `first_failure is None`); N1 covers rows 1–4 as a pure call on hand-built rows, not through the query | row 5 entirely; rows 1–4 not on the production read path; the structural probe was run but not committed |
| C9 percent docs | 1 | 0 | all |
| C10 queries | 14+ (3 queries × 4 + update happy + rename collision × 2 paths) | 0 (N6 asserts the rename happy path only) | all |
| C11 roles & audit | 13 routes × 2 rejection rows + retention rows + 9 audit rows | 0 | **all** — no test in the repo references the item-economics router |

### P4-2 — mutation ledger (L8 compliance)

Every declared mutation re-run in a disposable worktree with observed pytest node
ids. "shipped" below = the 7 nodes above.

| Mutation | Site | Observed |
|---|---|---|
| C1 drop `is_deleted = false` from the open-basis lookup | `create_production_cost_basis_version.py:22` (definition site) | reddens **exactly** N7 (1 failed / 6 passed) — declaration accurate |
| C4 return the unquantized parsed Decimal | `requests/__init__.py:22` | reddens **N3, N4, N6** (3 failed / 4 passed) — declaration accurate but under-counted |
| C5 collapse index discrimination to a blanket conflict | `_common.py:32-38` | reddens **only N5** — the proxy the plan excludes; the A5/name DB-path rows do not exist |
| C8 precedence from `EconomicsStatusEnum` iteration | `configuration.py:12-17` | shipped 7/7 green **and** all five reviewer status rows green — the four `not_configured` members are declared in §11A.4's order, so only a structural guard can bite; the shipped explicit tuple is correct |
| C11 remove `MANAGER` from `POST /cost-groups` | `item_economics.py:96` | shipped 7/7 green; **full suite byte-identical to unmutated** (same 1744/28/23 within the probe worktree) |
| C9 delete the router `percent_value` description | `item_economics.py:68` | shipped 7/7 green; full suite byte-identical |
| C6(a) drop the in-lock re-check | `delete_production_cost_basis_version.py:30` | shipped 7/7 green; reviewer serial probe reddens (`serial: accepted` — the version is soft-deleted while an evaluation references it) |
| C6(b) drop `FOR UPDATE` | `_common.py:78-79` (`get_basis`) | shipped 7/7 green; reviewer lock probe flips `reference_blocked_while_locked` **True → False** |

The ledger's "observed node ID" column cited architecture-graph anchors rather
than pytest node ids (P-I's second extension). Re-run, the four executable
declarations were nonetheless factually accurate — C11's was not: the "13-route
role-gate count probe" it names is not a committed test, so nothing in the suite
observed it.

### P4-3 — C6 concurrency, executed

Both C3 rows and both C6 rows were built with committed sessions from
`_session_factory()`, `SET LOCAL lock_timeout`, and `try/finally` teardown, per
the plan's harness block.

- **C3 basis:** two sessions past S1; the loser's INSERT blocked on the winner's
  uncommitted index entry (verified still pending after 400 ms), then raised
  `ITEM_COST_CONCURRENT_BASIS_VERSION`; exactly **one** row satisfied the open
  predicate afterwards. **C3 model:** identical, `ITEM_COST_CONCURRENT_MODEL_VERSION`.
  §7A.2 holds on the real DB path.
- **C6 serial:** delete of a referenced version → `ITEM_COST_BASIS_VERSION_IN_USE`
  on the locked re-check.
- **C6 interleaved — the plan's row cannot be built (finding S3).** A referencing
  `item_cost_evaluations` INSERT needs `KEY SHARE` on the version row, which
  conflicts with the delete's `FOR UPDATE`: the second session blocks and cannot
  "commit a referencing evaluation" while the seam is paused. My first attempt at
  the plan's literal wording hung the run — exactly the deadlock the harness block
  anticipated. The corrected arbiter is in the Review log.
- **Consequence for §7.5 (note N11):** once the delete commits, the blocked INSERT
  proceeds and lands an evaluation referencing a **soft-deleted** version
  (`referenced_version_is_deleted: True`). The hazard §7A.6 describes is live and
  real; phase 7's `FOR SHARE` counterparty is genuinely load-bearing, not a formality.

### P4-4 — production-code mechanisms, verified independently

Correct: canonicalize-then-derive (`Decimal(str(v))` then `quantize(HALF_EVEN)`;
stored `173.46` with rate `12.0105`, and pydantic v2 preserves JSON decimal text at
the router — `173.4567890123456789` arrives as `Decimal('173.45678901234567')`, never
a float expansion); index-name discrimination with unknown re-raise (all six
registered names match §6.2 exactly); **admission totality** (all 20 rows, verified
row by row); classifier precedence from `CONFIGURATION_FAILURE_PRECEDENCE`, never
enum iteration; `is_applicable` half-open and deletion-aware; no term-mutation
route; no workspace event (`grep` for `event_bus` in the command package: 0 hits);
audit events exactly the 9 registered strings; the reference predicate counts all
evaluation rows regardless of kind or `is_deleted`; group delete guarded on
non-deleted versions and `removed_at IS NULL` memberships; `router` percent
description carries all three P-D elements.

`has_open_*` vs applicability (the implementer's judgment call): **§7A.3-consistent**
— under §7A.3's theorem the open row is precisely today's applicable row, and the
only state where the two could disagree (`effective_to` in the future) is
unreachable from these commands, which always close at a date ≤ today. Verified on
a chain closed yesterday: `has_open_basis_version: false` with
`first_failure: not_configured_no_basis_version` — coherent. Recorded as note N7 so
phases 5/7 do not re-litigate it.

P-K audit of the shared helper `_common.py`: `admission_error` pre-satisfies no
criterion row (it is the mechanism under test, called by both chains with different
identity prefixes); `translate_integrity_error` is the single point every conflict
row would flow through — a criterion asserting only one identity through it would
be satisfied by a helper that returns that identity for every index, so C5's and
C3's rows must each assert their own token (they do, where they exist).
`reference_exists` pre-satisfies nothing because nothing calls it (finding S2).

### P4-5 — smuggled field

The N4 pin holds behaviourally: a request carrying `cost_per_worker_minute_minor:
999.9999` **succeeds** and persists `12.0105`, the derived value. But the mechanism
is not the pin's: the **router body model declares the field**, so the OpenAPI
schema advertises the derived rate as an accepted input (finding S1). The command
request model is the one that ignores it.

### P4-6 — architecture-graph delta (47 pending, revision `bf6dad5b…`)

Code read first, stored claim second, per the anti-pattern rule. **No item
adjudicated.** Every claim is factually true; the defect is in the anchors.

| Item group | Count | Claim verdict | Anchor verdict | Recommended |
|---|---|---|---|---|
| `endpoint-item-economics-*` (13 nodes: post/get/patch/delete cost-groups, sections ×2, basis ×3, cost-model ×3, status) | 13 | **accurate** — every path matches §6.5's registered surface in FastAPI notation, and every "ADMIN/MANAGER route" claim matches `require_roles([ADMIN, MANAGER])` in code | **exact** — 93-99, 102-109, 112-119, 122-128, 131-138, 141-148, 151-159, 162-170, 173-179, 182-188, 191-198, 201-207, 210-215 all bound their route precisely | **promote** |
| `command-…-create-production-cost-group` (13-36), `…-create-production-cost-basis-version` (13-51), `…-create-cost-model-version` (14-74), `…-delete-cost-model-version` (14-37) | 4 | accurate | **exact** | **promote** |
| `command-…-update-production-cost-group` (12-30 vs 13-34), `…-delete-production-cost-group` (12-38 vs 15-41), `…-add-section-to-cost-group` (12-48 vs 15-49), `…-remove-section-from-cost-group` (12-33 vs 14-32), `…-delete-production-cost-basis-version` (13-38 vs 14-37) | 5 | accurate | **imprecise** — each starts on a blank/import line and three truncate before the audit write and return | **edit** (re-anchor to the function's real span), then promote |
| All 25 relationships (`accepts` ×9, `writes_to` ×9, `reads_from` ×6, `configured_by` ×1) | 25 | accurate | **wrong file for 9 of them** — every edge carries the identical blanket anchor `routers/api_v1/item_economics.py:88-215`; the `command --writes_to--> table` edges have no evidence in the router at all (the writes are `session.add(...)` in the command modules) | **edit** (re-anchor per edge; the nine `writes_to` edges to their command's add/flush site), then promote |

Incompleteness worth the owner's attention (not errors, so not filed as
discrepancies): `create_cost_model_version` also writes `cost_model_terms` and
`GET /cost-model-versions` also reads it — no edge to `table-cost-model-term`
exists; `create_production_cost_basis_version --uses--> domain-item-economics`
(the calculator call, the phase's whole point) has no edge; and only
`endpoint-item-economics-status` is linked to `domain-item-economics`, leaving the
other 12 endpoints unattached to the domain.

## Findings by severity

- **B1 (blocking)** — criteria coverage: ~6 of ~60 enumerated rows. Full
  inventory in P4-1 and in the plan's Review log, with per-criterion correction
  clauses.
- **B2 (blocking)** — request models validate shape only; all eight out-of-range
  numeric inputs reach the client as HTTP 500 "An unexpected internal error
  occurred." (`DivisionByZero` ×2 inside the calculator, `IntegrityError` ×5
  re-raised, `DataError` ×1), violating §6A.4's "rejected twice (request + DB
  CHECK)" where §6.2 pins that no upper-bound CHECK exists for `percent_value`.
- **S1 (should-fix)** — the router body model declares the derived
  `cost_per_worker_minute_minor` as an input field (§5, §6A.6).
- **S2 (should-fix)** — dead `_common.reference_exists`; `get_group(for_update=)`
  never passed `True` (charter rule 4).
- **S3 (should-fix, plan text)** — C6's interleaved row cannot be built as
  written; corrected arbiter supplied.
- **11 notes** (N1–N11) in the Review log: S1-before-S2 rests on SQLAlchemy's
  flush ordering with nothing pinning it (N1); `.value` enum comparison (N2);
  `ITEM_COST_TERM_SHAPE_INVALID` reuse and message shape (N3); uniform conflict
  sentence (N4); C9's assertion case (N5); C5's term-index DB paths unreachable by
  construction (N6); `has_open_*` divergence verified benign (N7); handoff
  arithmetic (N8); ledger node ids (N9); vestigial `version = None` (N10); §7.5's
  residual hazard verified live (N11).

## Lessons for the plans

- **L1 — a criterion that only the router can satisfy needs a router-level test
  named in the plan.** C9 and C11 were both written as assertions "on the router
  model" / "per route", and both shipped with zero arbiters because nothing in the
  repo ever instantiates the app for these routes. The plan should name the
  harness (`TestClient` / `app.routes` introspection) the way §10 names the DB
  recipe, otherwise "router-surface assertion" reads as satisfiable by inspection.
- **L2 — a dual-path identity criterion must first establish that the second path
  is reachable.** C5 demanded the DB-conflict path for two term indexes that
  cannot be violated: terms are always inserted against a version created in the
  same transaction. Registry §6.4's dual-path rule needs a reachability column.
- **L3 — a named mutation must be paired with the observable it flips, not with
  the outcome it "should" change.** C6(b) named the rejection outcome; the real
  observable is "the referencing INSERT is blocked while the lock is held". This
  extends P-I/L8: declare the *assertion* that reddens, not the scenario.
- **L4 — lock criteria must state which counterparty acquires which lock.** The
  plan assumed `FOR UPDATE` had no counterparty before phase 7; PostgreSQL's FK
  `KEY SHARE` is one, and it is what makes the plan's own interleaving deadlock.
- **L5 — "request canonicalization" and "request validation" are different
  criteria.** R11-1 got a criterion (and shipped correctly); the bounds the same
  columns carry got none, and the gap is invisible in a green suite.

## Human-authorization backlog

47 architecture-graph items pending, recommended in P4-6 as **17 promote /
30 edit-then-promote**. No item was promoted, edited, rejected or removed.

## Full write perimeter

- `plans/phase_4_configuration_services.md` — frontmatter `state` → CHANGES_REQUESTED; Review log entry appended (append-only).
- `master_plan.md` — phase-4 tracker row only (state, actor, note). The parallel 4B session's rows and §6.3/§6.4/§6.5 edits in `ef21f1e` were left untouched.
- `handoffs/reviewer/2026-08-12_phase4_review_r1_handoff.md` — this file.
- **No code, test, migration or `.archgraph` file was written.**

## Mutation-probe declaration

All probes ran in **disposable git worktrees** created from `d933e6a` and
`98c75a8~1` under the session scratchpad, never in the main working tree.

- Probe test files (`test_zz_reviewer_probe.py`, `test_zz_reviewer_concurrency.py`,
  `test_zz_reviewer_lock.py`) existed only inside the probe worktree and were
  deleted with it. Both worktrees are removed; `git worktree list` shows only the
  main tree; `git status` in the main tree is clean.
- Eight source mutations (table in P4-2) were applied inside the probe worktree
  and reverted with `git checkout --`; the worktree was verified clean before
  removal. One mutation (C6a) survived a killed run and was detected and reverted
  by an explicit `git status` check — recorded here rather than discovered later.
- **Database side effects restored.** The committing probes own `try/finally`
  teardown; one killed run left residue, which was found and removed by hand:
  `production_cost_groups`, `production_cost_basis_versions`, `cost_model_versions`,
  `cost_model_terms`, `item_cost_evaluations`, `production_cost_group_sections` and
  this domain's `audit_logs` rows all verified back to **0** afterwards, and the two
  probe workspaces/users deleted. The configured database is at head
  (`90cdd23a828e`); no migration was run.
- `app/.env` was copied into both worktrees (untracked, required for settings);
  removed with them.
