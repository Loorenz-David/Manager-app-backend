---
plan: phase 2 (schema, models & migration)
role: reviewer
round: 1
date: 2026-08-12
---

# Session prompt — review phase 2 (first review, full checklist)

You are the **reviewing agent** for phase 2 of the item-cost-calculation pipeline.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — FIRST review: full checklist
   against plan criteria and semantic authorities; adversarial re-derivation;
   mutation-tested tests.

## Gate check

- Tracker shows phase 2 **IMPLEMENTED** (Codex).
- Implementer handoff:
  `handoffs/implementer/2026-08-12_phase2_implement_r1_handoff.md`.
- **The effective checkpoint is `8b3f9f7`** — the handoff cites `500dfbd`, which was
  amended into `8b3f9f7` (they differ only in the handoff file itself; verified by
  the coordinator). The diff under review is `git show 8b3f9f7`.

## Read order (after doctrine)

1. `plans/phase_2_schema_models.md` — criteria as amended 2026-08-12 (C1a/b, C2 with
   (b)-per-clause + named mutations, C3 incl. the 12-row type table and exception
   classes, C4, C5 migration-site proof + M-a/M-b, C6) + the implementer's Review
   log entry.
2. `master_plan.md` §6 entire (the CLOSED CHECK list, deliberate absences, named
   FKs, enum registry), §9, §10 (incl. the disposable-DB recipe AND its new
   migration-chain-stall caveat).
3. Intention §4 entire (round-6 §4.6, round-7 §4.5 pin), §4A, §4.7A, §6A.4, §7A
   intro.
4. The implementer handoff — judgment calls are your probe list.
5. The diff: `git show 8b3f9f7` (code) — coordinator commits around it
   (`d58c50d`, `ab2b71c`, docs) are not the implementer's perimeter.

## Coordinator probes (verify, don't trust)

- **P2-1 (the declared gap — treat as an open criterion, not a trusted claim):**
  the implementer did NOT run C2's multi-clause predicate mutations (INV-B1,
  INV-E1, INV-V1) and said so. Run them yourself (disposable worktree, one clause
  at a time, revert, sha256-verify): dropping a single clause from each index's
  `postgresql_where` must redden exactly that index's corresponding (b) row. If a
  (b) row survives its clause's removal, that row is decoration — a finding.
- **P2-2 (closed-list conformance):** diff the actual DDL (the migration file AND
  `pg_constraint`/`pg_indexes` on the migrated dev DB) against master plan §6.2's
  closed CHECK list, the nine `uix_`/`uq_` names, and the three named FKs — both
  directions: nothing missing, nothing extra, no silently-truncated name (query by
  exact name; every name should be ≤ 63 bytes stored).
- **P2-3 (enum ownership):** re-run M-a and M-b independently (the implementer ran
  them — verify, don't inherit): reused-type `create_type=True` must fail `upgrade`
  on a DB at head; a `task_state_enum` drop in `downgrade` must fail the round-trip.
  Also verify `downgrade` drops exactly the five new types (C1b's static proxy
  exists and bites).
- **P2-4 (lifecycle workaround adequacy):** the from-scratch disposable recipe
  stalled on a pre-existing migration-chain defect, so the implementer cloned the
  dev schema and exercised THIS revision's `downgrade → upgrade` there. Judge
  whether that proves C1's round-trip for revision `90cdd23a828e` (it plausibly
  does — the round-trip of one revision needs only the pre-state schema), and
  verify the stall is genuinely pre-existing (reproduce briefly at the pre-phase
  commit if cheap). The stall itself is out of scope — confirm it is filed, not
  fixed.
- **P2-5 (per-table shapes):** verify the D5/D6/round-7 column shapes in the actual
  models: membership table has NO soft-delete trio and NO `updated_*`;
  `item_valuations` has no `updated_*`; `item_cost_evaluation_terms` matches the
  §4.5 round-7 pin exactly (incl. `workspace_id`, no `value` column);
  `item_cost_results` has `task_state_snapshot` NOT NULL + nullable
  `task_closed_at` (C6). Deliberate absences absent: no CHECK on
  budget/allowance/`task_state_snapshot`, no `percent_value` upper CHECK.
- **P2-6 (graph delta — standing flow, master plan §8):** the 15 pending review
  items ARE phase 2's inferred delta (9 `table-*` nodes + ownership edges). For
  each: open the cited model file BEFORE reading the stored claim, state what it
  defines in your own words, then compare (the anti-pattern rule in the
  archgraph-discrepancies skill). Report per item: claim exact / claim wrong /
  anchor wrong, with a recommended decision (promote / edit / reject). **Do NOT
  adjudicate** — the coordinator confirms after approval on the owner's standing
  authorization. Also sanity-check edge count: the handoff says 6 ownership edges;
  the graph gained 4 net — reconcile (the owner's concurrent backlog adjudication
  may account for it; say what you find).

## Scope-fence verification

No existing table's model changed; no command/query/router/calculator; the three
reused PG enum types are neither created nor dropped by the migration; the
configured dev DB is at head `90cdd23a828e` and was never downgraded.

## Constraints

- Full suite per master plan §10 (healthy containers; runs with connection noise
  are never evidence). Baseline: the §10-recorded 23 known failures.
- Findings → the phase plan's Review log (append-only), severity B/S/N, exact
  correction clauses (fix prompts quote them verbatim).
- Tracker row (yours only): IMPLEMENTED → REVIEWING → verdict; append to the Note,
  never overwrite prior actors' stamps.
- Mutation probes in disposable worktrees only; revert, sha256-verify, declare.
- Do not fix anything — findings, not patches.

## Closing protocol

1. Review log entries; tracker row + verdict (APPROVED / CHANGES_REQUESTED).
2. Deposit the handoff at
   `handoffs/reviewer/2026-08-12_phase2_review_r1_handoff.md` (frontmatter `plan`,
   `role`, `round: 1`, `date`, `state`, `verdict`, `actor`): summary;
   `⚠ OWNER DECISIONS REQUIRED (n)` (one line if zero); findings by severity;
   probe results P2-1…P2-6 (P2-6 as a per-item table with recommended decisions);
   lessons for the plans; full write perimeter incl. probe declaration.
   **Deposit the handoff before ending the session.**
