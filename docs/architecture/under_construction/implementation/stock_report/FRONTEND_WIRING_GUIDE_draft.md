---
subject: stock_report — what the frontend must change to run against the finished backend
status: READY — phase 14 re-verified and re-issued the contract; this guide is updated to match
date: 2026-09-22
actor: orchestrator
authority: owner, 2026-09-22 — the wiring stage; BL-1 ruled "queue as the first item of the wiring stage"
---

# Stock Report — frontend wiring guide

**Read this instead of re-reading the API.** Every route, shape and event already works and the
frontend already calls almost all of them correctly. This document is only the **delta**: the
places where the two sides disagree, ordered by what breaks first.

**The contract moved on 2026-09-22, and this guide is written against the new one.** Phase 14
re-verified the published contract field by field against shipped code, found one real error, and
re-issued: **`HANDOFF_TO_FRONTEND_stock_report_api_20260922.md` is now the document to build
against.** The previous `…_api_v2_20260921.md` was **moved unedited** into `archived/`.
`…_match_preview_v2_20260921.md` is **not** superseded and is still current.

**So the frontend's `backend_handoff/` folder now holds two dead documents, not one** — see W-4.

**Verified against shipped code**, not against documents: `routers/api_v1/stock_report.py`,
`domain/stock_report/serializers.py`, `criteria_normalization.py`, and the commands and queries
behind them. Where a document and the code disagreed, the code won and the document is listed as
the defect.

---

## The one-paragraph summary

The integration is in good shape. **No key the frontend expects is missing from the backend** — I
checked all four shapes key by key. What is wrong is concentrated in three places: one schema that
is **too strict** and can blank the whole board, one cache invalidation that is **missing** and
strands an open detail page, and **error handling that discards the message** so two operations fail
silently. Everything after that is hygiene: the frontend still has a superseded contract sitting in
its folder, and its schema is loose in places the backend now guarantees.

---

# BLOCKING — fix before live testing

## W-1. One odd `properties` value from Scanner blanks the entire board

**This is the one that can dark the board in production, and it is first for that reason.**

**What happens.** `GET /items` returns the whole list. The frontend validates the whole array in one
`safeParse` (`packages/stock-report/src/api/stock-report-api.ts:18-20`). Its schema
(`stock-report.types.ts:81`) requires every `properties` value to be `string[] | null`:

```ts
properties: z.record(z.string(), z.array(z.string()).nullable()).nullable().optional(),
```

**Why the backend can break that.** `normalize_stock_criteria`
(`domain/stock_report/criteria_normalization.py:6-22`) converts only two things: a non-blank string
→ `[string]`, and a non-empty all-string list → sorted unique list. **Everything else falls through
untouched** — an integer, a boolean, a blank `""`, a mixed list `["a", 1]`, a nested object. And the
demand webhook validates only that `properties` is a dict at all
(`stock_demand_request.py:53-56`: `properties_ok = isinstance(properties_raw, dict)`), nothing about
the values. **Scanner controls those values.**

**The blast radius is the whole list, not the row.** One bad row fails the array parse, `request()`
throws `ApiRequestError(502, "invalid_response", …)` (`packages/api-client/src/api-client.ts:169-175`),
and the board goes to its error state for **every** row — with the raw zod blob rendered verbatim to
the user (`use-stock-report-board-controller.ts:42` → `StockReportBoardView.tsx:98-101` →
`StockReportBoardStates.tsx:29`).

**What to change.** Loosen to `z.record(z.string(), z.unknown())` and coerce inside
`toStockReportPropertyTags` (`stock-report.types.ts:146-153`, which currently calls
`values.map(titleCase)` and would throw on a bare string) — **or** wrap each value in `.catch(null)`.
Separately, stop piping `ApiRequestError.message` into user-visible copy when
`code === "invalid_response"`.

**Note the precedent in your own file.** The same defence was already applied to `priority` and the
reason was written down at `stock-report.types.ts:86-88`: *"Preserve unknown strings long enough for
the mapper to drop only that row instead of rejecting the complete response (B18)."* The rule was
found once and not carried to the neighbouring field. Applying it to `properties` is finishing a
decision you already made.

**Backend follow-up, filed separately:** the shipped normaliser is permissive about values Scanner
can send. Hardening it is a backend change with its own intention, not part of this wiring.

## W-2. Deleting a row strands an open detail page on "Loading stock need…" forever

**What happens.** There is **no single-row read endpoint** — `routers/api_v1/stock_report.py` defines
ten routes and none is `GET /items/{client_id}`. So the detail surface sources its row **only** from
the board list caches (`surfaces/StockReportDetailSlidePage.tsx:45-49`) and renders a permanent
`"Loading stock need…"` when the lookup misses (`:98-103`).

On `stock_report_item:deleted` the socket handler removes the row from **every** list cache
(`packages/stock-report/src/socket-events.ts:48-52`). With the detail surface open: row leaves cache
→ view model is null → the page hangs on "Loading" and never recovers.

