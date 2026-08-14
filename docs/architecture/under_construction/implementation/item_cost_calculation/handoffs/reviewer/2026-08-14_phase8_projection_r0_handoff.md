---
plan: phase 8 (status & results — status query, result handler, §8B emissions)
role: reviewer (projection)
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-14
actor: Claude Opus 5 (projectionist)
---

# Phase 8 projection r0 — amendment ledger

## Opening (owner-readable)

I did the implementer's first hour of phase 8 on paper, against the code as it
actually stands today. The plan is broadly sound — the schema it needs is already
in the database, no migration is required, and the hard parts (the money boundary,
the replay contract) are well specified. But the plan was written before four
phases shipped, and it now asks for a few things the code cannot do as written:
one of the two "hooks" it wants to add sits in a function that has no database
handle, the last piece of work in the phase (an item's lifetime economics view)
has no test criteria at all, and one instruction, followed literally, would make
the result event silently skipped for any task whose completion notifies nobody.
**Two things need you personally** — both about what a number on screen should
say. Everything else routes to the coordinator as plan amendments before the
implementer prompt is compiled.

## ⚠ OWNER DECISIONS REQUIRED (2)

### Card 1 — Should the live budget screen show "result" figures before the task is closed?

**Question:** When a task has reached READY (work finished) but nobody has resolved
it yet, should the budget screen show the stored result figures, or hide them until
the task is formally closed?

**Story:** A chair finishes on the shop floor on Monday; the system marks the task
READY that afternoon and stores the episode's economics — 214 minutes used against
180 allowed. The manager who resolves tasks is away until Thursday. For those three
days the manager opening the task sees either the real overrun, or a screen that
says nothing has been computed yet — while the number sits in the database.

**Branches:**
- **Show it always** — the overrun is visible on Monday; the screen also carries
  which boundary it was computed at, so "final" is still distinguishable.
- **Hide it until closed** — the screen matches today's written spec, but the
  figures a manager most needs on Monday are invisible for three days.

**Recommendation:** show it always, labelled with its boundary — the whole point of
the round-6 change was that READY, not resolution, is when the work actually ended.

**On silence:** the gate holds; phase 8 is not implemented on a guess.

**Trace:** intention §8A.6 (pre-round-6 sentence) vs §8B; plan task 2; ledger L10.

### Card 2 — What status should the screen show right after a price is deleted, in a workspace that isn't configured yet?

**Question:** After deleting an item's price, should the response say "unpriced", or
say the more basic thing that is also wrong (e.g. "no cost group set up")?

**Story:** A manager is trialling the system in a workspace where no cost group has
been created yet. They type a price on a chair, then delete it. Today the screen
answers "item unpriced" — true, but it hides that nothing in this workspace can be
costed at all. Everywhere else in the product, the missing-setup reason is shown
first, precisely so the manager fixes the setup rather than re-typing prices.

**Branches:**
- **Re-resolve the real reason** — one rule everywhere; in a configured workspace it
  still says "unpriced", so nothing changes for normal use.
- **Keep the literal "unpriced"** — matches one sentence in the spec, and stays a
  second place where status is decided by hand.

**Recommendation:** re-resolve the real reason — a status vocabulary with two
producers drifts, and this is the only surviving hand-written status in the domain.

**On silence:** the gate holds; the line stays as shipped and is re-filed for phase 9.

**Trace:** intention §11A.4 ordering vs §11A.5(d); `delete_item_valuation.py:44`;
phase-5 review N2; ledger L18.

---

## Decision ledger

Severity: **B** = blocking (implementer prompt must not compile until routed),
**S** = should-fix, **N** = note. Classification per plan-projection doctrine:
*plan gap* → amendment; *intention gap* → upstream/owner; *free choice* → explicit
delegation.

| # | Sev | Decision point | Class | Section amended | Routing |
|---|---|---|---|---|---|
| L1 | B | C7 enumerates "all eleven values"; the shipped enum has twelve, and `ok`/`infeasible` have a different producer than the other ten | plan gap | plan C7 + task 2 | re-enumerate against the shipped enum, one parametrize id per member, expression differing per row (P-V 3rd ext) |
| L2 | B | Task 5 (lifetime read model) has **no acceptance criterion** — C1–C10 cover none of it | plan gap | plan, new C11 | add an enumerated criterion incl. its route |
| L3 | B | Task 5 is undecidable: which evaluations, summed or listed, ordering, role gate, empty-result behaviour | plan gap | plan task 5 | pin the five axes before the prompt compiles |
| L4 | B | `maybe_reopen_task_to_working` is **sync and session-less**; the §8B.1 hook is not implementable without changing its signature and its callers | plan gap | plan files list + §9 P-E fence | amend the fence and the file list; add a criterion on the awaited call site |
| L5 | B | "One `create_instant_task` line each, inside the existing side-effect block" lands inside `if target_user_ids:` in all three terminal commands | plan gap | plan task 3 + C10 | state "outside the notification conditional"; C10 fixture must have **zero** notification targets |
| L6 | B | Upsert `DO UPDATE SET <derived columns>` is not enumerated, and the repo has **no `on_conflict_do_update` precedent** | plan gap | plan task 3 | enumerate the SET column list; name the dialect import and the conflict target |
| L7 | B | Adding budget-status to `_ROUTES` breaks the existing all-routes-reject-worker test; cheapest green is to gate the route ADMIN/MANAGER — silently violating §11A.1 | plan gap | plan C10 (or new C12) | split the route table; completeness arbiter over the union; P-G retention mutation |
| L8 | S | C1 names two filter call sites; phase 8 ships **three** (the worker service is the third) | plan gap | plan C1 | third row + third named mutation |
| L9 | S | §8B.2 is total over eight task states; C6b enumerates only PENDING among the three refusing ones | plan gap | plan C6b | += ASSIGNED, STALLED rows |
| L10 | S | "Result block when closed + present" predates round 6 — a row now exists from the first READY entry | intention gap | intention §8A.6 | **owner card 1** |
| L11 | S | Which result-block keys the **worker** variant carries is unstated; C9's "zero monetary keys" needs the allowed key set to be decidable | plan gap | plan task 2 + C9 | enumerate the worker payload's key set |
| L12 | S | Phase-7 N6 says "two loaders"; there are **three** today, and the status query would be a fourth | plan gap | plan Notes + a criterion | choose the pin's shape; any structural property states its exclusions and a non-vacuity row |
| L13 | S | C9's "test over both serializer outputs" never enumerates either family | plan gap | plan C9 | quantify over the enumerated module surface (P-J 2nd ext) |
| L14 | S | C2's "ended-shift" bucket is not a step state — it is `PAUSED` + `transition_reason = SHIFT_ENDED` | plan gap | plan C2 | name the construction (P-Q 4th ext) |
| L15 | S | C5's whole-row-identity variant is non-vacuous only if `computed_at` is observed to advance | plan gap | plan C5 | state the observation (P-J 3rd ext) |
| L16 | S | R2-N2 hardening lands in a **phase-7 test file** that is not in phase 8's file list | plan gap | plan files list | name the file so the perimeter check does not read it as out-of-fence |
| L17 | S | 4B N3/N4 target a file phase 8 does not rework — the forward note has no landing site | plan gap | plan Notes | fold N4 into phase 8 with a declared one-file extension; defer N3 to phase 9 |
| L18 | S | `delete_item_valuation` hardcodes a status the §11A.4 ordering contradicts | intention gap | intention §11A.5(d) | **owner card 2** |
| L19 | S | Three shipped `human_confirmed` graph nodes become false when this phase lands | plan gap | plan Notes (archgraph) | delta includes three description edits, filed not worked around |
| L20 | N | Whether the worker service re-derives or wraps the manager service is unstated | free choice | plan task 2 | delegate explicitly; recommendation below |
| L21 | N | The money-audience predicate for route service selection already exists in code | free choice | plan task 2 | delegate with a reuse recommendation |
| L22 | N | Router-only criteria (role split, service selection, no `response_model`) name no harness | plan gap | plan C9/C10 | name the existing `_client` recipe (P-R) |
| L23 | N | Re-emit mechanics: no TaskStep lookup needed; one new `Task` SELECT; the branch is also gated on `credited_user_id` | — | plan task 4 | record as implementation-determining fact |
| L24 | N | A ready-making transition produces **two** result events by design | — | plan C6/C10 | counts must be exact per scenario, never "at least one" |
| L25 | N | Environment re-verified; no migration needed | — | — | recorded below |

---

## Findings in detail

### L1 (B) — C7's vocabulary, and the two meanings of `OK`

`plans/phase_8_status_results.md:150` — "**C7 — status vocabulary (§11A.4), all
eleven values enumerated**". The shipped enum
(`domain/item_economics/enums.py:19-31`) has **twelve** members;
`ITEM_MISSING_MAJOR_CATEGORY` is absent from C7's list. This is D23, forwarded from
the phase-7 projection and explicitly owed before this projection — it is not yet
executed in the plan text.

Second, deeper defect in the same criterion: C7 reads as if one producer emits all
twelve. It does not.

- `resolve_item_economics_status(...)` (`configuration.py:129-169`) terminates at
  `NOT_EVALUATED`. It can never return `OK` or `INFEASIBLE`.
- `resolve_economics_selection(...).status` returns `EconomicsStatusEnum.OK`
  (`configuration.py:122`) to mean **"configuration resolved"** — a completely
  different claim from the payload status `ok`, which per §11A.4 rule 1 means "a
  current committed evaluation exists and its allowance is positive".
- `ok` / `infeasible` are produced **only** by the committed-evaluation branch:
  evaluation present → `infeasible` if `allowed_worker_minutes <= 0` else `ok`,
  irrespective of live configuration (§11A.4 rule 1 / HC-1).

So the status query is a two-stage composition, and the dangerous failure is
leaking `selection.status is OK` into the payload for a task with no committed
evaluation — which renders as "ok" with null numerics. C7 must state, per row,
which producer the row exercises, and carry one row for exactly that hazard
(config fully resolved, no committed evaluation → `not_evaluated`, never `ok`).

**Amendment:** re-enumerate C7 over the twelve shipped members, one parametrize id
per member naming its §11A.4-as-amended-by-§7C.3 authority row (P-V 3rd ext: each
row's *expression* differs, not only its id), plus the composition row above and
the existing priority row.

### L2/L3 (B) — task 5 has no criteria and no decidable shape

`plans/phase_8_status_results.md:100-102` is the entire specification of the
lifetime read model, and `master_plan.md` §6.5 registers both the service
(`get_item_lifetime_economics.py`) and its route
(`GET /items/<item_client_id>/economics`). Criteria C1–C10 contain **no row that
touches either**. A whole task and a whole route would ship with zero arbiters —
and, because the route is also absent from the C13 completeness arbiter's
authoritative table, nothing would even notice it exists.

Undetermined by the artifacts (I could not write the test):

1. **Which evaluations.** "committed evaluations … across its tasks" — the whole
   superseded chain, or the current committed row per task? Summing the chain
   double-counts every re-commit. §11 (`intention.md:1715`) says "per-task committed
   evaluation" (singular); the plan says plural.
2. **Summed or listed.** §11 and §8B.4 both say "Σ episodes" / "read-time
   summation"; the plan says only "read model". If it sums, which figures, and does
   a task with an evaluation but no result row yet contribute zeros (forbidden by
   R-9) or drop out?
3. **Ordering** — unbounded per item, so the §6.5 pagination question applies (the
   evaluations read was pinned unpaginated because both sets are bounded per task;
   an item's episodes are not bounded).
4. **Role gate / money audience.** §6.5 says "everything ADMIN/MANAGER except
   budget-status", so this route carries money for managers only — but that makes
   it a money surface with no P-A/P-H row.
5. **`task_type_snapshot` / `return_source_snapshot`** typing is stated ("never live
   task fields") with no criterion, and that is exactly a silent-failure shape: a
   join to `tasks` reads correct today and diverges the first time a task type is
   corrected.

**Amendment:** pin all five in task 5 and add criterion C11 enumerating them,
including a mutation that replaces a snapshot read with the live task field.

### L4 (B) — the reopen hook has nowhere to land

`services/commands/tasks/_task_state_transitions.py:30-48`:

```python
def maybe_reopen_task_to_working(task: Task, *, now: datetime, updated_by_id: str) -> bool:
```

It is **synchronous** and receives **no session**. `create_instant_task` requires
`session` and `await` (`task_factory.py:46`). Its sibling
`maybe_evaluate_task_ready` (`:51`) is `async` and already takes `session` and
`workspace_id`, so §8B.1's hook 1 drops straight in; hook 2 does not exist without
a signature change.

Verified blast radius (grep, whole tree):
- one production caller — `services/commands/task_steps/add_task_steps.py:182`
  (`task_reopened = maybe_reopen_task_to_working(...)`, inside the command's
  transaction, result consumed at `:198`) → becomes `await`;
- two unit tests — `tests/unit/test_task_state_transitions.py:17` and `:30` → both
  call it synchronously and assert on `task.state`; both go red on the change.

The plan's "Files expected to change" lists `_task_state_transitions.py` but not
`add_task_steps.py` and not the unit-test file, and §9's **P-E** fence reads "no
phase modifies … except the four §8B emission touch points … Nothing else in the
execution path" — a call-site edit in `add_task_steps.py` is outside that fence as
literally worded.

**Amendment:** state the signature (`async def maybe_reopen_task_to_working(session,
task, *, workspace_id, now, updated_by_id)` or equivalent), add both files to the
list, and amend P-E to admit the call-site adaptation the hook forces. Add a
criterion that the reopen emit fires from the `add_task_steps` path (the only
production driver), with the named mutation "delete the emit at its definition site
in `_task_state_transitions.py`" — definition-vs-call-site per charter rule 11.

*(Alternative — put the emit at the call site — is rejected upstream: §8B.1 says
"inside the helper so every caller inherits". Recording it so nobody re-opens it.)*

### L5 (B) — the terminal emit inside the notification conditional

All three terminal commands share one shape. `resolve_task.py:74-101`:

```python
target_user_ids = list(await resolve_task_notification_targets(...))
if target_user_ids:
    item_label = await resolve_item_label_for_task(...)
    ...
    await create_instant_task(session=ctx.session, task_type=TaskType.CREATE_NOTIFICATIONS, ...)
```

Same at `fail_task.py:84-88` and `cancel_task.py:84-88`. The plan's "one
`create_instant_task` line each, inside the existing side-effect block / same
transaction" (`plans/phase_8_status_results.md:54-56`) names the only
`create_instant_task` in the file, which sits **inside** `if target_user_ids:`.
Following it literally makes the result event conditional on the task having
notification recipients — a task resolved by its only participant would never get a
final result row, and the straggler path (READY ∪ terminal) would only heal it if
somebody later touched a step.

Worse, the defect is invisible to C10 as written ("each enqueue exactly one result
task inside their transaction"): any realistic fixture has notification targets, so
the row passes with the emit in the wrong block — two sufficient causes, charter
rule 2's sole-predicate companion.

**Amendment:** task 3 says "inside `maybe_begin`, **after** the notification block,
never inside `if target_user_ids:`"; C10's three rows each use a fixture with **zero**
notification targets, and the criterion says so.

### L6 (B) — the upsert is under-specified and has no repo precedent

`plans/phase_8_status_results.md:92-94` — "upsert `INSERT … ON CONFLICT (task_id)
DO UPDATE SET <derived columns>`". Verified: `grep -rn "on_conflict_do_update"
beyo_manager/` returns **zero hits** — no repo pattern to copy, so the implementer
writes the first one.

The SET list is load-bearing and cannot be derived from "derived columns":

- **must be in it** — `evaluation_id` and `item_id` (§8A.3 resolves the current
  committed evaluation *at handler time*, so a commit landing after a close must
  re-point the existing row; §7B.3 pins `item_id` to `evaluation.item_id`),
  `actual_worker_seconds`, `actual_worker_minutes`, `consumed_cost_minor`,
  `variance_worker_minutes`, `variance_cost_minor`, `task_closed_at`,
  `task_state_snapshot`, `calculation_version` (A7), `computed_at`;
- **must not be** — `client_id` (PK, `IdentityMixin` default), `task_id` (the
  conflict key), `created_at`, and `workspace_id` (invariant per task; including it
  is harmless but should be a stated decision, not an accident).

Verified live against the database (see measurements): the conflict target is a
**UNIQUE CONSTRAINT** `uq_item_cost_results_task_id`, not a partial index, so both
`index_elements=["task_id"]` and `constraint="uq_item_cost_results_task_id"` are
valid; the plan should name one. Note that the ten SET columns are exactly §8A.4's
replay-identity set (as extended by §8B.2) plus `computed_at` — which is the
property C5 exists to prove, so the enumeration is free.

### L7 (B) — the router role table cannot absorb an all-roles route as-is

`tests/unit/routers/api_v1/test_item_economics_router.py` holds `_ROUTES` (21 rows,
`:12-43`) and three consumers:

- `:68-76` — parametrized over **every** row × {worker, seller}, asserting **403**;
- `:79-87` — every row × {admin, manager}, asserting 200;
- `:103-126` — the C13 completeness arbiter: `actual == expected` over the whole
  route surface, so **every** route must appear in `_ROUTES`.

Phase 8 adds `GET /tasks/<task_client_id>/budget-status`, which is all-roles with
role-split serialization (§6.5, §11A.1, card 4). Adding it to `_ROUTES` reddens the
worker/seller rejection rows; leaving it out reddens the completeness arbiter. The
cheapest way to green is to gate the route ADMIN/MANAGER — which silently reverses
card 4 and §11A.1, and no criterion in the plan would notice.

**Amendment:** the plan states the table split — `_MANAGER_ONLY_ROUTES` (rejection
rows) and `_ALL_ROLE_ROUTES` (budget-status; asserts 200 for all four roles) with
the completeness arbiter over the **union** — and carries P-G's retention mutation:
*removing WORKER from the budget-status allow-list must redden the worker row*, and
*adding budget-status to the manager-only table must redden the same row*.

### L8 (S) — the third filter call site

C1 (`:106-110`) names two mutation sites: `get_task_budget_status.py` and
`process_item_cost_result.py`. §8A.6 requires the literal `kind = 'committed' AND
superseded_at IS NULL AND is_deleted = false` in **every operational read**, and the
phase ships three: the manager query, the worker query, the handler. The worker
variant has no row and no mutation — and it is precisely the payload a defect would
be least visible in. (Precedent: three inline copies of this predicate already exist
— `create_item_cost_projection.py:32-33`, `commit_item_cost_evaluation.py:278-279`
and `:288-289` — so inline-literal is the established shape; extraction is not
proposed, since it would collapse the per-site mutations C1 depends on.)

### L9 (S) — the admission table is sampled, not enumerated

§8B.2 is explicitly "total over all eight `TaskStateEnum` values". C6b (`:138-148`)
carries: READY entry, reopen → `working`, re-entry, three terminal rows, and one
PENDING refusal. Admitted five ✓. Refused three: PENDING ✓, **ASSIGNED ✗, STALLED
✗**. Charter rule 2 — a sampled table over a *total* contract is the classic shape.
Add the two rows (both: replayed event, committed evaluation present, nothing
written, log emitted).

### L11 (S) — the worker payload's result block

Task 2 says the worker variant is "minutes/percent only", and C9 asserts "zero
monetary keys". But the status payload also carries the result block (§8A.6), whose
own columns include `consumed_cost_minor` and `variance_cost_minor` — money. The
plan never says which result-block keys the worker variant carries, so C9's key-set
assertion is not decidable: an implementer can satisfy "zero monetary keys" by
dropping the block entirely, or by keeping it and stripping two keys, and both read
as compliant. Enumerate the worker key set explicitly (P-H is a *structural*
criterion; it needs a declared set to be structural about).

### L12 (S) — the two-loader pin is a three-loader reality

Phase-7 N6 names `_load_preview_inputs` and `_load_live_inputs`. Verified by grep,
there are **three** loaders of the same configuration triple today:

| Loader | Site | Locking | Shape |
|---|---|---|---|
| `_load_preview_inputs` | `services/commands/item_economics/_common.py:172-216` | none | per-item; resolves selection + terms |
| `_load_live_inputs` | `services/commands/item_economics/commit_item_cost_evaluation.py:140-173` | `FOR SHARE` on basis + model | per-item; same resolver, same `today_utc()` |
| `get_economics_configuration_status` | `services/queries/item_economics/get_economics_configuration_status.py:13-36` | none | **per-category, workspace-wide** — deliberately different |

The status query would be a fourth. Two consequences the plan must settle:

1. A structural "no unmediated configuration loader" property (the natural P-J 2nd-ext
   shape) **fails on the config-status query on day one** unless it states its
   exclusions — and an exclusion list without a non-vacuity row (P-J 3rd ext) is a
   silent pass.
2. `_load_preview_inputs` lives under `services/commands/`. A query importing it
   crosses the command/query boundary; moving it to a shared home is a
   **shared-machinery scope exception**, so **P-Z binds** — before/after property
   tests in the same cycle.

Recommendation: the status query consumes `_load_preview_inputs` where it stands
(no move, no P-Z cost), and the pin is an **equality property row** — one fixture,
both loaders, assert the two selections are equal field-for-field — which reddens on
exactly the divergence N6 describes and costs no refactor.

### L13 (S) — C9's disjointness needs its two families enumerated

"the money-key sets of the step-payload family and the item-economics payload family
are disjoint (test over both serializer outputs)" — neither family is enumerated,
so a test constructing one member of each satisfies it (P-J 2nd ext: a property over
a module set must *quantify* over the set). Enumerate: the step family is
`serialize_step` (`domain/tasks/serializers.py:158`) plus the two shared builders of
§11A.2's census; the economics family is the public functions of
`domain/item_economics/serializers.py` (ten today, plus this phase's status
serializers). C9's named mutation is already correctly sited (definition site,
`domain/item_economics/serializers.py`).

### L14 (S) — C2's ended-shift bucket does not exist as a state

`ENDED_SHIFT` is **not** a `TaskStepStateEnum` member (deleted by migration
`2645b4327b17`; the graph carries this as `concept-ended-shift-collapse`). It is
derived: `bucket_for` (`domain/analytics/time_buckets.py:23-34`) returns the
ended-shift bucket for `PAUSED` **+** `transition_reason == SHIFT_ENDED`, and
`averaged_time.py:45` carries the SQL twin. A prescribed fixture written against a
nonexistent enum member cannot be built (P-Q 4th ext — the fixture is checked
against the engine semantics it will meet). C2 names the construction, and its
fourth bucket (marked-wrong) is `recorded_time_marked_wrong`, which lands in
`inaccurate_working_seconds` and never in `total_working_seconds`.

### L15 (S) — C5's whole-row variant

After `ON CONFLICT DO UPDATE`, `client_id` and `created_at` are preserved, so
`computed_at` is the **only** column that can differ between two runs. The "whole-row
identity assertion must fail" clause is therefore non-vacuous only if `computed_at`
is observed to advance between the two handler runs. State the observation (P-J 3rd
ext); otherwise a handler that stamps `computed_at` once produces a green
whole-row assertion and the criterion silently proves nothing.

### L16 (S) — R2-N2's landing site is a phase-7 file

`tests/integration/services/commands/item_economics/test_phase7_evaluations.py:175-183`:

```python
async def capture(events):
    dispatched.extend(events)
    async with database._session_factory() as verify_session:
        for event in events:
            if "evaluation_id" in event.extra:
                assert await verify_session.scalar(...) is not None
```

If no dispatched event carries `evaluation_id`, the loop body never runs and the
seam's whole point — the row is visible to a second session at dispatch time —
evaporates green. (Line 203's `count(...) == 1` is a *post-hoc* assertion on
`dispatched`; it does not make the inner check fire.) Hardening: count the checked
events and `assert checked == 1` after the loop. The file belongs to phase 7 and is
not in phase 8's "Files expected to change" — name it there, so the reviewer's
perimeter check reads it as intended work rather than an out-of-fence edit.

### L17 (S) — the 4B forward notes have no landing site in this phase

N3 and N4 target `get_economics_configuration_status.py` (`:38` and `:47` carry the
redundant `and not version.is_deleted`; `:53` is `evaluable = status.value == "ok"`).
Phase 8 does **not** rework that file — it is absent from the file list, and the note
says "simplify or keep knowingly **when reworking**". Left unrouted, the note dies.

Recommendation: fold **N4** into phase 8 with a declared one-file perimeter
extension (`status is EconomicsStatusEnum.OK`) — it is the exact brittleness the new
status query must not copy, and phase 8 is where the reader will be looking; defer
**N3** to phase 9's drift batch, which already carries code items (annotations,
`checkfirst`).

### L19 (S) — three shipped graph nodes go false

The plan's archgraph note describes the delta as additions only. Verified against the
live graph (166/239, all `human_confirmed`), three existing nodes are contradicted the
moment this phase lands:

- `infra-queue-analytics` — "**Only** PROCESS_STEP_TRANSITION routes here";
- `infra-analytics-worker` — "Its HANDLER_MAP binds PROCESS_STEP_TRANSITION";
- `analytics-process-step-transition` — enumerates the handler's four effects; the
  §8A.5 re-emit is a fifth.

Per the archgraph-discrepancy discipline these are recorded as description edits in
the phase delta, not silently left disagreeing with the code.

### L20/L21/L22 (N) — free choices, made explicit

- **L20 — worker service shape.** §11A.3 mandates a separate *serializer*; §6.5
  registers a separate *service*. Whether `get_task_budget_status_worker` re-derives
  or wraps the manager service is a free choice — but if it wraps, C1's third filter
  site (L8) collapses into the manager query's, and the criterion must say so.
  Recommendation: independent service with its own literal filter (keeps three
  mutation sites, keeps the money boundary structural).
- **L21 — the money-audience predicate.** `include_monetary_step_fields(role_name)`
  (`domain/tasks/serializers.py:150-155`) already encodes ADMIN ∪ MANAGER and is the
  phase-1 boundary. Recommendation: the route's service selection reuses it rather
  than writing a second literal role set — one audience, one definition.
- **L22 — harnesses (P-R).** All three router-level obligations are decidable with
  the existing recipe: `test_item_economics_router.py::_client` monkeypatches
  `run_service` and captures `(command, ctx)`, so "the route selected the worker
  service" is `calls[0][0] is get_task_budget_status_worker`; P-H's structural
  criterion is `route.response_model is None` over `item_economics.router.routes`.
  Verified: no route in that module declares a `response_model` today, so the
  criterion starts green and can only be broken by a regression — which is exactly
  its job. Name both in the plan.

### L23/L24 (N) — re-emit mechanics

- `StepTransitionPayload` (`domain/execution/payloads/step_transition.py`) already
  carries `task_id` (and `step_task_id`), so the re-emit needs **no** `TaskStep`
  lookup — only one new `Task` SELECT for the READY ∪ terminal guard, placed after
  `_recompute_step_time_totals` (`process_step_transition.py:73`) and before the
  handler's `await session.commit()` (`:121`), which keeps it atomic with the step
  totals (`decision-transactional-outbox`).
- The branch is additionally gated on `payload.credited_user_id` (`:63`) and on
  `closing_state in TIME_BEARING_STATES` = `{WORKING, PAUSED}`. A settlement with no
  credited user never recomputes time and therefore never re-emits — intended, but
  C6's fixture must credit a user or the row cannot fire.
- **Double emission:** a step transition that drives the task to READY produces two
  result events — the READY-entry hook (request transaction) and the straggler
  re-emit (analytics handler, once the task reads READY). Harmless under
  recompute-and-SET, but C6/C10 must assert exact counts per scenario; "at least one"
  is the disjunction charter rule 2 forbids.

### L25 (N) — plan/citation reality checks

Everything the plan cites still resolves:

| Citation | Status |
|---|---|
| `process_step_transition.py` `_recompute_step_time_totals` "verified at `:161`" | ✔ still `:161` |
| `task_factory.py` `create_instant_task` `:46` | ✔ |
| `execution/db.py` `task_db_session` `:10` | ✔ |
| §8A.5's premise — `transition_step_state.py:150` guards only the **step** being terminal | ✔ exact line |
| §8B.1's "`maybe_evaluate_task_ready` is the only route into READY" | ✔ `task.state = TaskStateEnum.READY` occurs at exactly one site (`_task_state_transitions.py:92`) |
| `routers/README.md` | ✔ present |
| Registration test "per existing pattern" | ✔ `tests/unit/workers/test_shopify_worker.py`; no `test_analytics_worker.py` exists yet, and no test asserts the analytics `HANDLER_MAP` is a singleton — adding the second handler breaks nothing |
| "phase 8 SHOULD need no migration" | ✔ confirmed against the live schema |

---

## Live measurements (this session)

- **Head:** `alembic current` → `be9dfe42a035 (head)` — unchanged.
- **Schema:** `item_cost_results` exists at head with `task_state_snapshot
  task_state_enum NOT NULL`, `task_closed_at` nullable, `calculation_version` NOT
  NULL, `uq_item_cost_results_task_id` as a **UNIQUE CONSTRAINT**, and
  `ck_item_cost_results_actual_worker_seconds_non_negative`. **No migration is
  required by phase 8.**
- **Economics tables:** all nine at **0 rows** (before and after this session — this
  session performed no writes).
- **Collection:** `PYTHONPATH=. pytest --collect-only -q -m 'not e2e'` →
  **2099/2100 collected (1 deselected)** in 1.57s — reconciles exactly with §10's
  `2076 / 23 / 1 = 2099 selected` baseline.
- **Payload-key greps (Projection practice, review-r1 lesson 2):** `percent_consumed`,
  `remaining_worker_minutes`, `actual_worker_minutes`, `actual_worker_seconds`,
  `item_binding`, `consumed_cost_minor`, `variance_worker_minutes` across
  `beyo_manager/` and `tests/` → **zero payload-key hits** (only calculator parameter
  name strings in `calculator.py`). No existing consumer breaks; the C9 disjointness
  test starts from a clean slate.
- **`on_conflict_do_update` precedent:** zero occurrences repo-wide.
- **Graph:** `archgraph_status` → 166 nodes / 239 edges, **0 pending, 0 stale**,
  revision `b0f9127d0a0b…`, permission mode `review`, no diagnostics — matches the
  prompt exactly.

## Write perimeter and probe declaration

- **Documents written (1):** this handoff —
  `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase8_projection_r0_handoff.md`.
- **Code written:** none. **Plans/intention/master plan edited:** none.
- **Mutation probes:** none created, none run — this is a paper projection; no test
  file, scratch file or fixture was authored anywhere in the tree.
- **Database:** read-only (`alembic current`; `SELECT count(*)` over the nine
  economics tables; `\d item_cost_results`). No writes, no residue; configured DB
  left at head.
- **Archgraph:** READ-ONLY — `archgraph_status` and one `archgraph_search_nodes`
  query. **Zero delta**, nothing adjudicated, revision unchanged at `b0f9127d…`.
- `git status` outside this handoff is expected to be clean.

## Exit gate

Verdict **AMENDMENTS_REQUIRED**: 7 blocking, 12 should-fix, 6 notes, 2 owner cards.
Per the charter, the implementer prompt compiles only after every ledger row is
routed (amendment applied, upstream change made, or delegation recorded) and the two
owner cards are answered. One line in the phase plan's Review log is the
coordinator's to write at consumption, not mine.
