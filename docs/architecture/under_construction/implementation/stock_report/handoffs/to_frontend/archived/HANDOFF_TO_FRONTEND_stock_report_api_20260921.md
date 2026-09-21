# HANDOFF_TO_FRONTEND_stock_report_api_20260921

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_stock_report_api_20260921`
- Created at (UTC): `2026-09-21T09:00:00Z`
- Owner agent: pipeline orchestrator (Claude Opus 5), on the owner's instruction
- Source plan: `backend/docs/architecture/under_construction/implementation/stock_report/master_plan.md`
- Source contract: `.../stock_report/planning/intention.md` (RATIFIED — the authority for everything marked STABLE)
- Backend state at issue: **phases 1–7 VERIFIED** (batches A and B APPROVED). Phases 8–14 not built.

---

## 0. Read this first — the three tiers

This handoff is issued **early and deliberately**, so the frontend can work in parallel with backend
batches C and D. That means most of it describes endpoints that **do not exist yet**. Every section
is tagged, and the tags are the whole point:

| Tag | Meaning | Safe to build against? |
|---|---|---|
| **STABLE** | Taken from the ratified intention or from shipped, verified code. Will not change. | **Yes.** |
| **PROVISIONAL** | Written down in a plan, but nothing has been built or run. The shape is the current intent, not a delivered contract. | Build the *shape*, expect field-level surprises. |
| **NOT PINNED** | Genuinely undecided. Listed in §8 so you do not have to guess. | **No.** Ask before assuming. |

**Nullability and exact field types are NOT in this document, for any endpoint.** That is
deliberate: the backend derives the nullability contract from shipped code in its final phase
(phase 14), and inventing it now is how a previous handoff cost this team four days. §8 says what
you will get and when.

**This file is never edited in place.** If anything here changes, a new dated handoff supersedes it
and this one is archived. If you are reading a copy, check that no later
`HANDOFF_TO_FRONTEND_stock_report_api_*` exists.

---

## 1. What is actually live today

Three endpoints are shipped and verified. **None of them is a board endpoint.**

- `GET /api/v1/stock-report/consistency` — admin diagnostics
- `POST /api/v1/stock-report/repair` — admin repair
- `POST /api/v1/location-tracker/webhooks/stock-demand` — inbound from Scanner, not called by you

The board itself — listing rows, setting priority, reordering, drilling into assignments — is
**phase 12 and 13, the backend's last batch**. Plan your sequencing around that: the surface you
most want is the furthest out. The parts you can build *now* against a stable contract are the
**realtime event handling, the permission model, the error handling and the assignment override
dialog** (§2, §3, §4, §6).

---

## 2. Global conventions — **STABLE** (verified in shipped code)

### Success envelope

```json
{ "data": <object or array or null>, "ok": true, "warnings": [] }
```

Source: `app/beyo_manager/routers/http/response.py:6-12`. Every endpoint below wraps its documented
payload in this. Where this document says a response is `{"stock_report_items": [...]}`, the wire
shape is `{"data": {"stock_report_items": [...]}, "ok": true, "warnings": []}`.

### Failure envelope

```json
{ "error": "<human-readable message>", "ok": false }
```

Source: same file, lines 15-25. The `error` string is for humans — **do not parse it, do not
switch on it.** Where a machine-readable cause exists, it arrives as a separate `code` key (§6).

### ⚠ The 403 exception — this one breaks the envelope

A role refusal is raised by FastAPI, not by the service layer, so it renders:

```json
{ "detail": "Insufficient role permissions." }
```

**No `ok`, no `error`.** Source: `app/beyo_manager/routers/utils/jwt_dep.py:41-49`. This appears in
no other project document; it is stated here because a client that assumes the standard envelope
will crash on every permission denial. Special-case status 403 before you read the body.

### Authentication

- **Frontend endpoints:** the existing JWT. Workspace is taken from the token — you never send a
  workspace id.
- **Scanner webhooks:** an `x-api-key` header, no JWT, no role. Listed here only so you know they
  exist and are not yours to call.

---

## 3. Realtime events — **STABLE** (ratified §9D / contract MC-19)

Six event names, three payload shapes. Payloads arrive in `extra`.

| Event name | `extra` |
|---|---|
| `stock_report_item:created` | `{}` |
| `stock_report_item:deleted` | `{}` |
| `stock_report_item:updated` | `{"quantity_requested": int, "quantity_in_queue": int, "quantity_in_progress": int, "quantity_awaiting": int, "priority": "high"\|"medium"\|"low"\|null, "priority_order": int\|null}` |
| `stock_task_assignment:created` | `{"stock_report_item_id": str, "task_id": str, "state": str}` |
| `stock_task_assignment:state-changed` | same three keys |
| `stock_task_assignment:deleted` | same three keys (the state *at* deletion) |

`priority` and `state` are always **plain lowercase strings**, never enum objects — verified in
`_events.py` on the shipped tree, and pinned by a criterion row. `state` is one of six values:
`in_queue`, `in_progress`, `awaiting`, `resolved`, `failed`, `resolved_early`.

A `:created` event carries `{}`, so **on `stock_report_item:created` you must fetch** — the payload
tells you nothing but the id.

### Delivery rules you must design for

- **At most one event per entity per request**, and only on a real net change.
- **A no-op emits nothing.** Setting priority to the value it already has produces no event.
- A replay, or a rolled-back request, emits nothing.
- Events are dispatched **after** the transaction commits — never mid-write.
- Reordering emits one `:updated` per row whose order actually moved, including neighbours you did
  not touch.
- Deleting a row emits `:deleted` for it, `:deleted` per assignment, and `:updated` for shifted
  neighbours — but **no `:updated` for the deleted row itself**.
- Deleting an assignment in a terminal state moves no counter, so it emits **no** row `:updated`.

⚠ **Timing caveat:** the coalescing logic that guarantees "at most one event per entity" ships in
phase 8. Until then, treat the guarantee as intent rather than observed behaviour.

---

## 4. Role matrix — **STABLE** (ratified §9E)

| Operation | ADMIN | MANAGER | WORKER | SELLER |
|---|---|---|---|---|
| List stock report rows | ✓ | ✓ | ✓ | ✓ |
| List a row's assignments | ✓ | ✓ | ✓ | ✓ |
| Create assignments | ✓ | ✓ | ✓ | ✗ |
| Delete assignments | ✓ | ✓ | ✓ | ✗ |
| Set priority | ✓ | ✓ | ✗ | ✓ |
| Set priority order | ✓ | ✓ | ✗ | ✓ |
| Delete a row | ✓ | ✓ | ✗ | ✗ |
| Read consistency report | ✓ | ✓ | ✗ | ✗ |
| Run repair | ✓ | ✓ | ✗ | ✗ |

Note the two asymmetries — they are intentional, not typos: **WORKER can assign but not prioritise;
SELLER can prioritise but not assign.**

---

## 5. Endpoints

### 5.1 `GET /api/v1/stock-report/consistency` — **SHIPPED**

Admin diagnostics. No request body, no params.

```json
{ "workspace_id": "...", "checked_at": "<ISO>", "divergences": [
  { "kind": "...", "client_id": "...", "field": "...", "stored": ..., "expected": ... } ] }
