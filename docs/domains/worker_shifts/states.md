# Worker Shifts — states

## The states

`UserShiftStateEnum` — `domain/users/enums.py`

| State | Meaning |
|---|---|
| `STARTED_SHIFT` | Clocked in, nothing else happening yet |
| `WORKING` | At least one task step is actively being worked |
| `IN_PAUSE` | Paused — either a paused step or a declared off-task state |
| `IDLE` | Clocked in, nothing accounted for |
| `ENDED_SHIFT` | Clocked out |

`IDLE` is the residue. Everything the system can explain becomes one of the other four; whatever is
left is idle. That is why declarations matter — without them, cleaning, meetings, and loading all
collapse into `IDLE` and a manager sees an unexplained gap.

---

## Why a segment is paused

`IN_PAUSE` has two explanation channels, and they answer different questions.

| Channel | Carried by | Means |
|---|---|---|
| Catalog reason | `reason` (a `par_…` id) | A human chose this reason from the workspace catalog |
| Transition reason | `transition_reason` | The system paused this itself, and this is which transition |

The vocabulary is **code-owned** — `TransitionReasonEnum`, three members:

| Member | Written when |
|---|---|
| `shift_ended` | Clock-out closed a step that was still being worked |
| `other_task_priority` | The worker started another task, so this step auto-paused |
| `worker_declared_state` | The segment projects a worker declaration |

Because it is code-owned, a system transition never resolves through the catalog and therefore
never depends on a workspace having been seeded. **Nothing in the state machine may be gated on a
catalog row existing.** The catalog explains only what a worker picked.

The two channels are mutually exclusive on `step_state_records`: a step record carries a catalog
reason or a transition reason, never both. The derived timeline has one deliberate exception — a
declaration-sourced segment carries `worker_declared_state` *and* the catalog reason the worker
chose, because both facts are true and both are wanted.

Readers resolve the catalog reference first when a segment has one, then the transition reason, and
fall back to an unattributed bucket only when a pause carries neither.

**The explanation channel is the only thing that separates one kind of pause from another.** A step
the worker paused for a stated reason and a step the system paused because the shift ended are both
simply paused; there is no third state, and nothing may reintroduce one. Which of the two a segment
is has to be read from `transition_reason` / `reason`, never from the state.

---

## Two derivations, not one

This is the part that surprises people. The domain computes a worker's state **twice**, by two
different algorithms, for two different purposes.

### Live — `derive_target_state` (`domain/users/shift_state_machine.py`)

Runs during the day, every time something changes. It answers *"what is this worker doing right
now?"* from the currently open rows, by **precedence**:

```
open WORKING step  >  open declaration  >  open PAUSED step  >  IDLE
```

Highest match wins. It is cheap, it only looks at open rows, and it is deliberately provisional —
the segment it writes may be replaced later the same day.

**The open rows it considers are scoped to the current shift** — only those entered at or after this
shift's start marker. That scoping is load-bearing, not an optimisation. Clock-out pauses any step
the worker still had open and leaves it that way, so a step stopped at 17:00 is still an open pause
at 08:00 the next morning. Without the scoping it would win the precedence table and the worker
would clock in reading `IN_PAUSE`, credited to yesterday's interruption, before they had done
anything. A carryover step is not this shift's state; the worker is `IDLE` until they act.

### At clock-out — `compute_linear_segments` (`domain/analytics/linear_timeline.py`)

Runs once, at clock-out. It answers *"what did this worker's whole day look like?"* by sweeping the
day's source intervals in time order and cutting them into non-overlapping segments.

It is a **linear sweep**, not a precedence check. Overlapping intervals are resolved into an ordered
partition of the shift, so the day's segments are contiguous, non-overlapping, and sum to the shift
duration.

**The two do not have to agree moment-by-moment, and that is intentional.** The live derivation
optimises for "cheap and good enough to render". The clock-out sweep optimises for "correct and
reproducible". Only the second one is authoritative.

