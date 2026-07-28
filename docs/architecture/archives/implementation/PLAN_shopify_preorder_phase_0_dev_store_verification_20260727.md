# PLAN_shopify_preorder_phase_0_dev_store_verification_20260727

## Metadata

- Plan ID: `PLAN_shopify_preorder_phase_0_dev_store_verification_20260727`
- Status: `archived`
- Phase: **0** — **manual, human-executed. Not a Codex task.**
- Parent plan: `PLAN_shopify_preorder_product_20260727.md` (rev 8)
- Depends on: nothing
- Blocks: `PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`
- Owner: David
- Created at (UTC): `2026-07-27T00:00:00Z`
- Last updated at (UTC): `2026-07-27T21:00:00Z`

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

- [→] **0.2 — DEFERRED into the Phase 1 post-implementation verification** *(David's decision,
      2026-07-27)*. Does the `UNLISTED` product stay off the Online Store?

      **Rationale for deferring:** the probability is low — every product in the merchant's live
      Shopify/Zettle workflow is already `UNLISTED` (R11), and Shopify documents the status as
      excluded from search, collections and recommendations by definition. The only realistic leak
      path is a sales channel with `autoPublish: true`. Phase 1's **acceptance criterion 4**
      already requires "absent from the storefront", so the check happens during the dev-store
      verification that gates the release regardless. Deferring costs nothing and removes a
      blocking step.

      **What the deferral does *not* buy, and must not be misread as:** a failure is **not** a
      one-line parameter change. No other `ProductStatus` works — `ACTIVE` is storefront-visible,
      `DRAFT` is invisible to sales channels and therefore to Zettle. The fix is
      `publishableUnpublish`, requiring `read_publications` + `write_publications`, an env change,
      a Shopify Partner Dashboard change, and a **merchant OAuth reauthorization for every
      installed shop**. That is an operational step the merchant must perform, not something a
      debugging pass patches. Escalate for scope approval rather than working around it.

      **Consequence of the deferral:** the reauthorization, if needed, is discovered *after*
      implementation rather than before. Accepted deliberately.

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

1. ✅ Gates 0.1 (PASS), 0.3 (retired) and 0.4 (resolved) are recorded in the parent plan.
2. ✅ Gate 0.2 is **deferred by explicit decision** into Phase 1's post-implementation dev-store
   verification, with the deferral and its consequence recorded above.
3. When 0.2 is eventually run, a FAIL carries an explicit decision beside it — scope approval or
   re-plan — never a silent workaround.

**This plan is complete.** Nothing here blocks implementation.

## Lifecycle transition

- Current state: `approved`
- Next state: `implemented` once all four gates are recorded
- Transition owner: David
