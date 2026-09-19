---
plan: (pre-plan, project-level — no master plan and no phase plans exist yet)
role: reviewer (mechanism-inventory gate — re-check after the round-7 fold)
round: inventory-recheck
date: 2026-09-19
skill: mechanism-inventory (`/Users/davidloorenz/agent-skills/mechanism-inventory.md`, via the pipeline charter)
---

# Mechanism-inventory re-check: `stock_report`

You are re-running the mechanism-inventory gate on a **narrow perimeter**. The full inventory ran
on 2026-09-18 and answered `OWNER_DECISIONS_PENDING`; the owner answered every card; the
intention-shaper folded the answers (round 7). Your job is to decide whether the folded contracts
are contract-grade, and to answer `PASS`, `OWNER_DECISIONS_PENDING` or `FAIL`.

## Gate check — stop and report if any line fails

1. `docs/architecture/under_construction/implementation/stock_report/planning/intention.md` has a
   header line beginning `status: RATIFIED` **written by the owner** for round 7 (the changelog
   §18 must carry a round-7 re-ratification entry). If the header still says
   `READY_FOR_RATIFICATION`, stop: the owner has not approved the fold; do not proceed and do not
   write the status yourself.
2. The intention is committed (`git status --porcelain` shows it clean).
3. The round-6 handoff exists:
   `handoffs/reviewer/2026-09-18_inventory_mechanism_inventory_handoff.md`.
4. No `master_plan.md` and no phase plans exist yet.

## Read, in this order

1. The pipeline charter and the mechanism-inventory skill.
2. The round-6 handoff — its "Final owner answers" table is the specification of the fold.
3. The intention: the top section, §14D (the owner's words), then **only** the contracts below,
   then §14C rows C10, C30, C37–C40, §16 P33–P36, §13 M1, §13A, §17, §18 round 7.

## Perimeter — re-check these, nothing else

| Contract | What the fold changed | What to verify |
|---|---|---|
| §5A MC-1 | card-9 branches replaced by self-heal: guarded UPDATE, inline repair, second trigger on row deletion | Is "0 rows = would go negative" sound under the lock order (row locked, exists, workspace predicate)? Is the write order (assignment state flushed **before** the absolute recomputation) stated for every caller incl. DELETE and creation? Can the recomputation itself be wrong under a concurrent writer of the same row (MC-11)? Is the repair-record rule (`stored + delta ≠ recomputed`) decidable per column? |
| §6A MC-5 | floor removed; self-heal of a negative goal total | Same questions for the goal record: which lock protects `R` when `R` is not the current record; is the credit memory cleared before the Σ; does the worked sequence still hold |
| §8B MC-9 | card 11 → A; new 5 s time limit (11a) | `SET LOCAL` inside `maybe_begin` on this codebase's async session/pool: does it hold for the whole request transaction, does it leak on pooled connections, what does asyncpg raise and which status does the router answer? Does the rule-10 instrument prove the **default** is applied? Does a timeout leave nothing written? Read Scanner's `DISPATCH_TIMEOUT_MS` again and confirm 8 s |
| §5B MC-14 | last row: `find_or_create_item` guarded (cards 10/10a → A) | Read `find_or_create_item.py` and `create_task.py`: is the raise inside the transaction so nothing persists; are there other callers of `find_or_create_item`, and is refusing right for each; lock order Items → Tasks respected |
| §9E MC-18 | 28 → 36 cells | The two new operations exist as endpoints in §12A; cell count is exact |
| §12A MC-20 repair | write mode, manual command, `stock_report_repair_records` | Per-kind repair table total? `priority_order_nullness` repair vs MC-7 invariants; lock order with the advisory lock first; events per MC-19; authorship per MC-17; "clean workspace = zero statements"; instrument (e) — tests must assert the repair table is **empty** so self-heal cannot mask an M1 defect; the reset phase order with the new table |
| §14D D6 | demand webhook set-based, fixed statement count | Consistent with MC-4 find-or-create under two concurrent first deliveries, MC-6 comparison-under-lock, and MC-9 zero-statement replay? |

## Method rules

- A contract is "contract-grade" when an implementer cannot satisfy its words with two different
  behaviours. Where it is not, **write the missing sentence into the intention as a lettered
  addition or in place inside round-7 text** (round-7 text is yours to tighten; rounds 0–6 text is
  not), and log it in §18.
- Every absence claim carries its search and scope (charter rule 15).
- Anything that changes product behaviour is an owner card in the charter's card format — never a
  unilateral edit. Settled and not to be reopened: every row of §14D, the 21 unilateral
  resolutions U1–U21 if the owner's re-ratification covered them, the published v1 Scanner
  handoff (never edited; a change ships as a v2 file).
- Never promote, reject or edit archgraph review items. Do not commit.

## Closing protocol

Write `handoffs/reviewer/2026-09-19_inventory_mechanism_inventory_recheck_handoff.md`: verdict,
the per-contract finding table, any cards, the write perimeter from `git status --porcelain`.
End with the owner-layer message (what I did → what I found → what happens next → what needs you).
On `PASS`, the next session is the implementation-planner; carry into its prompt the owner's
requirement D6 (set-based demand webhook with a statement-count criterion).
