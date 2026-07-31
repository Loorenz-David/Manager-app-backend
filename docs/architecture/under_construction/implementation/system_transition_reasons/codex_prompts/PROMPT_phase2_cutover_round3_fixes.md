# Fix prompt — System Transition Reasons, Phase 2: cutover (round 3)

You are fixing review findings in the ManagerBeyo backend (`backend/`). Round 2 returned
`NEEDS_CHANGES`: **one blocking finding, two low.**

Round 2's four fixes were all verified correct by execution and are **not** in scope. Do not revisit
them. What is in scope is the generalisation the R2 fix implied and did not reach.

## Protocol

1. Load and follow `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process as: fix → validate → review-log entry → **STOP for re-review.** No summary, no archive,
   no phase-table flip, no handoff edit.
2. Read, in order:
   - The round-2 reviewer entry in
     `.../system_transition_reasons/PLAN_system_transition_reasons_phase2_cutover_20260731.md`
     (Review log, last entry) — the findings in full, with file:line and evidence.
   - The master plan's **"Phase 1 inventory"** read-path audit, specifically row **R9**.
   - `docs/domains/worker_shifts/` if you end up changing documented behaviour. F1 does not change
     it — it restores it.
3. No clarifications are open. F1 has one operator-decidable branch, described below; take it only
   if you genuinely conclude the fix is wrong.

## F1 (BLOCKING) — R9 is R2, in a third render site

`app/beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py:432`

`record_detail` renders a **full `PauseReason` object**:

```python
"pause_reason": serialize_pause_reason(pause_reason) if pause_reason is not None else None,
```

`pause_reason` there is `pause_reason_objects.get(record.reason)`. This phase sets
`pause_reason_id = NULL` on every `SHIFT_ENDED` and `OTHER_TASK_PRIORITY` record, so it resolves to
nothing and the field serialises `null` where it previously carried a populated catalog object.

The consumer is shipped: `frontend/packages/stats/src/lib/time-line-calendar/segment-adapter.ts:113`
— `reasonLabel: record.pause_reason?.name ?? null` — rendered at `TimelineEventBlock.tsx:52,112-115`,
`WorkerTimelineSlidePage.tsx:176-177`, `WorkerTimelineEventSheetPage.tsx:101-102`. The schema is
`packages/stats/src/types.ts:304`, the **same full `PauseReasonSchema`** that drove the R2 fix.

**The fix is the R2 fix.** `record.transition_reason` is already on `_StepTimelineRecord`;
`resolve_transition_reason_catalog_reference` already exists and
`resolve_transition_reason_label` is already imported in this module. It is a one-call substitution
plus a `created_at` source.

### Two things you must also change, or the fix is not done

1. **`app/tests/integration/services/queries/worker_stats/test_transition_reason_read_tolerance.py:386-389`
   currently pins the defect.** It asserts `step_details[0]["pause_reason"] is None` under the
   comment *"the step payload gains no field in this phase"* — the exact premise round 2 overturned
   for the other two sites. Reverse the assertion and rewrite the comment. Leaving a green test that
   asserts the old behaviour is how this survived a round.
2. **The master plan's audit row R9** still reads "same test (asserts `pause_reason: null`, no new
   key)". Correct it the way R2's row was corrected — **strike through, mark as decided, name the
   round** — so phase 1's text is visibly superseded rather than overwritten. Match the existing
   formatting of the R2 row exactly.

### Prove it failing-first

Do not assume. Write the assertion, confirm it **fails** against the current code, then fix
`record_detail` and confirm it passes. Report both, per node.

`test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both:496` already asserts a populated
object for a row that *does* carry a catalog id — it is your control and must stay green and
unmodified.

### The one branch that is the operator's, not yours

If you conclude the null is correct on this surface, **do not just leave it** — that is what round 2
did by omission and it is the finding. Write the case in the Review log with the consumer evidence
and STOP for a ruling, exactly as criterion 13 requires. The default is: apply the fix.

## F2 (LOW) — round-1 F3 was reported fixed and is fixed in one of three places

Round 1 named `labels.py` **and** explicitly added the two model files. Only `labels.py` was edited.
All three comments are now false:

- `app/beyo_manager/models/tables/tasks/step_state_record.py:54` — "nothing writes it in phase 1"
- `app/beyo_manager/models/tables/users/user_shift_state_record.py:36` — "Nothing writes it in
  phase 1."
- `app/beyo_manager/services/queries/worker_stats/list_workers_linear_timeline.py:59` — "Nothing
  writes it yet, so this is inert today"

The third is the one that matters. It sits directly above the
`record.reason or record.transition_reason or UNSPECIFIED_REASON` fallback **that this phase made
live**. A reader trusting it would delete the branch and silently re-break roster bucketing.

Rewrite all three to say what is true now. Same standard applied to `labels.py` in round 2: state
the reasoning, not just the conclusion, so the next reader inherits why rather than what.

## F3 (LOW) — the seed's drift guard points at two of three copies

`app/beyo_manager/services/commands/bootstrap/phases/seed_pause_reasons.py:10-14` warns that the row
data is duplicated in migration `49bd666da846` and must be mirrored there. There are now **three**
copies of the image URLs. `labels.py` points at the other two; the guard at the source does not point
back at `labels.py`.

Add `labels.py` to that warning. One line. The guard is one-directional today and will not stop the
drift it exists to stop.

## Hard constraints — unchanged from round 2, and one addition

- **Do not touch `manually_recorded` or the `changed_by_id` provenance heuristic** (T7). Verified
  clean in round 2; improving either is a finding.
- **Do not edit `docs/handoff/to_frontend/`.** Operator-owned.
- **Do not edit the archived declared_worker_states plan.**
- **Do not reopen round 2's four fixes**, criterion 11, or the
  `backfill_worker_shift_state_records.py` carry-forward. All three are recorded deferrals with the
  reasoning confirmed. Re-litigating them costs a cycle phase 3 is waiting on.
- **New: F1's fix must not widen.** The segment-level `reason` key, `bucket_key`, and the
  `pause_reasons` map top-up are already correct and already tested. Change `record_detail`'s nested
  object and nothing else in that function's neighbourhood.

## Before you claim the sweep is closed this time

Round 2's sweep rested on one grep pattern (`.pause_reason`) and concluded "exactly two render
sites". It missed this one because `record_detail` calls `serialize_pause_reason` on a
**separately-fetched local**, not on `record.pause_reason`.

Re-derive by the route that finds it: **every caller of `serialize_pause_reason`**, and every
construction of a twelve-field pause-reason-shaped dict. Then state the result as a list of
call sites with file:line, not as a count.

For the record, the reviewer re-derived this and found the remaining audit rows genuinely clean —
R1 (catalog leaf), R3/R4 (take a `PauseReason` directly; `UserDeclaredStateRecord.pause_reason_id`
is `Mapped[str]`, NOT NULL), R16 (`selectinload` feeding the now-fixed R2), R19–R22. R9 was the only
surviving instance. Confirm that independently rather than inheriting it.

## Optional, if it costs nothing

`serialize_step_pause_reason` falls back to `created_at=""` when both `created_at` and `entered_at`
are `None`. Inert today — it satisfies `z.string()` and nothing reads the field — but `""` is not a
datetime. Fix or leave; say which.

## Not yours to fix — context only

- **The hardcoded S3 URLs are assessed and accepted.** Blast radius is one row per slug database-wide
  (`uq_pause_reasons_slug` is **globally** unique); the host matches `.env.production.ec2`'s
  `STORAGE_BUCKET`; `update_pause_reason.py:43` lacks an `is_system_managed` guard so divergence is
  possible, but `seed_pause_reasons.py:39-46` repairs `image_url` on bootstrap rerun and the worst
  case is a stale icon. Recorded as risk, not a finding. **Do not add a guard to
  `update_pause_reason` in this phase** — that is a separate change with its own blast radius.
- **The `slug` choice is right, its stated justification is not.**
  `resolvePauseReasonTransition` is fed only from `usePauseReasonsQuery`, so a step record's embedded
  reason never reaches that branch. The real reason is the schema's non-nullable `slug` plus display
  parity. If you touch `labels.py`'s docstring for F3, correct that sentence while you are there;
  otherwise leave it.

## Definition of done

- F1 fixed at `get_worker_linear_timeline_breakdown.py:432`, with the reversed assertion **proven
  failing-first**, and audit row R9 corrected in the master plan in the R2 row's format.
- F2: all three comments true. F3: the drift guard names all three copies.
- The `serialize_pause_reason` caller sweep re-derived and stated as a list with file:line.
- Full suite: **node sets**, not counts, **run-2 vs run-2**. The reviewer measured
  `26 failed / 1396 passed` with run-1 and run-2 node sets byte-identical. Any deviation from that
  node set is yours to explain.
- `ruff check` clean on touched files.
- Review log entry: what changed, the failing-first evidence per node, and the sweep. Then **STOP for
  re-review.**

## One note on the tree

Two commits landed during round-2 review (`f344230`, `b0dd236`) committing the plans and amending
**phase 3 and phase 4** scope. Docs only — no production or test file moved. Rebase your mental model
on `HEAD`, and do not treat the phase-3 amendment as part of this round's scope.
