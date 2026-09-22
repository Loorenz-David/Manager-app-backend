# HANDOFF_TO_BACKEND_stock_match_property_evaluations_20260922

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_stock_match_property_evaluations_20260922`
- Created at (UTC): `2026-09-22T06:00:00Z`
- Owner agent: `Claude Fable 5.1` (frontend), on the owner's decision after manual testing
- Related:
  - `docs/architecture/under_construction/implementation/stock_report/backend_handoff/HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md`
    — the RATIFIED preview contract this request extends. Its §7 fixes `property_failures[]` as
    `{key, reason}` and promises the element shape is identical to the create endpoint's 409
    `details[].failures[]`. We keep both promises.
  - `…/backend_handoff/HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` §4.3 (the 409) and
    §4.5 (the preview response).
  - Frontend intention: `…/stock_report/planning/intention.md` §8.5 and §12A A2 — the warning
    sheet, currently specified as a list of `{label, explanation}` lines.
- **Asking for:** two additive read-only fields on each failure element, in both places the
  element appears (preview `property_failures[]` and 409 `details[].failures[]`). No shape change
  to anything that exists; no new endpoint; `{key, reason}` stays identical on both.

## Summary

The preview does its job: it says "this item would need an override, and `upholstery` is why".
What the user then sees is:

> **Upholstery** — The item's value is not accepted for this stock need.

That sentence is true and useless. The user is holding an item and looking at a stock need, and the
one question they have — *what does the need want, and what does this item have?* — is exactly
what the response does not carry. They cannot decide "Continue" or "Change item" from a key name.

The owner's target design is a short comparison, **one row per failed criterion only** — matching
properties are not shown:

```
PROPERTY        ASKED              ITEM
Upholstery      Foam / Synthetic   Down         ← not accepted
Wood group      Light              Light teak   ← not accepted (see the grouping rule below)
Lot no.         2291-C             —            ← missing on the item
```

To draw it we need, for each failure, what the matcher compared on each side — **in the same
vocabulary on both sides** (§"The grouping rule").

## Evidence

Captured 2026-09-22 from the managers app during manual testing. Request to
`POST /api/v1/stock-report/items/{id}/match-preview`:

```json
{ "task_id": null, "article_number": "0000405", "sku": null,
  "item_category_id": "itc_01KVX0G0WHH023EWJ200SCK9DE",
  "properties": { "upholstery": "Down", "wood_type": "Teak" }, "quantity": 6 }
```

Response payload:

```json
{ "can_proceed": true, "override_required": true, "refusal_reason": null,
  "property_failures": [ { "key": "upholstery", "reason": "value_not_accepted" } ],
  "matched_item_client_id": null, "values_source": "supplied" }
```

Everything here is correct. The gap is what is absent: which value was rejected and which values
the row accepts.

## Why we cannot derive it client-side

We considered rendering the two columns from what the client already holds — the form's candidate
values and the board row's `properties` — and rejected it:

1. **The matcher compares normalised values; the client holds raw ones.** The row's `properties`
   are "stored, normalized" (api v2 §6.1) and the reason `no_group_for_value` exists because item
   values are mapped to groups before comparison. In the capture above the form sends
   `wood_type: "Teak"` while the row's criterion is keyed differently. A client-side comparison
   would line up values the matcher never compared, and could show a visual match beside a backend
   mismatch — worse than the sentence we have today.
2. **`values_source: "stored"` means the client does not know the item side at all.** The backend
   evaluated the stored item, not the form (preview v2 §3). The lookup prefill is *usually* the same
   values, but the user may have edited a field after the lookup, and the contract itself warns
   that this is the confusing case. Only the matcher knows what it read.
3. **The 409 has no candidate.** On the create-then-409 path the retry sheet must show the same
   rows, and there the client has only `{key, reason}`.
4. **Re-implementing the comparison forks the rule.** The verdict and the values are shown side by
   side; if the client computes the values and the server computes the verdict, they will
   eventually disagree.

The backend already has both values in hand at the moment it builds each failure.

## What we are asking for

### 1. On the preview response — two fields on each `property_failures[]` element

```jsonc
{
  "...": "existing keys, unchanged",
  "property_failures": [
    { "key": "upholstery",
      "reason": "value_not_accepted",             // unchanged, the existing four values
      "accepted_values": ["Foam", "Synthetic"],   // the row's criterion for this key, as evaluated
      "item_values": ["Down"] }                   // what the matcher evaluated on the item side
  ]
}
```

- **`item_values` are the values the matcher actually compared**, after whatever mapping it
  applies, so the two columns are the same kind of thing — see the grouping rule below.
- **`missing_on_item`** → `item_values: []`; that is the dash.
- **`criterion_not_understood`** → `accepted_values: []`; we render "criterion invalid" for that
  row and never show an empty accepted list as "accepts nothing".
- Values are strings, exactly as the matcher sees them; we format for display.
- Nothing else in the response changes. Passing criteria are not reported — we do not need them.

### 2. On the 409 `stock_assignment_property_mismatch` — the same two fields per failure

```jsonc
{ "error": "…", "ok": false, "code": "stock_assignment_property_mismatch",
  "details": [ { "index": 0, "stock_report_item_id": "…", "task_id": "…", "item_id": "…",
                 "failures": [ { "key": "upholstery", "reason": "value_not_accepted",
                                 "accepted_values": ["Foam", "Synthetic"], "item_values": ["Down"] } ] } ] }
