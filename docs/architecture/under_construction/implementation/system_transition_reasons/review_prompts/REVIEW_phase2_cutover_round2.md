# Re-review prompt — System Transition Reasons, Phase 2: cutover (round 2)

You are performing an independent, adversarial code review. Work from the repo files; assume no
prior conversation. Do not fix anything — report.

Round 1 returned `NEEDS_CHANGES` with four findings, two blocking. The implementer has fixed all
four. **This is a verification pass, not a fresh review** — but a fix is a change, and the round-1
checklist applies in full to everything the fixes touched.

Read `REVIEW_phase2_cutover.md` (round 1) for the full checklist, and the plan's Review log for the
round-1 findings and the implementer's round-2 entry.

## What changed in round 2

| Finding | Fix |
|---|---|
| **R2** (blocking) | `serialize_step_pause_reason` added to `domain/tasks/serializers.py`, used at both `:186` and `:377`. A transition-typed step record now synthesizes a full `PauseReason`-shaped object instead of serializing `null`. |
| **Finding 2** (blocking) | `domain/transitions/labels.py` now carries the seeded `image_url` values, plus `slug` / `requires_description` / `is_system_managed`. New `resolve_transition_reason_catalog_reference()`. |
| **Finding 3** | Stale comment deleted from `labels.py`. |
| **Finding 4** | `states.md` corrected to the narrow behaviour; `test_rebuild_leaves_a_declaration_projection_without_an_actor` added. Implementer ruled **the code was right and the doc wrong**. |

Also edited: the **master plan** — the R2 audit row, the "Label-resolution strings" note, and
**phase-3 binding item 3**, which the implementer marked CLOSED.

## The strongest attacks on this round — start here

These are the places the round-2 work is most likely to be wrong. The implementer flagged the first
three himself; that is a reason to check them harder, not to trust them.

- [ ] **The hardcoded S3 URLs have never been verified against production.** `labels.py` now serves
      `https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/...`. The
      evidence for these being universal is two *repository* files (`seed_pause_reasons.py` and
      migration `49bd666da846`). **The production database is unreachable from the operator's
      machine and was never measured** — see the master plan's "Phase 1 inventory". If a production
      `pause_ended_shift` row carries a different URL, this phase replaces a working icon with a
      broken one, immediately, for every new system transition. Establish what the risk actually is
      and whether a bucket/host that reads `test-bootstrap-local` belongs in shipped domain code at
      all. This is the finding most likely to matter in production and least likely to be caught by
      any test in this repo.
- [ ] **`client_id` on the synthesized object is not a `par_`-prefixed id** — it is the transition
      value (`"shift_ended"`). Hunt for any consumer that assumes the prefix, uses this id as a key
      into a catalog map, sends it back to the server as a `pause_reason_id`, or persists it. The
      published schema brands it (`PauseReasonIdSchema`), which makes a wrong value type-invisible
      on the client.
- [ ] **`slug` reproduces the replaced row's slug** (`pause_ended_shift`), not the transition value.
      The implementer's justification is that shipped frontend code branches on
      `reason.slug === "pause_ended_shift"`. Verify that reading, and then verify the *converse*:
      does a step-record object now carrying that slug, plus `is_system_managed: true` and
      `requires_description`, cause any client to treat it as a selectable or transitionable catalog
      reason when it is not one? Reproducing a slug is the choice that keeps the contract invisible
      *or* the choice that makes a synthesized object indistinguishable from a real one. Decide
      which.
- [ ] **`created_at` echoes the owning record's timestamp.** Confirm nothing renders, sorts, or
      dedupes on it.

## Verify the fixes actually fix

- [ ] **R2's failing-first claim.** Revert both sites in `domain/tasks/serializers.py` to
      `serialize_pause_reason(record.pause_reason) if record.pause_reason is not None else None` and
      confirm `test_step_payload_pause_reason_render.py` fails. The implementer reports 6 of 8
      failing, with 2 controls passing. A test that passes either way proves nothing — and phase 1's
      R9 test is the specific example, so check it was not quietly extended instead of a new test
      being written.
- [ ] **The sweep's exhaustiveness.** The implementer claims the `pause_reason` *object* channel has
      exactly two render sites and six consuming surfaces, resting on one grep pattern. Re-derive it
      independently, by a different route than grepping `.pause_reason` — e.g. from the four
      `selectinload` sites outward, or from the response schemas backward. **R2 was a class, not an
      instance:** any other path phase 1 marked "phase 2 decides" or "no label logic" is suspect.
- [ ] **The two realtime payloads** (`transition_step_state.py:512`,
      `transition_step_state_batch.py:185`) render through the fixed serializer. These were not in
      round 1's endpoint list. Confirm they are covered, and that no *other* event payload embeds a
      pause reason by a different route.
- [ ] **Criterion 14, re-verified rather than restated.** The kiosk test now asserts a non-null
      `image_url` for both channels. Note the implementer changed a **test fixture** to make that
      assertion pass (the catalog `PauseReason` was constructed without an image). Confirm that was
      a fixture defect and not the assertion being bent to fit.
- [ ] **Three phase-1 assertions were changed** from `image_url: None` to the restored URL. Confirm
      each still fails on regression to `None` — an updated assertion that no longer detects
      anything is a weakened test.

## Finding 4 — check the direction, not just the edit

The implementer concluded **the code was correct and the doc wrong**, citing the archived
declared_worker_states Phase 2 plan: *"Reconcile-authored declaration projections have
`changed_by_id IS NULL`."*

- [ ] Read that quote **in its full context** and decide independently whether it supports the
      conclusion. If a declaration-sourced segment should carry the declaring worker, the fix went
      into the wrong file and `_reconstruct_shift_middle.py` is the defect.
- [ ] Either way, confirm the strengthened test pins the invariant in **both** directions and that
      neither `manually_recorded` nor the `changed_by_id` heuristic was touched (T7 — improving them
      is a finding).

## The master plan was edited — check it did not overreach

- [ ] **Phase-3 binding item 3 is marked CLOSED.** Phase 3 is the irreversible phase; an amendment to
      its brief is consequential. Confirm the closure is supported by the evidence and that nothing
      else in phase 3's scope was narrowed as a side effect.
- [ ] The R2 audit row and the "Label-resolution strings" note now contradict what phase 1 recorded.
      Confirm the corrections are right and marked as corrections — phase 1's text should be visibly
      superseded, not silently overwritten.
- [ ] The archived declared_worker_states master plan is still unedited.

## Carried over from round 1 — confirm as deferrals, do not re-litigate

- [ ] **Criterion 11.** The `startswith("par_")` branch is provably *alive*, not dead. This follows
      from the operator's "keep `reason`, no migration" ruling and is discharged by phase 3. Confirm
      the reasoning holds; it is not a new finding.
- [ ] **`app/scripts/backfill/backfill_worker_shift_state_records.py`** builds `LinearInterval`s
      without `transition_reason`. Flagged for phase 3, deliberately not folded in. Confirm that is
      still the right call.
- [ ] The five pre-existing `F401`s in `transition_step_state.py` are baseline debt (T8).

## Suite comparison

- [ ] Node sets, not counts; run-2 vs run-2. The implementer reports `26 failed / 1396 passed` with a
      node set **identical to round 1's**. Re-measure on a quiet tree — do not accept a number taken
      while another session is active.

## Verdict

End with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated criterion,
severity). Record findings in the plan's Review log; that should be the only file you modify.

If this round is `APPROVED`, say so plainly — a second `NEEDS_CHANGES` on unrelated ground, or on
items already recorded as deferred, costs a cycle that phase 3 is waiting on.
