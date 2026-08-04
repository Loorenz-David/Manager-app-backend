# HANDOFF_TO_FRONTEND_sku_template_gapless_allocation_20260804

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_sku_template_gapless_allocation_20260804`
- Created at (UTC): `2026-08-04T00:00:00Z`
- Owner agent: `claude-opus-5`
- Route (changed): `backend/app/beyo_manager/routers/api_v1/tasks.py` → `route_create_task`
- Route (preview, unchanged but now the sanctioned entry point): `backend/app/beyo_manager/routers/api_v1/sku_templates.py` → `route_get_sku_template_by_task_type`
- Route (removed): `route_reserve_sku_scalar` — see §2, this is a breaking change if you call it today.
- Command service: `backend/app/beyo_manager/services/commands/tasks/create_task.py`
- Allocation helper: `backend/app/beyo_manager/services/commands/sku_templates/_allocate_sku_scalar_in_session.py`
- Shared item-creation helper (new — see §3a): `backend/app/beyo_manager/services/commands/items/_create_item_in_session.py`

> **STATUS: ready to consume.** No migration required on your data. One endpoint was
> **removed** — read §2 first if you currently call it.

---

## 1. What changed and why

The SKU template system (prefix + auto-incrementing index, e.g. `PRE-7`) used to hand out a
number through a dedicated `reserve` call, separate from actually creating anything. That
meant closing the form, navigating away, or the item create failing afterward left the number
permanently burned — gaps in the sequence with nothing to show for them.

The fix: the number is no longer handed out on its own. It's allocated **as part of** creating
the task's item, inside the same database transaction. If that transaction doesn't commit —
validation fails, you close the tab before submitting, anything — the number was never
consumed. Reopening the form and submitting again gets the next number, not one further along.

**For pre-order tasks this goes one step further.** `PUT /api/v1/tasks` already accepts an
optional `shopify_preorder` section that queues the Shopify product for a background worker to
create — it was never a separate call your frontend had to fire. That means the whole thing —
resolving the item's sku, then handing the *same* sku to the Shopify product — now happens
**inside one backend request**, in a guaranteed order, before anything is queued. There is no
frontend orchestration left for this path: no sequencing, no waiting on one response to fire a
second request. You send one request; the backend guarantees the item and the eventual Shopify
product share a sku.

What replaces the old reserve-then-create flow:

- **Preview** (no commitment): `GET /api/v1/sku-templates/by-task-type/{task_type}` — already
  existed, was already non-destructive, and is now the endpoint you should call for the
  provisional display while the user fills out the form.
- **Real allocation** (commits with the item, and flows into the queued Shopify product):
  `PUT /api/v1/tasks` — request shape unchanged except one field became optional (§4), plus new
  optional response fields `item_id` / `item_sku`.

---

## 2. Breaking change: the reserve endpoint is gone

```
POST /api/v1/sku-templates/by-task-type/{task_type}/reserve
```

**This endpoint no longer exists.** If your pre-order form currently calls it to get a number
to show the user before they submit, that call will now 404 at the routing layer (not a
domain `404` — the route itself is gone).

**Migration:** switch that call to the preview endpoint in §5. It returns the same kind of
data (`next_sku_preview`) but never increments anything, so it's safe to call as often as you
like — on every keystroke, on focus, whatever your form needs. The number that actually gets
assigned to the item comes back from `PUT /api/v1/tasks` (§3), not from this preview.

---

## 3. `PUT /api/v1/tasks` — what's new

**Authentication:** required, unchanged. **Roles:** `admin`, `manager`, `seller`, `worker` —
unchanged.

### Request — one field became optional, nothing else changed

```ts
{
  task_type: "pre_order" | "return" | "internal",
  // ...all existing fields, unchanged...
  item?: {
    article_number?: string,
    sku?: string,           // omit this to get the auto-assigned template SKU
    // ...
  },
  shopify_preorder?: {
    shop_integration_id: string,
    product: {
      title?: string,         // NEW: now optional — see §4
      sku?: string,            // NEW: now optional — see §4
      price: string,
      // ...
    },
    inventory: [...],
  }
}
```

If you omit `item.sku` on a `pre_order` task (or any task type with a configured template),
the backend now fills it in automatically from that task type's SKU template. If you send an
explicit `sku`, it's used verbatim and no number is consumed — the template is a helper, not a
requirement, matching how it works today for manual entry.

### Response — two new optional fields

```ts
data: {
  client_id: string
  task_scalar_id: number
  item_id?: string       // NEW — the item's client_id, prefix `itm_`
  item_sku?: string      // NEW — the item's final sku, including auto-assigned ones
  shopify_preorder?: { ... }  // unchanged
}
```

| Field | Present when | Notes |
|---|---|---|
| `item_id` | `item` was included in the request | Previously **not returned at all** — if you were re-fetching the task afterward just to learn the item id, you no longer need to. |
| `item_sku` | `item` was included in the request | The item's `sku` after any auto-assignment. **Omitted from the JSON entirely** (not `null`) when no `item` was sent — check for the key's presence, not just truthiness, if that distinction matters to you. |

### When `item_sku` comes back `null` (not omitted — present but null)

- `item.sku` was sent explicitly → echoes it back, unchanged.
- `item.article_number` matched an **existing** item that already has a real `sku` → returns
  that item's existing sku. The template is never touched in this case — you get back
  whatever that item already had, which could itself be `null` if it was created without one.
- The task type has **no configured template** (anything other than `pre_order` today) and no
  `sku` was sent → `null`, same as before this change. No error, no different behavior than
  what you already handle today. (This case only applies when `article_number` **was** sent —
  see §3a for what happens when it wasn't.)

---

## 3a. Creating an item with no identifier at all — template-only items

This is new, and it's the piece that actually closes the gap you asked about: a form that
relies **entirely** on the auto-generated SKU, with no `article_number` field at all.

**Before this change**, sending an `item` with neither `article_number` nor `sku` always
failed — `422`, `"At least one of article_number or sku must be provided."` — regardless of
whether a template existed. That validation lived in the generic find-or-create item logic,
which has no concept of SKU templates.

**Now:** if you send `item: {}` (or any `item` object with both fields omitted), the backend
takes a different path — instead of trying to look up a matching existing item (which is
meaningless with nothing to search by), it **always creates a new item** and derives its sku
from the `task_type`'s template. This is the same underlying logic `PUT /api/v1/items` already
used for its own `sku_template_task_type` field, just triggered automatically from `task_type`
here rather than requiring you to name the field explicitly.

**The error behavior is different from the `article_number`-present case above, on purpose:**
if no template exists for the task type in this scenario, the request **fails** with a `404`
(`SKU template not found.`) instead of silently succeeding with `sku: null`. That's intentional
— with no `article_number` and no template, the item would have no identifying value
whatsoever, which isn't a useful thing to create silently.

| `item` sent | Template exists for `task_type`? | Result |
|---|---|---|
| omitted entirely | — | No item created. No error. (Unchanged.) |
| `{}` (no article_number, no sku) | yes | New item created, `sku` auto-assigned from the template. |
| `{}` (no article_number, no sku) | no | `404 SKU template not found.` — the whole task creation fails. |
| `{article_number: "..."}` (no sku) | yes | New item (or matched existing one), `sku` auto-assigned if new. |
| `{article_number: "..."}` (no sku) | no | Succeeds, `sku: null` — no error (§3). |
| `{sku: "..."}` (with or without article_number) | n/a | Used verbatim, template never touched. |

**Practical takeaway for a template-only form:** you can now build a pre-order form that
collects nothing identifying at all — no article number field, no sku field — and send
`item: {}`. As long as the workspace has a `pre_order` template configured (it does by
default), the item gets created with a real, gapless, auto-assigned sku, and the request
response includes it in `item_sku` exactly as described in §3.

---

## 4. `shopify_preorder.product.sku` is now optional — it defaults to the item's sku

This is the piece that actually closes the loop for pre-order tasks.

**Before this change**, `product.sku` was **required**. Your form had to already know a sku
value to put there at the moment you built the request — which meant either a manual value, or
whatever the old `reserve` call had returned. That's gone now, so this field can no longer be
filled that way for the auto-assign case.

**Now:** omit `product.sku` entirely, and the backend fills it in from the same item sku that
was just resolved for `item.sku` (§3) — auto-assigned from the template, or whatever you sent
explicitly. **The local item and the Shopify product are then guaranteed to carry the same
sku**, because they're now sourced from one place in one transaction, not two independent
values your frontend had to keep in sync.

**You can still override it.** If you send `product.sku` explicitly, that value is used for the
Shopify product verbatim — even if it differs from `item.sku`. This is for the rare case where
you deliberately want the Shopify-facing sku to differ from the internal one; it is not the
normal path, and doing this means the two systems will disagree on the item's sku.

### The intended form flow

1. On load, call the preview endpoint (§5) and show the result as ghost/placeholder text in
   the sku field — not real input, just a hint of what will be assigned.
2. If the user never touches that field, **don't send `sku` at all** — omit `item.sku` and
   `product.sku` both. The backend assigns one real number and uses it for both the item and
   the Shopify product.
3. If the user types a value into the field, send **that** as `item.sku`. Whether you also want
   it applied to `product.sku` is up to you — sending it in both places keeps them explicitly
   in sync; omitting `product.sku` still makes it default to whatever `item.sku` resolved to,
   including the user's override, since the item is resolved first either way.

### Worked example — auto-assigned, ghost accepted

Request:
```json
{
  "task_type": "pre_order",
  "item": { "article_number": "ART-1" },
  "shopify_preorder": {
    "shop_integration_id": "shpint_1",
    "product": { "title": "Oak chair", "price": "5200.00" },
    "inventory": [{ "location_id": "gid://shopify/Location/1", "quantity": 2 }]
  }
}
```

Response:
```json
{ "ok": true, "data": {
  "client_id": "tsk_...", "item_id": "itm_...", "item_sku": "PRE-7",
  "shopify_preorder": { "queued": true, "preorder_operation_id": "...", "..." : "..." }
}}
```

The queued Shopify product will carry `sku: "PRE-7"` when the background worker processes it —
same value as `item_sku` in the response, with nothing further for you to send.

### Worked example — user typed their own sku

Request: same as above but `"item": { "article_number": "ART-1", "sku": "CUSTOM-7" }`, and
`product` still has no `sku`.

Result: `item_sku` comes back `"CUSTOM-7"`, and the queued Shopify product also gets
`sku: "CUSTOM-7"` — the default still applies, it just defaults to the override instead of an
auto-assigned number.

---

## 4a. `shopify_preorder.product.title` is now optional too — same idea, one layer further

Once `product.sku` can be auto-derived (§4), there's a knock-on problem: **`title` was still
required**, and if a seller doesn't type a product title, your form would have nothing to send
for it — the same gap that used to exist for sku.

**Now:** omit `product.title` and it defaults to whatever `product.sku` resolved to (auto-
assigned, overridden, whatever the final value is from §4) — so a seller who fills in nothing
but the required inventory/price fields still gets a valid Shopify product, titled with its own
sku. Send `product.title` explicitly and it's used verbatim, same override relationship as sku.

**Order of resolution**, so you can predict the exact value: `product.title` (if you sent one)
→ else `product.sku` (if you sent one) → else the resolved item sku (§4) → else nothing, and
the request fails cleanly with a `422` (`items.0.title: Field required`) rather than a vague
500 — this only happens if there's no item on the task at all *and* neither `title` nor `sku`
was supplied in `product`, which shouldn't occur in your normal pre-order flow.

| Field sent | `product.title` sent | Resulting Shopify title |
|---|---|---|
| Nothing (full auto) | — | the resolved sku, e.g. `"PRE-7"` |
| `item.sku: "CUSTOM-7"` | — | `"CUSTOM-7"` |
| — (auto sku) | `"Solid Oak Armchair"` | `"Solid Oak Armchair"` (title always wins over the sku default when you send one) |

**Practical takeaway:** if your form doesn't collect a separate product title for pre-orders,
you can now omit `product.title` entirely and stop worrying about it — the sku (real or
auto-assigned) fills the gap. If you *do* collect one, keep sending it as before; nothing
changes for that path.

---

## 5. `GET /api/v1/sku-templates/by-task-type/{task_type}` — the preview endpoint

This already existed; it's called out here because it's now the **only** supported way to show
a provisional SKU before save.

**Roles:** `admin`, `manager`, `worker`, `seller`.

```
GET /api/v1/sku-templates/by-task-type/pre_order
```

```ts
data: {
  client_id: string
  task_type: string
  prefix: string
  separator: string
  pad_width: number
  last_scalar: number
  next_scalar: number        // last_scalar + 1
  next_sku_preview: string   // formatted, e.g. "PRE-7"
  // ...timestamps, created_by_id, updated_by_id
}
```

It is a plain read — **it never increments anything**, no matter how many times you call it.

**Treat it as a hint, not a promise.** Under concurrency (two pre-order forms open at once),
the number this preview shows can be one behind what actually gets assigned by the time either
form is submitted, because someone else's submit can land in between. Display it as
provisional/ghost text ("will be assigned around `PRE-7`") and always defer to the real
`item_sku` from the `PUT /api/v1/tasks` response — never treat the preview value as final, and
never send the preview value back as `item.sku`/`product.sku` on the theory that it'll match;
just omit both and let the backend assign the real one.

**Error case:**

| HTTP | `error` message | Cause |
|---|---|---|
| `404` | `SKU template not found.` | No template configured for this task type in this workspace. Hide the preview UI for task types you know have none (anything but `pre_order` today), or handle the 404 by just not showing a preview. |

---

## 6. Manual override still works exactly as before

The SKU field on an item is, and remains, a **free string** — nothing about this change makes
it required or locks it to the template's format. If your form lets a seller type their own
value into the SKU field, keep sending it as `item.sku`; the backend will not touch the
template counter when you do, so overriding costs nothing and never creates a gap. See §4 for
how the same override now also flows through to the Shopify product automatically.

---

## 7. Realtime events — unchanged payload, different trigger

The `sku_template:scalar-reserved` event still fires, with the same payload
(`{ client_id: <template id>, extra: { last_scalar: <number> } }`), broadcast to the
workspace room. The only difference is *when*: it now fires as part of the `task:created`
dispatch batch (right alongside the other events `PUT /api/v1/tasks` already emits), instead
of from a standalone reserve call. If you have a socket handler keyed off this event name, no
changes are needed — same name, same shape, just a different originating action.

---

## 8. Required UX handling

1. **Stop calling `POST .../reserve`.** It's gone (§2). Replace with `GET
   .../by-task-type/{task_type}` for the provisional display.
2. **Do not fire a separate Shopify create request after `PUT /api/v1/tasks`.** For pre-order
   tasks, include `shopify_preorder` in the same request and let the background worker handle
   it — there is nothing left to orchestrate client-side for this flow. If you have code today
   that waits for the task response and then calls Shopify separately, remove it; it's not just
   unnecessary now, it duplicates what the backend already queues.
3. **Stop sending `product.sku` unless you mean to override it.** Omitting it is what makes the
   item and the Shopify product share one sku (§4). If your form was always copying the same
   value into both `item.sku` and `product.sku`, you can simplify to setting `item.sku` alone.
4. **Stop requiring a product title for pre-orders if you don't actually collect one.**
   `product.title` is optional now too (§4a) — if your form never had a real title field for
   this flow and was sending the sku (or some placeholder) as the title just to satisfy the old
   required field, you can drop that and omit it.
5. **Show the preview as provisional**, not as the number that will definitely be assigned —
   see the concurrency note in §5.
6. **Don't gate the SKU field as required.** A blank `item.sku` is exactly what triggers
   auto-assignment; requiring input there would defeat the feature.

---

## 9. Validation notes

**Backend validation run:**

- New integration suite for `create_item`'s allocation path
  (`test_create_item_sku_template.py`): 4 tests — allocation, manual-override skip,
  rollback-on-mid-transaction-failure, missing-source validation. All pass.
- New integration suite for `create_task`'s allocation path
  (`test_create_task_sku_template_integration.py`): 5 tests — gapless allocation across two
  tasks, no-overwrite on an existing-item match, silent no-op when the task type has no
  template, gapless creation from a template alone with no `article_number`/`sku` at all
  (§3a), and a clean `404` when that no-identifier case has no template to fall back on. All
  pass.
- Refactored `create_item.py`'s core item-construction logic into a shared, transaction-agnostic
  helper (`_create_item_in_session.py`) reused by both the standalone `PUT /api/v1/items`
  command and `create_task`'s new no-identifier path — chosen specifically so `create_task`
  never has to fall back to a lookup-based match for an item it has no key to search by. The
  existing `create_item` suite (4 tests) was re-run against the refactored version and confirmed
  unaffected — this was a pure extraction, not a behavior change for that endpoint.
- New integration suite for the Shopify-sku/title mirroring
  (`test_create_task_preorder_sku_mirrors_item_integration.py`): 4 tests — `product.sku`
  defaults to the auto-assigned item sku when omitted, an explicit `product.sku` overrides it,
  `product.title` defaults to the resolved sku when omitted, and an explicit `product.title`
  overrides that default. All assert the actual queued
  `ShopifyProductSyncItem.normalized_payload_json`, not just the response. All pass.
- Verified separately that the fully-unresolvable case (no item, no `product.sku`, no
  `product.title`) fails with a clean `422` (`items.0.title: Field required`) rather than an
  unhandled `500` — the existing required-field validation on the service-layer request model
  catches it before any write happens.
- Existing `create_task` / shopify-preorder integration suite (9 tests, including the
  existing-item-match-by-sku case and the router-forwarding unit tests) re-run and unaffected:
  all pass.
- Existing sku-templates command/query/router suites updated for the removed endpoint and
  re-run: all pass.
- Five pre-existing, unrelated failures (task-date-fields, batch-item-position ×2, a flaky
  dimension-migration pair) were confirmed present before this change too (verified via
  `git stash`) — not caused by this work.

**Suggested frontend validation:**

1. Open a pre-order form, watch the preview call (§5) fire without any write happening —
   confirm hitting it repeatedly doesn't advance the number.
2. Submit the task with `item` and `shopify_preorder` both present, neither carrying a `sku` →
   confirm `item_sku` in the response is populated, and once the background worker processes
   the queue, the resulting Shopify product's SKU matches it exactly.
3. Close the form after seeing a preview, without submitting, then reopen it → confirm the new
   preview shows the **same** next number, not one ahead (this is the gap you asked to fix).
4. Submit twice in a row for two different pre-order tasks → confirm the second `item_sku` is
   exactly one more than the first, with no skip.
5. Submit with an explicit `item.sku` (manual override) and no `product.sku` → confirm both the
   item and the eventual Shopify product carry the override value.
6. (Edge case, optional) Submit with `item.sku` omitted but `product.sku` explicitly set to a
   different value → confirm the item gets the auto-assigned number while the Shopify product
   gets your explicit override. Only exercise this if you actually have a use case for the two
   diverging.
7. Submit a task type with no template (e.g. `internal`) and no `item.sku` → confirm
   `item_sku` is `null` and the request still succeeds, same as before this change.
8. Submit a pre-order with `item.sku` omitted and `product.title` omitted → confirm the queued
   Shopify product's title equals the resolved sku (not blank, not an error).
9. Submit the same as #8 but with an explicit `product.title` → confirm your title wins and the
   sku is unaffected.
10. Submit a pre-order task with `item: {}` (no `article_number`, no `sku` at all) → confirm it
    succeeds with a real auto-assigned `item_sku`, exactly like #4 but with no identifying field
    sent at all (§3a).
11. Submit `item: {}` on a task type with **no** template (e.g. `internal`) → confirm this one
    **does** fail (`404`), unlike #7 — the difference is whether `article_number` was present.

---

## 10. Trace links

- Route (changed): `backend/app/beyo_manager/routers/api_v1/tasks.py` → `route_create_task`
- Route (preview): `backend/app/beyo_manager/routers/api_v1/sku_templates.py` → `route_get_sku_template_by_task_type`
- Command: `backend/app/beyo_manager/services/commands/tasks/create_task.py`
- Shopify-sku/title mirroring: `backend/app/beyo_manager/services/commands/shopify/_create_preorder_sync_item_in_session.py`
- Request models (product.sku and product.title now optional): `backend/app/beyo_manager/services/commands/tasks/requests/__init__.py` → `ShopifyPreorderProductInput`, `backend/app/beyo_manager/routers/api_v1/tasks.py` → `_ShopifyPreorderProductBody`
- Still-required downstream check (fails cleanly if nothing resolves): `backend/app/beyo_manager/services/commands/shopify/requests/process_shopify_products_request.py` → `ProcessShopifyProductItemRequest.title`
- Also touched (same capability, different entry point — `PUT /api/v1/items` gained the same
  optional `sku_template_task_type` field for item creation outside of a task; not covered in
  depth here since it isn't the flow your frontend uses today):
  `backend/app/beyo_manager/services/commands/items/create_item.py`
- Shared item-creation helper (§3a) — extracted from `create_item.py`, used by both it and
  `create_task.py`'s no-identifier path: `backend/app/beyo_manager/services/commands/items/_create_item_in_session.py`
- Allocation helper: `backend/app/beyo_manager/services/commands/sku_templates/_allocate_sku_scalar_in_session.py`
- Removed: `backend/app/beyo_manager/services/commands/sku_templates/reserve_sku_scalar.py`
- Tests: `backend/app/tests/integration/services/commands/tasks/test_create_task_sku_template_integration.py`,
  `backend/app/tests/integration/services/commands/tasks/test_create_task_preorder_sku_mirrors_item_integration.py`,
  `backend/app/tests/integration/services/commands/items/test_create_item_sku_template.py`
