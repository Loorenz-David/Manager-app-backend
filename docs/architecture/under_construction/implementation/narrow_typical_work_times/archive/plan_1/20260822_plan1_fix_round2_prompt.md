---
plan: plan_1
role: implementer
round: 2 (fix cycle)
date: 2026-08-22
---

# Fix prompt — plan 1, round 2 (coordinator consumption findings)

Round 1 is sound: the engine's logic is correct at every site I checked, the snapshot
was captured honestly pre-refactor, and the L4 stamp matches the 21-ID baseline exactly.
This cycle closes **criteria-coverage gaps only** — rows the plan enumerates that the
test files do not contain. **No production logic is expected to change.** If any fix
below reddens a production behaviour, stop and report: that is a real defect, not a test
gap, and it changes this cycle's shape.

Read `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
`/Users/davidloorenz/agent-skills/implementation-executor.md` first. Repo:
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`, branch
`main`. **Never push.** Explicit paths only.

## Write perimeter — exactly two files, plus bookkeeping

- `app/tests/unit/domain/item_economics/test_typical_filters.py`
- `app/beyo_manager/domain/item_economics/typical_filters.py` — **only** if F5 proves a
  real defect (it should not).
- `plans/plan_1.md` (Review log) and this project's `master_plan.md` (tracker row 1).

Anything else is a finding. No new test file, no new module.

## F1 — C7 row (i) is missing: an entire production branch is untested

`plan_1.md` §6 C7 enumerates thirteen grid rows (a)–(m); `test_resolution_grid` carries
twelve. **Row (i) is absent**: non-narrowing spec, narrowed `(3, None)`, section
`(3, None)`, `BROADEN_TO_SECTION` → `insufficient_sample` / `None` / `3`.

This is not a bookkeeping miss — it is the **only** row that exercises
`typical_filters.py`'s non-narrowing insufficient branch (the `return` at the end of the
`if not spec.is_narrowing:` block). Every other non-narrowing row has
`section_sample_count = 61` and takes the `has_section` branch above it. Today that
branch has zero coverage: delete it and rewrite it as `raise`, and the suite stays green.

Add row (i). Then verify with a named mutation: in `resolve_section_typical`
(definition), make the non-narrowing insufficient branch return
`narrowed_sample_count` instead of `section_sample_count` — contract `3`, mutation `3`
(**inert on this fixture**), so instead use: make it return the section **seconds**
instead of `None` — contract `None`, mutation `None` (also inert, both are None).
**Therefore give row (i) a fixture whose two populations differ**: narrowed
`(3, 700)`, section `(4, 800)` → expected `insufficient_sample` / `None` / `4`. Now the
mutation "return `narrowed_sample_count`" flips `4` → `3`, and "return the section
seconds" flips `None` → `800`. Both sides differ; record both.

