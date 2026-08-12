---
plan: phase 3
role: review
round: 4
verdict: APPROVED
date: 2026-08-12
actor: Claude (plan-reviewer)
---

# Phase 3 reviewer handoff — canonical calculator (re-review r4, delta-scoped: S6/N14/N16)

**Verdict: APPROVED.** Zero findings. All three routed corrections verify independently,
and the main-worktree probe deviation resolves as procedural only.

Phase 3 closes with B1, B2, B3 and S1–S6 all resolved and each independently
re-derived rather than accepted from a log. The calculator is the pure calculation
monopoly the phase set out to build: correct arithmetic at every seeded cell,
context-independent by construction, total over malformed input, and its closed-set
guarantee still has a live arbiter.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. R9-1 and R10-1 are implemented and verified; card 3 (the held graph node) needs
the coordinator's single adjudication now that approval has landed — anchors supplied
below.

## Step 1 — verified perimeter: PASS

`git show 71f137b` contains **exactly** four files: `calculator.py` (+4 lines),
`test_calculator.py` (+20/−6), the master-plan tracker row, the plan's Review log. The
fix handoff sits alone in its own deposit commit `3a80ee3` — the deposit-after-checkpoint
discipline held this round. Working tree clean at review start and end.

**Main-worktree probe deviation — weighed, resolved as procedural only.** r4 ran its
mutation probes in the main worktree rather than a disposable one, so the reversion
claim needed independent confirmation rather than acceptance. I checked it three ways:

1. Working-tree sha256s equal the declared values — calculator
   `03389d0a2743ae7968a0e5aecc88cc5b2675bea6762c2b9bbec2d87662af8eb0`, tests
   `6733181ed998b101ac2bcb0d95f4f5bfc3729f4d1a6ca8e40b619b8b705daa86`.
2. Those same values are the sha256 of the blobs **as committed in `71f137b`**
   (`git show 71f137b:<path> | shasum -a 256`) — so the checkpoint content and the
   current content are the same bytes.
3. `git diff 71f137b..HEAD -- app/` is empty, and `git log 71f137b..HEAD -- app/` lists
   no commit at all.

No probe residue exists anywhere. Recorded as a process note (a disposable worktree
keeps this cheap to prove), **not** a finding.

## Step 2 — delta probes

**R4-P1 (S6 — the one that mattered) — PASS.** Verified by hand before touching the
tests: `2166 / 399.5000 = 5.421777…`, which Q3 quantizes to **`5.42`** — exactly the
stored allowance. So at the new fixture the allowance *agrees*, and the cascade clause
is the only thing that can produce the second entry. (The old `399.0000` gave `5.43`,
which was the second sufficient cause that made the row pass for the ordinary reason.)
Then by mutation: deleting `or rate != stored_rate` at `calculator.py:533` reddens
**exactly** `test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload`
(1 failed / 64 passed) — where the identical deletion left **65/65 green** in r3. The
owner's pinned cascade now has its arbiter.

For the record, r3's mis-declared mutation is now moot: the `and` inversion reddens
**both** `test_rederive_reports_allowed_worker_minutes_mismatch_payload` *and* the
cascade row, because the new fixture makes the cascade row genuinely sensitive to the
clause. The declaration and the behaviour finally agree.

**R4-P2 (N14) — PASS, homogeneous across every shape.** I enumerated all eight entry
shapes rather than spot-checking one — four plain (budget, allowance, term amount,
rate+cascade) and four converted (zero rate, malformed term, NULL purchase, evaluation
snapshot). **Every entry carries exactly
`{field, rederived_value, stored_value, error}`**, so phases 7–8 may key
`entry["error"]` unconditionally; the `KeyError` hazard r3 flagged is gone. Each of the
four plain-entry `error: None` additions is live, probed separately:

| Probe | Reddened |
|---|---|
| rate entry's `error` corrupted `None` → `"x"` | the zeroed-rate row + the cascade row |
| budget entry's `error` key dropped | `test_rederive_reports_production_budget_mismatch_payload` |
| allowance entry's `error` key dropped | the allowance row + the cascade row |
| term entry's `error` key dropped | `test_rederive_detects_a_changed_term_amount_on_the_same_orm_shape` |

**R4-P3 (N16) — PASS.** An AST sweep over every `rederive` test confirms all six rows
now construct `ItemCostEvaluationTerm`, directly or via `_valid_rederive_terms()`.
`_term()`/`SimpleNamespace` survives in exactly one place —
`test_duplicate_purchase_terms_vary_only_the_snapshot_term_rows`, a non-rederive shape
test settled in r1. Charter rule 3 and C7's ORM pin now hold across the whole rederive
family.

**Suite — PASS.** `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app`:
**1749 passed / 23 failed / 1 deselected** in 57s — unchanged from r3, as expected for
a fix that adds no tests. Focused suite **65 passed**. Zero connectivity noise. The 23
failure IDs `diff` **empty** against the phase-1 routed list; N14's Shopify flake did
not fire. `ruff check` on both files: clean.

