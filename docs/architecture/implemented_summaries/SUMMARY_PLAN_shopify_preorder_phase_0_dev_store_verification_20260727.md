# SUMMARY_PLAN_shopify_preorder_phase_0_dev_store_verification_20260727

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_preorder_phase_0_dev_store_verification_20260727`
- Status: `implemented`
- Owner: `David` (manual verification) with `claude-opus-5` (research resolution)
- Created at (UTC): `2026-07-27T00:00:00Z`
- Source plan:
  `backend/docs/architecture/archives/implementation/PLAN_shopify_preorder_phase_0_dev_store_verification_20260727.md`
- Parent plan:
  `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_product_20260727.md`

## What this plan was

A verification-only plan. No code. It existed to answer the questions about the merchant's
Shopify/Zettle environment that no amount of code reading could settle, before committing to an
implementation shape.

## How it shrank

It opened at **sixteen gates** and closed at **four**, then three of those four resolved without a
dev store:

| Rev | Gates | What removed them |
|---|---|---|
| 7 | 16 | — |
| 8 | 4 | Merchant evidence (R11) settled the metafield shape and the duplicate-SKU condition; the public-bucket finding (R3) settled the image fetch; the Shopify reference settled `UNLISTED`, `@idempotent` and `changeFromQuantity`; the rest became hardening backlog |
| 9 | 1 | Gate 0.1 confirmed by the merchant; 0.3 retired as a non-backend concern; 0.4 resolved from the request contract |

## Outcomes

- **0.1 — PASS.** Zettle imports an `UNLISTED` product. This was the load-bearing assumption of
  the whole feature.
- **0.2 — DEFERRED, not run.** Does an `UNLISTED` product stay off the Online Store? Deferred by
  explicit decision (2026-07-27) into the Phase 1 post-implementation dev-store verification,
  where acceptance criterion 4 already requires storefront absence.
- **0.3 — RETIRED.** Which Shopify location Zettle synchronises is not a backend concern: the
  seller selects the location and the merchant owns that operational mapping.
- **0.4 — RESOLVED.** The price is the full product price straight from the form — not per-unit,
  not derived from any quantity. Already enforced; nothing to verify.

## Outstanding, and deliberately so

**Gate 0.2 has not been executed.** The deferral was accepted on the grounds that the probability
is low (every product in the merchant's live workflow is already `UNLISTED`, and Shopify documents
the status as excluded from search, collections and recommendations) and that the check happens
anyway during the Phase 1 dev-store verification.

The consequence was recorded rather than glossed: **a failure is not a parameter change.** No
alternative `ProductStatus` satisfies both requirements — `ACTIVE` is storefront-visible and
`DRAFT` is invisible to sales channels and therefore to Zettle. The fix would be
`publishableUnpublish` plus `read_publications` / `write_publications` plus a **merchant OAuth
reauthorization for every installed shop** — an operational step the merchant performs, not
something a debugging pass patches. If it fires, escalate for scope approval.

## Verification method for 0.2, when it runs

Storefront search · `/collections/all` · `/sitemap_products_1.xml` · `resourcePublications` on the
created product. **A direct `/products/<handle>` URL loading is expected, not a leak** — that is
the definition of `UNLISTED`, and misreading it would trigger a reauthorization cycle for nothing.

## Trace links

- Phase 1 delivery: `SUMMARY_PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`
- Research record and hardening backlog: `PLAN_shopify_preorder_product_20260727.md` (R1–R13)
