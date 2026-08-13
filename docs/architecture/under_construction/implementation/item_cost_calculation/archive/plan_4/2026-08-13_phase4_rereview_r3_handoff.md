---
plan: phase 4 (configuration services)
role: review
round: 3 (re-review, delta-scoped — B1/B2/S1–S4)
verdict: APPROVED
state: REVIEWING → APPROVED
date: 2026-08-13
actor: Claude
---

# Phase 4 re-review r3 handoff

**Verdict: APPROVED** — 0 blocking, 0 should-fix, 4 notes.

All six r2 gaps are closed, and each closure was re-proven by a mutation I applied
myself rather than read from the ledger. Three of the mutant sha256s I produced are
byte-identical to the implementer's declared values, and the two that mattered most
now bite where r2 said they did not: B1's guard drop reddens the two `table-row-5`
nodes, and S1's index→identity swap reddens the **real** two-session race, not just
the hand-built proxy. The cycle changed no production file. Both of the coordinator's
pre-resolved consumption notes check out — the garbled probe paths are a transcription
defect (every declared sha256 matches the real file), and the focused/suite arithmetic
reconciles exactly once one consistent test set is used.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. The 47 architecture-graph items remain held for the
coordinator's single post-approval adjudication under master plan §8's standing
authorization.

## Step 1 — verified perimeter

- `git show 74b280b` = exactly `test_phase4_fix_coverage.py`,
  `test_item_economics_requests.py`, the master-plan tracker row and the phase-4
  Review log — **4 files, +405/−27**, precisely the fix prompt's allowance.
  `c89354c` carries only the handoff; `c55c3de` only the tracker row and the
  re-review prompt.
- `git diff 2567fc7..HEAD -- app/beyo_manager/` is **empty**.
  `git diff 4e19506..HEAD -- app/` is the two test files alone. **Zero production
  changes**, as the fix prompt required.
- `git status --porcelain` empty at open and at close.

### Pre-resolved consumption notes — both confirmed, neither filed

1. **Garbled probe paths.** The handoff lists
   `app/beyo_manager/services/commands/item_economics/queries/list_groups.py` and
   siblings; that directory does not exist. All six declared "main" sha256 values
   match the real files at their real paths:

   | Declared sha256 | Real file |
   |---|---|
   | `3b594c36…` | `services/commands/item_economics/_common.py` |
   | `904b635f…` | `services/commands/item_economics/requests/__init__.py` |
   | `9f424164…` | `services/commands/item_economics/update_production_cost_group.py` |
   | `75d81316…` | `services/queries/item_economics/list_production_cost_groups.py` |
   | `1841fae0…` | `services/queries/item_economics/list_cost_model_versions.py` |
   | `e4b75249…` | `services/queries/item_economics/list_production_cost_basis_versions.py` |

   The probes were real; the transcription is the defect. Recorded, not filed.

2. **Focused +13 vs suite +17 — reconciled, no test is missing.** The two numbers
   were measured over two different sets. On one consistent set
   (`tests/integration/.../item_economics` + `tests/unit/.../item_economics` +
   `tests/unit/routers/api_v1/test_item_economics_router.py`), collection goes
   **124 → 141 = +17**, exactly matching the full-suite collection delta
   **1898 → 1915 = +17**. The implementer's 139 excludes
   `test_configuration_commands.py` (2 tests); r2's 126 included two others.
   (Measured by checking the two test files out at `2567fc7`, collecting, then
   restoring — both files sha256-verified byte-identical afterwards.)

## Step 2 — delta probes

### R3-P1 — the r2 green mutations now bite

Every mutation applied in the main worktree, exercised, reverted with
`git checkout --`, sha256 re-verified byte-identical.

