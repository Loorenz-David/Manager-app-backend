---
plan: phase 1 (worker money redaction)
role: reviewer
session_doctrine: plan-reviewer (re-review variant, delta-scoped)
round: 2
date: 2026-08-12
state: COMPLETE
verdict: APPROVED
actor: Claude (plan-reviewer)
---

# Re-review handoff — phase 1, round 2

## Summary

**APPROVED.** Both r1 should-fix items are resolved and independently verified, and the
fix cost nothing: `git diff 4416570..ed99e7e -- app/beyo_manager/` is **empty**, so the
redaction machinery approved on the merits in r1 is byte-identical and every entry in
r1's "Verified correct" list still stands. The perimeter is exactly the six allowed
files.

S1 is closed on substance, not just on row count. Criteria coverage is now 24/24
(endpoint × admitted role) cells and 26/26 rows, and the five added rows demonstrably
earn their place: dropping ADMIN from the allow-list reddens **exactly nine**
ADMIN-bearing test ids — one per endpoint plus the unit helper — with zero ADMIN ids left
green and zero collateral reddening. Before fix r2 that same regression would have been
caught on only three of the eight endpoints. S2's correction is append-only, carries the
verified pair verbatim, and its 23-item list is set-identical to r1's verified set
(compared programmatically, both directions).

One new note (N7, cosmetic test naming) is carried forward. No findings.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Nothing in this re-review needs an owner answer; phase 1 is ready for its gate
commit and phase 2 may start.

## Step 1 — verified perimeter: PASS

`git show ed99e7e` = six files, all allowed: the four test modules
(`test_reassigned_steps_integration.py`,
`test_worker_stats_endpoint_split_integration.py`,
`test_get_user_last_active_step_record_integration.py`,
`test_list_working_section_steps_payload_characterization.py`), the phase-1 plan
(Review log) and the master-plan tracker row. Nothing outside.

Two further perimeter facts worth recording:

- **No production code changed** — `git show --stat ed99e7e -- app/beyo_manager/` is
  empty, and `git diff --stat 4416570..ed99e7e -- app/beyo_manager/` is empty. The fix is
  purely test coverage plus a record correction, which is why this re-review could stay
  delta-scoped without re-deriving the census or the fail-closed construction.
- Commits `3e40646`, `65a20f0`, `bb7de26` sit after the checkpoint and are coordinator
  docs only (verified: no `app/` paths). Attributed to the coordinator, not the fixer.

## Probe results

### R2-P1 — the reshaped function — **PASS**

The two reshaped tests parametrize only the *retained-money* call; the worker contexts
still take the `"worker"` default (`_list_ctx` / `_ctx` at
`test_reassigned_steps_integration.py:68` and `:31`). So criteria rows **19 and 22
survived** and now execute **twice each**, once per parameter. Confirmed by collection
and by mutation, not by reading alone.

All five S1 rows collect as live parameters and assert equality with the seeded `4321`:

| Row | Endpoint | Asserting parameter id |
|---|---|---|
| 9 | `/working-sections/{id}/steps` | `test_list_working_section_steps_payload_key_sets_are_stable[admin-False]`, `[admin-True]` |
| 12 | `/working-sections/steps/user-last-active` | `test_last_active_step_payload_applies_role_money_boundary[admin-True]` |
| 17 | `/task-step-acknowledgments/reassigned-steps` | `test_reassigned_and_pending_…[admin]` (first assertion) |
| 20 | `/task-step-acknowledgments/pending` | `test_reassigned_and_pending_…[admin]` (second assertion) |
| 23 | `/worker-stats/last-interacted-steps` | `test_last_interacted_steps_keep_money_for_manager[admin]` |

Row 9's assertion is set-equality against the full `_STEP_KEYS` **plus**
`item["total_cost_minor"] == 4321` — equality, not presence, as the criteria preamble
requires.

### R2-P2 — baseline record — **PASS, exact**

- **Append-only:** the plan-file diff for `ed99e7e` contains **no deletions at all**; the
  historical implementer r1 numbers are preserved beside the correction. Placement inside
  the implementer entry is precisely what r1's correction clause authorized ("replace the
  baseline numbers in the implementer entry, or add a correction line").
- **Verified pair carried verbatim:** `545e504` → 1578 passed / 23 failed / 1 deselected;
  `4416570` → 1600 passed / 23 failed / 1 deselected; sets byte-identical.
