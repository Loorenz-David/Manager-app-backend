---
plan: phase 7 (evaluations — commit/supersede, projections, auto-commit)
role: reviewer (re-review)
round: 2
date: 2026-08-14
---

# Session prompt — re-review phase 7, round 2 (after fix r1)

You are the **re-reviewing agent** for phase 7. Round 1 found 3 blocking / 5
should-fix / 8 notes; the fix cycle's production diff is deliberately tiny
(the B1 kind gate + two dead-code deletions + a docstring + whitespace) and
the bulk is the adoption of YOUR round-1 probe suite as the phase's real
rows. Verify every r1 finding closed by re-running the arbiter that was
green (or absent) in r1 and red (or present) now.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- r1 handoff: `handoffs/reviewer/2026-08-14_phase7_review_r1_handoff.md`
  (your findings). Fix handoff:
  `handoffs/implementer/2026-08-14_phase7_fix_r1_handoff.md`.
- Plan: `plans/phase_7_evaluations.md` — base + **A1–A5** + the **fix-r1
  block F1–F9, GOVERNING**. Master plan §6.4/§6.5 (incl. the
  `no_primary_item` literal) and §9 incl. the six rules r1 earned (P-T 3rd,
  P-Q 4th, P-R 2nd ext, P-AB, deferral rule, P-L 2nd ext).
- Checkpoint **`bb233db`** (10 files; the handoff deposit is untracked/after).
- Coordinator consumption (verified, do not re-litigate): all FIVE final
  hashes match the working tree (4 declared production files + the router's
  unchanged baseline `87fcb318…`); `git diff bb233db..HEAD -- app/` empty;
  perimeter = declared exactly, with ONE delegation outside the fix fence,
  declared and accepted: the F4 translation row extended
  `tests/unit/services/commands/item_economics/test_item_economics_requests.py`
  (+1 line) instead of a new file. The F1 gate, F7 branch deletion, and N1
  validator deletion verified present by inspection.

## Environment facts

- Alembic head `be9dfe42a035` (no migration); declared suite **2076 / 23 / 1**
  (r1 measured 2037/23/1 → +39); declared focused: phase-7 surface 82,
  committing concurrency subset 5 (run twice), phase-5 surface 55 (54 + the
  new translation row). Graph declared unchanged: 166/239, 52 pending, rev
  `0a71061…`, zero delta.

## Probes (minimum — the ledger is yours)

- **R2-P1 — B1 closed:** re-run your r1 B1 scenario (scratch projection,
  override 2000 vs valuation 1000) against the shipped tree — the valuation
  must be untouched, exactly one valuation row. Re-run the F1 mutation
  (declared mutant `cea28666…9f24`): removing the kind gate must redden
  exactly C5 row 7. Verify the P-AB effect enumeration in the helper's
  docstring matches the code (chain-close scope, `committed_at`, mirror,
  history, audit, event — anything the docstring omits or invents is a
  finding).
- **R2-P2 — B2 closed (adoption fidelity):** diff the adopted
  `test_phase7_criteria.py` / `test_phase7_concurrency.py` against the
  preserved sources in `probes/reviewer_r1/` (sha256s `a26f11c1…` /
  `e42d59d3…`) — every r1 probe assertion must SURVIVE adoption (weakened or
  deleted assertions are findings); the added parametrize ids map to
  authority rows per P-V. Re-issue the row-coverage map: every C1–C14 row
  (as amended by A3/A4 + F1–F8) → an observed node id; rows with no arbiter
  are findings.
- **R2-P3 — B3 closed:** the C8 byte-unchanged check commits and reads ALL
  columns including `updated_at` from a fresh second session, before and
  after the promote; the same-session assertion is gone.
- **R2-P4 — S1/S2/S3 closed:** the direct-INSERT direction is deleted; the
  translation unit row exists — probe it (corrupt the index name in the
  constructed IntegrityError or in `INDEX_IDENTITIES` → the row must
  discriminate); re-run M1 (task lock, `FOR NO KEY UPDATE` counterparty) and
  M2 (valuation lock, no-override fixture) from their declared mutant hashes
  — each must redden its named probe; re-run M3/M4 — **row 1 only** per
  chain (a row-2 red contradicts the declaration).
- **R2-P5 — S5/F7 + notes:** cross-WORKSPACE promote → `NotFound` row bites;
  N3's literal `no_primary_item` asserted; N4's seam asserts fired-once +
  second-session visibility; N7's row asserts the EXACT successor id (probe:
  point `superseded_by_id` at the wrong row → red).
- **R2-P6 — numbers (P-L; third round of the transcription class):** re-run
  the full suite foreground and reconcile +39 against the actual new node
  count (`--collect-only` on the changed test files, r1 vs now); failure set
  byte-compared to the phase-1 list; report YOUR focused number on a stated
  set. The committing subset twice with residue scope named (rule 11½).
- **R2-P7 — no regressions:** M6/M7 re-runs (declared hashes differ from r1's
  — same defect class, different mutant text; verify behaviourally); ruff on
  the perimeter; DB at head after your passes; graph READ-ONLY zero delta
  (state exit revision/counts; the 52 pending stay held).

## Closing protocol

1. Verdict (`APPROVED` / `CHANGES_REQUESTED`), counts from the ledger table
   (P-L). Owner cards only for semantic decisions.
2. Mutations you run: per-row sha256 pairs COPY-PASTED, observed red sets
   with pytest node ids, reversion proven (tree == `bb233db` blobs).
3. If APPROVED: carry-forward dispositions table (N5 graph-type question
   rides the held post-approval pass; N6 → phase 8; anything new you find →
   named landing spot). Anchor spans for the 52 held graph items only if
   the fix moved them (production diff was 4 files — check
   `commit_item_cost_evaluation.py` spans in particular).
4. Deposit AFTER your writes, citing final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase7_rereview_r2_handoff.md`
   (full path): findings ledger; row-coverage map; mutation ledger; full
   write perimeter + probe declaration; lessons.
