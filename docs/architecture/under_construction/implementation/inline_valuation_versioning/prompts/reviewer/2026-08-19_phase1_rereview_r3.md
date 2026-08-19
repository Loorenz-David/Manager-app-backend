---
plan: 1
role: reviewer
round: 3 (re-review)
date: 2026-08-19
pipeline: inline_valuation_versioning
---

# Re-review round 3 — plan 1 (fix r2 verification)

You are the reviewer. You fix nothing. This is a **narrow round**: confirm S1 is closed,
that nothing was loosened to close it, and adjudicate one coordinator-found item. Write
perimeter: exactly one handoff file:

`…/inline_valuation_versioning/handoffs/reviewer/2026-08-19_phase1_rereview_r3_handoff.md`

Your r1 "settled ground" section stands — do not re-derive it.

## Already verified by the coordinator — do NOT redo

- **S1 closed, probed independently on the final tree.** Both plants were re-applied
  **separately**, which is stronger than r1's combined plant because it proves each root on
  its own: `app/scripts/_coord_probe.py` → red; `docs/handoff/from_frontend/_coord_probe.md`
  → red. Both removed, tree verified clean.
- **Suite re-run: 2320 passed / 26 failed / 1 deselected**, failure IDs byte-identical.
  Test count unchanged, as expected for a widened glob.
- **Perimeter exact.** Checkpoint `e9531dc` = two files (the test, and `plans/plan_1.md`).
  No production file, no graph state, no tracker.
- **The graph is done and is not yours.** Card 1 was answered and applied:
  `command-task-create`'s anchor widened 72-580 → **72-594**, the span verified by AST.
  Graph at revision `50b39402…`, 0 diagnostics. Do not re-flag it.

## What to adjudicate

1. **F1 — the extension narrowing (coordinator-found).** The guard filters to `*.py` and
   `*.md`; C9 names the trees `app/` and `docs/handoff/` with no extension qualifier.
   Probed: `app/_coord_probe.yml` carrying the literal leaves the guard **green**.

   This is S1's shape one layer out. The coordinator's reading is **note, not should-fix**:
   the filter is pre-existing module behaviour, the realistic carriers of a Python error
   constant are covered, and widening to every file type would sweep lockfiles and
   binaries. Acting on your own r1 rule — *"if any root is deliberately left out, say so in
   the criterion, not silently in the test"* — **C9 has been restated** to name the
   extension filter and the `app/.venv/` exclusion explicitly.

   **Rule on it.** Is stating the narrowing in the criterion sufficient, or does C9's
   durability demand the guard actually cover non-`.py`/`.md` files? You wrote the rule; you
   are better placed than the coordinator to say whether this satisfies it. If you disagree
   with note-level, say so plainly — a should-fix here is two more lines.

2. **The `app/.venv/` exclusion.** The implementer excluded it and declared it. Confirm it
   is the *only* exclusion, that no live source root was narrowed by it, and that it cannot
   be used to hide a real occurrence.

3. **Nothing loosened.** `git diff 6f82579 e9531dc` is the whole evidence base — ten lines.
   Confirm the widening did not weaken any other assertion in that module, and that the
   two named handoffs still resolve through `_HANDOFFS`' new `to_frontend/` child.

4. **The three DECISIONS the implementer declared.** Rule on each — particularly (3), where
   `ruff format --check` reports the module would be reformatted and they deliberately did
   **not** apply it, reverting an exploratory format. Was leaving it unformatted right?

5. **N1's mapping is recorded** in plan_1's Review log (`C1-row-* → C7-row-*`). Confirm it
   is accurate and that the two archived phase-8b citations are now followable.

## Environment

`PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`. Start point **2320 / 26 / 1**.
**A single run is not evidence** — this suite has been observed at 25, 26 and 27 on
unchanged code. If your count disagrees, repeat and diff the **ID set**.

## Output

Verdict `APPROVED` or `CHANGES_REQUIRED`, then a numbered ledger with file:line and, for
each finding, the mutation demonstrating it. Include the closure line for S1 and your
ruling on F1.

If everything closes, say so plainly and do not manufacture findings — this phase has had
one should-fix and it is fixed. A clean re-review is the expected outcome. Finish with the
tracker line for the coordinator to fold.
