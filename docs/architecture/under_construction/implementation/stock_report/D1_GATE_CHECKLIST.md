---
subject: stock_report — orchestrator worklist for the D1 gate
date: 2026-09-21
actor: orchestrator
status: OPEN
---

# D1 gate checklist — the orchestrator's own worklist

Not the owner's list (`OWNER_CARDS_batch_D.md`) and not the plan (`FINALIZATION_STEPS.md`). This
is what I must not forget between rounds, written down because this session may be compacted.

## Apply after the implementer checkpoints, BEFORE the tester prompt is written

Both are corrections to counts, applied under L-33 (restate a measurement, never a paraphrase).
Neither adds or strengthens an assertion, so neither is an owner card — but both must land before
the tester derives its `declared` set, or the count it gates on is wrong.

1. **Plan 12 C4(e) says "two mutants … both runs recorded" and then lists three.** My own defect,
   introduced when I added the `image_url` mutant `(iii)` to the cell and left the preamble words
   untouched. The substance is right — `(i)` extra key, `(ii)` missing key, `(iii)` drop
   `image_url` — only the count words are stale. Fix to "**three mutants … all three runs
   recorded**". **This is the owner's own row**; under-counting it is exactly how the key would
   ship unarmed, which is the failure this amendment existed to prevent.

2. **Plan 13 §7 says "18 criterion rows in 5 criteria"; the committed script says 19 in 6.** Stale
   since owner card 2 moved **C6(a)** in from plan 8 — that added a sixth criterion and a
   nineteenth row, and the sizing note was never re-derived. Verify with
   `python3 SR/count_criteria.py` (never type a total) and correct §7. Plan 12's "45 rows in 7
   criteria" is **correct** as written.

## Independent counts I already derived, for the tester prompt

- Rows: **plan 12 = 45 in 7 criteria; plan 13 = 19 in 6** (`count_criteria.py`, 36 + 13 table
  lines plus 15 shorthand expansion). Project total **652 rows in 107 criteria across 16 plans**.
- **Zero empty mutation cells** in either plan — the batch D fold closed all of them. So every
  cell in scope is *binding and the set is closed*; there are no class-2 blanks for the tester to
  site, which is different from batch C2 and worth saying in the prompt.
- Declared mutation **runs**: my upper bound is **91** (plan 12 = 60 after C4(e)'s correction to
  three, plan 13 = 31). It is an upper bound, not the answer — the tester derives its own and
  wins.

## Verify at the gate, by my own hand — never consumed from a stamp

1. **C4(e)'s `image_url` is genuinely armed.** Drop the key from the `item_category` block and
   confirm **both** rows go red — the populated one *and* the NULL-category-image one. A key that
   is emitted but asserted by nobody is the exact defect this row was amended to prevent, and the
   owner asked for this one personally.
2. **The `_row_values` consolidation was inert.** The three donor modules' own test files must be
   green **with no edits to them**. If the implementer touched those test files, the inertness
   proof is gone and the consolidation needs re-proving another way.
3. **The cascade's two fresh `SELECT`s exist** — counter `stored_before` and gap-close
   `removed_order`. C2(b) arms the first. **Nothing in phase 13 arms the second**; its only
   evidence anywhere is 13A C5(b), which cannot be written until D2. So at this gate I read the
   code for it directly. This is the single requirement most likely to pass D1 and fail D2.
4. **The cascade reaches for no `ctx`.** `grep` the module. Its second caller passes
   `actor_user_id=None`, and no criterion in phase 13 exercises that path.
5. **`priority_order` is `StrictInt`** in the request model, or C1(n) is inert.
6. **One uncontaminated L4**, mine, on a clean tree, diffed both ways against
   `handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`, with the pass arithmetic
   reconciled from **3679**.

## Then

Register `stock_report_item:deleted`'s build site in §6.5 (card D-2), settle plan 13A's validator
extraction in the D2 prompt (card D-3), and carry the priority-order tenancy proposal (card D-1)
to the owner unapplied.