The escape hatch exists but cannot fire. `isMissing` (`:52-55`, `:60-62`) only triggers when the
**assignments** query 404s — and nothing refetches it (`staleTime: 60_000`,
`use-stock-report-queries.ts:13`), because `:deleted` does not invalidate
`stockReportKeys.assignments()`.

**This is not hypothetical.** Scanner's `stock-demand-deleted` webhook (phase 13A, shipping in this
batch) deletes rows **in a loop**, underneath whoever is looking at them.

**What to change.** In `socket-events.ts`, have `stock_report_item:deleted` also invalidate
`stockReportKeys.assignmentList(client_id)` so the 404 path fires and the surface closes — or close
the detail surface directly when its `stockNeedId` disappears from the caches.

## W-3. Both `PATCH`es fail silently

**What happens.** `use-stock-report-actions.ts:25` and `:41` handle `onError` by restoring the
previous cache and nothing else. No message, no toast.

**When the user sees it.** `PATCH …/priority-order` has two real refusals the UI can still provoke —
`STOCK_REPORT_ROW_HAS_NO_PRIORITY` and `STOCK_REPORT_TARGET_OUT_OF_RANGE` — for example a drag racing
a concurrent `stock_report_item:updated` that changed the group size, or a row whose priority another
user cleared between render and drop. **The card snaps back with no explanation.**

**What to change.** Add a `notify.error` on both mutations: use the human `error` string for the
`{error, ok: false}` shape, and fixed copy for the pydantic `detail`-array shape (see W-5).

---

# SILENT DIVERGENCES — correct today, wrong later

## W-4. The frontend is still carrying a superseded contract, and waiting on a handoff that already arrived

The **implementation** already adopted v2 — `planning/intention.md:43` and `:620-631` carry the
amendment, `handoffs/LOGIC_PHASE_HANDOFF.md:16-18` says "Adopted API v2", and the shipped TypeScript
reflects v2. **But three artefacts still point at v1, and v1 sits in the frontend's folder with
nothing marking it dead** (the backend moved its own copy to `archived/`):

| File | Line | What it does |
|---|---|---|
| `prompts/PROMPT_02_codex_logic_phase.md` | 28 | tells the logic implementer to read the **v1** handoff as source 3 |
| `planning/raw_intention.md` | 22 | names v1 by absolute path as "the" API documentation |
| `handoffs/LOGIC_PHASE_HANDOFF.md` | 51-55 | waits for a "promised final verification handoff" — **it has now arrived**: it is `…_api_20260922.md` |
| `backend_handoff/` (whole folder) | — | holds **v1 and v2**, both now dead, and **not** the current `…_api_20260922.md` |

That last one matters most. It says `item_category.image_url` stays nullish in the schemas *until*
the promised verification handoff. **v2 is that handoff.** Nothing further is coming unless plan 14
finds a divergence.

**What anyone re-reading v1 will reintroduce:** `item_category` as **three** keys (v2 and
`serializers.py:35-40` ship **four**); "treat every field as possibly null" (v2 §6 pins nullability —
this is the direct cause of W-5); a claimed 11-or-12 field contradiction in the compact task shape
(v2 pins **12**); and "payloads arrive in `extra`" when the wire payload is **flat**
(`socket_handler.py:59-63` sends `{"client_id": …, **event.extra}`).

**What to change.** Copy in `HANDOFF_TO_FRONTEND_stock_report_api_20260922.md` from the backend's
`handoffs/to_frontend/`; move **both** `…_api_20260921.md` (v1) and `…_api_v2_20260921.md` (v2) into
`backend_handoff/archived/`; repoint `PROMPT_02_codex_logic_phase.md:28` and `raw_intention.md:22`
at the **20260922** file; and rewrite `LOGIC_PHASE_HANDOFF.md:51-55` — the verification handoff it
is waiting for has arrived, and `item_category.image_url` can stop being nullish in the schemas.

**Keep `…_match_preview_v2_20260921.md` exactly where it is.** It is not superseded.

## W-5. Every field is optional-and-nullable because v1 said nullability was unpinned

`stock-report.types.ts:70-127` applies `NullishString` / `NullishNumber` to fields the backend
**guarantees**:

| Field | Frontend | Backend truth |
|---|---|---|
| `item_category` | nullable + optional | always an object; `item_category_id` is `nullable=False` |
| `item_category.name`, `.major_category` | nullish | both `nullable=False` |
| the four quantities | `NullishNumber` | `nullable=False, default=0` — always integers |
| `properties` | nullable + optional | `JSONB, nullable=False` |
| assignment `state`, `item_id`, `item`, `task` | nullish | always present; `item`/`task` batch-loaded and required |

