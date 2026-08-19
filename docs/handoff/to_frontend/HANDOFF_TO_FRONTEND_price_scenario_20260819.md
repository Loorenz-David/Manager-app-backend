# HANDOFF_TO_FRONTEND_price_scenario_20260819

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_price_scenario_20260819`
- Created at (UTC): `2026-08-19T18:00:00Z`
- Owner agent: `Claude Opus 5` (backend pipeline coordinator)
- Source plan: `backend/docs/architecture/under_construction/implementation/simple_valuation_editor/master_plan.md`
- Phase artifacts: `.../archive/plan_1/plan_1.md` (pure arithmetic, APPROVED `62ab05e`),
  `.../archive/plan_2/plan_2.md` (read model, APPROVED `97520fb`)
- Authority for every contract below: `.../planning/intention.md`

**This document supersedes nothing and edits nothing.** Where it amends the 2026-08-15
operational handoff, it does so **by reference** (§7) — that file is not touched. Convention
adopted from `HANDOFF_TO_BACKEND_production_time_live_share_state_20260819`.

---

## Backend delivery context

**What backend implemented.** One read-only, task-scoped endpoint that hands you the closed
set of constants the "Expected sold price" screen needs, so the screen can project the
consequences of a price **live, at every frame of a slider drag, with no network round trip**.

The backend already owns the price → budget → allowance function as pure, no-I/O code. This
endpoint publishes the function's *inputs* rather than one evaluated output at a time. That is
the whole design: you get constants, you do the arithmetic locally.

**API changes.** One new route. Nothing existing changed shape, and no existing payload moved.

**Feature flags.** None.

---

## Frontend action required

1. **Fetch once per screen open**, then compute everything locally from the constants. Do not
   re-fetch per drag frame.
2. **Implement `round_half_even` in BigInt exactly as §4 specifies.** This is the one place
   this handoff is not negotiable — a `Math.round` here makes your screen and the server
   disagree at the precise pixel the user is looking at.
3. **Render the chip and the suggestion from `anchors`, never from your own computed
   allowance** (§5.3).
4. **Disable Save when `can_commit` is `false`** (§6) — pressing it is a guaranteed error.
5. **Reconcile after Save** against the commit response, and refetch on mismatch (§6.3).
6. **Handle `model: null` *and* `saved: null` — they are different absences.** `model: null`
   means no slider and no numbers (§5.2). `saved: null` means nobody has priced this item yet,
   and it arrives **with a full `model`** — that is the screen's main use case, not an error
   state (§2, §3).

---

## 1. The endpoint

```
GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario
Auth: ADMIN, MANAGER only
```

**Task-scoped, not item-scoped**, for a reason that matters if you are tempted to call it from
an item context: the typical time and the participating section set only exist relative to a
*task's* steps, and the write this screen pairs with is task-scoped too. Both ends resolve the
same item by the same rule, so the two cannot disagree.

WORKER and SELLER receive `403`. There is no redacted variant — this payload is dense with
money and is not routed to those roles at all.

**Errors:** `404` for an unknown, deleted or cross-workspace task. Envelope is the house one
(`{"data": …, "ok": true, "warnings": []}`); errors carry no `code` field — the identity is the
leading token of `error` up to the first colon.

---

## 2. The payload, exactly as it ships

Written from the shipped serializer, not from a design document.

```jsonc
{
  "task_id": "tsk_…",
  "status": "ok",                    // the twelve-value vocabulary
  "item_binding": "bound",           // bound | detached | mismatched
  "can_commit": true,
  "currency": "swedish_krona",       // null whenever "saved" is null — including the
                                     // unpriced item of §5.2. Do not format money with it
                                     // unchecked.
  "calculation_version": 1,
  "config_fingerprint": "cmv_7a1:pcbv_3f9:v1",   // null exactly when "model" is

  "item": {                          // null when item_binding is "detached"
    "client_id": "itm_…",
    "article_number": "0000608",     // nullable
    "label": "Dining chairs",        // the item's category snapshot — nullable
    "quantity": 6
  },

  "saved": {                         // null when there is no valuation row, and on any
                                     // non-"bound" item_binding
    "valuation_id": "ival_…",
    "expected_sale_price_minor": 855000,   // null under item_missing_expected_price —
                                           // the state §6.2's flow deliberately creates
    "purchase_cost_minor": null,
    "created_at": "2026-08-14T10:24:00+00:00",
    "created_by": {                  // null only if the user row cannot be loaded
      "client_id": "usr_…",
      "username": "Marta Lind",
      "profile_picture": "https://…"   // nullable — null, never an empty string
    }
  },

  "model": {                         // null — see §5.2
    "cost_model_version_id": "cmv_…",
    "basis_version_id": "pcbv_…",
    "residual_percent_milli": 22000,
    "constant_deduction_minor": 0,
    "cost_per_worker_minute_ten_thousandths": 13000000,
    "is_purely_proportional": true
  },

  "typical": {                       // ALWAYS present
    "total_seconds": 12300,
    "is_estimated": false,
    "sections_without_sample": 0,
    "sections_total": 4,
    "method": "median_completed_section_totals",
    "window_days": 90,
    "min_sample_size": 5
  },

  "anchors": {                       // present whenever "model" is; members may be null
    "is_fundable": true,
    "break_even_price_minor": 1211335,
    "suggested_price_minor": 1215000,
    "infeasible_at_or_below_minor": 29
  },

  "domain": {                        // null when there is no usable band
    "rule": "break_even_band_v1",
    "min_minor": 420000,
    "max_minor": 1650000,
    "step_minor": 15000
  }
}
```

**Nullable: `currency`, `config_fingerprint`, `item` and both its string fields, `saved` and
every one of its members except `valuation_id` and `created_at`, `profile_picture`, all four
numeric blocks, and `break_even_price_minor` / `suggested_price_minor` within `anchors`.**
Non-null on every response: `task_id`, `status`, `item_binding`, `can_commit`,
`calculation_version`, `typical` and all seven of its members, and `anchors.is_fundable` /
`anchors.infeasible_at_or_below_minor` when `anchors` is present.

The screen's first render for a brand-new item has `saved: null`, `currency: null` and a fully
populated `model`.

**Note the integer-scaled fields.** `residual_percent_milli` and
`cost_per_worker_minute_ten_thousandths` are integers, **not** the house decimal-as-string,
precisely because you must do exact integer arithmetic with them. A decimal string here invites
a `parseFloat` and reintroduces the float exposure this contract exists to avoid. The unscaled
decimals are deliberately **not** also shipped — two representations of one number is how they
drift.

**`residual_percent_milli` is the residual, not the cost.** `22000` means 22 % of the price is
left for work after deductions — the model deducts **78 %**. It is easily misread.

**Money is whole-item minor units, always.** The backend never multiplies or divides by
`quantity`. `quantity` travels solely as your display divisor — see §8.

---

## 3. What the screen renders, key by key

**`model === null` gates the four numeric blocks and nothing else.** `saved`, `currency` and
`item` are independently nullable — a brand-new item renders with a full `model` and none of
the three. Every row below marked ⚠ needs its own null check.

| On screen | From |
|---|---|
| `1 425 SEK` per piece | draft price ÷ `max(1, item.quantity)`, your side — ⚠ `item` is `null` on `detached` |
| `× 6 pieces · 8 550 SEK total` | `max(1, item.quantity)`, draft price — ⚠ as above |
| `AT PRICE 2h 25m` | `allowance_seconds(P)` — §4 — ⚠ needs `model`, so gate on `model !== null` |
| `TYPICAL 3h 25m` | `typical.total_seconds` — always present |
| chip `Below typical work` | draft price vs `anchors.break_even_price_minor` — §5.3 — ⚠ `anchors` null with `model`; the member is independently nullable |
| `suggested 2 025/piece` | `anchors.suggested_price_minor ÷ max(1, quantity)` — ⚠ as above |
| slider ends `700` / `2 750` | `domain.min_minor` / `max_minor` ÷ `max(1, quantity)` — ⚠ `domain` null with `model`; **and note `2 750`, not the mockup's `2 700` — see §5.4** |
| `Marta Lind · saved version · 14 Aug, 10:24` | `saved.created_by.username`, `saved.created_at` — ⚠⚠ **`saved` is `null` for an item nobody has priced and on any non-`bound` binding; `created_by` is separately nullable. Two checks, not one.** |

---

## 4. The arithmetic — implement this exactly

Three integer operations turn a candidate whole-item price `P` into an allowance in seconds.

```
budget_minor(P)     = round_half_even(P × residual_percent_milli, 100_000)
                      − constant_deduction_minor
