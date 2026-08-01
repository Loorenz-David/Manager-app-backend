# Domain: Worker Shifts

## Responsibility

Owns a worker's working day: when they clocked in and out, what they were doing at any moment of it,
and what they declared they were doing when not working a task step.

It does **not** own task steps themselves (that is the task-steps domain) or the catalog of pause
reasons (that is the pause-reasons domain). It **reads** both.

---

## The one thing to understand first

The domain has **source** tables and a **derived** table, and confusing them is the most common way
to get this wrong.

```
SOURCE   step_state_records            what the worker did on task steps
SOURCE   user_declared_state_records   what the worker DECLARED they were doing off-task
         ↓
DERIVED  user_shift_state_records      the worker's timeline — live during the day,
                                        fully rebuilt at clock-out
```

`user_shift_state_records` is **not** a log that other code appends to. It is a projection. During
the day it is maintained provisionally so the UI has something live to render; at clock-out the
day's rows are discarded and rebuilt deterministically from the two source tables.

The practical consequence: **anything written only to the derived table is destroyed at clock-out.**
If a fact must survive the day, it belongs in a source table.

---

## Entities

### `UserShiftStateRecord` — derived timeline

Prefix `uss` · `user_shift_state_records`

| Field | Type | Description |
|---|---|---|
| `client_id` | prefixed ULID | Primary key and stable public identifier |
| `user_id` | prefixed ULID | The worker this segment belongs to |
| `workspace_id` | prefixed ULID | Owning workspace |
| `state` | `UserShiftStateEnum` | What the worker was doing during this segment |
| `entered_at` | datetime (UTC) | Segment start |
| `exited_at` | datetime (UTC), nullable | Segment end; `NULL` means still open |
| `changed_by_id` | prefixed ULID, nullable | Who caused the transition, when a person did |
| `reason` | string(512), nullable | The catalog reason the worker chose — see the caveat below |
| `transition_reason` | string(32), nullable | Which system transition produced this segment |
| `manually_recorded` | bool | Segment originated from a worker action rather than a step transition |

A paused segment is explained through **one of two channels**, and which one tells you who decided
it:

- `reason` — a `par_…` id pointing at the workspace catalog. A human picked this.
- `transition_reason` — a member of the code-owned vocabulary. The system decided this, and no
  catalog row is involved.

> **`reason` is overloaded; `transition_reason` is not.** Besides catalog ids, `reason` also holds
> plain strings on older records, and readers distinguish the two by inspecting the id prefix. Treat
> any code that reads it as fragile, and do not add a third meaning to it. `transition_reason` only
> ever holds a vocabulary member, so it needs no such inspection.

A declared state is the one segment that carries **both**: the catalog reason the worker chose, and
`worker_declared_state` saying the segment came from a declaration rather than from a task step.

### `UserDeclaredStateRecord` — source, worker declarations

Prefix `uds` · `user_declared_state_records`

| Field | Type | Description |
|---|---|---|
| `client_id` | prefixed ULID | Primary key |
| `user_id` | prefixed ULID | The worker who declared |
| `workspace_id` | prefixed ULID | Owning workspace |
| `pause_reason_id` | prefixed ULID, **not null** | The catalog reason chosen — a declaration always has one |
| `description` | string(512), nullable | Free text, required when the reason demands it |
| `entered_at` / `exited_at` | datetime (UTC) | Open interval; `exited_at NULL` means still declared |
| `created_by_id` | prefixed ULID | The account that opened it (the acting manager when on-behalf) |
| `closed_by_id` | prefixed ULID, nullable | The account that closed it |

### `UserWorkProfile` — per-worker settings

Relevant fields only: `clock_in_code` (nullable, ≤16 chars — the code a worker types at a shared
floor device), `connecteam_user_id`, and hourly salary figures used by reporting.

---

## States

`UserShiftStateEnum`: `STARTED_SHIFT`, `WORKING`, `IN_PAUSE`, `IDLE`, `ENDED_SHIFT`.

See [states.md](states.md) for the machine, the precedence rules, and how the two derivations differ.

---

## Business rules

- A worker has **at most one open shift segment** and **at most one open declaration** at a time.
  Both are enforced by partial unique indexes on `(user_id, workspace_id) WHERE exited_at IS NULL`,
  not by application logic alone.
- **Declaring requires an open shift.** A declaration never clocks anyone in.
- **Declaring auto-pauses the worker's open working steps**, so step analytics and the shift timeline
  tell the same story. Starting or resuming a step closes the open declaration.
- **Declaring while a declaration is open is a switch** — close and open, one transaction.
- Clock-out **closes any open declaration** at the clock-out instant, then rebuilds the day.
- Clock-out **pauses any step the worker was still working**, typed `shift_ended`, and leaves steps
  the worker had already paused untouched. Every step the shift ended under stays open and resumable
  — the worker picks it back up next shift.
- **Raising a case on a task pauses every working step of that task**, typed `case_created`, with the
  case type in the description. Raising a case means work has stopped; without this the timeline
  shows a worker still working while the problem is being discussed. Three things about it:
  - **Every** working step of the task, not one. A case links to a task, never to a step, and a task
    may have several steps `WORKING` at once under `allows_batch_working`.
  - A case on a **customer** pauses nothing — no task, therefore no step.
  - **Closing the case does not resume the step.** A case closing does not mean the worker is back
    at the bench. Resumption stays a deliberate human action.

  The pause is a side effect of the case, not part of it: it runs outside the case's write
  transaction, so a failure to pause logs and leaves the case standing rather than losing the
  worker's conversation.