- **List match:** extracted the recorded 23 node ids and set-compared against the r1
  reviewer's verified set — identical in both directions, no additions, no omissions.
  (Intra-group ordering differs from r1's alphabetical listing; membership is what the
  probe asks for.)

### R2-P3 — liveness of the new rows — **PASS**

Fix r2 ran no mutation probes, so all of these are mine. Disposable worktree at
`ed99e7e`, per-parameter granularity, control run 15/15 green before mutating:

| Probe | Site | Result |
|---|---|---|
| blanket `False` | site-5 derivation | RED — daily-breakdown test (rows 15 + 15b) |
| blanket `False` | `build_step_record_payload` derivation | RED — `last_interacted[admin]` **and** `[manager]` **independently** (rows 23 + 24); also `last_active[admin-True]`/`[manager-True]` (rows 12/13); worker row correctly green |
| M4 hardcode `True` | `build_steps_list_payload` derivation | RED — `key_sets_are_stable[worker-False]`/`[worker-True]` (row 11) and the reassigned test under **both** params plus the pre-existing pagination characterization (row 19); admin/manager rows correctly green |
| M5 hardcode `True` | `build_step_record_payload` derivation | RED — `last_active[worker-False]` (row 14) and the reassigned test under both params (row 22); retention rows correctly green |

**Extra probe, not requested — ADMIN dropped from the allow-list.** This is the only
mutation that isolates an ADMIN-specific regression, so it is the real test of whether
S1's fix has value rather than row-count conformance. Result: **exactly nine**
ADMIN-bearing ids red — `key_sets_are_stable[admin-False]`, `[admin-True]`,
`last_active[admin-True]`, `reassigned_and_pending[admin]`,
`last_interacted[admin]`, `daily_step_breakdown_…`, `get_task[admin-True]`,
`list_task_steps[admin-True]`, `money_boundary_role_derivation[admin-True]` — with
**zero** ADMIN ids green and **zero** MANAGER/WORKER rows disturbed. Before fix r2 only
three of the eight endpoints would have caught it.

This also settles a doubt I raised while probing: the daily-breakdown test uses a
sequential `for role_name in ("manager", "admin")` loop rather than a parametrization, so
a manager-side failure short-circuits before the admin assertion. The ADMIN-drop probe
shows the admin iteration does execute and does bite, so **row 15b is genuinely live** —
r1's note N6 about shared tests is cosmetic, not a coverage hole.

### Arithmetic — PASS, exact

Collection 1624 → **1629** = +5, matching the added parameters exactly: characterization
role 2→3 × group_by_upholstery 2 = **+2**; last-active 2→3 = **+1**; reassigned 1→2 =
**+1**; last-interacted 1→2 = **+1**. Nothing else added or removed. Passed count moves
1600 → 1605, the same +5.

## Step 3 — full suite: PASS

`PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`, containers `app-postgres-1` /
`app-redis-1` healthy (up 43 h): **1605 passed / 23 failed / 1 deselected** of 1629
collected, 55 s. **Zero connection noise** — no `ConnectionRefused`, `OperationalError`
or redis `ConnectionError` lines anywhere in the log — so this run is admissible
evidence, not a sandbox artifact. The 23-item failure set is **byte-identical** to the
recorded baseline: the fix introduced no regression and, as expected, resolved none of
the pre-existing failures.

## Archgraph — zero delta, confirmed

Read-only `archgraph_status`: 116 nodes / 157 edges, revision `b0702c3c…`, 0 stale, 244
pending, permissionMode `review` — unchanged from r1 and from the fixer's record.
Trivially correct here: the fix touched only test files, so no architecture could have
moved. Nothing written, no review item adjudicated, no discrepancy filed.

## Findings

None. One new note:

### N7 — note (cosmetic, carry-forward). Two test names under-describe their coverage

`test_reassigned_and_pending_step_payloads_keep_money_for_manager_and_redact_worker`
(`test_reassigned_steps_integration.py:262`) and
`test_last_interacted_steps_keep_money_for_manager`
(`test_worker_stats_endpoint_split_integration.py:261`) both now cover ADMIN, and their
local variables still read `manager_reassigned` / `manager_pending`. This matters mildly
because opacity about which roles were covered is exactly what produced S1 — a reader
scanning test names would conclude ADMIN is untested. **Correction:** rename to
`…_for_money_audience_roles_and_redact_worker` and
`…_keep_money_for_money_audience_roles` on the next touch of these files. Not a blocker;
does not justify a cycle of its own.

