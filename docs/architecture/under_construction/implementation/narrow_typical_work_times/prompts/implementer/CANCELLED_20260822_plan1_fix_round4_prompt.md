---
plan: plan_1
role: implementer
round: 4 (fix cycle — micro)
date: 2026-08-22
---

# ⛔ CANCELLED — not dispatched. Superseded by a plan-4 carry-forward.

**Cancelled by the coordinator, 2026-08-22, on the owner's challenge to the round count.**
The two escapes below are real and measured, but they are escapes in a *guard against a
hypothetical future import*, in a package that is flat today, and closing them does not
change any behaviour a user or a downstream consumer can observe. Spending a whole
implement-and-stamp cycle on three lines of test code is the diminishing-returns end of
this phase.

**Disposition:** carried to `plans/plan_5.md`'s sibling — specifically **plan 4**, which
already edits this package (the reviewer nominated it as the guard's natural home in its
carry-forward section). `plans/plan_1.md` C4(c) has been amended to state what phase 1
actually delivers, so the phase is not approved against a criterion it does not meet.

Kept as a record because the measurements below are the evidence plan 4 inherits — do not
re-measure them.

---

# Fix prompt — plan 1, round 4 (one file, two escapes in the purity guard)

Round 3 closed all seven findings; I verified each at source and every one holds. The
production diff is `_optional_values` alone, the reconciliation tuples now pin what the
review's mutants moved, and both of your purity probes bite.

**One thing did not survive my consumption pass.** The guard added in F6 — the test that
exists *because* a session grep could not fail — has two escapes of its own, and I
measured both on the round-3 tree. Neither is hypothetical:

| # | I did this | Guard said |
|---|---|---|
| H1 | appended a **second, differently-shaped** use of `config_fingerprint` to `serializers.py`: `def _leak(scenario): return scenario["config_fingerprint"]` | **2 passed** |
| H2 | created `domain/item_economics/sub/leak.py` containing `import hashlib` | **2 passed** |

Both were reverted; the tree is clean.

**Why each escapes.** H1: the pin asserts the *exact* line
`'"config_fingerprint": scenario["config_fingerprint"]'` appears once, then strips **every**
occurrence of the bare token `config_fingerprint` from the source before scanning — so any
additional use in any other shape is erased before the assertion sees it. H2:
`PACKAGE_ROOT.glob("*.py")` is **non-recursive**. The package is flat today (10 modules,
measured), so nothing is missed now — but this guard's entire purpose is to still be
guarding when phases 4 and 5 touch the package.

`plans/plan_1.md` C4(c) already states the requirement H1 violates: *"pin the exception by
name so that removing it does not silently widen the claim, and so that a second
fingerprint anywhere in the package reddens."* It does not.

## The fix

`app/tests/unit/domain/item_economics/test_domain_purity.py` only.

1. **Walk recursively** — `rglob("*.py")` instead of `glob("*.py")`, so a future
   subpackage cannot escape either guard (both share `_domain_modules()`).
2. **Make the exception surgical.** Strip only the *pinned occurrence*, not every
   occurrence of the token — e.g. remove the one pinned line and then scan what remains,
   so a second use in any shape reddens. Keep the `count(...) == 1` pin: it is what stops
   the exception from being silently deleted or widened.

Nothing else changes. This is a test-only cycle; if any production file needs to move,
stop and report.

## Named mutations (both must bite)

Run at **L1 whole-file scope** on `test_domain_purity.py`, reverting between probes:

- **M1 (H1):** append `def _leak(scenario): return scenario["config_fingerprint"]` to
  `app/beyo_manager/domain/item_economics/serializers.py`.
  Contract: **reddens**. Before this fix: 2 passed.
- **M2 (H2):** create `app/beyo_manager/domain/item_economics/sub/leak.py` containing
  `import hashlib`. Contract: **reddens**. Before this fix: 2 passed.
  Delete the directory afterwards — `git status --porcelain` must be clean of it.
- **M3 (regression, keep the round-3 probes honest):** `import hashlib` in
  `typical_filters.py` still reddens, and
  `from beyo_manager.models.tables.items.item import Item` still reddens.

Record both sides for each.

## Recorded — no action, for your handoff only

`_optional_categories` still has no explicit `str` guard. It is **not** a contract
violation: `{"major_categories": "wood"}` iterates to `'w','o','o','d'`, fails the enum
conversion, and raises `ValidationError` — the outcome intention §3C requires. Only the
*message* is misleading ("contains an unknown value" for a caller who passed a valid
category as a scalar). Note it in your handoff as a recorded nit so the re-reviewer does
not open it as a finding; do not change it in this cycle.

## Evidence budget

- M1–M3 at L1 whole-file scope, never `-k`.
- **One L4 stamp** on the tree you hand over (`PYTHONPATH=. pytest -m 'not e2e'` from
  `backend/app/`), Redis checked first, failing-ID delta against the 21-ID comparator in
  both directions. Round 3's stamp does not carry over — you are changing the tree.
  Round 3's count was 2617 passed / 21 failed / 2638 collected; state yours.

## Closing protocol

Checkpoint commit (`CHECKPOINT (not approved): `, explicit paths, never squashed, never
pushed). Update `plans/plan_1.md` Review log and `master_plan.md` tracker row 1. Handoff
at `handoffs/implementer/20260822_plan1_fix_round4_handoff.md` (frontmatter `plan`,
`role`, `round: 4`, `date`, `actor`): owner-readable opening, the M1–M3 ledger with both
sides, the L4 stamp, the full write perimeter from `git status`, the checkpoint SHA, and
the recorded nit above. Final chat message is the charter's owner layer.
