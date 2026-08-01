# Handoff — remove `pause-reason-transition.ts` (workers app)

**Type:** cleanup. No backend change, no contract change, no coordination window.
**Blocking anything?** No. Do it whenever convenient.
**Repo:** `frontend/apps/workers-app/ManagerBeyo-app-workers`

---

## What this is

`resolvePauseReasonTransition` existed to answer one question: *does this pause reason mean the
worker is ending their shift, or just pausing?* It read `reason.slug` and returned a different state
machine target for `pause_ended_shift`.

**That branch is already gone** — the worker-home workstream removed it. What remains is a function
that always returns the same constant plus one field copied straight off its argument:

```ts
export function resolvePauseReasonTransition(reason) {
  return {
    newState: "paused",                              // constant
    requiresDescription: reason.requires_description, // passthrough
  };
}
```

There is nothing left to resolve. This handoff is the tidy-up.

---

## Why the branch went away (context, not required reading)

The backend used to encode *why* a step stopped inside the step's **state** — `ended_shift` was a
`TaskStepStateEnum` member. So picking a pause reason had to change the state, and the frontend had
to know which reason was special.

Reasons now travel separately from states. A system-caused stop carries a code-owned
`transition_reason`; a worker's choice carries `pause_reason_id`. The state is just `paused` either
way, so no reason is special to the client any more.

`pause_ended_shift` **remains in the catalog and remains selectable** — a worker can still pick
"Ended shift" from the sheet. Only its power to change the state target is gone.

---

## The change

### 1. Delete two files

```
src/features/task_steps/lib/pause-reason-transition.ts
src/features/task_steps/lib/pause-reason-transition.test.ts
```

### 2. `src/pages/task_steps/PauseReasonSheetPage.tsx` — three edits

Remove the import (line ~9):

```ts
import { resolvePauseReasonTransition } from "@/features/task_steps/lib/pause-reason-transition";
```

**First call site** (~line 100), in the reason-picked handler:

```ts
// before
const transition = resolvePauseReasonTransition(reason);
if (transition.requiresDescription) { … }
…
new_state: transition.newState,

// after
if (reason.requires_description) { … }
…
new_state: "paused",
```

**Second call site** (~line 129), in `handlePauseWithDescription`:

```ts
// before
const transition = resolvePauseReasonTransition(selectedReason);
transitionStepState({ …, new_state: transition.newState, … });

// after
transitionStepState({ …, new_state: "paused", … });
```

The `PauseReasonTransition` type disappears with the module; nothing else imports it (verified —
`resolvePauseReasonTransition` and `PauseReasonTransition` have no other references in `src/`).

---

## What must not change

- **Both requests still send `pause_reason_id`.** That is now the *only* thing carrying why the step
  stopped. Dropping it would produce an unexplained pause.
- **The `requires_description` two-step flow stays.** Reasons that demand a description still route
  through the description view before transitioning.
- **`pause_ended_shift` stays in the picker.** It is an ordinary reason now — do not filter it out.

---

## How to know it worked

Behaviour should be **identical**, because the function already returns a constant. If anything
changes visibly, something else was wrong.

- Pick a reason with `requires_description: false` → step goes to `paused`, `pause_reason_id` sent.
- Pick one with `requires_description: true` → description view, then `paused` with the description.
- Pick "Ended shift" → behaves exactly like any other reason. **This is the one worth eyeballing**,
  since it is the case that used to be special.

---

## One thing coming later — do not act on it yet

A backend change will remove `ended_shift` from `TaskStepStateEnum` entirely, at which point no step
record carries that state. **Read-side code that renders `ended_shift` must keep working until
then** — historical records still hold it, and they will until that migration runs.

So: delete the *write*-side mapping now (this handoff), leave any *read*-side handling of
`ended_shift` alone. A separate handoff will cover it when the backend is ready.
