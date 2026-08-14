---
plan: phase 8 (status & results — status query, result handler, §8B emissions)
role: reviewer
round: 1
date: 2026-08-14
---

# Session prompt — review phase 8 implementation (r1 + r1b)

You are the **reviewing agent** for phase 8 — the last mechanism phase.
Re-derive independently; never accept a declaration you can re-run. This
phase reached you through TWO implementation rounds: r1 shipped the
production surface with a missing enum migration (coordinator-reproduced:
24 task-boundary failures) and almost no proof; r1b added the migration,
restored the baseline, and built part of the matrix — **explicitly
deferring all 17 named mutations and several criterion families to you,
per row**. Your mutation pass is not garnish; it is most of the phase's
proof.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- Plan: `plans/phase_8_status_results.md` — base + forward notes + the
  GOVERNING **projection block A1–A17** + **A18** (the enum-migration
  correction; also records that the r1 handoff's dirty-DB diagnosis was
  false). Intention round 17 (R17-1 result-block-from-READY,
  boundary-labelled; R17-2 DELETE status re-resolved). Master plan
  §6.4/§6.5, §9 P-A…P-AB + ALL extensions (P-E as amended for the reopen
  call-site; the deferral rule — r1b's per-row deferral is compliant in
  FORM; you are the substance).
- Checkpoints: r1 `ae12f23` (29 files), r1b `6c1da6b` (9 files: the
  migration + 5 test files + docs; handoff committed INSIDE the checkpoint
  then amended by `908848a` — the phase-3 process-slip class, recorded).
- Handoffs:
  `handoffs/implementer/2026-08-14_phase8_implement_r1_handoff.md` (its
  suite numbers and diagnosis are CORRECTED by the plan's A18/Review log —
  read it for the perimeter, not the verdicts) and
  `…/2026-08-14_phase8_implement_r1b_handoff.md` (the 17-row deferred
  mutation ledger and the 19 final hashes).
- Coordinator consumption (verified, do not re-litigate): `git diff
  6c1da6b..HEAD -- app/` empty; 9 of 19 declared final hashes recomputed
  byte-identical (spot set incl. the migration); DB at `c1d2e3f4a5b6` with
  the enum label present by state query; §10's head entry updated; r1's
  three A16 graph discrepancy filings present under the maintenance
  ledger's `open/`.

## Environment facts

- Head **`c1d2e3f4a5b6`** (the phase's one migration). Declared suite:
  **2111 / 23 / 1 deselected** — the 23 observed as an ID-set match only;
  the byte-compare is YOURS. Prior baseline 2076/23/1 = 2099 selected →
  expect +35 collected; reconcile against `--collect-only` on the changed
  test files.
- `alembic check` reports three PRE-EXISTING drifts
  (`email_sync_states_connection_id_key`, two `step_state_records`
  indexes) — pre-phase-8; verify they exist at `b71d252` too and route to
  the only-if-cheap ledger, not this phase.
- Graph: 21 pending (r1's delta) + the migration mapping delegated to the
  coordinator's post-approval pass — READ-ONLY for you, zero delta,
  rev `c74eb913…` at entry.
- Integration on the queue path needs the analytics worker (§10 Makefile
  caveat); in-process handler invocation is the default seam.

## Probes (minimum — the ledger is yours)

- **P8-1 — the 17-row deferred mutation ledger is YOURS.** Run every row
  (r1b's list): C1's THREE filter deletions (manager/worker/handler —
  each reddens its own row only); A15's re-resolution removal; the FIVE
  emission deletions at their definition sites (READY-entry; reopen —
  must redden THROUGH the `add_task_steps` path; resolve/fail/cancel —
  their rows must use ZERO-notification-target fixtures or the mutation
  cannot bite the placement, A4); the straggler deletion AND its
  READY-half guard narrowing (two distinct rows); C7's selection-OK
  producer swap (the hazard row); C9's `total_cost_minor` serializer
  addition; C11's live-field substitution; A6's two P-G route-table
  mutations; A13's `computed_at` freeze. Per row: sha256 pairs
  COPY-PASTED, observed pytest ids, reversion proven (tree == `6c1da6b`
  blobs). A row whose test does not EXIST yet is a coverage finding —
  build the probe, run it, and attach it for the fix cycle (the phase-7
  adoption-fidelity pattern: preserve your probe files with hashes at a
  named path).
- **P8-2 — the declared-unbuilt families.** r1b names them honestly:
  C2 (bucket policy — the ended-shift bucket is `PAUSED` +
  `transition_reason == SHIFT_ENDED`, A12), C3 (batch dilution), the
  C6/C10 boundary-emission EXACT-COUNT rows (a ready-making transition
  yields exactly TWO result events — L24; "at least one" is a finding),
  A10's loader-equality row + its non-vacuity arbiter, and the remaining
  lifetime/status sole-predicate rows. Build, run, report — same
  preservation discipline.
- **P8-3 — row-coverage map** over C1–C11 as amended (A1–A18): every row →
  an observed parametrize id (r1b's 33 focused + r1's units + your
  probes); rows with no arbiter are findings (P-V; the phase-7 B2
  precedent).
- **P8-4 — independent re-derivation of the mechanisms:** §8B.2 total
  admission against the code; the upsert's SET list vs A5's eleven-column
  enumeration + four exclusions (first `on_conflict_do_update` in the
  repo — read it hard); §8A.1's consumption expression (COALESCE, deleted
  steps out, SKIPPED counts); the two-producer composition (resolver OK
  never in the payload); R17-1's boundary-labelled result block; R17-2's
  re-resolution asserted as the LITERAL equality (deleted-price status ==
  never-priced status, configured AND unconfigured workspaces);
  `item_binding` three values; the reopen signature + P-E-as-amended
  adherence (`add_task_steps.py` diff is the await only); the worker
  payload's five-key result block (A9) and the enumerated-family
  disjointness (A11); `include_monetary_step_fields` reuse (A17);
  `route.response_model is None` structural row.
- **P8-5 — the migration:** read `c1d2e3f4a5b6_…` against the
  `f2c3d4e5f6a7` precedent; run the disposable round-trip r1b skipped
  (fresh DB → upgrade head; state-query the label; document the
  downgrade's shape — PG cannot drop enum values, so verify what the
  precedent does and that the docstring says so honestly). Verify the
  three `alembic check` drifts predate the phase.
- **P8-6 — numbers:** full suite foreground YOURSELF; failure set
  BYTE-compared (sorted diff) to the phase-1 list; +35 reconciled;
  focused sets on stated scopes; any committing subset twice with residue
  scope named (rule 11½). DB left at head `c1d2e3f4a5b6`.
- **P8-7 — the R2-N2 hardening** (`assert checked == 1` — verify it can
  actually fail: rename the extra key in a probe and watch it redden).

## Closing protocol

1. Verdict with blocking / should-fix / notes counted from the ledger
   table (P-L); story-shaped owner cards only for semantic decisions.
2. Your mutation + probe ledgers: per-row hashes, observed red sets,
   reversion proven; probe artifacts preserved WITH sha256s at a named
   path under the pipeline folder for the fix cycle to adopt
   (adoption-fidelity rule).
3. Graph: READ-ONLY, zero delta; state exit revision/counts (21 pending
   held); anchor-spans service only if something you find moves spans.
4. Deposit AFTER your writes, citing final hashes, at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase8_review_r1_handoff.md`
   (full path): findings ledger; row-coverage map; mutation ledger; full
   write perimeter + probe declaration; lessons.
