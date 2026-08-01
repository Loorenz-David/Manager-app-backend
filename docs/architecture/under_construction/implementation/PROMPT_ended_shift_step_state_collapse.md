# Implementer prompt — Ended-shift step state collapse

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

`TaskStepStateEnum.ENDED_SHIFT` is a **state that encodes a reason**. This removes it: a step that
stops because a shift ended is simply `PAUSED`, and *why* travels in `transition_reason` (system) or
`pause_reason_id` (the worker's choice). It is the same category error the `system_transition_reasons`
set removed one layer down, applied one layer up.

## Protocol

1. Load and follow `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process as: implement → validate → review-log entry → **STOP for independent review.**
   Summary/archive only after the reviewer approves.
2. Read, in order:
   - `docs/domains/worker_shifts/` — all three files. The living map of the domain you are changing,
     and **`states.md` becomes materially wrong in this change** (see "Domain documentation").
   - Your plan: `docs/architecture/under_construction/implementation/PLAN_ended_shift_step_state_collapse_20260801.md`
     — design decisions **E1–E5**, the ten acceptance criteria, and the eight implementation steps.
   - The intention, for reasoning: `.../intention/INTENTION_ended_shift_step_state_collapse_20260731.md`
   - `architecture/30_migrations.md`, including "Migration-owned bookkeeping tables".
3. **No clarifications are open.** E1 and E2 were both ruled by the operator. If a case arises that
   E1–E5 do not cover, escalate in the Review log and **stop** — do not choose. A deferred decision
   without an owner *and* a default is how the predecessor set lost two review rounds.

## The step order is load-bearing — do not reorder it

E5 is the reason this can ship safely: the derived bucket expression

```
bucket = 'ended_shift'  when state = 'paused' AND transition_reason = 'shift_ended'
       = state          otherwise
```

is **correct at every point in the rollout**. Before the migration a clock-out row is
`state='ended_shift'` and the `otherwise` branch yields it; after, the first branch does. That is
what lets readers (step 2) ship before the writer (step 4) and the migration (step 6).

Reordering — writer before readers, or migration before either — breaks that property and misbuckets
live analytics silently.

**`_TIME_STATES` must keep BOTH `ENDED_SHIFT` and `PAUSED` until the migration lands, then drop
`ENDED_SHIFT`.** Dropping it early makes every historical row vanish from every total.

## E3 is the highest-blast-radius line in the plan

The intention's original trace named `domain/task_steps/aggregate_metrics.py:17-25` as the bucketing
site. **`increment_step_time_metrics` has zero callers.** Re-keying it changes nothing while looking
exactly like the work was done. Do not be satisfied by editing it.

The real single point is
`services/queries/analytics/averaged_time.py::compute_record_contributions`, whose emitted `.state`
six consumers bucket on — **three of which the original trace missed**
(`list_workers_totals.py`, `reconcile_user_time.py`, `estimation_sample.py`).

Criterion 7 requires all six verified **per consumer**, not inferred from the shared helper. Get
this wrong and every analytics surface misbuckets without an error anywhere.

## E2's third row is the judgement call

| Historical row | Becomes |
|---|---|
| `transition_reason='shift_ended'` | `paused`, unchanged |
| `pause_reason_id` set (worker picked it) | `paused`, reason kept, **no `transition_reason`** |
| neither set | `paused`, **`transition_reason='shift_ended'`** |

**Never apply the third row's default to a row carrying a `pause_reason_id`.** That silently re-types
a worker's stated choice as a system transition, irreversibly. Criterion 9 exists for this line
alone; assert it directly.

## The migration is irreversible — and the chain matters

Removing a member from a **native Postgres enum shared by two tables** (`task_steps`,
`step_state_records`) means recreating the type and rewriting both columns, plus the reclassifying
backfill. Reports change retroactively; that is accepted (E2) and is why it cannot be undone.

Three things, learned the hard way in the predecessor set:

- **Never run `alembic upgrade head` against a database holding irreplaceable state.** Use explicit
  revision targets. A routine `upgrade head` destroyed a 270-row backfill journal in the previous
  set because `head` had moved; it was recoverable only by luck of that database having no live
  traffic.
- **If you write a bookkeeping/journal table, name it `*_journal` and guard its drop** behind an
  explicit environment acknowledgement. `architecture/30_migrations.md` has the pattern and the
  reasoning. Given E2 rewrites rows in a way no predicate can identify afterwards, **strongly
  consider journalling** — and say why if you decide not to.
- **The local database is at `c8f3d2e60a17`; the server is still at `a7d21f4c8b03`.** The
  `system_transition_reasons` set is *not deployed*. Your migration stacks on top of a chain that
  has not run in production. Do not assume the two are in the same state.

## Two invariants with a history of breaking

- **Criterion 6 — the `entered_at_or_after` guard at `reconcile_worker_shift_state.py:172` becomes
  load-bearing here.** Today it is redundant for this case because `ENDED_SHIFT` is never queried;
  after the collapse, yesterday's still-open `PAUSED` step could derive the worker into `in_pause`
  instead of `idle` on the next clock-in. It needs its **own** test, not an inherited one.
- **The rebuild must stay idempotent and declarations must survive it.** Four fix cycles were spent
  on that in an earlier feature set. If you touch the rebuild path, assert both.

## Characterization first (step 1), and it asserts DIFFERENT things per path

Criterion 3 is not "the numbers are unchanged". It is:

- clock-out force-close → `total_ended_shift_seconds` / `_count` **equal** before and after;
- worker-picked ended-shift pause left open overnight → the time **moves** to `total_pause_seconds`,
  attributed to the chosen reason.

The second is the deliberate behaviour change (E1). A characterization test asserting both are
unchanged would be wrong and would pass for the wrong reason.

## Domain documentation is a deliverable

`docs/domains/worker_shifts/` must be updated **in this change**. `states.md` currently describes a
step-state vocabulary that includes ended-shift semantics, and the README's entity tables and
business rules reference it. Both become wrong.

Domain docs state what is true **now**: no plan references, no phase numbers, no "previously", and
nothing about work that has not shipped.

## Hard constraints

- **Do not edit `docs/handoff/to_frontend/`.** Operator-owned. A handoff for deleting
  `pause-reason-transition.ts` already exists
  (`HANDOFF_TO_FRONTEND_remove_pause_reason_transition_20260801.md`); step 5 coordinates with it
  rather than rewriting it. Contract changes are **proposed** in the Review log.
- **Do not edit archived plans** — the `system_transition_reasons` set is closed.
- **`pause_ended_shift` stays selectable** (E4). It is an ordinary workspace row with no special
  handling anywhere.
- **`total_ended_shift_seconds` / `_count` and `ended_shift_seconds` / `ended_shift_open_count` stay
  in every payload that carries them today** (criterion 10) — published contract, unchanged names
  and unchanged meaning. Only their derivation moves.
- **T9 — commits.** Stage explicit paths, never `git add -A`. Implementation, close-out and planning
  are separate commits; domain docs ride with the implementation that made them true.

## Validation

- **Run `git` from `backend/`.** The parent directory is not a repository — two agents in the
  previous set concluded there was none and silently downgraded their verification.
- **A baseline worktree needs all of `app/.env*`.** `.env.testing` alone cannot start the app.
- **Compare failure node sets at the same run index.** The last measured baseline was **23 failed**
  at `8a6af89`. The old "one latching shopify node" note is stale — none of the 23 passes in
  isolation; do not carry that instruction forward.
- **Any sweep must be re-derived by a second, different route** and stated as a list with
  `file:line`, never a count. Three rounds of a previous phase turned on a sweep resting on one grep
  pattern; what finally closed it was re-deriving from output keys rather than call sites.
- **Prove behavioural claims failing-first.** Write the assertion, watch it fail, then fix. A test
  that passes before and after proves nothing, and that has shipped here twice.

## Definition of done

- All ten acceptance criteria met with evidence, criterion 7 verified **per consumer**.
- Characterization tests written first and asserting the two different outcomes.
- Reclassification correct per E2's three-row table, with criterion 9 asserted directly.
- `docs/domains/worker_shifts/` true again.
- Full suite per the rules above; `ruff check` clean on touched files.
- Review log entry with the six-consumer verification and the migration's reversibility position
  stated plainly. Then **STOP** — no summary, no archive, no handoff edit.
