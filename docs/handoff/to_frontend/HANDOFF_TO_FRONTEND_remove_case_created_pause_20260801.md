# Handoff — remove the case-created pause from the workers app

**Type:** required before the next backend deploy. **Coordinated** — see Timing.
**Repo:** `frontend/apps/workers-app/ManagerBeyo-app-workers`

---

## What happens today, and why it is wrong

`use-task-step-detail.controller.ts`'s `onCaseCreated` handler transitions the step to `paused`
after a case is created:

```ts
transitionStepState({
  …,
  new_state: "paused",
  pause_reason_id: caseCreatedPauseReasonId,   // ← resolves to undefined
  …
});
```

`caseCreatedPauseReasonId` is looked up by `slug === "pause_case_created"`. **That catalog row was
soft-deleted**, so the lookup yields nothing and the request goes out with no reason at all.

The step pauses, but nothing records *why*. There are **40 such records** in the database, 35 of
them from July. They are the unexplained pause blocks on the manager timeline that nobody can
account for — the client has been creating them all along.

## What changed on the backend

Creating a case now pauses the task's working steps **server-side**, with a typed reason
(`transition_reason = case_created`) and the case type in the description. It works in any
workspace, needs no catalog row, and cannot silently lose its reason the way the slug lookup did.

**So the client's follow-up transition is now both redundant and harmful.** The backend has already
moved the step to `paused`; the client's request then attempts `PAUSED → PAUSED`, which the
transition matrix rejects. The case is created and the step is correctly paused — **but the worker
sees an error.**

## The change

Delete the `transitionStepState({...})` call inside `onCaseCreated`, and the
`caseCreatedPauseReasonId` lookup that feeds it if nothing else uses it.

The `if (step?.state !== "working") return;` guard goes with it — it exists only to protect that
call. Keep whatever else the handler does with `plainText`.

**Do not** replace it with a different transition, a retry, or error suppression. There is nothing
for the client to do here any more: the pause is the backend's, and it happens inside the same
request that creates the case.

## Timing — this matters

- **Ship this together with, or before, the backend deploy.** Shipping it *after* means every case
  created from a working step shows the worker an error in the interim.
- **Shipping it early is safe.** Today's client-side pause records no reason, so removing it loses
  nothing worth keeping. There would be a window where a case does not pause the step at all —
  which is the state the timeline has effectively been in since the reason went missing.

## How to know it worked

- Create a case from a **working** step → case created, no error, and the step shows as **paused**
  with the reason resolving to **"Case created"** on the manager timeline.
- Create a case from a step that is **not** working → case created, nothing else happens.
- The manager timeline should stop accumulating pause blocks with no reason attached.

## No new field, and no schema change — asked and answered

**The backend does not emit `transition_reason` on any timeline payload.** It routes the new reason
through the channels your schemas already have, so nothing is silently dropped:

| Where | What arrives | Your schema |
|---|---|---|
| `segment.reason` | the string `"case_created"`, in the slot a `par_…` id normally occupies | `z.string().nullable()` — already fits |
| the sibling `pause_reasons` lookup map | key `"case_created"` → `{name: "Case created", image_url: null, pause_type: "blocker"}` | `PauseReasonLookupSchema` — `image_url` is already `.nullable()` |
| `timeline.pause_by_reason` | keyed `"case_created"` | already `z.record(z.string(), z.number())` |
| `steps[].pause_reason` | a **full** `PauseReason`-shaped object, `client_id: "case_created"` | `PauseReasonSchema.nullable()` — parses; `image_url` and `created_by_id`/`updated_at` are all nullable there |

So `resolvePauseReasonLabel` finds it in the map and renders **"Case created"**, not the raw key.
The fallback you verified is the safety net, not the path.

### Where the case type actually is

**In `steps[].description`** — `"case created: Damaged item"` — not in the segment label. The label
is the constant `"Case created"`; the case type is the per-instance detail, and it travels in
`description` exactly as task-switch's `"started working with {sku}"` does.

That means: on any surface rendering `steps[].description` you get the case type for free. On the
calendar block, which renders label text only, you get `"Case created"` — correct and sufficient,
just not itemised. **Nothing to build either way** — the earlier wording of this section implied the
case type would appear on the segment itself, which was wrong.

## One thing you will notice

The case-created pause resolves with a **label but no icon** (`image_url: null`). Every other
transition reason carries an image; this one has none, because the retired catalog row was seeded
with a null image and no asset exists in the repository. Moot on the calendar, which renders no
reason imagery at all. Cosmetic, tracked backend-side — no client change wanted for it.
