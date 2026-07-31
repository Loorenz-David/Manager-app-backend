# Codex prompt — Phase 2 FIX CYCLE, ROUND 2 (review verdict: NEEDS_CHANGES)

You are fixing round-2 review findings on the Phase 2 implementation (`backend/`). Round-1 findings
(F1/F2/F3/F5) are fixed and independently verified at commit `aa0260a` — do not revisit them except
to keep their tests green. The new findings (G1–G3), with probes run against both `aa0260a` and the
baseline, are in the **Review log** of
`backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase2_derivation_20260729.md`.
Read that first, then this brief.

## The core problem (G1 — BLOCKING)

The F3 symmetric re-check now demands reason/`manually_recorded` equality for EVERY `IN_PAUSE`
target, but the legacy carve-out still guards only `target is IDLE`. Result: an open legacy
`/pause` row (worker's own manual pause) is closed and replaced by a step-sourced `IN_PAUSE` the
moment any step pause opens — and `/resume` then 409s (it requires the open record to be
`manually_recorded`). `/pause`/`/resume` are live until Phase 3; baseline behavior (fully sticky)
must be restored for them.

The difficulty: after the F3 fix, an open `IN_PAUSE` + `manually_recorded=True` record can be
EITHER a legacy `/pause` row (must be sticky vs. both `IDLE` and step-`IN_PAUSE`) OR a
reconcile-authored declared-sourced row (must re-derive when the declaration closes — F3's probe).
Same flags, opposite required behavior.

**Suggested distinguisher (design is yours within plan constraints):** provenance via
`changed_by_id`. An OPEN `IN_PAUSE` with `manually_recorded=True` was written either by
`pause_worker_shift` (`changed_by_id = <worker>`) or by the reconcile (`changed_by_id = NULL`).
So: `manually_recorded AND changed_by_id IS NOT NULL` → legacy manual → fully sticky (no-op for
both `IDLE` and `IN_PAUSE` targets, exactly baseline); `manually_recorded AND changed_by_id IS
NULL` → declared-derived → F3 re-derivation applies. Whatever mechanism you choose: it is
TRANSITIONAL — Phase 3 deletes the carve-out and `/pause`/`/resume` entirely — so keep it minimal
and mark it with a comment referencing Phase 3's removal.

## Findings in scope

- **G1 (BLOCKING).** Restore legacy manual-pause stickiness (above). Flagship test FIRST, asserting
  baseline parity: `/pause` at T0 → step pause opens T1 → reconcile → `changed=False`, manual row
  still open, reason + marker intact → `/resume` succeeds. F3's original probe (declared closed →
  step reason takes over) must STILL pass.
- **G2 (MEDIUM).** Step→step pause re-derivation changed from sticky (baseline: earliest reason
  kept, `changed=False`) to re-emitting. The plan scoped "step-sourced pauses unchanged" — so
  narrow the guard: the F3 re-check applies ONLY to declared-involved transitions (declared row
  open, or current record declared-derived). Pin baseline step→step stickiness with a test (two
  paused steps, earliest closes → no-op, reason R1 kept). If you believe re-emitting is more
  correct (it converges with the rebuild), STOP and ask the operator — do not decide silently.
- **G3 (MINOR, docs).** Amend the phase plan's **Scope → In scope** list to include the additive
  `domain/analytics/linear_timeline.py` ownership-priority change, with the deploy-neutrality
  argument written down (optional field, default preserves behavior, all callers checked). Add one
  sentence to `_reconstruct_shift_middle`'s docstring noting
  `scripts/backfill/backfill_worker_shift_state_records.py` builds its own intervals and does not
  fold declared rows (a second projection — harmless for pre-declaration history, revisit only if
  the backfill is ever rerun over post-declaration dates).

## Protocol

1. Fix on top of `aa0260a`. Tests first (G1 flagship, G2 pin), watch them fail, then fix.
2. Re-run the full phase Validation plan + baseline rule (no NEW failures vs. baseline; all
   round-1 regression tests still green; touched files ruff-clean).
3. Append a round-2 fix entry to the plan's Review log (per finding: change + pinning test).
4. **Do NOT archive, do NOT write a summary, do NOT flip the master table** — the phase returns to
   the reviewer (`review_prompts/REVIEW_phase2_derivation.md`) and archives only on APPROVED.
5. One fix commit referencing G1/G2/G3.
