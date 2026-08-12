---
plan: phase 1 (worker money redaction)
role: reviewer
session_doctrine: plan-reviewer (first review, full checklist)
round: 1
date: 2026-08-12
state: COMPLETE
verdict: CHANGES_REQUESTED
actor: Claude (plan-reviewer)
---

# Review handoff — phase 1, round 1

## Summary

The implementation is right. The worker money leak is closed on the complete
eight-endpoint census, fail-closed at the interface (keyword-only, no default), derived
uniformly through one allow-list helper with no hardcoded boolean anywhere — site 5
included — and it survives to the wire (no `response_model` re-adds the key). I
re-derived the census from the tree without trusting any recorded census and got the
same eight endpoints and the same role sets. I re-ran the mutation battery
independently in a disposable worktree: **8/8 bite**, and the round-5 pairing holds —
M4 reddens rows 11 *and* 19, M5 reddens rows 14 *and* 22. Probe P-R1 is settled: the
pre-change and post-change failure sets are **byte-identical**, so phase 1 introduced
zero regressions.

`CHANGES_REQUESTED` rests on what the phase *proves*, not on what it does. Five of the
26 enumerated criteria rows — every ADMIN money-present row except two — have no
asserting test, so the plan's post-round-5 enumeration is satisfied 21/26 (19 of 24
endpoint × role cells). And the recorded suite baseline, which master plan §10 makes
later phases inherit, says 22 pre-existing failures where the verified number is 23,
on top of a pre-change baseline measured in a sandbox with the database denied. Both
are cheap to fix and neither indicates a defect in the redaction.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Nothing in this review needs an owner answer — the two open items are a test
parametrization and a record correction, both the coordinator's to route.

## Findings

### S1 — should-fix. Five acceptance-criteria rows have no asserting test

**Authority:** charter rule 1 (criteria met by automated tests) and rule 2 (enumerate,
never sample); the plan's own criteria table as corrected by intention §11A.2 round-5.

Rows **9, 12, 17, 20, 23** — ADMIN / money present on
`GET /working-sections/{id}/steps`, `GET /working-sections/steps/user-last-active`,
`GET /task-step-acknowledgments/reassigned-steps`,
`GET /task-step-acknowledgments/pending` and
`GET /worker-stats/last-interacted-steps` — are unexercised. ADMIN appears in exactly
three places in the phase: `test_worker_money_redaction.py:23`, `:46` (rows 1, 5) and
`test_get_worker_daily_step_breakdown.py:169` (row 15b). The four role-parametrized
payload tests carry `["worker", "manager"]` only, and
`test_worker_stats_endpoint_split_integration.py:31` (`_ctx`) hardcodes
`role_name="manager"` with no override, so row 23 is unreachable as written.

Verified coverage: **19 of 24 (endpoint × admitted role) cells; 21 of 26 rows.**

**Exact correction clause:** add `"admin"` to the role parametrization at
`tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py:228`,
at
`tests/integration/services/queries/working_sections/test_get_user_last_active_step_record_integration.py:154`,
and to
`tests/integration/services/queries/task_step_acknowledgments/test_reassigned_steps_integration.py:262`
(covering both the reassigned assertion at `:267` and the pending assertion at `:276`);
and give `tests/integration/services/queries/worker_stats/test_worker_stats_endpoint_split_integration.py::_ctx`
a `role_name` parameter so `test_last_interacted_steps_keep_money_for_manager` (`:256`)
also runs under ADMIN. Every added row asserts `== 4321` — equality with the seeded
value, never key presence (projection D4).

**Coordinator's alternative:** if the ADMIN rows are judged redundant because one
shared helper serves ADMIN and MANAGER through identical code, then amend the plan's
criteria table to say so and record why. What must not stand is five enumerated
criteria left silently unmet — that is the failure mode charter rule 2 exists to
prevent.

### S2 — should-fix. The recorded suite baseline is wrong, and later phases inherit it