allowed_centimin(P) = round_half_even(budget_minor(P) × 1_000_000,
                                      cost_per_worker_minute_ten_thousandths)
allowance_seconds(P)= round_half_even(allowed_centimin(P) × 3, 5)
```

`× 1_000_000` is `10⁴` (undoing the rate's stored scale) × `10²` (expressing the result in
centi-minutes). The third line is the two-step minutes → seconds conversion the server uses;
**a direct budget → seconds shortcut disagrees by up to a second**, which would make this
screen and the production-time screen name different numbers for the same task.

### `round_half_even(a, b)` — the part that must be exact

`a` may be **negative**: `budget_minor(P) < 0` for any price below the constant deduction,
which is exactly the `infeasible` state this screen exists to fix. Every language disagrees
about negative rounding, so implement the reference algorithm, not your platform's primitive:

```js
function roundHalfEven(a, b) {            // BigInt, b > 0n
  let q = a / b, r = a % b;               // JS truncates toward zero
  if (r < 0n) { q -= 1n; r += b; }        // → floor semantics
  const twice = 2n * r;
  const qIsOdd = ((q % 2n) + 2n) % 2n === 1n;   // q may be negative
  if (twice > b || (twice === b && qIsOdd)) q += 1n;
  return q;
}
```

**This transcription was executed, not just written.** It was run in Node and compared against
the shipped Python implementation over **612 cases** — five divisors (`2`, `3`, `5`, `100 000`,
the rate's `13 000 000`), every numerator from `−60` to `+60`, plus the exact operands of the
three published operations at `P = 855 000`. **Zero mismatches**, including every negative tie.
Copy it verbatim; if you rewrite it, re-run that comparison.

**`Number` is forbidden throughout.** `855_000 × 22_000` is already `1.881e10`, and the second
line multiplies by another `10⁶` — well past what a double carries losslessly. **`Math.round`
is half-away-from-zero, not half-even; using it is the single most likely way to ship a screen
that disagrees with the server.**

Two of the three operations can actually land on a tie (the price × residual multiply, and the
rate division). The seconds conversion is provably tie-free over integers — `3·cm mod 5` is
never `2.5` — so **the half-even tie rule never fires there**. It still rounds, and you still
call `roundHalfEven` for it: BigInt `/` truncates toward zero, which disagrees on negative
operands (`allowed_centimin = −1n` → `−1n` half-even, `0n` truncated). Use the function for all
three.

### Display rounding

`AT PRICE` is **rounded to the nearest minute**, not truncated. At `855 000` the allowance is
`8 681 s` = 144.68 min, which renders `2h 25m`; truncation renders `2h 24m`.

### It is an approximation, and here is the bound

The server's persisted formula rounds **each** percentage term separately; this published form
rounds **once**. The difference is bounded by `(n + 1) / 2` minor units, where `n` is the number
of **percentage** terms in the model (not the term count). One percentage term ⇒ ≤ 1 öre ⇒
about **0.046 s** at the rate above; two ⇒ ≤ 1.5 öre ⇒ about **0.07 s**. Either way the largest
error is under a tenth of a second against a display quantised to whole minutes. We assert this
bound by test against the real persisted path, over seven model shapes.

The trade buys you a payload of three integers instead of an unbounded term array, and a
**monotone** budget function — the per-term form is not monotone, so a search over it can be
off by one step.

---

## 5. The blocks, and when they are null

### 5.1 `typical` is always present

`total_seconds` is the sum of the task's participating sections' typical times. A section
participates if it has at least one non-deleted step that is not `SKIPPED`, `CANCELLED` or
`FAILED`.

- `is_estimated: true` means at least one participating section had no usable typical and the
  median of the others was substituted for it — **or that there are no participating sections
  at all.** Say "estimated" in the UI when this is true.
- `sections_without_sample` / `sections_total` let you say *how* estimated.
- When **no** section has a usable typical, `total_seconds` is `0`, `is_estimated` is `true`,
  and `anchors.break_even_price_minor` is `null`. **Show the typical column empty with a
  reason — never "typically 0m".** A typical built on two completed jobs can be wrong by a
  factor, and a manager who trusts it prices the next fifty items on it.

`method`, `window_days` and `min_sample_size` are derivation labels. **Key any explanatory copy
off these fields** rather than hard-coding "90-day median" — when the backend refines how
typicals are derived, those values change and the payload shape does not.

### 5.2 When `model`, `anchors` and `domain` are null

`model`, `anchors`, `domain` and `config_fingerprint` are published together or not at all.
**Four things must hold at once**; `status` is only one of them.

1. **`item_binding` is `"bound"`.** Under `detached` or `mismatched` all four are `null`
   **whatever the status says** — and `mismatched` always reports `ok` or `infeasible`, so
   status alone will tell you the blocks are there when they are not. Check the binding first.
   (§5.5.)
2. **`status` is one of** `ok`, `infeasible`, `item_unvalued`, `item_missing_expected_price`,
   `not_evaluated`. It is `null` for the other seven — the five configuration failures,
   `item_missing_purchase_cost`, and `currency_mismatch`.
3. **The *live* configuration still resolves and its currency still agrees.** `ok` and
   `infeasible` come from the *committed* snapshot and do not consult the live configuration,
   so a task committed while the configuration was healthy reports `ok` after its cost model
   version expires — with every block `null`. This is the same live/displayed split §6.1
   describes for `can_commit` — an expired cost model version empties these blocks and turns
   `can_commit` false at the same time. Beyond that shared cause the two are independent (§6.1).
4. **The model collapses** — a cost model with a purchase-cost term and no purchase cost
   available yields `null` blocks under any status, the same as `item_missing_purchase_cost`.

**Treat `model === null` as the switch, never `status`.** Every rule above is a way for the
blocks to be missing under a status that looks healthy.

**This is the important one:** the screen works for an item **nobody has priced yet**. Under
`item_unvalued` and `item_missing_expected_price` you still get the model, the anchors and the
band — because the missing price is the variable the screen exists to choose. This is a
deliberate change from the 2026-08-15 handoff's §6 table; see §7.

`infeasible` is **not** a degraded state here. It means the allowance is ≤ 0 at the committed
price, and fixing that is exactly what the user came to do. Render the screen fully.

**Never show zeros for a null block.** Keep the frame, name the missing thing, disable the
slider.

### 5.3 The chip and the marker are anchor-driven

Decide `Below typical work` / `Just covers typical work` by comparing the **draft price** to
`anchors.break_even_price_minor`, and place the suggestion marker at
`anchors.suggested_price_minor`. **Do not compare your own `allowance_seconds(P)` against
`typical.total_seconds`.**

Comparing computed values puts the chip's flip at the mercy of the last minor unit of rounding,
exactly at the boundary — the most visible place on the screen to be off by one step. Comparing
against a server integer makes the flip exact and makes the chip and the marker agree by
construction.

`is_fundable` is `false` and `break_even_price_minor` is `null` when no price funds the typical
work — a cost model whose terms consume the whole price, no typical evidence at all, or when no
representable price funds it. Then the chip and the marker are not rendered; your handling is
the same in all three cases.

`infeasible_at_or_below_minor` is the highest whole-item price that buys **no work at all**. It
is never null. Note it is often **not** zero — for the example model it is `29`.

### 5.4 The slider band — and why your mockup's top end moves

`domain` is `null` when there is no usable band. Disable the slider and say why; **do not
invent a band around the saved price** — a band with no anchor invites a manager to drag it and
trust the result.

When present, every value is a multiple of `step_minor`, which is itself a multiple of
`max(1, quantity)` — **see §8.2, and use that divisor, not `quantity`** — so
`min_minor / max(1, quantity)` and its siblings are all exact integers.

**The band is derived, not fixed** (`rule: "break_even_band_v1"`) — 0.35× to 1.35× of the
break-even price, stepped. Fixed ends were rejected: a workspace pricing cabinets at 9 000 a
piece would find every item pinned to the right edge, and a band typed in today stays centred
on today's economics after the hourly cost changes.

**One difference from the mockup, ratified by the owner:** for the mockup's own data the band
runs `700` … **`2 750`** per piece, not `2 700`. The bottom matches exactly; the top is one
step wider. Reproducing `2 700` would mean fitting a constant to one drawing of one item, which
is what choosing a derived band was meant to avoid. **Render the ends you are given.**

If `rule` ever changes value, the arithmetic behind the band changed — re-read this section
rather than assuming.

---

### 5.5 The payload when `item_binding` is not `"bound"`

`item_binding` governs the whole payload and **wins over `status`** — on both non-`bound`
values, every time, not as an edge case.

| Key | `detached` | `mismatched` |
|---|---|---|
| `item` | **`null`** — there is no item row to describe | populated |
| `saved`, `currency` | `null` | `null` |
| `model`, `anchors`, `domain`, `config_fingerprint` | `null` | `null` |
| `typical` | **populated** — it derives from the task's steps alone | **populated** |
| `status` | as resolved | **always `ok` or `infeasible`** |
| `can_commit` | `false` | **as resolved — may be `true`** |

The `mismatched` row is the trap: the status will read `ok`, which §5.2 item 2 lists as a
"blocks present" status, and the blocks are `null` anyway. **Check `item_binding` before
`status`, and `model === null` before both.**

Both states mean the task lost or swapped its primary item. That is an empty state, not an
error — `200`, keep the frame, say what is missing.

---

## 6. Saving

**Save is one call:** `POST /api/v1/item-economics/tasks/{task_client_id}/evaluations/commit`
carrying `expected_sale_price_minor`. It both prices the item and moves the task's working
budget. The rejected alternative — price now, commit later — fails *silently*: the floor keeps
working to an allowance the price no longer funds, and nothing surfaces the gap until the job
overruns.

### 6.1 `can_commit` is load-bearing, not informational

When `false`, **disable the button and say why.** Commit is admitted only when all of: the task
exists and is not deleted; its state is one of `PENDING`, `ASSIGNED`, `WORKING`, `STALLED`,
`READY`; an active PRIMARY item exists and its row is not deleted; a current valuation row
exists; the configuration resolves; the currency agrees; and a purchase cost is present if the
model has a purchase term.

It is computed from the **live** configuration, not from the displayed status — a task
committed while the configuration was healthy can still read `ok` after its cost model version
expires, and committing would then fail. **The same live/displayed split governs the `model`
block** (§5.2 item 3): both are computed from the live configuration, so an expired cost model
version empties the blocks and turns `can_commit` false together. **That shared cause is the
only thing they share** — see the two paragraphs below.

**`can_commit` is deliberately conservative in one direction.** It is computed without knowing
the price or purchase cost you will send, because a GET cannot. The commit endpoint *does*
accept a `purchase_cost_minor` in its body, so a commit carrying one could succeed where
`can_commit` reads `false`. This screen's Save sends only the price, so that never bites — but
if Save is ever extended to send a purchase cost, expect the field to be conservative rather
than wrong, and do not conclude it is broken.

**`can_commit` is unrelated to whether the blocks are present.** Under
`item_binding: "mismatched"` it can read `true` with no model on screen — a saveable task whose
price screen has nothing to show. See §5.5.

### 6.2 Save cannot create the first valuation row — set the purchase price first

**This is the one thing in this document whose omission is silent.** If the item has **no
valuation row at all**, the commit endpoint refuses **regardless of the price in your request
body** — the price is ignored, nothing is saved, and pressing again changes nothing. You will
see this as `can_commit: false` with `status: "item_unvalued"`.

Your planned flow already prevents it: prompting for the purchase price first *creates* the
valuation row, because the purchase cost lives on that row. `PUT /items/{id}/valuation` accepts
a purchase cost **alone**. After that, `status` is `item_missing_expected_price`, `can_commit`
is `true`, and Save works in one call.

**Recorded because the backend cannot enforce it:** if that prompt is ever skipped — for
instance as an optimisation when the cost model has no purchase term — Save fails on every
press. `can_commit: false` is the signal that guards it.

### 6.3 Reconcile after saving

Echo nothing to the server, but **assert the commit response's `production_budget_minor` and
`allowed_worker_minutes` against what you displayed**, and refetch on mismatch. A mismatch
means the configuration moved mid-drag, or the ≤ 1-öre approximation crossed a display
boundary. Refetch-and-tell, never silent save.

`config_fingerprint` is `cost_model_version_id:basis_version_id:v{calculation_version}`; it is
`null` exactly when `model` is. It covers **the configuration and nothing else** — the rate and
the whole term set, because cost model terms are immutable for the life of their version.

**It does not cover the typical, and therefore does not cover the anchors or the band.**
`typical.total_seconds` is a workspace-wide median over a rolling 90-day window, so it moves
when *any* task in the workspace completes a step — and, because the window slides, with time
alone. `break_even_price_minor`, `suggested_price_minor` and all three `domain` values are
derived from it, so **all five can change between two polls with an identical fingerprint**,
and the commit-response reconciliation above cannot see it: the budget and the allowance are
functions of the price and the model, never of the typical.

It also does not cover `item.quantity` or `item.label`.

**So: refetch the scenario on `task:step-state-changed` for *any* task in the workspace, and on
`item:updated` for this item** — not only on a fingerprint mismatch. Both are workspace
broadcasts you already have a socket for; do not filter the step event to this task, because
the typical is a workspace-wide median and any task's step transition can move it.
`item:updated` is emitted on item edits (quantity, category) and, to our knowledge, has not
been named in a handoff to you before — if your client does not handle it yet, this is the
screen that needs it. The window also slides with time alone, which no event covers; a screen
left open for a long session should refetch on reopen regardless.

---

## 7. Amendments to `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`

**That file is not edited. These three amendments live here and supersede it by reference.**

1. **§6's status → treatment table.** It says the numerics are `null` everywhere but `ok` and
   `infeasible`. **For this endpoint only**, `model`, `anchors` and `domain` are also present
   under `item_unvalued`, `item_missing_expected_price` and `not_evaluated` (subject to §5.2 item 4 — the model must collapse). Other endpoints are unchanged.
2. **§8.4's display prohibition** ("do not show '1000 × 5' anywhere near these figures") is
   **lifted for this screen**. Its *contract* stands unchanged and is not negotiable: a
   valuation is per item, never per unit; the wire carries whole-item minor units; the backend
   never multiplies or divides by `quantity`. Per-piece display is a frontend transform at the
   display edge, and `quantity` is shipped for exactly that purpose.
3. **§9.1's refusal is gone.** Sending an inline price on task creation for an item that
   already has a valuation **no longer fails**. It re-prices the item: a new valuation version
   credited to whoever created the task when the values differ, and **nothing written at all**
   when they match. A field you omit keeps its current value rather than being nulled, and a
   currency change counts as a difference.

   **The error identity that refusal raised is retired, and this document deliberately does not
   spell it out.** A backend guard sweeps every live document for retired error identities — precisely so nobody codes against an error that can no longer occur. Search your
   own codebase for the identity you were handling on that path and delete the branch.

**On the last one, an apology and a process change.** §9.1 was corrected by editing the
2026-08-15 file **in place, under its original filename and date**, on 2026-08-19. Your team
cited the stale copy in good faith for four days and built around a refusal that no longer
existed. That will not recur: your convention — a new dated file, superseding by reference — is
adopted, and it is why this document amends rather than edits.

---

## 8. Two divergences you should hear from us, not discover

### 8.1 `AT PRICE` is gross of work already done

This screen's `AT PRICE` is the allowance for the **whole job**, before any of it is worked.
The production-time screen shows what is left to distribute, and it subtracts one thing this
screen does not: `charged_seconds` — the time already logged on steps that were **skipped,
cancelled or failed**. Time worked on ordinary steps is subtracted by neither; it is allocated,
not removed.

**So on a task carrying excluded-step time, the two screens differ by exactly that amount.**
This is deliberate and owner-ratified: this screen compares a plan to a plan — "does this price
fund the job this item needs?" — and sunk time changes what is *left*, not what the job
*costs*. A price that moved with accidents would be worse. Told here because a manager who
notices it and is not told why will file one of the two screens as broken.

### 8.2 `quantity` may legally be zero

`items.quantity` has no database constraint behind it — `quantity >= 1` is enforced by the
application on all three write paths, but a row written before those validators existed could
hold `0`. **Use `max(1, quantity)` as your divisor.** The backend does the same internally.

---

## 9. Validation notes

**Backend validation run.** Full non-`e2e` suite at the phase-2 approval gate:
**2 425 passed / 26 failed / 1 deselected** — the 26 are inherited failures unrelated to this
work, byte-identical to the pre-phase baseline and independently re-measured three times.

The feature ships **105 tests** across two phases. Review found **0 blocking issues**, and 34
mutations applied to the shipped code one at a time confirmed that **no mutation produced a
wrong-but-green payload**. The break-even literal, both slider bands, the rounding table and the
error bound were each re-derived from an independent reference implementation written from the
specification alone.

**Suggested frontend validation.**

1. **The rounding primitive first, before anything else.** Assert
   `roundHalfEven(-3n, 2n) === -2n`, `roundHalfEven(-5n, 2n) === -2n`,
   `roundHalfEven(3n, 2n) === 2n`, `roundHalfEven(5n, 2n) === 2n`. A truncating implementation
   passes the positives and fails the negatives — and negatives are reachable on this screen.
2. **Reproduce our numbers.** With `residual_percent_milli: 22000`,
   `constant_deduction_minor: 0`, `cost_per_worker_minute_ten_thousandths: 13000000`: at
   `P = 855000` you must get `allowance_seconds = 8681` (`2h 25m` at nearest-minute). If you
   get `8680` or `2h 24m`, check your rounding mode and your display rounding in that order.
3. **The chip's flip.** At `P = break_even_price_minor` the chip must read covered; at
   `P − 1` it must not. Drive it from the anchor, not from your allowance.
4. **A null `model`.** Force a non-`ok` status and confirm the screen keeps its frame with the
   slider disabled and no zeros rendered.
5. **`can_commit: false`.** Confirm Save is disabled with a reason, and never fires.

---

## 10. Trace links

- Master plan: `backend/docs/architecture/under_construction/implementation/simple_valuation_editor/master_plan.md`
- Contract authority: `.../planning/intention.md` — §3.1A (rounding), §3.2A (the bound),
  §4.2A (break-even), §7A.1 (the band), §9.2A (binding precedence), §9A.1 (the status table),
  §9A.2 (`can_commit`), §9A.3 (the fingerprint)
- Owner decisions: `.../planning/owner_decisions.md` — D1–D10
- Phase plans: `.../archive/plan_1/plan_1.md`, `.../archive/plan_2/plan_2.md`
- Related: `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`,
  `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` (amended by §7 above)