- A worker may only act on their own shift. An admin or manager must name a worker explicitly and
  may not act on themselves through these endpoints. This applies identically to clock actions and
  declarations.
- Idle is what is left over. Once declarations exist, `IDLE` means genuinely unaccounted time — not
  "we don't know."

---

## Relationships to other domains

| Domain | Relationship |
|---|---|
| Task steps | Reads `step_state_records` as the primary source of the timeline. Step transitions auto-pause conflicting steps, which surfaces here. |
| Pause reasons | Reads the catalog. Declarations reference a reason by id; the reason's type decides whether a worker may pick it. A worker's own choices are the only thing this catalog explains. |
| Transitions | Reads the code-owned `transition_reason` vocabulary and its label map. System transitions resolve there, never through the catalog, so they do not depend on a workspace having been seeded. |
| Cases | Raising a case on a task pauses that task's working steps, which surfaces here. This domain is read-only to cases: the write lives in the cases domain and only ever reaches here through `step_state_records`. |
| Auth | Role and app-scope decide who may act on whose shift, and which fields a roster response exposes. |
| Analytics / worker stats | Consumes the derived timeline for manager-facing reporting and the clock-out summary. |
| Connecteam integration | An external clock source that writes shifts through the same close path. |

---

## Files in this domain

| Layer | Location | Responsibility |
|---|---|---|
| Router | `routers/api_v1/worker_shifts.py` | Clock and declaration endpoints |
| Router | `routers/api_v1/worker_stats.py` | Manager-facing reporting endpoints |
| Commands | `services/commands/users/_clock_worker_shift.py` | Shared clock-in/clock-out core — **every** clock source calls this |
| Commands | `services/commands/users/clock_in_worker_shift.py`, `clock_out_worker_shift.py`, `toggle_worker_shift.py` | HTTP-facing wrappers |
| Commands | `services/commands/users/declare_worker_state.py`, `close_declared_worker_state.py` | Declaration write path |
| Commands | `services/commands/users/reconcile_worker_shift_state.py` | Keeps the derived table current during the day |
| Commands | `services/commands/cases/_case_created_step_pause.py` | Pauses a task's working steps when a case is raised on it (cases domain; listed here because it writes `step_state_records`) |
| Commands | `services/commands/users/_reconstruct_shift_middle.py` | The clock-out rebuild |
| Queries | `services/queries/users/get_current_worker_shift_state.py` | Live state for the UI |
| Queries | `services/queries/users/worker_shift_access.py` | Who may act on whose shift |
| Queries | `services/queries/worker_stats/` | Reporting and the clock-out summary |
| Domain | `domain/users/shift_state_machine.py` | `derive_target_state`, transition validity |
| Domain | `domain/analytics/linear_timeline.py` | The clock-out linear sweep |
| Domain | `domain/users/serializers.py` | Shift state output shapes |
| Models | `models/tables/users/user_shift_state_record.py`, `user_declared_state_record.py`, `user_work_profile.py` | Table definitions |
| Background | `services/tasks/users/auto_clock_out_open_shifts.py` | Closes shifts left open overnight |
| Background | `services/tasks/connecteam/handlers/` | External clock source |

---

## Known gaps in this domain

Real, current, and deliberately unfixed. Repository-wide debt lives in
[docs/repo_health.md](../../repo_health.md); these are specific to worker shifts.

- **The seven historical case-created pause records are not backfilled.** Records written before the
  capability was removed carry the soft-deleted `pause_case_created` catalog reference rather than
  the `case_created` transition, so the same interruption has two representations in the data. Both
  resolve to the same label and nothing depends on the distinction. `pause_ended_shift` is already
  in exactly this state.

- **`backfill_worker_shift_state_records.py` destroys declared-state projections.** It deletes every
  `UserShiftStateRecord` for a worker-day and rebuilds from **step records alone**, so a declaration
  projection — which carries `worker_declared_state` *and* the catalog reason the worker chose — is
  not reconstructed. Offline and `--execute`-gated, so not a live risk, but do not run it on a day
  containing declarations expecting them to survive.

- **Offline repair scripts have no test coverage**, and they are where this domain's subtlest bugs
  land. Both `heal_open_shifts_today.py` and `backfill_worker_shift_state_records.py` have shipped
  defects that no suite could catch, in both cases because a filter's *selected population* changed
  without the filter being edited. If you change what a step state or transition reason means, check
  these two by hand — see the sweep note in `docs/repo_health.md`.

---

## Keeping this document true

**This is a living document. It describes what the system does now, not how it came to.**

Any change that alters the *logic* of this domain must update the affected file in this folder **in
the same change** — not afterwards, and not in a separate document. That includes:

- adding, removing, or changing the meaning of a state, a field, or an entity
- changing an invariant, a precedence rule, or who may act on whose shift
- adding or removing an endpoint, or changing a request or response shape
- changing how the derived timeline is built, or what survives the clock-out rebuild
- moving a file listed in the table above

Changes that do **not** require an update: refactors that preserve behaviour, performance work,
test-only changes, and internal renames that no other domain can observe.

If a change makes something here wrong and you are not updating it, that is a defect — the same as
leaving a broken test. A reader who cannot trust this file will read the code instead, and then this
file is worse than not existing.

Do not add implementation history, migration steps, or rationale for past decisions here. Those
belong elsewhere. This file answers *what is true* and *where to look*.
