# Phase 0 — Dev-store verification

> ⚠️ **This is a manual task for a human, not a Codex prompt.** There is no code to write.
> Every gate requires the real merchant store, the Shopify Admin GraphQL explorer and the Zettle
> POS app. Running them against mocks proves nothing.

## What to do

Open:

- `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_phase_0_dev_store_verification_20260727.md`

Rev 8 cut this from sixteen gates to **four** — the only questions nothing in the code can answer:

1. **Does Zettle import an `UNLISTED` product?**
2. **Does it stay off the Online Store?**
3. **Does Zettle read inventory at Västberga Warehouse?**
4. **Does the supplied price reach Zettle unchanged?**

Record **observed** behaviour, not documented behaviour — merchant Zettle configuration can change
the result.

## The one that can change scope

**Gate 2.** If an `UNLISTED` product leaks onto the storefront, the fix is `publishableUnpublish`
plus `read_publications` / `write_publications` plus **merchant reauthorization** — a scope change
needing approval, not a bug fix. Stop and escalate rather than working around it.

## Where to record outcomes

Append a Review-log entry to the parent plan
`PLAN_shopify_preorder_product_20260727.md`:

```
- `<YYYY-MM-DD>` `David`: Phase 0 outcomes — 0.1 PASS; 0.2 PASS (no autoPublish channel);
  0.3 PASS (Västberga, available=1 visible in Zettle); 0.4 PASS. No failures.
```

Then set the Phase 0 plan's `Status` to `implemented`.

## What was retired, and why

Twelve gates from rev 7 no longer need a dev store — the metafield shape and duplicate-SKU
condition are proven by the merchant evidence (R11), the image fetch is answered by the public
bucket and WebP support (R3), `UNLISTED` and the inventory mutation contract are verified against
the Shopify reference, and the rest belong to hardening that is now backlog. The full list is
retained, collapsed, in the parent plan for whichever hardening ticket eventually needs it.

## Next

Once the four gates are recorded, `PROMPT_phase_1_minimum_delivery.md` is unblocked — that is the
entire pre-order feature, one Codex session.
