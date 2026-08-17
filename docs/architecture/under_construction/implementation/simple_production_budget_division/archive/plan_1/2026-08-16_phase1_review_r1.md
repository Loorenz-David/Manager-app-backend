---
plan: 1
role: reviewer
round: 1
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Review round 1 — plan 1 (LIGHT-SCOPED first review)

You are the reviewer (plan-reviewer doctrine,
`/Users/davidloorenz/agent-skills/pipeline-charter.md`). This first review is
deliberately **light-scoped** (coordinator decision, owner-ratified): projection
round 0 already did the deep semantic walk against real data, and the implement
rounds closed a complete named-mutation ledger. Your job is to VERIFY that record
and go deep only where the numbers are made — do not re-derive the whole phase.
Budget guidance: this should be a fraction of a full crawl, not 40 minutes of
re-walking settled ground. Anything you see wrong in passing, in or out of scope,
you report (that clause has caught real bugs).

## Read first

1. `plans/plan_1.md` — criteria C1–C21 AND the Review log (projection round 0,
   K1–K6, r1b consumption, r1c consumption + the two ADJUDICATED equivalence
   STOPs — the adjudications are decided; you check their reasoning, you do not
   re-open them without evidence they are wrong).
2. `planning/intention.md` — §3 (M1), §4 (M2) as amended round 5–6; §5 payloads;
   HC-1..5 + HC-1a (FOUR authorized v1 artifacts).
3. The three implementer handoffs (`handoffs/implementer/…r1…`, `…r1b…`,
   `…r1c…`) — the closed ledger and criterion→test map in r1c are your audit
   objects.
4. `master_plan.md` §4 (registry), §6 (rules in force), §7 (environment, baseline).

## Scope — exactly this

1. **Verified perimeter (charter re-review protocol).** `git diff` the span
   before `0b85701` → `fb48d13` (three checkpoints): confirm every touched file
   is either a registered new file (master plan §4) or one of the FOUR HC-1a
   artifacts, each modified by addition only. Anything else = automatic finding.
   Known out-of-scope tree dirt (NOT this phase's, do not review it): modified
   `.archgraph/architecture.yml` (r1 committed it carrying a pre-existing foreign
   graph delta — recorded K5), `bootstrap_app.py`, untracked bootstrap-seed files
   and `to_implement_the_accurate_costs_and_projections/`.
2. **Full adversarial depth on the TWO rule-6 mechanisms only:**
   - **M1 SQL** (`get_working_section_typical_times.py`): read the actual query
     against intention §3 as amended — grouping unit, contributing-step
     predicates, MAX(closed_at) group admission, percentile_cont on the double,
     rounding locus (no `::numeric` anywhere on that path), min-sample handling,
     left-join section enumeration, `working_section_ids` filter interaction with
     the grouped subquery, workspace scoping.
   - **M2 function** (`budget_division.py`): read against §4 — B_seconds
     half-even quantization pre-C, partition, charged C, clamp, weight ladder
     (`t_i > 0`, fallback median incl. even-count interpolated mean, equal
     split), Fraction-exactness (no float on the path), largest-remainder with
     the NULL-safe tie key, share_state mapping, empty-set path.
3. **Ledger audit by sampling:** pick FIVE ledger rows minimum — at least two M1
   SQL mutations (C9c and C9d-rounding recommended) and two M2 mutations (C5b
   and C19 recommended) plus one of your choice — re-apply each mutation
   yourself, observe the red, revert. You are verifying the ledger's honesty,
   not re-running all of it.
4. **Two-doors + budget-status agreement spot-check:** run the C13 test file;
   read its fixture; confirm E2's `actual_worker_seconds` agreement with
   `get_task_budget_status` semantics (same filter, same column).
5. **Hand-checks with no automated guard:** README rows for E1 (P11 — Quick
   Index + detail section present and accurate: route, roles, params, payload
   keys); E1 declaration position above `working_sections.py`'s param route;
   tab-indentation consistency (N12); serializer payloads vs intention §5
   (key names, `string | null` snapshot, decimal-string minutes, no monetary
   key anywhere — the C17 test asserts it, but read the serializer once).
6. **Suite (P-L):** re-run `PYTHONPATH=. pytest -q -m 'not e2e'` from
   `backend/app/` yourself. Expected: 26 failures = the 23 v1 baseline IDs
   (enumerate-diff against
   `item_cost_calculation/plans/phase_1_worker_money_redaction.md:198-220`) + 3
   `test_seed_item_economics_configuration.py` (foreign, out of scope). Record
   your own totals.

## Explicitly OUT of scope

Re-deriving projection round 0's walks; re-running the full mutation ledger;
re-opening the adjudicated C13b-door2/C20 equivalences absent contrary evidence;
the foreign bootstrap work; frontend handoff documents (coordinator closeout).

## Verdict + handoff

Handoff:
`handoffs/reviewer/2026-08-16_phase1_review_r1_handoff.md` — frontmatter
(`plan: 1, role: reviewer, round: 1, state: REVIEWED, verdict:
APPROVED | CHANGES_REQUESTED, actor: <model>`), your full write perimeter (that
one file), findings ranked (blocking / should-fix / notes) each with evidence
`path:line`, your ledger-sample results (five rows: mutation, observed red,
reverted), your suite totals + failure-list diff result, and the owner-cards
section `⚠ OWNER DECISIONS REQUIRED (n)` right after the summary (`(0)` with one
line if none). Cards story-shaped per charter; everything else technical.
