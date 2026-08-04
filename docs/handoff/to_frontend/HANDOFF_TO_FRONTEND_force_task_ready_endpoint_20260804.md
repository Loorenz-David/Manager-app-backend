# HANDOFF_TO_FRONTEND_force_task_ready_endpoint_20260804

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_force_task_ready_endpoint_20260804`
- Created at (UTC): `2026-08-04T00:00:00Z`
- Owner agent: `claude-opus-5`
- Route: `backend/app/beyo_manager/routers/api_v1/tasks.py` → `route_force_task_ready`
- Command service: `backend/app/beyo_manager/services/commands/tasks/force_task_ready.py`
- Request model: `backend/app/beyo_manager/services/commands/tasks/requests/__init__.py` → `ForceTaskReadyRequest`

> **STATUS: new endpoint, ready to consume.** No migration required. Nothing about existing
> endpoints changed — this is purely additive from your side.

---

## 1. What this is for

Until now there was **no way to move a task to `ready` manually.** Task state is derived: a
task becomes `ready` only when every one of its steps reaches a terminal state. The only
manual state controls were `resolve`, `cancel` and `fail`, all of which are *terminal* — they
close the task out entirely.

That left a gap. A task whose remaining steps will never actually be worked (the customer
withdrew, the item was handled off-system, the work happened before the task was created) had
no route to `ready`, and therefore no route into the post-completion process that follows it.

This endpoint fills that gap. It is a **manager override**, not a normal part of the worker
flow — see §8 for the UX implications, which are not optional.

---

## 2. Endpoint

```
POST /api/v1/tasks/{task_id}/force-ready
```

**Authentication:** required. `Authorization: Bearer <jwt>`. Workspace comes from the token.

**Allowed roles:** `admin`, `manager`. Note this is stricter than `resolve`
(`admin`/`manager`/`seller`) — **sellers cannot force a task ready.** If your UI shows the
resolve button to sellers, do not put this one next to it unconditionally.

---

## 3. Request body

```ts
{
  reason: string          // required, non-blank
  mark_inaccurate?: boolean   // optional, defaults to true
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `reason` | `string` | **yes** | Free text, 1–1024 chars. Whitespace-only is rejected. Leading/trailing whitespace is trimmed server-side before storage. |
| `mark_inaccurate` | `boolean` | no (default `true`) | Flags the recorded time on interrupted steps as unreliable. See §7 — you almost certainly want the default. |

`reason` being mandatory is deliberate and enforced server-side. A forced task is
indistinguishable from a genuinely finished one in the data unless the reason is captured, so
there is no "just force it" path. **Make it a required field in your form** rather than
letting the user discover the `422` — see §8.

### Example

```json
{
  "reason": "Customer withdrew the return; item already back on the floor.",
  "mark_inaccurate": true
}
```

---

## 4. Response envelope

Standard for this API. Success:

```json
{ "ok": true, "warnings": [], "data": { ... } }
```

Failure:

```json
{ "ok": false, "error": "Human-readable message." }
```

`warnings` exists only on success, `error` only on failure. Read `data` only after checking
`ok === true`. `warnings` is always `[]` for this endpoint today.

### `data` shape

```ts
data: {
  client_id: string          // the task id, prefix `tsk_`
  state: "ready"             // always this literal on success
  skipped_step_ids: string[] // ids of steps this call closed, prefix `tsp_`
}
```

| Field | Type | Notes |
|---|---|---|
| `client_id` | `string` | Echoes the task from the URL. |
| `state` | `"ready"` | Constant. The call cannot succeed and leave the task in another state. |
| `skipped_step_ids` | `string[]` | Steps that were **still open** and got closed. Ordered by `sequence_order`. **Can be empty** — see below. |

`skipped_step_ids` is empty in two legitimate cases: the task had no steps at all, or every
step was already terminal. Empty is **not** an error and does not mean nothing happened — the
task still moved to `ready`. Do not branch on `skipped_step_ids.length > 0` to decide whether
the call succeeded; branch on `ok`.

Use the array for the confirmation toast ("3 steps skipped") and to know which step rows to
re-render.

---

## 5. Error cases

| HTTP | `error` message | Cause | What to do |
|---|---|---|---|
| `404` | `Task not found.` | Wrong id, wrong workspace, or soft-deleted. | Treat as gone; refresh the list. |
| `409` | `Task is already in a terminal state.` | Task is `resolved` / `failed` / `cancelled`. | Hide or disable the action for these states (§8). |
| `409` | `Task is already ready.` | Task is already `ready`. | Same — disable the action. |
| `422` | `reason: Value error, reason must not be blank.` | `reason` blank or whitespace-only. | Validate client-side first. |
| `422` | `reason: Field required` | `reason` omitted. | Validate client-side first. |
| `422` | `Cannot force this task ready — <step_id>: cannot skip a step in state <state>.` | A step is in a state with no legal skip path. | Should not occur in practice; surface the message. |
| `422` | `Cannot force this task ready — no open state record for: <ids>` | Data integrity issue on a step. | Surface the message and report it — this indicates a backend data problem, not user error. |
| `403` | — | Caller is not `admin`/`manager`. | Do not render the control for other roles. |

**The call is all-or-nothing.** If it fails for any reason, no step was closed and the task did
not move. There is no partial state to reconcile — you can safely re-issue after fixing the
input.

---

## 6. Realtime events

On success the backend emits, in this order:

| Event | Payload | When |
|---|---|---|
| `task:step-state-changed` | **batched** — `{ items: [{ client_id, new_state: "skipped" }, ...] }` | Only if at least one step was closed. Omitted entirely for a stepless task. |
| `task:state-changed` | `{ client_id, extra: { new_state: "ready" } }` | Always. |

Note the step event is the **batched** shape (`items[]`), the same one
`POST /tasks/steps/transition-batch` emits — not N individual events. If your handler assumes
one step per `task:step-state-changed`, it will need to handle the array form here.

Both events fire after the transaction commits, so the data is readable when they arrive.

---

## 7. What actually happens to the steps

This matters for what you display afterwards.

Each still-open step is moved to **`skipped`**, not `completed`. This is deliberate: a forced
close is not throughput, and `completed` would credit whoever pressed the button in worker
stats and completion counts. `skipped` is equally terminal and is excluded from completion
analytics.

**Practical consequences for the UI:**

- Skipped steps show `state: "skipped"`. If your step-state rendering only handles
  `completed` / `failed` / `cancelled`, **add `skipped`** — it was previously reachable only
  via step removal and you may not have styled it.
- Each skipped step's latest state record carries `transition_reason: "forced_ready"` and
  `description: "<the reason you sent>"`.
- The step's `pause_reason` object resolves to `{ name: "Forced ready", image_url: null, ... }`.
  `image_url` is `null` — there is no icon for this reason, so **do not assume a non-null
  `image_url`** when rendering the reason chip on a skipped step.
- Steps that were *already* terminal are untouched. A genuinely completed step keeps its
  `completed` state and its credit.

**About `mark_inaccurate`** (default `true`): when a step is closed out of `working` or
`paused`, real accrued time is being cut short administratively. With the flag on, that time
is marked unreliable (`recorded_time_marked_wrong` / `taken_from_average` on the step) so
analytics can discount it. Steps sitting in `pending` carry no time and are unaffected either
way. The accrued time stays credited to the **worker who accrued it**, never to the manager
forcing the task — so forcing a task does not distort anyone's hours.

---

## 8. Required UX handling

These are not stylistic suggestions — each maps to a real behaviour above.

1. **Gate on role.** `admin` / `manager` only. A seller who can resolve a task cannot force
   it ready.
2. **Gate on state.** Hide or disable when the task is already `ready`, `resolved`, `failed`
   or `cancelled`. All four `409`.
3. **Require a reason in the form.** Do not let the request go out with an empty one.
4. **Confirm before sending.** This closes other people's in-progress work — a worker
   actively on a step will have it closed underneath them. The confirmation should say how
   many steps will be skipped, which you know from the task's step list before calling.
5. **Do not present this as "complete the task."** It is an override. Label it as such
   ("Force ready", "Mark ready without completing steps") so it is not mistaken for the
   normal finish action.

---

## 9. Downstream side effects

Forcing a task ready runs **the exact same post-`ready` process** as a task finishing
normally. Specifically, depending on task type and return source, the backend creates:

- a **post-handling** instance (`return` and `pre_order` tasks), and/or
- a **customer-coordination** instance (`pre_order`, and `return` tasks whose source is not
  `store_return`).

So after a successful call, the task may immediately appear in your post-handling or customer
coordination queues, and the counts at `GET /tasks/post-handling/counts` and
`GET /tasks/customer-coordination/counts` will change. **Refetch those if they are on screen.**

This was the main design constraint on the endpoint: it drives the steps and lets the existing
readiness evaluation flip the task, rather than writing the state directly, precisely so these
instances are never skipped.

---

## 10. What happens if work resumes afterwards

If someone adds a **new step** to a forced-ready task, the task automatically reopens to
`working` (existing `add_task_steps` behaviour, unchanged). You will get a `task:state-changed`
with `new_state: "working"`.

Existing steps cannot be restarted — terminal states have no exit in the step state machine, so
a skipped step stays skipped. Adding a new step is the only route back into active work.

---

## 11. Validation notes

**Backend validation run:**

- 17 new integration tests for `force_task_ready` — all pass.
- 5 new integration tests for a related fix (§12) — all pass; verified failing against the
  unfixed code.
- Unit suite: 1031 pass, 8 pre-existing unrelated failures (unchanged before/after).
- Integration (`tasks`, `task_steps`, `services/tasks`): 65 pass, 2 pre-existing failures
  caused by a dirty local `roles` table, unrelated and unchanged before/after.

**Suggested frontend validation:**

1. Force a `return` task with 2–3 open steps → task shows `ready`, steps show `skipped`,
   post-handling row appears in the queue.
2. Force a task with **no steps** → succeeds, `skipped_step_ids: []`.
3. Force an `internal` task → succeeds, **no** post-handling or coordination row appears.
4. Attempt on an already-`ready` task → `409`, UI shows the message rather than a generic
   failure.
5. Submit with a blank reason → blocked client-side; confirm the server `422` is also handled
   if it slips through.
6. With a second session open on the same task, confirm the batched
   `task:step-state-changed` updates every step row, not just the first.

---

## 12. Related backend fix (no frontend action)

While verifying this work, a pre-existing bug was found and fixed in the deferred
step-completion worker (`finalize_pending_step_completion`), which handles the "undo window"
after a worker marks a step done. It wrote the `ready` transition by hand and so skipped
creating the post-handling and customer-coordination instances — permanently, since nothing
downstream would repair it.

**This does not affect you today:** the undo-window scheduler is currently disabled in
`transition_step_state`, so the path never runs and no live task is missing its instances. The
fix matters for whenever that window is switched back on. No API or contract change.

---

## 13. Trace links

- Route: `backend/app/beyo_manager/routers/api_v1/tasks.py` → `route_force_task_ready`
- Command: `backend/app/beyo_manager/services/commands/tasks/force_task_ready.py`
- Readiness predicate: `backend/app/beyo_manager/services/commands/tasks/_task_state_transitions.py` → `maybe_evaluate_task_ready`
- Side effects: `backend/app/beyo_manager/services/commands/tasks/_reconcile_task_side_effects.py`
- Tests: `backend/app/tests/integration/services/commands/tasks/test_force_task_ready_integration.py`
- Related fix + tests: `backend/app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py`,
  `backend/app/tests/integration/services/tasks/task_steps/test_finalize_pending_step_completion_integration.py`