**Authority:** master plan §10 ("the phase-1 implementer records the baseline … and
later phases inherit it from there").

The implementer entry records a pre-change baseline of 1092 passed / 473 failed / 38
errors — taken in a sandbox with PostgreSQL and Redis denied, i.e. not a measurement —
and a post-change run of "1601 passed, 22 failed". Re-run with healthy containers
(`make dev-up` state, containers up 42 h):

| Commit | Result |
|---|---|
| `545e504` (pre-change, disposable worktree) | 1578 passed / **23 failed** / 1 deselected |
| `4416570` (checkpoint) | 1600 passed / **23 failed** / 1 deselected |

The two failure sets are **byte-identical** (`comm` on sorted node-id lists: empty in
both directions). So: zero regressions, 22 tests added and all passing, and the
pre-existing failure count is **23, not 22**. The implementer's category list also
omits one of them —
`tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`.

**Exact correction clause:** correct the implementer Review-log entry (or append a
correction line) to carry the verified pair above and the full 23-item list, so phase 2
compares against a number that was actually measured. The verified list is in the
reviewer Review-log entry.

### N1 — note. A live frontend contract doc now misstates the worker payload

`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
describes a **worker-app** page (`app_scope="worker"`, allowed roles admin/manager/
worker) and publishes `total_cost_minor` as an always-present nullable int (`:393`,
sample payload `:166`). A WORKER now receives no such key from that endpoint. The
redaction is owner-ordered and correct; the published contract is what is now false.
**Correction:** route to phase 9's docs/drift batch, and add a coordinator note for the
frontend team beside the existing `LastActiveStepCard.tsx` smoke note.

### N2 — note. The money-audience boundary is stated nowhere in the graph

The implementer's explicit zero delta is **confirmed correct** (evidence under P-R3/
archgraph below). Separately, the ADMIN/MANAGER-only step-money audience is now a real
architectural policy that no node carries. **Correction:** carry forward to phase 9 as
a candidate node/description — not a phase-1 fix, and not a discrepancy to file.

### N3 — note. Cross-module id reconstruction in the new test

`tests/integration/services/queries/tasks/test_worker_money_redaction.py:32`, `:48`
rebuild the seeded task's `client_id` as
`f"tsk_{workspace.client_id.removeprefix('ws_')}"` because the imported `_seed_step`
returns no task. Correct today; fails loudly, not silently, if that helper's id scheme
changes. **Correction:** optional — return the task from `_seed_step`, or query it.

### N4 — note. Gratuitous whitespace churn in two pre-existing test files

A stray blank line inside an unrelated test at
`test_get_worker_daily_step_breakdown.py:136-137`; at
`test_reassigned_steps_integration.py:250` a blank line removed and the new test
separated by one blank line instead of two. In perimeter, no behavioral effect.
**Correction:** optional tidy on next touch.

### N5 — note. The tracker actor stamp was overwritten

At `4416570` the phase-1 row read `IMPLEMENTED | Codex`; the coordinator's consumption
commit `d457d84` rewrote the actor to `coordinator`, so the row no longer records who
implemented the phase — and this review's own gate check (which expects "actor Codex")
mismatched on it. **Correction:** process note — keep the producing actor in the Actor
column and put consumption detail in the Note column.

### N6 — note. Rows 19 and 22 share one test function

Both round-5 worker rows are asserted inside
`test_reassigned_steps_integration.py::test_reassigned_and_pending_step_payloads_keep_money_for_manager_and_redact_worker`.
M4 and M5 each redden it (verified), and row 19 has a second independent witness in the
pre-existing pagination characterization, so detection is intact — a single failure
report just does not say which endpoint regressed. **Correction:** optional split.

## Probe results

### P-R1 — baseline validity — **RESOLVED, claim upheld, count corrected**

Ran the suite at `545e504` in a disposable `git worktree` and at the checkpoint, with
healthy containers. Failure sets byte-identical (23 = 23, empty symmetric difference),
so no failure is attributable to this phase — the implementer's post-hoc claim was
correct. The count is 23, not 22, and one failure was uncategorized (see S2). The two
that most deserved scrutiny —
`tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
(a worker-stats payload-shape test) and the item/upholstery router tests — are present
at the pre-change commit, so neither is phase-1 fallout.

### P-R2 — criteria mapping — **FAIL (S1)**

Every row mapped to its asserting test on the pinned harness. All 21 covered rows use
query-service-level integration with a hand-built
`ServiceContext(identity={"role_name": …})`, a real `TaskStep` ORM instance seeded via
`flush()` on the rolled-back `db_session`, present rows asserting `== 4321` and absent
rows asserting `key ∉ dict`. **No row is satisfied by the router idiom** — no stubbed
`run_service` appears anywhere in the phase's tests, so the harness pin holds. Rows 16
and 25 are unit-level exactly as the plan allows (row 25 against the derivation helper,
covering `""` and `"unknown"`). Five rows have no test: S1.

### P-R3 — mutations — **PASS, 8/8, independently re-run**

The committed tree contains no probe remnant (the diff is the evidence; probe worktree
`git status` clean). Battery re-applied at `4416570` in a throwaway worktree, one
mutation at a time, each reverted and sha256-verified:

| Mutation | Site | Result |
|---|---|---|
| M1 default `include_monetary=True` | `serializers.py` definition | RED (row 16) |
| M2 hardcode `True` | `tasks.py` call site | RED (rows 3, 4) |
| M3 hardcode `True` | `list_task_steps.py` call site | RED (rows 7, 8) |
| M4 hardcode `True` | `build_steps_list_payload` derivation | RED — row 11 **and** row 19, the latter via two independent tests |
| M5 hardcode `True` | `build_step_record_payload` derivation | RED — row 14 **and** row 22 |
| M6 allow-list → deny-list | derivation helper | RED (row 25) |
| blanket `False` | site 5 derivation | RED (rows 15, 15b) |
| blanket `False` | `build_step_record_payload` derivation | RED (rows 23/24 witness) |

Control run before mutating: 42 tests, all green.

### P-R4 — characterization authority — **PASS**

`_STEP_KEYS` still contains `total_cost_minor`
(`test_list_working_section_steps_payload_characterization.py:48`) — the published key
set was **role-conditioned, not edited**: manager asserts `set(item) == _STEP_KEYS` plus
`item["total_cost_minor"] == 4321`, worker asserts `_STEP_KEYS - {"total_cost_minor"}`
plus `key ∉ dict`. The ended-shift test shows exactly the one-token keyword addition
(`serialize_step(step, include_monetary=True)`) with no assertion changed. The key-set
change is recorded in the implementer Review-log entry. One enumeration gap belongs to
the *plan*, not the implementer: projection D8 named two existing tests that would
break; three did — `test_reassigned_steps_integration.py:245` also asserted set
equality including `total_cost_minor` under a worker context (see Lessons).

### P-R5 — fixture sole-predicate — **PASS**

All five seed helpers plus the unit stub seed `total_cost_minor=4321`
(`test_list_working_section_steps_payload_characterization.py:172`,
`test_reassigned_steps_integration.py:52`,
`test_get_user_last_active_step_record_integration.py:99`,
`test_get_worker_daily_step_breakdown.py:83`,
`test_worker_stats_endpoint_split_integration.py:82`,
`tests/unit/test_task_serializers.py:63`), so redaction is the only possible cause of
absence. No fixture carries two sufficient causes. No row can pass vacuously — each
indexes into a payload that must exist first (`IndexError`/`KeyError` otherwise), and
the mutation battery empirically proves every one is live.

## Scope-fence verification — PASS

- `serialize_item` untouched; item money persists until phase 6 per owner card 1 → R5-2.
- The three round-5 endpoint query services untouched — they inherit behavior from the
  builders, exactly as design (a) intended. An edit to any would have been out of
  perimeter; none occurred.
- Serialization not relocated to routers: all changes sit in the query layer, per master
  plan contract-gap 2.
- ADMIN/MANAGER money retained on both worker-stats endpoints, proven by rows 15/15b/24
  and by the two blanket-`False` probes.
- **Perimeter exact:** `git diff 545e504..4416570` = the 14 declared code/test files +
  this phase plan + the master plan. Nothing outside. Review-log edit append-only;
  master-plan edit touched only the phase-1 row.

## Structural verification the harness cannot reach

The plan forbids router-level tests for the criteria rows (correctly — under the stubbed
`run_service` idiom, M2–M5 never bite). That leaves one thing no criterion can observe:
whether the HTTP boundary re-adds the key. Verified by reading rather than by test —
none of the four routers declares a `response_model`, and `build_ok`
(`routers/http/response.py:11`) wraps the dict verbatim into a `JSONResponse`, so no
schema coercion reinstates `total_cost_minor: null`. Also verified: no production code
reads the key (the only other references in `beyo_manager/` are the ORM column and the
analytics writers), so redaction cannot raise downstream; and `ServiceContext.role_name`
returns `""` when the claim is absent (`services/context.py:40-41`), which the
allow-list turns into False — fail-closed for any non-HTTP caller.

## Architecture graph — zero delta CONFIRMED

Read-only: `archgraph_status`, `archgraph_search_nodes` (×2), `archgraph_get_node`
(`table-task-step`). State unchanged from the implementer's record — 116 nodes / 157
edges, revision `b0702c3c…`, 0 stale, 244 pending, permissionMode `review` — which
independently confirms nothing was written. The judgment holds: no node exists for
`serialize_step` or for seven of the eight endpoints;
`endpoint-worker-daily-step-breakdown` describes the route without mentioning money or
per-role visibility; `table-task-step` describes `total_cost_minor` as a column of the
step's own analytics rollup, which this phase did not change. Nothing in the graph
became false. No discrepancy filed. Carry-forward N2 records the boundary that the
graph does not yet state.

## Lessons for the plans (coordinator folds these upstream)

1. **Enumerating a matrix does not make an implementer walk it.** The plan listed all 24
   cells after the round-5 correction and the implementation covered 19 — every gap on
   the ADMIN side, where the expected outcome equals MANAGER's. When a criteria table
   has rows whose expected outcome is identical to a neighbour's, name them as
   *separately required* or collapse them explicitly; a row that looks redundant is the
   row that gets sampled.
2. **Projection D8's enumeration was one short.** Three pre-existing tests broke under
   the redaction, not two: `test_reassigned_steps_integration.py:245` asserted set
   equality including `total_cost_minor` under a worker context. The class of miss is
   the same as D1's — the projection enumerated tests that call the changed *symbol*,
   not tests that assert the changed *payload*. Future projections should grep the
   affected payload key across tests, not just the function name.
3. **A baseline measured in a broken environment must not be recorded as a baseline.**
   Master plan §10 makes phase 1's number inheritable, so a sandbox artifact propagates
   for eight phases. Worth a standing rule: if the environment cannot reach the DB, the
   baseline step *fails* rather than records.
4. **The harness pin needs a companion structural check.** Pinning criteria to the query
   layer (right call) leaves the HTTP boundary unproven by construction. Phases that
   redact or reshape a payload should carry a one-line structural criterion — "no
   `response_model` on the affected routes" — so the next reviewer does not have to
   discover the gap by intuition.
5. **A tracker row's Actor column is provenance.** The coordinator's consumption
   overwrote the implementing actor, and the review prompt's own gate check then
   mismatched the tracker it was written against.

## Full write perimeter

- **Documents written:** three — the Review log entry in
  `plans/phase_1_worker_money_redaction.md` (appended, nothing above it altered), the
  phase-1 tracker row in `master_plan.md` (that row only), and this handoff.
- **Not written by this session, but modified in the tree:**
  `prompts/reviewer/2026-08-12_phase1_review_r1.md` carries a mid-session owner edit
  (an elevated-permissions execution note added after the session began). Flagged here
  so the next perimeter reconstruction does not attribute it to the reviewer.
- **Code changed:** none.
- **Tests run:** two full non-e2e suites (`545e504`, `4416570`), one 42-test control
  run, and ~15 targeted runs during the mutation battery. All in disposable worktrees or
  read-only against the primary tree. **Environment evidence for the prompt's
  elevated-permissions constraint:** both full runs reached the real services — zero
  connection-refused / `OperationalError` / redis `ConnectionError` lines in either log,
  1578 and 1600 passing including the whole integration tier, against
  `app-postgres-1` (`127.0.0.1:5433`) and `app-redis-1` (`127.0.0.1:6380`), both
  healthy. No sandboxed run was used as evidence anywhere in this review.
- **Mutation-probe declaration:** every probe ran in a throwaway `git worktree` at
  `4416570` (`probe_head`); a second worktree at `545e504` served the P-R1 baseline. The
  primary working tree was **never modified** — clean at `d457d84` before and after.
  Files mutated and reverted inside the probe worktree, each sha256 byte-identical
  afterwards: `domain/tasks/serializers.py`, `services/queries/tasks/tasks.py`,
  `services/queries/tasks/list_task_steps.py`,
  `services/queries/working_sections/steps_list_payload.py`,
  `services/queries/working_sections/step_record_payload.py`,
  `services/queries/worker_stats/get_worker_daily_step_breakdown.py`. Both worktrees
  removed and `git worktree prune` run; `git worktree list` shows only the primary.
- **Database:** no committed rows — the suite's `db_session` fixture rolls back; the
  configured DB is left as found, at head. No migrations run.
- **Tool-recorded state:** none. Archgraph calls were read-only; no delta applied, no
  review item adjudicated.

## Verdict

**CHANGES_REQUESTED** — for S1 and S2 only. The redaction itself is approved on the
merits: correct, fail-closed, complete over the eight-endpoint census, mutation-proven,
regression-free, and inside its declared perimeter. A fix cycle that adds the five ADMIN
rows and corrects the baseline record should re-review as a narrow delta — the settled
ground is listed under "Verified correct" in the Review log so the next round need not
re-derive it.