```

Sorted by `(kind, client_id, field)`. **An empty `divergences` list means consistent.**

`kind` is one of: `counter_in_queue`, `counter_in_progress`, `counter_awaiting`, `task_flag`,
`order_density`, `priority_order_nullness`, `goal_total`, `signature`.

⚠ **`stored`/`expected` are heterogeneous.** Integers for the counter kinds, `goal_total` and
`order_density`; `int|null` for `priority_order_nullness`; a string for `signature`; and the
**strings `"true"`/`"false"`** for `task_flag`. Do not assume a number.

### 5.2 `POST /api/v1/stock-report/repair` — **SHIPPED**

Admin repair of the whole workspace. **Takes no body — any body you send is ignored**, so there is
no way to scope it. Response:

```json
{ "repaired": [<divergence>...], "not_repaired": [<divergence>...] }
```

`not_repaired` holds only `signature` divergences: re-signing a row could collide it with a live
row, so the backend reports and refuses rather than merging.

### 5.3 `POST /api/v1/stock-report/assignments` — **PROVISIONAL, batch C**

Request:

```json
{ "entries": [ { "stock_report_item_id": "...", "task_id": "...", "item_id": "...",
                 "override_property_mismatch": false } ] }
```

At least one entry. **Unknown fields are rejected with 422** — this is a local API and it is strict.

Response — **the full assignment shape, identical to `GET .../assignments`** (owner ruling
2026-09-21, master plan §9B): `{"stock_task_assignments": [ <see §5.8 for the shape> ]}`. You can
render a newly created assignment without a second request.

Errors: see §6 — this endpoint has the two structured ones.

### 5.4 `POST /api/v1/stock-report/assignments/delete` — **PROVISIONAL, batch C**

Request `{"client_ids": ["...", ...]}`, at least one. Response `{"deleted_client_ids": [...]}`.

**404 if any id is absent, already deleted, or belongs to another workspace — and nothing is
deleted.** It is all-or-nothing; do not expect partial success.

### 5.5 `GET /api/v1/stock-report/items?priority=high,medium,low` — **PROVISIONAL, batch D**

⚠ **The filter's default is a trap.** Omitting `priority`, or sending it empty, returns **only rows
whose priority is null** — not all rows. To list the prioritised board you must pass the values
explicitly. An unrecognised token is a 422.

**Unpaginated by design.** Pagination is an explicit non-goal; expect the full set.

Response `{"stock_report_items": [...]}`, each element carrying: `client_id`, `item_category`
(`{client_id, name, major_category}`), `properties`, `properties_signature`, the four quantities
(`quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`),
`priority`, `priority_order`, `created_at`, `updated_at`, `created_by_id`, `updated_by_id`.

Ordering: `high → medium → low`, then `priority_order` ascending. Null-priority rows list by
`created_at`, then `client_id`.

### 5.6 `PATCH /api/v1/stock-report/items/{client_id}/priority` — **PROVISIONAL, batch D**

Body `{"priority": "high"|"medium"|"low"|null}`. **The id goes in the path, never in the body**
(owner ruling 2026-09-21). Response `{"stock_report_item": {...}}`, same element shape as §5.5.

Setting the value it already has is a no-op: you get the row back, and **no event fires**.

### 5.7 `PATCH /api/v1/stock-report/items/{client_id}/priority-order` — **PROVISIONAL, batch D**

Body `{"priority_order": <int>}`. Response as above.

Two documented refusals, both **422 in the plain envelope with no `code` key**:
`STOCK_REPORT_TARGET_OUT_OF_RANGE` (the target is outside `1..n` for its group) and
`STOCK_REPORT_ROW_HAS_NO_PRIORITY` (the row's priority is null, so it has no group to order within).

### 5.8 `GET /api/v1/stock-report/items/{client_id}/assignments` — **PROVISIONAL, batch D**

Returns **non-deleted assignments in every state**, ordered by `created_at`, then `client_id`.
Response `{"stock_task_assignments": [...]}`, each element:

`client_id`, `state`, `stock_report_item_id`, `task_id`, `item_id`, `quantity`,
`property_mismatch_overridden`, `credited_history_record_id`, `created_at`, `created_by_id`,
`updated_at`, `updated_by_id`, plus nested:

- `item` — `client_id`, `article_number`, `sku`, `quantity`, `item_category_snapshot`,
  `item_major_category_snapshot`, `item_images` (each `{client_id, image_url, width_px,
  height_px, file_size_bytes}`)
- `task` — the compact task shape (see NOT PINNED #3)

### 5.9 `DELETE /api/v1/stock-report/items/{client_id}` — **PROVISIONAL, batch D**

**No request body.** Response `{"client_id": "..."}`. 404 (`"Stock report item not found."`) if
absent, already deleted, or foreign.

Semantics worth surfacing in your UI: this soft-deletes the row, its history, **and every
assignment in any state**. The deleted row keeps its own priority and order while the rest of the
group closes the gap.

### 5.10 Scanner webhooks — **not yours to call**

`POST /api/v1/location-tracker/webhooks/stock-demand` (shipped),
`.../items-processed` (batch C), `.../stock-demand-deleted` (batch D). Inbound from the Scanner app,
key-authenticated. Listed so you recognise them in logs.

One frontend-visible consequence: **a Scanner rule change can delete a board row and all its
assignments underneath the user.** A later demand creates a *fresh* row with no priority and no
assignments — users must re-add them by hand. Your UI should survive a row vanishing.

---

## 6. Assignment errors and the override flow — **STABLE** (ratified §9C)

These two are the only endpoints that return a machine-readable `code`.

### 422 — refused

```json
{ "error": "...", "ok": false, "code": "stock_assignment_refused",
  "details": [ { "index": 0, "reason": "item_already_assigned" } ] }
