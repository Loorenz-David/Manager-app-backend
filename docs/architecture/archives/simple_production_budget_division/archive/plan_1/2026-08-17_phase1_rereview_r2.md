---
plan: 1
role: reviewer
round: 2 (delta-scoped re-review after fix r2)
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Re-review round 2 — plan 1 (delta-scoped)

Charter re-review protocol: verified perimeter, full adversarial depth on the
changed seam only, settled areas not re-verified — but anything you see wrong in
passing, you report. Round 1's "Verified correct" section is settled ground; your
own round-1 findings S1–S5 and notes N-a–N-g are the checklist this round closes.

## Read first

1. Your round-1 handoff (`handoffs/reviewer/2026-08-16_phase1_review_r1_handoff.md`)
   — your findings are the acceptance list.
2. The fix handoff (`handoffs/implementer/2026-08-17_phase1_fix_r2_handoff.md`) —
   F1–F6 outcomes, five-probe delta ledger, lettered map.
3. `master_plan.md` §4 (the registered `typical_times_statement`) and §6 (the five
   rules earned from your round-1 lessons — check the fixes satisfy them).
4. `planning/intention.md` §5/§6 as amended round 7 (your N-h, folded).

## Scope

1. **Verified perimeter:** `git diff fb48d13 7f09637` — every changed file must be
   in the fix handoff's declared fix-owned list; anything else is an automatic
   finding. (Known foreign tree dirt unchanged: `.archgraph/architecture.yml`,
   bootstrap files, `to_implement_the_accurate_costs_and_projections/`.)
2. **Full adversarial depth on the ONE production seam — the S1 refactor:**
   - `typical_times_statement(...)` in `get_working_section_typical_times.py`:
     confirm the extraction preserved M1 exactly (grouping, four predicates,
     group-level window admission, percentile_cont, rounding locus, min-sample) —
     the round-1 verified SQL is your reference; diff mentally, not from scratch.
   - E2's `_load_typicals` now calling it: confirm E2-specific concerns (its
     filter, ordering, result shaping) live OUTSIDE the shared builder, and that
     no per-call-site drift remains possible (one-copy rule, master plan §6).
3. **Your five findings, closed?** For each S1–S5: read the new/changed test,
   judge whether it guards what your finding named (rationale-site rule — S2's
   fixture must actually run `resolve_economics_selection`; S4 must assert
   service identity, not status). Re-apply AT LEAST THREE of the five delta-probe
   mutations yourself (S1's `return {}`, S2's rationale-site query, and S3's
   `consumed_cost_minor` recommended), observe red, revert.
4. **Notes closed?** N-a: README detail sections now carry Request Body/Responses
   in house format and the E2 section sits in path order (hand-check). N-b
   comment accurate. N-c/N-f/N-g applied. N-d/N-e assertions present.
5. **Suite (P-L):** re-run `PYTHONPATH=. pytest -q -m 'not e2e'`; expect 26
   failures = the 23 baseline IDs byte-identical + the 3 foreign bootstrap IDs.
6. **Lettered map:** spot-check two lettered rows (e.g. C15b E1 identity, C17c
   step key set) against the actual test bodies.

## Out of scope

Re-deriving M1/M2 semantics (settled round 1); the full mutation ledger (r1c +
your round-1 sample stand); the foreign bootstrap work; frontend handoffs.

## Verdict + handoff

`handoffs/reviewer/2026-08-17_phase1_rereview_r2_handoff.md` — frontmatter
(`plan: 1, role: reviewer, round: 2, state: REVIEWED, verdict:
APPROVED | CHANGES_REQUESTED, actor: <model>`), write perimeter (that one file),
per-finding closure table (S1–S5, N-a–N-g: closed / not closed with evidence),
your probe results (≥3 rows), suite totals + diff result, owner-cards section
(`⚠ OWNER DECISIONS REQUIRED (0)` expected). If everything closes and nothing new
surfaces, say APPROVED plainly — the approval gate ritual is the coordinator's.