```

Additive keys on the existing element, so `{key, reason, accepted_values, item_values}` stays
identical between preview and 409 as the contract promises, and one renderer keeps serving both.

### The grouping rule — owner's decision, please build it exactly

**A failure is reported under the key the criterion is defined on, and both value lists are in
that key's vocabulary.** The stock need and the item must speak the same language in the two
columns, or the user is misled.

Worked example. The item's stored property is `wood_type: "teak"`. The backend maps `teak` to the
group `light teak`. The row's criterion is `wood_group: ["light"]`. The comparison the matcher
actually makes is *group vs group* — `light teak` is not in `["light"]` — so the failure is:

```jsonc
{ "key": "wood_group", "reason": "value_not_accepted",
  "accepted_values": ["light"], "item_values": ["light teak"] }
```

**not** `item_values: ["teak"]`. Showing "Asked: light · Item: teak" looks like a near-match and
leaves the user unable to see why it was refused; "Asked: light · Item: light teak" is the truth
at the level the decision was taken.

Conversely, if a row constrains `wood_type` directly (no grouping involved), the failure is keyed
`wood_type` with the raw values on both sides:

```jsonc
{ "key": "wood_type", "reason": "value_not_accepted",
  "accepted_values": ["oak"], "item_values": ["teak"] }
```

`no_group_for_value` is the one case where the item side cannot be expressed in the group
vocabulary; there, `item_values` carries the raw value that failed to map (`["teak"]`) and the
`reason` tells us to render it as "no known group for: teak".

We do **not** want a separate raw-value field. One vocabulary per row, chosen by the criterion.

## Semantics we are assuming

Please confirm or correct; each changes what we render:

- With `values_source: "stored"`, `item_values` come from the stored item; with `"supplied"`, from
  the request. Either way they are what was compared.
- `accepted_values` are the row's criterion **as stored on the row** (api v2 §6.1 `properties`),
  so the "Asked" column agrees with the tags the board already shows for that need.
- If `quantity` can fail as a criterion (preview v2 §2 says it is matched "like any other"), it
  arrives as a failure with the same two fields; tell us how `accepted_values` expresses a rule
  such as `>= 6` if it is not a set.
- When no item resolves and the request carries an empty `properties: {}`, every criterion fails
  `missing_on_item` with `item_values: []` — a column of dashes is the right thing to show for
  "nothing known yet".

## What we explicitly do NOT need

- **Do not change `reason`, `checks`, `refusal_reason`, `can_proceed` or `override_required`.**
  The verdict logic is right; this is about explaining it.
- **No passing criteria.** Only failures are displayed; do not add an evaluations array for the
  rows that matched.
- **No new endpoint, no batch, no reverse query.** Same call, two more keys per failure.
- **No change to the create request.** `override_property_mismatch` stays as it is.
- **No display strings.** We map `reason` to copy on our side; you send values, not sentences.

## Open questions

- [ ] **Confirm the grouping rule** above matches how the matcher already works: a group criterion
      compares mapped group against group; a plain criterion compares raw against raw; there is no
      case where a criterion on `wood_group` is evaluated against an unmapped `wood_type` value.
- [ ] **Multi-valued item properties.** Can an item carry more than one value for a key (hence the
      arrays)? If never, single strings are fine and we will adapt; we asked for arrays only to
      match the row side.
- [ ] **Cost.** If the matcher already holds both sides when it records a failure, this is a
      serialisation change; if not, say so and we will scope.

## Acceptance criteria

1. For the captured request, the `upholstery` failure carries `item_values: ["Down"]` and the row's
   accepted upholstery values.
2. Every `property_failures[]` element carries both fields; `missing_on_item` → `item_values: []`;
   `criterion_not_understood` → `accepted_values: []`.
3. `values_source: "stored"` → `item_values` reflect the stored item even when the request supplied
   different values for the same key.
3a. Grouping: an item with `wood_type: "teak"` (mapping to group `light teak`) against a row with
   `wood_group: ["light"]` yields a failure keyed `wood_group` with `accepted_values: ["light"]`
   and `item_values: ["light teak"]` — never `["teak"]`. The same item against a row constraining
   `wood_type: ["oak"]` yields a failure keyed `wood_type` with `item_values: ["teak"]`.
4. The 409's `failures[]` elements carry the same two fields with the same semantics, and their
   values equal what a preview of the same triple returns.
5. Once shipped the keys are always present (explicit empty arrays, never omitted); clients that
   ignore them keep working — the current frontend Zod schema strips unknown keys, so this can ship
   before we consume it.

## Interface expectations

- **Endpoint(s):** existing — `POST /api/v1/stock-report/items/{client_id}/match-preview` and
  `POST /api/v1/stock-report/assignments` (409 body only). Additive keys only.
- **Request shape:** unchanged.
- **Response shape:** as above; keys always present once shipped.
- **Error cases:** unchanged.
- **Socket events:** none.
- **Versioning:** none expected — additive on a RATIFIED contract; please issue it as a new dated
  handoff superseding preview v2 §7 for the failure element.

## Frontend contract implications

On delivery, three contained changes inside `packages/stock-report`, no intention reopening:

- `src/api/stock-report-api.ts` — the preview schema and the 409 `details` parser gain the two
  fields (nullish until the final verification handoff, like everything else);
- `src/hooks/use-stock-assignment-gate.tsx` — `toFailures` hands the sheet rows of
  `{label, asked, item, reason}` instead of `{label, explanation}`;
- `src/components/sheets/StockMatchWarningSheetContent.tsx` — renders the failed rows as the
  Property / Asked / Item comparison; the *Change item / Continue* choice and the locked sheet are
  unchanged.

Until it lands, the sheet keeps showing the key and the reason sentence — correct, just thin.

## Document convention

Please issue any answer or correction as a **new dated handoff** rather than editing this file or
the two 2026-09-21 handoffs in place.