```

`index` is the zero-based position in the `entries` array you sent. The closed reason vocabulary:

`duplicate_item_in_batch`, `duplicate_task_in_batch`, `stock_report_item_not_found`,
`task_not_found`, `item_not_found`, `item_not_task_primary`, `already_processed_by_scanner`,
`task_failed_or_cancelled`, `item_already_assigned`, `item_has_no_category`, `category_mismatch`.

### 409 — property mismatch, the overridable one

```json
{ "error": "...", "ok": false, "code": "stock_assignment_property_mismatch",
  "details": [ { "index": 0, "stock_report_item_id": "...", "task_id": "...", "item_id": "...",
                 "failures": [ { "key": "wood_type", "reason": "value_not_accepted" } ] } ] }
```

`failures` is sorted by key. `reason` is one of `missing_on_item`, `value_not_accepted`,
`no_group_for_value`, `criterion_not_understood`.

### The override flow — implement it exactly this way

1. On 409, show the listed failures to the user.
2. On confirmation, **resend the whole batch**, setting `override_property_mismatch: true` on the
   entries that were listed.
3. The retry is evaluated **from scratch** — it is a new request, not a continuation.

**Precedence guarantee:** a batch containing any hard failure answers 422 even if other entries also
mismatch. So a 409 means *every other entry was fine*, and you never offer an override for a batch
that would fail anyway.

---

## 7. What will never exist (so you do not wait for it)

Explicitly out of scope, from the ratified intention §12:

- No history-read endpoint
- No pagination anywhere
- **No endpoint to create a stock report row by hand** — rows exist only because Scanner asked for them
- No restore of a deleted row
- No automatic assignment
- No workspace-wide view of early-resolved items
- `is_stock_assignment` on tasks is internal and is not surfaced

---

## 8. NOT PINNED — do not guess these

1. **Field types and nullability, for every endpoint.** Deliberately deferred: the backend derives
   the nullability contract by reading shipped serializers in its final phase. **You will get this
   in the phase 14 handoff**, which is the last thing the backend ships. Until then, treat every
   field as possibly null and do not encode assumptions in types you will have to unwind.
2. **Datetime formats.** `created_at`/`updated_at` are stated as ISO UTC in one plan and left
   unqualified in another; the task timestamps (`ready_by_at`, `closed_at`, `completed_at`) have no
   stated format at all. Assume ISO 8601 UTC, and flag it if you see otherwise.
3. **The compact task shape has a field-count contradiction.** The intention lists twelve names
   (`client_id`, `task_type`, `priority`, `state`, `title`, `return_source`, `ready_by_at`,
   `return_method`, `created_at`, `updated_at`, `closed_at`, `completed_at`); plan 13 calls it
   "the eleven fields". One is wrong. **Treat the twelve-name list as the intent** and expect
   confirmation.
4. **The 404 message text** for `POST /assignments/delete` is unspecified. Do not match on it.
5. **Query-param plumbing** for `GET /items` is not specified at the router level. The param name
   and comma-list format above are from the contract and are reliable; the mechanics are not yours
   to worry about.

---

## 9. Frontend action required

Work that is safe to start **now**, against STABLE contracts only:

1. **Realtime event handling** — all six events, the three payload shapes, and the delivery rules in
   §3. In particular: handle `:created` as "fetch me", and handle a row disappearing.
2. **The 403 special case** — before anything else. Status 403 returns `{"detail": ...}`, not the
   envelope.
3. **The permission model** — §4, including the two asymmetries.
4. **The assignment override dialog** — §6. The error vocabularies are closed and ratified, and the
   retry semantics are fixed.
5. **Error handling generally** — envelope, `code` where present, and never parsing `error`.

Work to **shape but not finalise**: the board list and drill-down (§5.5, §5.8) — the shapes are
provisional and the endpoints are in the backend's last batch.

Work **not to start**: anything depending on field nullability or exact types.

---

## 10. Validation notes

- Backend validation at issue: phases 1–7 VERIFIED; full suite **21 failed / 3445 passed / 2
  skipped**, the 21 failures being a published pre-existing baseline unrelated to this project.
- The three shipped endpoints in §5.1–5.2 were confirmed against live router code, not only against
  the plan.
- Everything marked PROVISIONAL has **no** backend validation, because it has no implementation.
- Suggested frontend validation: mock the STABLE contracts (events, errors, roles) and assert
  against this document. Do not build fixtures for PROVISIONAL response fields yet.

## 11. Trace links

- Master plan: `.../stock_report/master_plan.md` — §6.6 routes, §6.5 signatures, §9A lesson
  register, **§9B the two owner API rulings recorded here**
- Ratified intention: `.../stock_report/planning/intention.md` — §8A envelopes, §9C assignments,
  §9D events, §9E roles, §12 non-goals
- Scanner-side contract (for reference): `docs/handoff/to_scanner/STOCK_REPORT_WEBHOOKS_v2_20260919.md`
- Superseding handoff, when it exists: the phase 14 frontend handoff, which will carry the
  nullability contract derived from shipped code
