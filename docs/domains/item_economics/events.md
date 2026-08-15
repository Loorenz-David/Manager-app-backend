# Item Economics Events

This domain emits exactly **one** event.

---

## `item_economics:evaluation-committed`

Emitted when a committed evaluation is written for a task — from the explicit commit
endpoint, from projection promotion, and from the automatic commit that runs inside task
creation. All three routes share one commit procedure, so the event cannot exist on one
path and not another.

A **projection never emits.** The event's whole meaning is "this task's operational
economics changed"; a what-if has not changed anything.

**Kind:** workspace event — broadcast to every client connected to the workspace room.

**Payload** (the socket message body):

```json
{
  "client_id": "tsk_…",
  "evaluation_id": "ice_…"
}
```

- `client_id` is the **task's** id, matching the `task:state-changed` shape — the event is
  about the episode, and the task is what a client has on screen.
- `evaluation_id` is the newly committed evaluation's id. Fetch the figures with
  `GET /api/v1/item-economics/tasks/{task_client_id}/budget-status`; the event carries no
  monetary value of its own, so it needs no role gate at the transport.

---

## Delivery semantics

**After the transaction, never inside it.** The event is built during the commit and
returned to the caller as a pending event; it is dispatched only once the write has
committed. On the automatic path inside task creation it rides `create_task`'s pending
events and is appended only after the savepoint exits normally — a failed auto-commit
therefore emits nothing.

**Process-independent.** Delivery goes through the shared event bus and the socket
handler: the API process broadcasts to its own clients and publishes to Redis for other
instances; a worker process publishes to the same channel and the API forwards. Callers
never choose a transport.

**A failing handler is logged and skipped**, so a socket problem cannot fail or roll back
an economic commit.

**Not an audited event.** `item_economics:evaluation-committed` is absent from the audited
event set; this domain writes its audit rows directly inside the transaction instead. The
audit vocabulary is:

| Event name | Written by |
|---|---|
| `production_cost_group.created` / `.updated` / `.deleted` | cost-group commands |
| `production_cost_group_section.added` / `.removed` | section membership commands |
| `production_cost_basis_version.created` / `.deleted` | basis-version commands |
| `cost_model_version.created` / `.deleted` | cost-model commands |
| `item_valuation.created` / `.deleted` | valuation commands, the commit-path mirror, and the inline birth price |
| `item_cost_evaluation.committed` / `.projected` / `.promoted` / `.deleted` | evaluation commands; `.deleted` covers projections only |

The automatic path writes `item_cost_evaluation.committed` too, attributed to the task
creator.

---

## The event this domain consumes

Not an emission, but the other half of the picture: the result row is produced by an
**execution task**, not by a socket event.

`TaskType.PROCESS_ITEM_COST_RESULT` is enqueued with `create_instant_task` inside the
existing side-effect block of the transitions that end or advance an episode, routed to
`queue:analytics`, and handled by
`services/tasks/analytics/process_item_cost_result.py::handle_process_item_cost_result`.

**Payload:** `{ "workspace_id": "ws_…", "task_id": "tsk_…" }` — a frozen dataclass, and
nothing else. No derived value ever travels in it. The handler re-resolves everything at
handler time, which is what makes replaying an old event produce today's correct answer.

The emission points and the handler's admission rules are in [states.md](states.md).
