---
plan: phase 3 (canonical calculator)
role: reviewer
round: 0 (plan-projection)
date: 2026-08-12
---

# Session prompt — plan projection (round 0), phase 3: canonical calculator

You are the **plan-projection agent** for phase 3 of the item-cost-calculation
pipeline. You implement nothing: you do the implementer's first hour **on paper**,
from the artifacts alone, and record every decision the plan fails to determine.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path, in this order)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` — shared charter.
2. `/Users/davidloorenz/agent-skills/plan-projection.md` — your session doctrine.

The plan file and its cited authorities are what you project; where this prompt
differs from them, they win.

## Gate check (verify before working; on any failure, stop and report)

- `master_plan.md` §4 tracker shows phase 2 **APPROVED** and phase 3 `NOT_STARTED`
  with a ⚑ projection gate.
- `plans/phase_3_canonical_calculator.md` exists and its Review log is empty.
- No phase-3 implementer handoff exists (you are round 0).

## Read order (after doctrine)

1. `master_plan.md` — §§5, 6.3–6.5 (enum registry as amended: four currency columns
   / three PG types; error-identity carrier §6.4; file layout §6.5), 9 (P-B, P-F,
   and the criteria-discipline rules P-G through P-M — apply them when judging the
   plan's rows), 10.
2. `plans/phase_3_canonical_calculator.md` — the plan you are projecting.
3. Intention **§6A entire** (the governing contract) + §6.1–6.6, §4A (A1–A3, A8),
   §6A.11's closed field set, R4-2 (gross-base planning-allocation semantics).
4. In-tree, as shipped by phase 2: `app/beyo_manager/domain/item_economics/enums.py`
   (what the calculator imports), `models/tables/item_economics/` (the ORM classes
   C7's rederive rows must instantiate unsaved), `app/beyo_manager/errors/`
   (ValidationError shape — no `code` field; identity = leading message token).

Line numbers date to 2026-08-11/12 — verify by symbol name.

## Depth targets (the phase's silent-failure mechanisms — inventory rows 1–14)

1. **Quantization-site totality (§6A.3 vs plan C2):** are Q1–Q5's inputs, scales and
   rounding pinned so two implementers write the same function signatures? For each
   tie row C2 requires, verify a fixture with an exact `.5` residue **and an even
   floor at the target scale** is actually constructible from valid domain inputs
   (integer minor units × percent at Q1; the Q2 rate expression; 2-dp minutes at
   Q4) — a tie row that cannot be constructed is an undecidable criterion.
2. **Boundary-guard table totality (§6A.1):** every input class × arriving type
   (int, Decimal, str from the request layer, float, None, enum member vs value) —
   decidable outcome per cell? Where does the guard sit (per-function or shared)?
3. **Error identities:** every named error the plan cites exists in master plan
   §6.4's identity list; the raise pattern (ValidationError, leading token) is
   implementable against the real error classes.
4. **`rederive` mechanics (C7):** can unsaved ORM instances actually be built
   without FK values (nullable at the Python layer before flush?); does "never
   dereferences an FK" have a decidable test form; is the §6A.11 closed set
   consistent with the shipped phase-2 columns (incl. `percent_value`/
   `fixed_amount_minor` — never `value`)?
5. **§6A.8 percent-consumed semantics:** `None` iff `allowed ≤ 0` — total over the
   sign of `allowed` and of `actual`; C5's variance-independence row constructible?
6. **Criteria decidability & first-hour reality:** file layout vs §6.5; the enums
   module's actual members (phase 2 shipped `EconomicsStatusEnum` in declaration
   order ≠ §11A.4 evaluation order — a phase-4 hazard, but confirm nothing in THIS
   phase iterates the enum); P-G(b) test naming; P-K shared-fixture audit
   obligations; every C-row's expected value exact and computable by hand.

## Constraints

- **No implementation, no code edits.** Read-only; write nothing outside your
  handoff. Plan defects are ledger entries for the coordinator — never fixed in
  place.
- Archgraph: read-only orientation (`domain-work-analytics` and the nine new
  `table-*` nodes are now `human_confirmed`); no delta.

## Closing protocol

1. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase3_projection_r0_handoff.md`
   (full path — do not resolve relative to the repo root) with frontmatter
   `plan: phase 3`, `role: reviewer`, `round: 0`, `date`, `state`, `verdict`,
   `actor`.
2. Body: opening summary; **`⚠ OWNER DECISIONS REQUIRED (n)`** (charter card
   format; one line if zero); the **decision ledger** (severity + routing per row);
   citation/decidability verification; the **explicit delegation list**; full write
   perimeter (expected: this handoff only). **Deposit before ending the session.**
3. Verdict per your doctrine; the implementer prompt compiles only after the
   coordinator routes your ledger.
