# PLAN_shopify_preorder_phase_0_dev_store_verification_20260727

## Metadata

- Plan ID: `PLAN_shopify_preorder_phase_0_dev_store_verification_20260727`
- Status: `approved`
- Phase: **0** — **manual, human-executed. Not a Codex task.**
- Parent plan: `PLAN_shopify_preorder_product_20260727.md` (rev 8)
- Depends on: nothing
- Blocks: `PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`
- Owner: David
- Created at (UTC): `2026-07-27T00:00:00Z`
- Last updated at (UTC): `2026-07-27T00:00:00Z`

## Goal

Answer the four questions that **only a dev store can answer**. Everything else that rev 7 listed
here has since been resolved from code, from merchant evidence, or from the Shopify reference —
see "Retired gates" below.

## Why this is not a Codex task

Each gate requires the real merchant store, the Shopify Admin GraphQL explorer and the Zettle POS
app. There is no code to write, and running them against mocks proves nothing.

## Status: one gate remains

- [x] **0.1 — PASS** *(merchant confirmation, 2026-07-27)*. Zettle imports an `UNLISTED` product.
      This was the load-bearing assumption of the whole feature.

- [ ] **0.2 — STILL OPEN. The only gate left, and the only one that can change scope.**
      Does the `UNLISTED` product stay off the Online Store? Search the storefront and check
      collections. `UNLISTED` is documented as *"active but you need a direct link… doesn't show
      up in search, collections, or product recommendations"*, so a leak would most likely come
      from a sales channel with `autoPublish: true`.
      **A failure is a scope change**, not a bug fix: it needs `publishableUnpublish` plus
      `read_publications` / `write_publications` plus **merchant reauthorization**. Stop and
      escalate rather than working around it.
      *Five minutes of work. Do it before the minimum delivery ships.*

- [x] **0.3 — RETIRED.** Whether Zettle syncs a *particular* location is not a backend concern:
      the frontend chooses the location, and the merchant owns that operational mapping. Consistent
      with the seller-selected model (R7). The Västberga GID remains useful only as the frontend's
      default selector option.

- [x] **0.4 — RESOLVED without a dev store.** The price is the **full product price straight from
      the form** — not per-unit, not derived from any quantity. Already enforced (R11 §7).

## Recording protocol

Append to the parent plan's Review log:

```
- `<YYYY-MM-DD>` `David`: Phase 0 outcomes — 0.1 PASS; 0.2 PASS (no autoPublish channel);
  0.3 PASS (Västberga, available=1 visible in Zettle); 0.4 PASS. No failures.
```

Then set this plan's `Status` to `implemented`.

Record **observed** behaviour, not documented behaviour — merchant-specific Zettle configuration
can change the result.

## Retired gates (rev 8)

Resolved without a dev store, and why:

| Gate | Resolution |
|---|---|
| Metafield shape | Answered by R11 — `custom` / `quantity` / `single_line_text_field`, definition `gid://shopify/MetafieldDefinition/241114906954`. The existing normalizer's dict form already handles it |
| Duplicate exact SKU | Proven by R11 — two products already share `CustomTC3`. `select_exact_variant_match` already raises |
| Shopify can fetch the image | **Answered** — the bucket is public and an object was fetched anonymously; WebP is an accepted Shopify format (R3) |
| `available` vs `on_hand` | Proven by R11 — the older `CustomTC3` product has `on_hand=1`, `committed=1`, `available=0` |
| `UNLISTED` is settable | Verified against the `2026-01` reference: a real `ProductStatus` value on both `ProductCreateInput` and `ProductUpdateInput`, available from `2025-10` |
| `@idempotent`, `changeFromQuantity` | Verified against the reference; correctness is asserted by the minimum plan's unit tests rather than a manual gate |
| Location selector fields, frozen location, cross-shop rejection, retry stability | Belong to hardening, which is backlog in the parent plan — not the minimum delivery |
| `inventoryPolicy` / `requiresShipping` / `taxable` | Observed values recorded in R11; the minimum delivery does not set them, so no decision is blocked |

The full sixteen-gate list is retained, collapsed, in the parent plan's "Clarifications required"
section for whichever hardening ticket eventually needs it.

## Acceptance criteria

1. ~~All four gates recorded~~ — three are done (0.1 PASS, 0.3 retired, 0.4 resolved).
2. **Gate 0.2's outcome is recorded before the minimum delivery ships**, since a failure changes scope.
3. A FAIL on 0.2 carries an explicit decision beside it — proceed, scope change, or re-plan — not
   a workaround.

## Lifecycle transition

- Current state: `approved`
- Next state: `implemented` once all four gates are recorded
- Transition owner: David
