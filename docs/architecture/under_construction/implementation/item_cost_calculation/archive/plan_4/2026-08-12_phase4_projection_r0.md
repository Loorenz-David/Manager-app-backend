---
plan: phase 4 (configuration services)
role: reviewer
round: 0 (plan-projection)
date: 2026-08-12
---

# Session prompt — plan projection (round 0), phase 4: configuration services

You are the **plan-projection agent** for phase 4 of the item-cost-calculation
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

- `master_plan.md` §4 tracker: phases 1–3 **APPROVED**, phase 4 `NOT_STARTED`
  with a ⚑ projection gate.
- `plans/phase_4_configuration_services.md` exists; Review log empty (the
  "Forward items routed here" block above it is coordinator routing, not a log
  entry).
- No phase-4 implementer handoff exists (round 0).

## Read order (after doctrine)

1. `master_plan.md` — §§5 (contract resolution incl. `32_concurrency`,
   `06_commands` + local), 6 entire (registry: routes, error identities incl.
   the version-admission and guarded-delete families, the phase-3 public API in
   §6.5 — this phase's rate derivation CALLS `calculate_cost_per_worker_minute`),
   9 (P-B…P-Q — the criteria-discipline rules bind your judgment of the plan's
   rows), 10.
2. `plans/phase_4_configuration_services.md` — the plan you are projecting,
   including its three forward items (N3 enum order, S4 request parse, N7
   persisted-rate arbiter).
3. Intention: **§7A entire** (chain construction order §7A.1, race arbitration
   §7A.2, resolution predicate §7A.3, version admission §7A.4, selection
   classifier §7A.5, deletion guards §7A.6), §4.1–§4.4 + §4A (the config tables),
   §7.1/§7.4/§7.5, §11A.4 (the ordered status vocabulary the classifier feeds),
   §6A.4's R4-2 presentation rule (this phase ships the term-creation API field
   docs — the binding "planning allocation, never statutory tax" wording), §14
   tests 8/10.
4. In-tree, as shipped: `domain/item_economics/` (enums — note
   `EconomicsStatusEnum` declaration order ≠ §11A.4 evaluation order, the N3
   hazard; calculator public API), `models/tables/item_economics/` (the chains'
   partial uniques the commands race against), and the repo command idiom
   (`services/commands/<domain>/requests/__init__.py`, `maybe_begin`,
   `run_service`) per §2.5.

Line numbers date to 2026-08-11/12 — verify by symbol name.

## Depth targets (inventory rows 15–20 + the forwards)

1. **Chain construction order (§7A.1)** — the close→insert→back-link order for
   both config chains: is it decidable per command, and does a criterion exist on
   the exact DB conflict path (not just the pre-check) per §7A.2 and charter
   rule 2's error-contract clause?
2. **Race arbitration (§7A.2)** — the `ConflictError` identities
   (`ITEM_COST_CONCURRENT_BASIS_VERSION`/`_MODEL_VERSION`) on the partial-unique
   conflict; `32_concurrency` row-locking (`FOR UPDATE`) at the seams the
   intention names; are the mutation sites named per P-G(a) (DDL vs command
   code)?
3. **Version admission (§7A.4)** — total over the open row's state; the six
   registry identities (`…_EFFECTIVE_FROM_FUTURE`/`_REQUIRED`/`_NOT_AFTER_OPEN`
   × two chains); one row per adjacent boundary pair (charter rule 2).
4. **§7A.5 classifier + N3** — the ordered selection/status classifier: verify
   the plan pins that precedence comes from §11A.4's evaluation order, NEVER from
   iterating `EconomicsStatusEnum` (its declaration order is wrong — shipped
   phase-2 fact); does a named mutation guard that?
5. **Rate derivation wiring + N7** — basis-version creation calls the phase-3
   calculator and persists the QUANTIZED rate; N7's arbiter belongs here: a
   criterion must prove later reads receive the persisted rate, not a raw
   re-division. Also §6A.6: the underflow identity at creation.
6. **Deletion guards (§7A.6)** — the three `…_IN_USE` identities on the exact
   referenced-row path, with the race closed (`FOR SHARE`/lock per intention).
7. **S4 request parse** — `Decimal(str(v))` on request-borne numerics, proven on
   a value with more decimals than target scale; never `Decimal(v)` on a float.
8. **R4-2 presentation rule** — the term-creation API field docs task exists with
   a decidable criterion (P-D).
9. **Criteria decidability & first-hour reality** — file paths, router
   registration, request-schema idiom, harness choice (phase-1's lesson: pinned
   query/command-level vs router idiom), P-K/P-M/P-Q discipline on shared
   fixtures and implication pins.

## Constraints

- **No implementation, no code edits.** Read-only; write nothing outside your
  handoff. Plan defects are ledger entries — never fixed in place.
- Archgraph: read-only orientation; all item-economics nodes are now
  `human_confirmed` (0 pending); no delta.

## Closing protocol

1. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase4_projection_r0_handoff.md`
   (full path — never resolve relative to the repo root) with frontmatter
   `plan: phase 4`, `role: reviewer`, `round: 0`, `date`, `state`, `verdict`,
   `actor`.
2. Body: opening summary; **`⚠ OWNER DECISIONS REQUIRED (n)`** (charter card
   format; one line if zero); the **decision ledger** (severity + routing per
   row); citation/decidability verification; the **explicit delegation list**;
   full write perimeter (expected: this handoff only). **Deposit before ending
   the session.**
3. Verdict per your doctrine; the implementer prompt compiles only after the
   coordinator routes your ledger.
