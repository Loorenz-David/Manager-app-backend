# ARCHIVE_RECORD_PLAN_case_created_transition_reason_20260801

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_case_created_transition_reason_20260801`
- Archived at (UTC): `2026-08-01T00:00:00Z`
- Archive owner agent: `claude-opus-5` (on operator direction, post-review)

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_case_created_transition_reason_20260801.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_case_created_transition_reason_20260801.md`
- Intention: none — a restoration of a lost capability, filed directly as a plan.
- Prompts: `.../archives/implementation/PROMPT_case_created_transition_reason.md`,
  `REVIEW_case_created_transition_reason.md`
- Implementation commit: `9497360`
- Debug chain: `none`

## Outcome classification

- Result: `completed`
- Acceptance criteria: ten met with evidence. Criterion 2 met **as amended** — `image_url: None`,
  because the retired catalog row's image does not exist to reuse (escalation 1, operator-accepted).
- Reviews: **one round, `APPROVED`**, no blocking findings, two non-blocking observations.
- Validation gates: **not waived.** 23 failed / 1463 passed against a 23/1453 baseline, node sets
  byte-identical at the same run index; `ruff` clean on all six touched files; the repository's
  pre-existing findings neither absorbed nor repaired (T8).

## Final notes

- **Criterion 7 has a second half that the obvious reading misses.** Isolating a side effect so it
  cannot fail the user's action is not achieved by `try`/`except` alone: the rollback expires every
  ORM object on the async session, so whatever runs *after* the guard breaks instead. The fix was
  ordering — snapshot the response before the side effect. The reviewer reverted the snapshot and
  confirmed the test fails, so it binds to the ordering rather than to the swallow.
- **The capability was lost through a slug lookup, not through a deletion.** The client resolved its
  pause reason by `slug === "pause_case_created"`; the row was soft-deleted; the lookup returned
  `undefined`; the pause kept firing with no reason. Nothing errored, nothing was logged, and 40
  records accumulated. That failure shape — *a lookup that degrades to silence* — is the concrete
  argument for the whole `system_transition_reasons` package.
- **First change to consume the zero-catalog property rather than establish it.** Four phases of work
  exist so system behaviour does not depend on a workspace-editable row; this is the first feature to
  assert it as a precondition of its own correctness, and to assert the catalog is empty *before*
  acting rather than assuming it.
- **The reviewer walked all 30 `WORKING` call sites, not the two named.** That is now the standard
  this codebase holds after R1, and it found two unnamed sites (both correct) plus one dormant one
  worth knowing about when someone re-enables the undo window.
- **Two escalations, both correct, both raised rather than decided.** Weighted as care, not as scope
  creep — this was the intended behaviour of the protocol and it worked.
- **A stale debt entry was retired in the same pass.** `docs/repo_health.md` recorded a `NameError`
  from a missing `select` import in `_step_transition_core.py`. Both agents independently found the
  import present; `git log -S` shows it arrived in `867b8fb`, within this same feature-set sequence.
  The defect is gone; the residual coverage claim was moved to the test-debt table with the history
  noted, rather than silently deleted.

## Open items at archive time

- **The frontend handoff gates the deploy.** `HANDOFF_TO_FRONTEND_remove_case_created_pause_20260801.md`
  must ship with or before the backend. Late means every case created from a working step shows the
  worker an error; early is safe.
- **No `task:step-state-changed` event on the case-created pause.** Recorded as a known gap in
  `docs/domains/worker_shifts/README.md`. Emitting it would remove the deploy-ordering coupling
  above. Operator decision.
- **The 7 historical `pause_case_created` rows keep the catalog representation** (ruling 4), so the
  same interruption has two shapes in the data. Nothing depends on the distinction and
  `pause_ended_shift` is already in that state.
- **`image_url: None`** — the segment renders label-only. A new asset is an operator call.
- **Nothing is deployed.** The server is at `d8e4f1a2c6b7`; this change adds no migration, so the
  chain is unchanged at eight revisions across the two predecessor feature sets.
