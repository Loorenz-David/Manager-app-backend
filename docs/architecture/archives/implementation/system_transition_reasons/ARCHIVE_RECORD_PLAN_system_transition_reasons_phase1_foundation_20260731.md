# ARCHIVE_RECORD_PLAN_system_transition_reasons_phase1_foundation_20260731

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_system_transition_reasons_phase1_foundation_20260731`
- Archived at (UTC): `2026-07-31T14:13:35Z`
- Archive owner agent: `claude-opus-5` (on operator direction, post-review)

## Source references

- Plan: `backend/docs/architecture/archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase1_foundation_20260731.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_system_transition_reasons_phase1_foundation_20260731.md`
- Master plan (intention role): `backend/docs/architecture/under_construction/implementation/system_transition_reasons/MASTER_PLAN_system_transition_reasons_20260731.md`
- Intention: `backend/docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`
- Debug chain: `none`

## Outcome classification

- Result: `completed`
- Acceptance criteria: all 17 met, independently re-verified **by execution** by the reviewer
  (APPROVED at round 2). One blocking finding (F1) and three non-blocking (F2–F4) raised at round 1
  and closed in one fix cycle.
- Validation gates: **not waived.** Failure node sets identical to the baseline worktree at
  `26d290d` (run-2 vs run-2, both trees), reproduced independently by the reviewer. `ruff check`
  clean on touched files. The pre-existing repository baseline was neither absorbed nor repaired
  (T8).

## Final notes

- **The phase is observably inert by design.** Nothing writes `transition_reason`; phase 2 cuts the
  writers over and ends the outage.
- **Two inputs were overturned by evidence, which was the point of running step A first.**
  (i) The slug-consumer audit found live frontend consumers of `pause_reasons.slug`, so **operator
  decision T6 was amended** — the column stays, and phase 4 scopes `uq_pause_reasons_slug` to
  `(workspace_id, slug)` rather than dropping it. The decisive consumer is a required, non-nullable
  `slug: z.string()` in `@beyo/pause-reasons`, which would have failed validation on every
  pause-reasons response. (ii) The intention's headline "3132 workspaces, exactly 1" was traced to
  the shared **test** database and is accumulated test residue; production remains unmeasured.
- **The intention's Finding 2 was confirmed by execution**, on a disposable database, not by
  inspection.
- **F1 is the finding worth remembering.** A guard that looked incidental —
  `details[0]["pause_reason"]` — was in fact the workspace-resolution check, and replacing it with
  an unconditional read leaked a foreign workspace's `par_…` id into a workspace-scoped response.
  The fix makes resolution structural: `bucket_key(resolved_catalog_ids)` cannot return a catalog id
  that did not resolve. The reviewer confirmed the new guard's extension is *identical* to the
  deleted one, not merely equivalent in the tested case.
- **Carried into later phases, recorded in the master plan's "Phase 1 inventory":** R14/R15 are
  writers that phase 2 **must** rewrite or the kiosk buckets everything as `unspecified`;
  `image_url` for system transitions is null once phase 3 backfills; and phase 3 must null only
  `pause_ended_shift` and `pause_other_task_priority`, never the `pause_case_created` anchor.
- **Repo-health items surfaced, outside this feature set** (both verified pre-existing at
  `26d290d`): the breakdown endpoint cannot resolve worker-level pause reasons in its own
  `pause_reasons` map; and the soft-deleted `pause_case_created` anchor is invisible to
  `list_pause_reasons`, so case-created pauses are being written today with no `pause_reason_id`.
  Tracked in the summary's "Known gaps".
- **Open for the operator:** `PLAN_..._phase3_backfill_20260731.md` clarification 3 still presumes
  `pause_case_created` needs its own enum member, which the F4 disposition contradicts. Editing a
  sibling phase plan was outside phase 1's remit.
