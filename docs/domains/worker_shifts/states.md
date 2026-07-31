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
2. Any open working step is closed.
3. The day's derived rows are discarded.
4. The day is rebuilt from `step_state_records` and `user_declared_state_records` by the linear
   sweep.
5. A final `ENDED_SHIFT` segment closes the day.

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