---

## The rebuild

At clock-out:

1. Any open declaration is closed at the clock-out instant, in the source table.
2. Any step still being **worked** is paused, carrying `shift_ended`. A step the worker had already
   paused is left exactly as it is — a pause measures how long the item stood still for the reason
   given, and truncating it at clock-out would destroy the duration it exists to measure. An item
   waiting three days on "waiting for upholstery" has a three-day pause, and that number is the
   point.
3. The day's derived rows are discarded.
4. The day is rebuilt from `step_state_records` and `user_declared_state_records` by the linear
   sweep.
5. A final `ENDED_SHIFT` segment closes the day.

Each rebuilt pause segment carries whichever explanation channel its source had, in the same field
it came from: a step record's catalog reason lands in `reason`, its transition reason lands in
`transition_reason`, and a declaration contributes both. The two are carried separately end to end
so nothing downstream has to recover which kind of value it is holding by inspecting the string.

Provenance is carried **only for legacy manual pause rows**, and that narrowness is the point.
A rebuilt segment sourced from one of those keeps its `changed_by_id`, so a pause a person recorded
directly does not come back out of the rebuild looking system-authored. Every other rebuilt segment
— step-sourced and declaration-sourced alike — gets `changed_by_id = NULL`.

That is not an omission. `changed_by_id IS NOT NULL` is how the live derivation recognises an
actor-authored manual pause and holds it sticky against re-derivation. A declaration projection is
authored by the system from a source row, not by a person acting on the timeline, so giving it an
actor would make it sticky too and suppress the re-derivation it depends on. The declaring worker
is not lost: the declaration row itself records who opened and closed it.

**The rebuild is idempotent.** Running it twice over the same source data must produce identical
rows. This is the invariant to protect when changing anything in the rebuild path — it is what makes
the timeline reproducible regardless of what the live derivation happened to write earlier.

**What survives, what does not:**

| Written to | Survives clock-out? |
|---|---|
| `step_state_records` | Yes — source |
| `user_declared_state_records` | Yes — source |
| `user_shift_state_records` | **No** — discarded and rebuilt |

---

## Open-row invariants

Two partial unique indexes carry rules that application code must not be trusted to enforce alone:

```sql
uix_user_shift_state_records_active     (user_id, workspace_id) WHERE exited_at IS NULL
uix_user_declared_state_records_active  (user_id, workspace_id) WHERE exited_at IS NULL
```

A worker therefore has at most one open shift segment and at most one open declaration. Code that
opens a new row must close the previous one **in the same transaction**, or the database rejects it.

Both tables also carry a check constraint that `exited_at` may not precede `entered_at`.

---

## Concurrency

Reads that precede a state change take a row lock on the open shift row. Under `READ COMMITTED`, a
locked `SELECT` can return no row when a concurrent transaction has just modified it — the lock is
granted against a version that no longer matches the predicate. Code in this path re-selects rather
than treating the empty result as "no open shift", because the naive reading produces a false
"worker is not clocked in" error under concurrent requests.

Anything adding a new locked read of the open shift row needs the same treatment.

---

## Time and day boundaries

- All timestamps are UTC.
- A shift that crosses midnight belongs to the day it **started**.
- A shift left open overnight is closed by a background job rather than being left to accumulate.
  That job calls the same shared close path as every other clock source, so it inherits the rebuild
  and the declaration close without special-casing.

---

## Clock sources

Three things can close a shift, and **all of them call the same shared core** in
`services/commands/users/_clock_worker_shift.py`:

| Source | Path |
|---|---|
| The app (worker, manager, or shared floor device) | HTTP endpoints |
| Connecteam | Webhook handler |
| Overnight safeguard | Scheduled job |

Keeping the core shared is deliberate: a change to how a shift closes must apply to all three, and
none of them should need to know about the others. Logic added to an HTTP wrapper rather than to the
shared core will silently not apply to the other two.
