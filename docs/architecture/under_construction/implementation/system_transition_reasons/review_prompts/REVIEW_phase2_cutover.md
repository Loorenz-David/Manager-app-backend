# Review prompt — System Transition Reasons, Phase 2: cutover

You are performing an independent, adversarial code review. Work from the repo files; assume no
prior conversation. Do not fix anything — report.

This is the phase that ends a live outage: in 3131 of 3132 workspaces, clocking out with an open
working step and starting a task while another is active both currently fail. So the central
question is narrow and testable — **does it actually work in a workspace with an empty catalog, on
every path, including the two that are not HTTP?**

## Inputs

- Plan under review: `.../system_transition_reasons/PLAN_system_transition_reasons_phase2_cutover_20260731.md`
- Implementer prompt: `.../codex_prompts/PROMPT_phase2_cutover.md`
- Master plan: decisions T1–T8 and the **"Phase 1 inventory"** read-path audit (R1–R24)
- Living domain docs: `docs/domains/worker_shifts/` (all three files)
- Published contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §5.1, §5.3

## Checklist — the outage fix

- [ ] **Zero-catalog clock-out** and **zero-catalog task switch** both pass, and **both fail against
      pre-phase code**. Verify the failing-first claim yourself by reverting — a test that passes
      either way proves nothing.
- [ ] **The change is in `clock_out_shift_for_user`, not a wrapper.** Confirm the Connecteam handler
      and `auto_clock_out_open_shifts` reach it and inherit the fix, with tests that exercise those
      two paths — not a test that asserts they *call* it.
- [ ] **Both task-switch sites changed**, one test each. `transition_step_state.py` and
      `_step_transition_core.py` are reached by different endpoints. Verify each test actually
      reaches its intended module — a test that hits the same path twice is the likely defect.
- [ ] `get_system_pause_reason_id` has zero runtime callers. Grep yourself.
- [ ] Records written carry `pause_reason_id = NULL` for system transitions (T2). A row carrying
      both is a finding unless it is the documented declared-state exception.

## Checklist — the failure shape from phase 1

Phase 1's blocking finding was a guard that looked incidental and was load-bearing:
`details[0]["pause_reason"]` was a workspace-resolution check, not a null check. **This phase
rewrites the modules that guard lived in.**

- [ ] **Read every changed conditional and ask what it actually tests.** Look for a `None` check
      standing in for a resolution check, and for a fallback chain whose first element can now be
      non-null where it previously could not.
- [ ] **No foreign id can reach a workspace-scoped response.** Probe it: a step carrying another
      workspace's `pause_reason_id`, and a reason hard-deleted since. Assert nothing foreign appears
      anywhere in the output.
- [ ] Phase 1's structural guard (`bucket_key(resolved_catalog_ids)`) is still structural — not
      loosened, defaulted, or made optional to make this phase's changes fit.
- [ ] **Any comment claiming two expressions are equivalent is a finding unless a test proves it.**
      That is precisely how phase 1's defect survived.
- [ ] R23/R24 (`domain/analytics/linear_timeline.py:220,264`) were rewritten and are covered.

## Checklist — derivation

- [ ] **Rebuild idempotence**: run it twice over the same source data, assert identical derived rows.
      Four fix cycles were spent here in a previous feature set; treat it as the central invariant.
- [ ] **Declarations survive the rebuild.** Declare, clock out, assert the declaration is present in
      the derived timeline. This is the architectural spine of the shift domain.
- [ ] Ownership priority unchanged where a step-sourced segment and a declaration overlap — asserted
      against existing expected behaviour, not re-derived.
- [ ] `changed_by_id` is not laundered by the rebuild. Assert the original actor survives end to end.

## Checklist — contract and scope

- [ ] The published three-way `reason_text` contract behaves exactly as handoff §5.3 documents, for
      four cases: system transition, worker-chosen catalog pause, declared state, legacy free-text
      row.
- [ ] **The handoff was not edited** and no liveness row flipped. A contract change, if any, appears
      as a *proposal* in the Review log.
- [ ] The kiosk `pause_by_reason` / `pause_reasons` contract still resolves every key, **including
      the literal `"unspecified"`**.
- [ ] **`manually_recorded`, the `changed_by_id` heuristic** are untouched (T7). Their improvement is
      a finding.
- [ ] The archived declared_worker_states master plan is unedited; D3/D5 amendments are in *this*
      feature set's master plan.
- [ ] Legacy pre-phase rows still resolve to their existing labels.
- [ ] **Read the full diff for out-of-scope production changes.** The last feature set shipped one
      that only a diff read caught — not the Review log, not the tests.

## Checklist — domain documentation (acceptance criterion 20)

- [ ] `docs/domains/worker_shifts/` was updated **in this change**, and matches what actually
      shipped. An unchanged docs folder alongside a behavioural change is a finding.
- [ ] The README's `UserShiftStateRecord.reason` overload warning: if the prefix check was removed,
      **the warning is now false** and must have been rewritten or removed.
- [ ] `states.md` matches the transition semantics that shipped.
- [ ] **The docs contain no history**: no references to plans, phases, migrations, or previous
      behaviour; no "previously" or "as of phase 2"; nothing describing phases 3–4, which have not
      shipped. Living documents state what is true now.
- [ ] The docs are *accurate*, not merely *edited*. Spot-check two claims against the code.

## Suite comparison

- [ ] Failure **node sets**, not counts, against a baseline worktree with `app/.env*` copied in
      (without `.env` the app cannot start). **Run-2 vs run-2** — the test DB and Redis are shared
      and not reset, so three nodes fail on any second consecutive run including in an unmodified
      tree. Sanity-check against the figures in phase 1's Review log, not older canonical numbers.

## Adversarial probes

- A workspace with an empty catalog, a worker mid-declaration, clocking out — does the declaration
  survive and resolve?
- A step whose `pause_reason_id` belongs to another workspace, through every changed read path.
- Task switch reached via the batch endpoint specifically, not just the single-transition one.
- A shift closed by the overnight safeguard in a zero-catalog workspace.
- Revert the rebuild's `transition_reason` write and confirm the derivation tests fail — otherwise
  they are asserting on data they seeded rather than on what the rebuild produced.

## Verdict

End with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated criterion,
severity). Record findings in the plan's Review log; that should be the only file you modify.