| # | Mutation | Mutant sha256 | Observed |
|---|---|---|---|
| 1 | B1: drop `open_from is not None` from `_common.admission_error`'s comparison | `d8c41d1a…` = **declared** | reddens **exactly** `test_c1_admission_matrix_has_one_exact_outcome_per_chain[table-row-5-null-open-at-or-before-today-basis]` and `…-model`; 24 other C1/C2 rows stay green |
| 2 | S1: `uix_production_cost_basis_versions_open` → `ITEM_COST_CONCURRENT_MODEL_VERSION` | `71249f1a…` = **declared** | reddens `test_c3_real_concurrent_open_insert_translates_the_loser[basis]` — **the real race row**, which stayed green in r2 — plus the translation proxy row |
| 3 | B2: drop `workspace_id` from `list_production_cost_groups` | `be98cdcc…` | reddens `[groups-workspace]` (+ `[groups-is-deleted]` collaterally, via committed non-test rows in the dev DB) |
| 4 | B2: drop `is_deleted` from `list_production_cost_groups` | `88520dd0…` | reddens **exactly** `[groups-is-deleted]` |
| 5 | B2: drop `workspace_id` from `list_production_cost_basis_versions` | `cf74b027…` | reddens `[basis-workspace]` (+ `[basis-is-deleted]`) |
| 6 | B2: drop `is_deleted` from `list_production_cost_basis_versions` | `011272df…` | reddens `[basis-is-deleted]` + the combined C10 arbiter |
| 7 | B2: drop `workspace_id` from `list_cost_model_versions` | `6429d5ea…` | reddens `[models-workspace]` + `[models-is-deleted]` + the combined arbiter |
| 8 | B2: drop `is_deleted` from `list_cost_model_versions` | `8f6c38e3…` | reddens **exactly** `[models-is-deleted]` |
| 9 | B2: delete the rename pre-check (`update_production_cost_group.py:25-26`) | `5398438f…` | reddens **exactly** `test_c10_group_rename_collision_precheck_is_a_validation_error` |
| 10 | S2: `Decimal(str(value))` → `Decimal(value)` | `66626dee…` = **declared** | reddens **exactly** `test_basis_request_parses_float_as_decimal_text_before_quantization` |
| 11 | S3: `Field(gt=0)` → `Field(ge=0)` on `fixed_monthly_cost_minor` | `3de51c17…` = **declared** | reddens **exactly** `test_basis_request_rejects_each_out_of_range_numeric_field[fixed-zero]` |
| 12 | Regression check — C1's *original* named mutation: drop `is_deleted = false` from the basis open-row lookup | `d613591f…` | still reddens **exactly** `[table-row-1-none-null-basis]` + the pre-existing dedicated test — rewriting the C1 table did not lose this arbiter |

My mutant hashes for rows 3–9 and 12 differ from the ledger's because I removed the
whole predicate line where the implementer patched differently; the reddened node
ids match the declaration in every case. Rows 1, 2, 10 and 11 hash **identical** to
the declared mutants, so those four are the same byte-for-byte experiment.

I ran **all six** filter drops, not the one the prompt required.

### R3-P2 — table mapping (P-V), not the count

The 20 collected ids are `table-row-1` … `table-row-10` × `{basis, model}` — no
duplicates, no omissions. Each fixture's (open-row state, requested date) pair was
re-derived against §7A.4 rather than trusting the id:

| §7A.4 row | Fixture | Expected outcome asserted |
|---|---|---|
| 1 none / NULL | soft-deleted open row (C1's pin) | accept |
| 2 none / ≤ today | empty chain, `today` | accept |
| 3 none / > today | empty chain, `today+1` | `…_EFFECTIVE_FROM_FUTURE` |
| 4 NULL-open / NULL | **live** `effective_from IS NULL` row | `…_EFFECTIVE_FROM_REQUIRED` |
| 5 NULL-open / ≤ today | **live** NULL-open, `today−1` | accept **and** `predecessor.effective_to == d` |
| 6 NULL-open / > today | **live** NULL-open, `today+1` | `…_EFFECTIVE_FROM_FUTURE` |
| 7 dated / NULL | open at `today−5` | `…_EFFECTIVE_FROM_REQUIRED` |
| 8 dated / ≤ d0 | requested `today−5` (= d0) | `…_EFFECTIVE_FROM_NOT_AFTER_OPEN` |
| 9 dated / d0 < d ≤ today | requested `today−4` | accept |
| 10 dated / > today | requested `today+1` | `…_EFFECTIVE_FROM_FUTURE` |

The whole `effective_from IS NULL` column that r2's B1 named is now built from a
live row, and row 5 carries the predecessor-close assertion.

### R3-P3 — the two legacy-arbiter filters

`models-workspace` and `basis-is_deleted` now redden **both** their own sole-cause
row and the combined C10 arbiter under their respective filter drops (rows 6 and 7
above). Nothing rests on the legacy arbiter alone any more.

### R3-P4 — S4, bounded waits, teardown

- Both C3 gates are bounded: `asyncio.wait_for(flush_complete.wait(), timeout=0.3)`
  and, inside `gated_audit`, `asyncio.wait_for(release.wait(), timeout=0.3)`.
- **Proof of the fix, not just its presence:** I re-created r2's hang exactly —
  the B1 mutant applied with C3 **included** in the run, the configuration that
  blocked for 120 s and had to be killed. It now completes in **3.35 s** with the
  two C3 rows red (`TimeoutError`) alongside the two `table-row-5` rows.
- Concurrency subset — now **6** tests (C3 ×2, C6 ×3, plus the new committing
  `test_c10_group_rename_db_conflict_translates_the_registered_identity`) — run
  **twice**: 6 passed each time, economics row counts flat before and after
  (3 workspaces / 2 groups / 3 basis / 3 model / 0 terms / 1 evaluation / 116 audit
  rows — all r2's N3 residue, deliberately untouched). Rule 11½ holds for the new
  committing test too.

### Suite and hygiene

- **1892 passed / 23 failed / 1 deselected** (63.8 s). The failure set `diff`s
  **byte-identical** against the phase-1 baseline list — 23/23, `diff` clean.
- `ruff check` on both changed test files: clean. Configured DB at head
  (`90cdd23a828e`); no migration run; no disposable database created.
- **§6.4 conformance spot-check:** the rename dual path matches the registry
  exactly — `ITEM_COST_GROUP_NAME_TAKEN` as `ValidationError`/422 on the pre-check
  and `ConflictError`/409 on the DB conflict, per §6.4's "Config uniqueness
  conflicts" row. The DB-path row is a genuine two-session index collision, not a
  hand-built `IntegrityError`.

## Step 3 — the 47 held graph items

Not adjudicated; no item promoted, rejected, edited or removed. Because **no
production file changed since `4e19506`**, r2's corrected spans remain valid as
supplied. Two spot-checked and exact:

| Node | r2 span | Verified |
|---|---|---|
| `endpoint-item-economics-post-cost-groups` | 92-98 | line 92 = `@router.post("/cost-groups")`, line 98 = the `_run` dispatch ✓ |
| `command-…-create-cost-model-version` | 15-75 | line 15 = `async def create_cost_model_version`, line 75 = last line (file is 75 lines) ✓ |

N7's two missing `table-cost-model-term` edges remain queued for the same batch.

## Findings

**Blocking: none. Should-fix: none.**

### Notes

- **N8** — `test_basis_request_accepts_each_included_numeric_boundary`'s three rows
  are one fixture with three names: the base payload already sits at all three
  included boundaries (`fixed=1, hours=1, util=100`) and each row overwrites a field
  with the value it already holds. Verified: tightening `monthly_paid_hours` to
  `gt=1` reddens **all three** rows. S3's correction is met (the accept side is
  arbitrated), but no per-row named mutation can be declared against them. Same
  family as N5. Next touch.
- **N9** — `test_term_request_rejects_each_excluded_numeric_boundary[percent-over-max]`
  duplicates the pre-existing
  `test_term_request_rejects_each_out_of_range_numeric_field[percent-over-numeric-bound]`
  (same field, same value `1000`, same calculation type). Harmless; low value.
- **N10** — the new `asyncio.wait_for` bounds (0.3 s on the C3 gates, 0.5 s on the
  rename gather) are wall-clock limits on real DB round trips. Strictly better than
  r2's unbounded waits, but they are the first suspect if C3 or the rename-DB row
  ever flakes under load.
- **N11 (passing glance, outside phase 4)** — a single full non-e2e run commits
  substantial **non-economics** residue to the configured dev database: +116
  workspaces (`shift-hook-*`, `Workspace <hex>`), +101 users, +19 tasks, +20 working
  sections. Phase-4's own tests left **zero** (the `economics …` workspace set was
  identical before and after every run this session). Pre-existing suite-wide
  behaviour, not this phase's; suggest a maintenance row rather than a phase-4 item.
  It also qualifies r2's N3 wording: "two full-suite runs → flat" was true of the
  economics tables only.

## Carry-forward dispositions

| Item | Destination |
|---|---|
| r2 N1 — C2's theorem row asserted at `second_day`, not `today` (covered transitively by C8) | recorded, no destination |
| r2 N3 — 3 economics workspaces of dev-DB residue from interrupted fix-r2 runs | phase-4 closeout purge (coordinator) |
| r2 N4 — C4's "exactly 4 dp" asserted with `Decimal.__eq__`, scale unarbitrated | phase 5 (same files) |
| r2 N5 — C8's six fixtures are a loop, not parametrized rows | phase 5 (same files) |
| r2 N6 — C3's monkeypatched-`audit` seam undeclared in the plan's harness terms | phase-4 closeout, documentation only |
| r2 N7 — two missing `table-cost-model-term` edges | coordinator's post-approval graph pass |
| N8 — accept-boundary rows are one fixture with three names | phase 5 (same file) |
| N9 — duplicated percent-`1000` reject row | phase 5 (same file) |
| N10 — wall-clock timeout bounds | phase 9 drift sweep, only if flakiness appears |
| N11 — suite-wide non-economics DB residue | maintenance row |
| 47 pending graph items (17 promote / 30 edit-then-promote) | coordinator's single post-approval pass, §8 standing authorization |

