# SUMMARY_case_created_transition_reason_20260801

## Metadata

- Summary ID: `SUMMARY_case_created_transition_reason_20260801`
- Status: `summarized`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-08-01T00:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_case_created_transition_reason_20260801.md`
- Intention: none — this was a restoration, not a new intention.

## What was implemented

Raising a case on a task now pauses **every** working step of that task, server-side, carrying
`transition_reason = case_created` and the case type in the description.

The capability existed once, was lost, and nobody noticed. It was lost in a way worth naming: the
client did the pausing, using a catalog reason looked up **by slug**, and that catalog row was
soft-deleted. The lookup started returning `undefined`, the request went out with no reason, and the
step kept pausing — silently, wrongly, **40 times**, 35 of them in July. Those are the unexplained
pause blocks on the manager timeline.

So the fix is not "add the pause back." It is *move the decision to the side that cannot lose it*.
As a code-owned enum member the reason is present in every workspace by construction, needs no
seeding, and no manager can rename or delete it — which is the whole point of the four phases of
`system_transition_reasons` work this sits on top of.

- One enum member (`enums.py:27`), one label entry, one new module
  (`services/commands/cases/_case_created_step_pause.py`), one call in `create_case.py`.
- **No migration.** Ruling 4 removed data work from scope; `app/migrations/versions/` is untouched.
- Reuses `_apply_step_transition` rather than writing a `StepStateRecord` inline — that is what emits
  the `PROCESS_STEP_TRANSITION` outbox task whose handler reconciles the derived timeline. A row
  written inline would exist and the timeline would not follow.
- `credited_user_id` comes off the **closed** record, not the actor. A manager raising a case on a
  worker's task must not acquire a pause segment on their own shift timeline; `created_by_id` still
  records who caused it.

## The finding worth carrying forward — criterion 7 has a second half

The criterion said *the case must survive a failed pause*: the case is the user's intent, the pause
is a side effect. The obvious reading is "wrap it in try/except." **That is not sufficient, and the
test proved it.**

A failed pause rolls back its own transaction, and the rollback **expires every ORM object on the
session**. Building `create_case`'s response afterwards then attempted lazy IO outside an `await` and
raised `MissingGreenlet` — so the side effect's failure became a failure of the user's action anyway,
by a completely different route than the one the criterion was written against.

Fixed by snapshotting the response off the ORM objects *before* the pause runs
(`create_case.py:209-219`). The reviewer reverted the snapshot and confirmed the test fails: it binds
to the **ordering**, not merely to the swallow.

**Generalisation:** when you isolate a failure so it cannot roll back the user's action, ask what
runs *after* it, not only what is inside the guard. On an async ORM session, a rollback anywhere is
an invalidation everywhere.

## The four rulings — all held, none quietly improved

| # | Ruling | Verdict |
|---|---|---|
| 1 | Every working step of the task pauses | Held. Asserted with **two** `WORKING` steps and both controls kept — a `PENDING` step on the same task, a `WORKING` step on a different one — which is what proves the selection is scoped rather than broad. |
| 2 | Customer cases skip, explicitly | Held. A dedicated `CUSTOMER` branch placed *ahead* of the general guard, so a reader sees a decision rather than a fall-through. |
| 3 | Closing a case does **not** resume the step | Held. No resume path exists anywhere; zero step-state references in `services/commands/cases/` outside the new module. This was the tempting addition. |
| 4 | The 7 historical rows are left alone | Held. Migration directory empty in the diff. |

## The sweep

This change *adds* a member rather than changing what one means, so the population-change mode was
unlikely — but the reviewer walked **all 30** `WORKING` call sites rather than the two the implementer
named, which is the standard this codebase now holds after R1.

The population that did move: a step that used to stay `WORKING` becomes `PAUSED`, so clock-out and
task-switch stop finding it — correct in both, since it is already paused. Two sites the implementer's
sweep had not named were checked and behave correctly; a third
(`finalize_pending_step_completion.py:70`) *would* skip a case-paused step but is dormant, its only
producer commented out.

**The one live dependency on the step still being `WORKING` is the state machine itself**, which
produced both observations below.

## Two things left open, both deliberate

- **No `task:step-state-changed` event is emitted.** The design note justified this as "matching
  clock-out," which is the weaker of two available precedents — the closer analogue, task-switch
  auto-pause, *does* broadcast. A manager can pause a worker's live step and that worker's client is
  never told. This is also why the client conflict bites at all: the workers app's
  `step?.state !== "working"` guard reads a cache the backend just invalidated silently. Emitting the
  event would make the stale state self-healing and remove the deploy-ordering coupling the frontend
  handoff carries. Recorded in `docs/domains/worker_shifts/` as a known gap; an operator call.
- **Resume-before-complete.** There is no `PAUSED → COMPLETED` edge, so a worker interrupted by a case
  must resume before finishing the step, where previously it stayed `WORKING` and completed in one
  action. Consistent with ruling 3, but it is the one real behavioural consequence of the population
  moving. Now written next to the pause rule in the domain README.

## Escalations — both were the right call

The implementer escalated rather than deciding, twice, and both stood.

1. **Criterion 2's image URL does not exist.** The criterion said to reuse the retired catalog row's
   image; that row was seeded with a literal `NULL` and no asset exists in the repository. The entry
   carries `image_url: None` and the segment renders label-only. Inventing an icon would have been
   scope creep dressed as compliance.
2. **The client still fires its own pause**, so it now attempts `PAUSED → PAUSED` and the worker sees
   an error. Backend-only scope and the protocol forbids editing handoffs, so it was raised and not
   acted on. The operator wrote `HANDOFF_TO_FRONTEND_remove_case_created_pause_20260801.md`
   separately. The backend half was verified end to end: case created, step paused **once**, the
   follow-up rejected as a clean `ValidationError` rolled back inside its own transaction — no
   corruption, no double-pause.

## Validation

23 failed / 1463 passed against a 23 failed / 1453 passed baseline at `f2cd58f`, failure **node
sets** byte-identical at the same run index. The +10 reconciles as 9 integration + 1 unit, no
parametrisation. `ruff` clean on all six touched files; `transition_step_state.py` untouched, so its
5 pre-existing findings stand.

The zero-catalog test asserts the catalog is empty **before** acting, so a fixture that later starts
seeding reasons cannot make it pass vacuously. That property — system behaviour that works in a
workspace with no `pause_reasons` rows at all — is what the whole predecessor feature set exists to
guarantee, and this is the first change to depend on it rather than establish it.

## For the deployer

Nothing new. This change adds no migration, so the chain is still the eight revisions from
`d8e4f1a2c6b7` described in `SUMMARY_ended_shift_step_state_collapse_20260801.md`.

**The frontend handoff gates the deploy.** Shipping the client fix late means every case created from
a working step shows the worker an error in the interim. Shipping it early is safe — today's
client-side pause records no reason, so removing it loses nothing worth keeping.
