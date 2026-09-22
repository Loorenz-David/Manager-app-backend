---
batch: D2
phases: [13A, 14]
role: projection
round: 0
state: PROMPT_READY
date: 2026-09-22
actor: orchestrator
model: Opus
authority: owner, 2026-09-22 — "apply after D1 approves, then continue with D2. you should complete all the remaning task by your self"
---

# Batch D2 projection — round 0. Mandatory and not waivable.

Read these by absolute path first and follow them as session doctrine:

- `/Users/davidloorenz/agent-skills/plan-projectionist.md`
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
Plans: `SR/plans/plan_13A.md` (37 rows / 7 criteria) and `SR/plans/plan_14.md` (5 rows / 2 criteria).
Intention: `SR/planning/intention.md` — **RATIFIED**, check its header, and it wins over any plan.
Master plan: `SR/master_plan.md` — §4 tracker, §6.5 signature ledger, §6.7 events, §9/§9A rules
and lessons.

**Batch D1 (phases 12 + 13) is APPROVED at `d800e73`.** 14 of 16 phases are VERIFIED. D2 is the
last implementation batch in the project. `SR/REMAINING_WORK.md` is the ordered list; this prompt
is its step 5.

## Why this projection is mandatory

Plan 13A carries the one criterion in the entire project that can observe a requirement phase 13
was sealed without: **C5(b)**. Phase 13's cascade must re-read a row's `priority_order` from the
database on every call, because the previous gap-close leaves a held ORM copy stale; no criterion
in phase 13 can see it, and phase 13's §4 perimeter forbade editing the cascade. That is why
batch D was split. **C5(b) is load-bearing for the split's whole rationale.**

## What D1 learned, and what it costs you if you ignore it

These five are not background reading. Each one changed an outcome in D1 and each applies
directly to what you are projecting.

**L-41 — an additive mutant is absorbed in this codebase.** Seven named mutants across D1 could
not fail, seven for seven, and the mechanism is now named: a spurious *write* is overwritten by
the mover's own later `UPDATE … RETURNING`, and a spurious *event* is dropped by
`coalesce_stock_report_events`. Only **subtractive** and **reordering** mutants bite. **Audit
every mutation cell in 13A and 14 for this shape and replace the additive ones.** 13A is a
multi-row cascade over exactly the idempotent, de-duplicating code where this bites hardest. This
is the single most valuable thing D1 learned.

**L-42 — fixture discrimination is per row, not per batch.** The same defect (an ordered
assertion whose fixture cannot distinguish the ordering terms) was fixed in plan 12 C4(b) and
found **untouched** in plan 13 C4(a) hours later, because the first fix was treated as covering
the class. **Audit every ordered assertion in 13A and 14 individually.** For each, state what the
fixture makes distinguishable and what it does not.

**L-40 — §9 rule 3 is too coarse as written, and C5(b) IS armable.** D1's tester found plan 13
C2(b)'s ORM-staleness tripwire inert and extrapolated that C5(b) would be inert for the same
reason. I measured instead of accepting it: the counter statement (PK equality + `RETURNING`)
leaves the ORM **synchronised** (7 vs 7), while `close_priority_gap`'s shift (range criteria)
leaves it **stale** (3 vs 2). **Do not let C5(b) be retired on the strength of C2(b)'s
inertness.** If you believe C5(b) cannot be armed, that is a stop-and-report, not a fold.

**L-43 — registering a signature emits a pin obligation in the same act.** §9 rule 18's first
violation since it was written happened in D1: `build_stock_report_item_deleted_event` was
registered in §6.5 and pinned by nothing, and a reviewer replaced its payload with junk while all
six delete tests passed. **Every signature 13A or 14 registers must have a row that pins it, named
in the same cell.**

**L-45 — a mutation against an already-red suite proves less.** Keep the suite green; if a
projection-time probe needs a red suite, say so.

## The six things to settle, each with evidence

### 1. Card D-3 — and do not pre-authorise the extraction

`SR/OWNER_CARDS_batch_D.md` card **D-3** asks whether plan 13A's scanner delete webhook needs the
per-field validators of APPROVED phase 7 **exposed** (extracted to a shared site) at all.

**Establish this by reading 13A's actual tasks and phase 7's actual code, not by reading the
plan's assertion that it needs them.** My earlier recommendation of "extract, behaviour-preserving"
was made **without** verifying the need, and I withdrew it. **If 13A does not need them, phase 7
is not touched at all** and the card closes as "no change". Touching an APPROVED file is a real
cost and needs a real reason.

### 2. Carried question D-13 (NEW, unruled) — the deleted event's `workspace_id` provenance

Intention line **1495** is ratified: *"`workspace_id` comes from the entity's row, never from
`ctx` (§2.5)"*, and master plan §6.7 restates it. But
`_delete_stock_report_item_cascade.py:203` builds `stock_report_item:deleted` with the
`workspace_id` **parameter**, which `delete_stock_report_item.py:126` fills from `ctx.workspace_id`.