**The cost is that a real backend regression validates fine.** A dropped `image_url` or a null
`quantity_requested` silently renders the `?? null` / `displayNumber(…) → 0` fallbacks
(`:135-137`, `:169-177`) instead of failing loudly.

**What to change.** Tighten `stock-report.types.ts` to v2 §6's pinned nullability and delete the dead
fallbacks. Your own handoff already names this file as the single tightening point.

**Do this after W-1, not before** — W-1 loosens one field deliberately, and the two changes touch the
same file.

## W-6. The contract's wrong `properties` example — FIXED, but only in the new document

The old v2 contract §6.1 showed `"properties": { "wood_group": "teak" }`. **The stored normalized
form is `{"wood_group": ["teak"]}`** — `criteria_normalization.py:9-10`, and
`criteria_matcher.py:96` does `token in accepted`, a membership test against a list.

**Your code was right and the document was wrong.** It is corrected in
`…_api_20260922.md`, and the correction is called out explicitly in that document's §0.

**Why this still needs your attention:** the wrong example is still sitting in the **archived** v2
file, which is still in your `backend_handoff/` folder and not marked dead. Anyone reading it would
"fix" a correct schema into a broken one. **That is W-4's real cost, and it is why W-4 is not just
tidying.**

**There is now a test that stops this class of error coming back.** `test_stock_report_docs.py`
parses the published document's field/nullability table and compares it field by field against the
shipped serializers. I planted three mutants against it — flip a nullable field to non-nullable,
flip a non-nullable to nullable, delete a table row — and all three redden it.

## W-7. Assumptions that hold today and are undefended

- **`priority_order` must be a true integer.** `use-stock-report-actions.ts:33` sends `toIndex + 1`
  from a dnd-kit array index, which satisfies `StrictInt`. The string `"2"` is a **422**, not coerced.
  A future fractional drop position becomes a silent 422 (see W-3).
- **`priority` must always be sent.** The key has **no default** — omitting it is a 422; `null` is
  legal and means "clear". `stock-report-api.ts:53-63` always sends it explicitly and
  `StockReportPrioritySheetPage.tsx:11-12` converts `"unset"` → `null` rather than omitting. Correct
  — and worth a test, because `JSON.stringify` drops an `undefined` value and would produce the 422.
- **Do not "fix" the `unset` filter into `priority=high,medium,low`.** Omitting `priority` means
  *null-priority rows only*, not "all rows", and the board relies on exactly that.

---

# NOT BROKEN — checked, aligned, leave alone

Recorded so nobody spends time here.

- **Realtime: fully aligned.** All six events subscribed, typed, and registered in all three apps.
  The builders put fields in `extra` but the socket handler flattens to `{"client_id": …, **extra}`
  on the wire, which is exactly what the frontend parses. Every handler `safeParse`s and falls back
  to an invalidate, so payload drift degrades to a refetch rather than a crash.
- **Error envelopes are distinguished correctly** at the api-client boundary — `ok`-first branching,
  `code`/`details` lifted, the two structured assignment errors fully handled including the 409 →
  override → resend loop and the eleven-reason vocabulary. Only the **pydantic 422** branch collapses
  to `"Request failed."` (W-3/W-5 territory).
- **No pagination anywhere, on either side** — by explicit product decision. Aligned.
- **Match preview** is called correctly, including the required `item_category_id`, the mutually
  exclusive `article_number`/`sku`, and branching on `can_proceed` rather than `refusal_reason`.
- **Roles.** The frontend is *narrower* than the backend for assignment (it additionally requires the
  `wood_worker` specialization). Intentional, fail-closed, safe.
- **Unused-but-harmless surface:** 5 row keys, 6 assignment keys, 1 item key, 6 task keys and 3 image
  keys are sent and dropped by non-strict zod objects. `GET /consistency`, `POST /repair` and
  `DELETE /items/{id}` have no frontend caller by ratified decision.

---

# One thing the frontend built that the backend will never serve

**The board search row does nothing.** `components/board/StockReportSearchRow.tsx` renders and its
value is held in the controller, but it filters nothing — it only suppresses reorder. `GET /items`
has **no search parameter and none is planned**; the UI handoff says plainly "it is inert today".

Because the list is complete and unpaginated, **client-side filtering is the whole fix** and needs no
backend change. Either do that or hide the row until there is a reason for it. Shipping an inert
search box to users is the worst of the three.

---

# Order of work

1. **W-1** — the only one that can dark the board in production.
2. **W-2** — make `:deleted` invalidate the assignments cache. Do this **before** 13A's delete
   webhook goes live, because that one deletes rows in a loop underneath open surfaces.
3. **W-3** — surface the two `PATCH` failures.
4. **W-4** — archive the v1 copy and repoint the three references. Cheap, and it stops the next
   person reintroducing three-key `item_category`.
5. **W-5** — tighten the schema, after W-1.
6. **W-7** — add the `priority`-always-sent test.
7. The search row — decide: implement client-side, or hide.