(That reasoning is the charter's rule-12 discipline applied to a row the plan wrote with
symmetric numbers — report it as a plan-wording correction you made, and amend C7 row
(i)'s numbers in `plan_1.md` §6 to the asymmetric fixture in the same edit.)

## F2 — C14 is missing three enumerated rows

`plan_1.md` §6 C14 enumerates rows (a)–(n).
`test_parser_handles_typed_params_absence_none_enums_and_client_errors` omits:

- **row (c)** — `{"width_cm_min": 60, "width_cm_max": 80}` → `(60, 80)`. Both-bounds is
  the ordinary case and is currently unasserted.
- **row (h), second half** — `{"can_have_upholstery": True}` → `True`. Only the `False`
  case is present.
- **row (m)** — `{"designers": ["dsg_a", "dsg_b"]}` → `frozenset({"dsg_a", "dsg_b"})`.
  The `designers` family has **no parser row at all**. This is the exact omission the
  projection raised (ledger L9) and the fold added as a row; it must not lapse twice.

Add all three.

## F3 — C10's field assertions are partial, and the gap is disclosure-shaped

`plan_1.md` §6 C10 requires the materialized ghost row to be asserted with
`narrowed_sample_count 0`, `section_sample_count 0`, **both seconds `None`**,
`typical_basis "insufficient_sample"`, `sample_count 0`. The tests assert only
`typical_basis`, `sample_count` and `participates`.

Nothing currently pins the **seconds**. Change `_zero_evidence` to return
`SectionTypicalEvidence(section_id, 0, 0, 0, 0)` and the suite stays green — yet that
mutant publishes `typical_worker_seconds: 0` beside `typical_basis:
"insufficient_sample"`, which is precisely the false-disclosure shape §3B B2 and §11A
T16b exist to forbid, and it would reach the wire in phase 4.

Extend the ghost assertions to the full field set, including
`selected["ghost"].typical_worker_seconds is None` and the four evidence fields. Named
mutation: `typical_filters._zero_evidence` (definition) returns
`SectionTypicalEvidence(section_id, 0, 0, 0, 0)` — contract: seconds `None`; mutation:
seconds `0` with the basis unchanged. Record both sides.

## F4 — two handoff claims are not what the tree measures

Correct these in your round-2 handoff; neither changes the code.

1. **The snapshot's last byte is `0x65` (`e`, the end of `working_sections.name`), not
   `0x6e`.** The substantive claim — no trailing newline — is TRUE and I verified it.
   Report measured values, not remembered ones.
2. **"Forbidden-token grep is empty on the clean domain perimeter" is false as stated.**
   Run from the repository root over
   `app/beyo_manager/domain/item_economics/`, the C4(c) term set returns one hit:
   `serializers.py:351` `"config_fingerprint"` — a **pre-existing price-scenario
   config fingerprint, unrelated to spec identity**, so §6.6's claim ("no *spec* hash,
   digest or fingerprint is introduced anywhere in this pipeline") still holds. State
   the hit and why it is out of scope, so the reviewer does not open a finding on it.

## F5 — one defensive check (expect: no change)

`reconcile_task_typicals` indexes `evidence[section_id]` for each id in
`participating_section_ids` (the quantifier). If a participating id were **not** in
`section_ids`, that raises `KeyError` — the same failure mode C10 exists to prevent, on
the other axis. Per §3.5, `participating ⊆ section_ids` holds by construction at every
call site, so this is structurally unreachable **today**.

Do not add a guard. Instead: confirm in one sentence in your handoff that the subset
relation is a stated contract, and note it as an assumption phases 4 and 5 inherit when
they wire real callers. If you find any path where it does not hold, that is a finding —
stop and report.

## Not in this cycle — recorded, do not act

The `_median = median` compatibility alias in `budget_division.py` stays. Your repair was
correct and correctly disclosed: the plan and the projection both missed that a private
name had a cross-module importer. Its removal belongs to **phase 5**, which owns
`get_task_price_scenario.py` and will point it at `typical_filters.median` directly. The
coordinator has recorded that; do not pre-empt it here.

## Evidence budget

- Every named mutation above runs at **L1 whole-file scope** on
  `test_typical_filters.py` — never `-k`.
- **One L4 stamp** closes this cycle
  (`PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`), taken on the tree you hand
  over, with the failing-ID delta against the 21-ID set in both directions. Round 1's
  stamp does not carry over — you are changing the tree.

## Closing protocol

Checkpoint commit (`CHECKPOINT (not approved): `, explicit paths, never squashed, never
pushed). Update `plans/plan_1.md` Review log and `master_plan.md` tracker row 1. Handoff
at `handoffs/implementer/20260822_plan1_fix_round2_handoff.md`, frontmatter `plan`,
`role`, `round: 2`, `date`, `actor`; body: owner-readable opening, the F1–F5 ledger with
both-sides mutation results, the L4 stamp, the full write perimeter from `git status`,
and the checkpoint SHA. Final chat message is the charter's owner layer.