## Carry-forward dispositions

| Note | Origin | Destination |
|---|---|---|
| N1 — live frontend handoff doc publishes `total_cost_minor` for the worker reassigned-steps page | r1 | phase 9 docs/drift batch + coordinator note to the frontend team |
| N2 — money-audience boundary stated nowhere in the graph | r1 | phase 9 (candidate node/description) |
| N3, N4, N6 — id reconstruction, whitespace churn, rows 19/22 sharing one test | r1, declined in fix r2 | closed as declined; N6 additionally settled by the ADMIN-drop probe |
| N5 — tracker Actor column overwritten | r1 | absorbed — fix r2 preserved the reviewer stamp and appended its own |
| N7 — test names under-describe role coverage | r2 | next touch of the two files |
| Lessons P-G / P-H | r1, folded by coordinator | master plan §9 |

Nothing on this list blocks phase 2.

## Lessons for the plans

1. **A criteria row is met by a test that can fail for that row's reason.** S1 was
   fixable by adding five parameters, but what made the fix *worth* reviewing was the
   ADMIN-drop probe showing those parameters are the only witnesses to an admin-specific
   regression. Worth generalizing: when a criteria table has rows whose expected outcome
   equals a neighbour's, the plan should name the mutation that separates them — here,
   "removing ADMIN from the allow-list must redden every ADMIN row" — so the rows cannot
   be dismissed as redundant during implementation. This is charter rule 11's
   named-mutation discipline applied to *retention* rows rather than guard rows.
2. **Test names are coverage documentation.** S1 arose partly because coverage was
   invisible from the outside; N7 shows the fix re-created that opacity at a smaller
   scale. A phase whose criteria are role- or audience-parametrized should say that test
   names must name the audience, not one example member of it.
3. **A fix cycle that changes only tests still needs its own probes.** Fix r2 ran none,
   which is defensible for a test-only change — but it meant the question "do the new
   rows bite?" reached the reviewer unanswered, and answering it was the substantive work
   of this round. Worth a standing line in fix prompts: rows added to satisfy a coverage
   finding are themselves mutation-tested by the fixer.

## Full write perimeter

- **Documents written:** three — the Reviewer r2 entry in
  `plans/phase_1_worker_money_redaction.md` (appended below the Fixer r2 entry, nothing
  above it altered), the phase-1 tracker row in `master_plan.md` (that row only, State →
  `APPROVED`, existing actor stamps preserved and mine appended, verdict appended to the
  Note), and this handoff.
- **Code changed:** none.
- **Tests run:** one full non-e2e suite at the fix HEAD, one collection-only run, two
  control runs (15 and 30 ids) and five mutation runs. All either read-only against the
  primary tree or inside the disposable worktree.
- **Mutation-probe declaration (round 2):** every probe ran in a throwaway `git worktree`
  at `ed99e7e` (`probe_r2`); the **primary working tree was never modified** — clean at
  `bb7de26` before and after. Files mutated and reverted inside the probe worktree, each
  sha256 byte-identical afterwards: `domain/tasks/serializers.py` (ADMIN-drop),
  `services/queries/working_sections/steps_list_payload.py` (M4),
  `services/queries/working_sections/step_record_payload.py` (M5 + blanket-`False`),
  `services/queries/worker_stats/get_worker_daily_step_breakdown.py` (site-5
  blanket-`False`). Probe worktree `git status` verified clean before removal; worktree
  removed and `git worktree prune` run; `git worktree list` shows only the primary.
- **Database:** no committed rows — `db_session` rolls back; the configured DB is left as
  found, at head. No migrations run.
- **Tool-recorded state:** none. One read-only `archgraph_status`; no delta applied, no
  review item adjudicated.

## Verdict

**APPROVED.** Phase 1 meets its acceptance criteria in full — 26 of 26 rows, each with a
test that has been shown capable of failing for that row's own reason — closes the
worker money exposure on the complete eight-endpoint census, fails closed by
construction, and introduces no regression. The phase is ready for its approval gate
commit, and phase 2 may begin.