**Archgraph — unchanged, read-only.** `archgraph_status` only: revision
`671fd92a560fbaffda67e74f21eff8128c55cacfae807d98ab27fdf6e586319b`, 126 nodes /
161 edges, **1 pending item** (the held `domain-item-economics` node), zero diagnostics,
zero stale nodes. **Zero delta.** Nothing promoted, rejected, edited, deprecated or
removed.

**Card-3 anchors for the coordinator's single held adjudication.** The final calculator
is **547 lines**. Spans matching the node's three evidence claims, each landing on a
real boundary this time (r1 filed both original spans as imprecise):

| Claim | Suggested span | Covers |
|---|---|---|
| module boundary + version contract | **1–52** | module docstring, imports, `CALCULATION_VERSION`, `REDERIVE_SKIPPED`, `REDERIVE_MISMATCH`, `__all__` |
| term shape + amount formulas | **131–242** | `_term_shape` → `calculate_term_amounts`, ending at a function boundary (the duplicate-purchase guard is now inside) |
| closed-set re-derivation | **375–547** | `validate_currency_equality` + `rederive` complete, including the final `return` |

## Findings

**None.** S6, N14 and N16 are closed and verified; nothing new was seen in passing.

## Carry-forward dispositions

Approval with open notes — every unresolved item is routed to a named destination so
none can evaporate:

| Item | Origin | Destination |
|---|---|---|
| N7 — C2's Q3 "consumes the persisted rate" cell cannot bite where the rate is a parameter | r1 | **phase 4/5** — the arbiter belongs at the call site |
| N15 — the `rederive` catch-all converts *programmer* errors into integrity markers; callers must not read the marker as proof of data corruption | r3 | **phase 7/8** — caller/escalation guidance |
| N8 — `__all__` holds **19** names; the "20" in r2 prose double-counts `REDERIVE_SKIPPED` (code is right) | r2 | **coordinator** — prose-only correction (P-L) |
| N9 — the `CALCULATION_VERSION` constant's own docstring (plan task 6's named carrier) has no arbiter; two docstrings duplicate the lists | r2 | next touch of `calculator.py` |
| N10 — `calculate_variance_worker_minutes` double-wraps `localcontext()` | r2 | next touch |
| N11 — indentation artifact in `validate_currency_equality`'s comprehension | r2 | next touch |
| N12 — `term_row.name` is the one attribute read outside a `try` (unreachable for ORM rows) | r3 | next touch |
| N13 — dead branching: two `if`s guarding three identical returns | r3 | next touch |
| N1, N5, N6 — duplicate test, dead `required=False` parameter, collection-time C2 fixtures | r1 | next touch (declined as optional in r2, correctly) |

## Lessons

None new. L1–L8 from rounds 1–3 stand; L7 and L8 were both vindicated this round — L7's
implication-fixture rule produced the correction that closed S6, and L8's
"declaration must match the run" is exactly what the r3 handoff got wrong and what this
round's per-branch observed node ids got right.

## Mutation-probe declaration

All probing was done in a **disposable git worktree** at `71f137b`
(`git worktree add --detach`), never in the main tree.

- `app/beyo_manager/domain/item_economics/calculator.py` — 6 mutations applied and
  reverted (cascade-clause deletion; cascade-clause inversion; four `error`-key
  corruptions/drops). Final sha256
  `03389d0a2743ae7968a0e5aecc88cc5b2675bea6762c2b9bbec2d87662af8eb0` ✓
- `app/tests/unit/domain/item_economics/test_calculator.py` — **not modified** by any
  probe this round. Final sha256
  `6733181ed998b101ac2bcb0d95f4f5bfc3729f4d1a6ca8e40b619b8b705daa86` ✓
- `__pycache__` cleared between every probe so no run could read a stale module.
- One non-source file created inside the worktree only: `app/.env`, copied from the main
  tree because it is gitignored and `conftest.py` cannot import settings without it. It
  went away with the worktree.
- Worktree removed (`git worktree remove --force`); `git worktree list` shows only the
  main tree. Main tree verified clean, both hashes unchanged.
- **Database/state side effects: none.** Every probe ran the pure unit module and
  in-memory unsaved ORM instances; no migrations, no DDL, no writes. The configured
  development database was never written to and remains at head. **Architecture graph:
  read-only** (`archgraph_status` only); revision unchanged.

## Full write perimeter

- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md`
  — appended the reviewer r4 Review log entry, including the carry-forward dispositions
  table and the card-3 anchors (append-only; all earlier entries untouched).
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
  — phase-3 tracker row only: state `IMPLEMENTED` → **`APPROVED`**, actor extended to
  `…; reviewer r4 (Claude)`, verdict summary appended. All prior actor stamps and every
  other row preserved verbatim.
- This handoff file, deposited after the Review-log and tracker writes.
- **No production or test code was modified.** All probe edits were made in the
  disposable worktree and reverted there before it was removed.

## Next for the coordinator

Phase 3 is APPROVED — the closeout ritual is yours: approval-gate commit, archive the
phase-3 prompts and handoffs to `archive/plan_3/`, run the single held graph
adjudication for `domain-item-economics` with the anchors above, apply the N8 prose
correction, and author the phase-4 projection prompt carrying N7 and N15 forward.