**Today this is unobservable and harmless** — the delete refuses anything outside the caller's
workspace, so the two values are identical by construction, and D1's tester recorded plan 13
C3(b)'s named mutant (ii) as `EQUIVALENT` for exactly that reason: the "mutated" form is what
ships.

**13A is the batch that adds the second caller** — a webhook that deletes rows in a loop rather
than one per request. **Answer, with evidence:**

- Does 13A's second caller make the difference **observable at a public boundary** (the webhook),
  or does it too scope every row to one workspace so the values stay identical by construction?
- If observable: 13A's §4 perimeter should include the one-line provenance fix in the cascade's
  event build, and you should **propose cell text** for a row that observes it. **Propose; do not
  author.**
- If not observable: say so plainly and the card closes as "unobservable, not unnecessary" with
  your measurement recorded. **Do not manufacture a red.**

Either way, **do not edit production code** and do not edit a criteria table.

### 3. Plan 14 C1(b)'s guard must root correctly

Plan 14 **C1(b)** is a structural guard over the event registry. It must root in **master plan
§6.7 plus every `event_name=` site in `app/beyo_manager/`**, not in `_events.py` alone — otherwise
it cannot see `build_stock_report_item_deleted_event`, which now lives in
`_delete_stock_report_item_cascade.py`, nor `stock_report_item:created`, which
`apply_stock_demand.py` builds inline. **Check the cell's current wording and report whether it
has this defect.**

### 4. Plan 14 task 3 is re-verify, not author

Plan 14 task 3 was changed at D1 planning time from *author* to **re-verify**: read the published
`HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` against shipped code, flip each
**SPECIFIED** line to **VERIFIED**, and re-issue **only if something moved** — a new dated file
carrying a `supersedes:` key, the old one **moved** to `archived/`, **never edited in place**. An
in-place edit of a published handoff once cost the frontend team four days.
**`…match_preview_v2…` is not superseded and not archived** (owner card 7).

Confirm plan 14's text matches that, and report if it still says "author".

### 5. The six carried questions of intention §14E

The owner waived 13A's mechanism-inventory re-check on the condition that **the six carried
questions of §14E are checked at projection**. That condition is yours to discharge. §9 rule 17
also applies: Postgres lock re-evaluation and deadlock shapes. Plan 13A **C5(g)** (CF-2: sorted
`VALUES` / sorted `FOR UPDATE` do not deadlock) is **owed by this batch** — it was authored at the
2026-09-21 owner fold and its phase never ran.

### 6. The ordinary projection duties

Decision ledger; every path in both plans resolves; every citation quotes text that exists at the
line it names; **zero empty mutation cells** left in 13A or 14; criteria sized against §7; and the
sizing note in each plan's §7 matching its actual row and criterion count.

## Authority, and it is narrow

- **You author no criterion row, restate no criterion row, and edit no criteria table.** Outcomes
  and criterion rows are the owner's. **Mutation cells and fixture cells are the orchestrator's** —
  propose folds in your handoff with the exact replacement text and I apply them.
- **You change no production code and no test.**
- **Do not touch `master_plan.md` or `OWNER_CARDS_batch_D.md`** — I am editing both concurrently.
  Register-worthy findings go in your handoff and I apply them.
- **Do not commit.** Write your handoff and your plan-file edits and stop; I commit with explicit
  paths. This is a deliberate departure from the usual checkpoint norm because another session is
  working the same tree right now.
- Files you may write: `SR/plans/plan_13A.md`, `SR/plans/plan_14.md` (Review log and the cells I
  named as yours), and your handoff.

## Environment

**Slot `BEYO_TEST_SLOT=dpj` on every pytest command** (`pytest.ini` carries `-n 6 --dist loadfile`,
so even a single-file run claims six worker databases). Baseline is the checked-in 23-ID set at
`SR/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`; current L4 is **23 failed / 3742
passed / 1 skipped**. A projection should need **no L4 at all** — probe at hypothesis scope.

## Deliverable

`SR/handoffs/projectionist/2026-09-22_batch_D2_projection_1_handoff.md`: verdict
(`PROJECTED` / `BLOCKED`); the decision ledger; your answers to items 1–5 each with pasted
evidence; the L-41 additive-mutant audit as a table (cell → current mutant → absorbed? →
replacement text); the L-42 per-row fixture audit of every ordered assertion; the C5(b) armability
statement; proposed cell text for anything you want folded; owner questions under
`⚠ OWNER DECISIONS REQUIRED (n)`.

**Report what you could hide.** Every session in this batch has — a fabricated placeholder SHA, an
arithmetic error in one of my own prompts, a measurably false claim I folded into a plan cell, and
a test its own author found could not fail. That norm is the point and it is holding.

**Never push.**