## Lessons for the plans

- **L5 (extends P-V).** The r2→r3 cycle closed cleanly because the fix prompt
  demanded the parametrize **ids state the table mapping**, not just the row count.
  Verifying P-V then cost one `--collect-only` plus ten fixture re-derivations
  instead of a full re-audit. Worth making the standing form for any
  enumerate-a-table criterion: *the id names the authority row it discharges.*
- **L6 (extends P-I).** The implementer's ledger declared four of the six filter
  mutations and reasoned the remaining two "remain protected by the existing
  combined arbiter". Both in fact redden their own new row. A ledger that reasons
  about a mutation instead of running it understates its own work and forces the
  reviewer to run it anyway — cheaper to require every enumerated row's mutation to
  be executed, even when the author expects an existing arbiter to cover it.
- **L7 (environment, extends the charter's rule 11½ record).** A residue check
  scoped to the phase's own tables can read as "the suite is clean" when it is not.
  State the scope: this session's economics-scoped check was flat, while the suite
  at large commits ~116 workspaces per run (N11).

## Human-authorization backlog

- 47 architecture-graph items still pending (17 promote / 30 edit-then-promote per
  r1), plus N7's two missing edges. **No item was promoted, rejected, edited or
  removed by this session.** r2's corrected spans stand unchanged (no production
  file moved); adjudication remains the coordinator's single post-approval pass.

## Write perimeter (this session)

Documents written — exactly three, all **after** every probe:

- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_4_configuration_services.md`
  (Review log append only — "Re-review r3" section; no other section touched)
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
  (phase-4 tracker row only: state `IMPLEMENTED` → `APPROVED`, actor, note; earlier
  stamps preserved verbatim)
- this handoff

**No code, test, migration or `.archgraph` file was written.** Architecture Graph
touched read-only (`archgraph_status`): revision
`bf6dad5b9264937b5950366affe9910dcaacf7abd68a42114bb52fa327e68262`, 148 nodes /
186 edges, valid, 0 diagnostics, 0 stale, **47 pending, zero delta** — unchanged
from the fix-r3 declaration.

## Mutation-probe declaration

Probes ran in the main worktree (the same `.git` limitation earlier rounds hit).
Every mutation was applied, exercised, reverted with `git checkout --`, and the
file's sha256 re-verified byte-identical to its pre-probe value.
`git status --porcelain` is empty at close.

Production files touched by probes (all restored, hashes as declared above):
`_common.py`, `requests/__init__.py`, `update_production_cost_group.py`,
`create_production_cost_basis_version.py`, `list_production_cost_groups.py`,
`list_cost_model_versions.py`, `list_production_cost_basis_versions.py`.

Test files touched by the **collection-reconciliation** probe (checked out at
`2567fc7`, collected, restored; sha256 verified byte-identical):
`test_phase4_fix_coverage.py` (`69a48c5a…`),
`test_item_economics_requests.py` (`cecb2a4f…`).

**Database side effects.** The economics-scoped row set is identical before and
after this session's entire probe sequence, including two full-suite runs' worth of
phase-4 tests: the same three 2026-08-12 workspaces (r2's N3) and their 2 groups /
3 basis versions / 3 model versions / 1 evaluation / 116 audit rows, deliberately
left untouched. **This session deleted nothing and created no economics rows that
survived.** The non-economics residue described in N11 is the suite's standing
behaviour, out of phase-4 scope, and was left as found. Configured DB at head
(`90cdd23a828e`); no migration run; no disposable database created.

## Coordinator fold-ins

- Phase 4 is **APPROVED** — the gate opens for phase 4B (its projection r0 handoff
  is already deposited).
- Close out phase 4: archive `plan_4` rows, purge the three N3 residue workspaces,
  and record N6's seam declaration.
- Run the single post-approval graph pass: 47 items on r2's spans (still valid) +
  N7's two `table-cost-model-term` edges.
- Fold L5–L7 into §9's standing rules (L5 → P-V, L6 → P-I, L7 → the rule-11½
  record).
- Route N8/N9 to phase 5's touch of the request tests; N11 to a maintenance row.
