# Phase 0 — Dev-store verification

> ⚠️ **This is a manual task for a human, not a Codex prompt.** There is no code to write.
> Every gate requires the real merchant store, the Shopify Admin GraphQL explorer and the Zettle
> POS app. Running them against mocks proves nothing.

## What to do

Open:

- `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_phase_0_dev_store_verification_20260727.md`

Rev 8 cut this from sixteen gates to four. **Rev 9 resolved three of those.** One remains:

> ### Gate 0.2 — does a newly created `UNLISTED` product stay off the Online Store?
>
> Create a product with `status: UNLISTED`, then search the storefront and check collections.
> Roughly five minutes.

`UNLISTED` is documented as *"active but you need a direct link… doesn't show up in search,
collections, or product recommendations"*, so a leak would most likely come from a sales channel
with `autoPublish: true`.

**This is the one gate that can change scope.** If it leaks, the fix is `publishableUnpublish`
plus `read_publications` / `write_publications` plus **merchant reauthorization** — a scope change
needing approval, not a bug fix. Stop and escalate rather than working around it.

### Already resolved — do not re-run

| Gate | Outcome |
|---|---|
| 0.1 Zettle imports an `UNLISTED` product | ✅ **PASS** — merchant confirmation, 2026-07-27 |
| 0.3 Zettle reads a specific location | ✅ **Retired** — the frontend chooses the location; which locations Zettle syncs is the merchant's operational mapping, not a backend concern |
| 0.4 price reaches Zettle unchanged | ✅ **Resolved** — the price is the full product price straight from the form, not per-unit and not derived from any quantity |

Record **observed** behaviour, not documented behaviour.

## This does not block Codex work

Gate 0.2's risk is **additive**: a failure appends a publication step and a scope change. It does
not invalidate the image support, the `create_task` wiring or the inventory work. Start
`PROMPT_shopify_product_sync_characterisation_net.md` and then
`PROMPT_phase_1_minimum_delivery.md` in parallel with running this check.

## Where to record outcomes

Append a Review-log entry to the parent plan
`PLAN_shopify_preorder_product_20260727.md`:

```
- `<YYYY-MM-DD>` `David`: Phase 0 gate 0.2 — PASS. UNLISTED product not findable on the
  storefront; no autoPublish sales channel captured it. Phase 0 complete.
```

Then set the Phase 0 plan's `Status` to `implemented`.

## What was retired, and why

Twelve gates from rev 7 no longer need a dev store — the metafield shape and duplicate-SKU
condition are proven by the merchant evidence (R11), the image fetch is answered by the public
bucket and WebP support (R3), `UNLISTED` and the inventory mutation contract are verified against
the Shopify reference, and the rest belong to hardening that is now backlog. Rev 9 then resolved
0.1, 0.3 and 0.4. The full list is retained, collapsed, in the parent plan for whichever hardening
ticket eventually needs it.
