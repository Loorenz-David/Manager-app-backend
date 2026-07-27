# Codex Prompt — Phase 1: Minimum delivery (Shopify pre-order product)

This is the **entire critical path** for the Shopify pre-order feature. One session.

## Load first, in this order

1. **`backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`** — governs how this plan
   moves through its lifecycle. Follow its execution protocol, output format
   (`skills/_shared/output_format.md`) and quality gate (`skills/_shared/quality_gate.md`).
2. **`backend/docs/architecture/under_construction/implementation/prompts/GUARDRAILS.md`**
3. **`backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`**
   — your plan. It is self-contained.
4. **`backend/architecture/06_commands.md` and `06_commands_local.md`** — load **both**; the local
   file defines `maybe_begin` owner vs subordinate semantics and is load-bearing here.

The parent plan `PLAN_shopify_preorder_product_20260727.md` is ~1300 lines of research and
backlog. **Do not read it** unless a decision in your plan is genuinely ambiguous.

## Prerequisite

The four Phase 0 gates must be recorded in the parent plan's Review log. Gate **0.2** especially —
if an `UNLISTED` product leaks onto the storefront, this is a scope change, not a bug fix. If the
gates are missing, stop and report.

## The single most important instruction

**The existing `/products/process` pipeline already does most of this.** SKU resolve-or-create,
ambiguous-SKU failure, variant SKU + price, `UNLISTED` (the normalizer uppercases whatever is
passed), single-shop targeting, tags, metafields in the `custom` namespace, inventory at a chosen
location, **location ownership validation**, **per-task replay safety via the existing ledger**,
and the whole worker / queue / retry / socket path.

**If you find yourself reimplementing any of that, stop — you have gone out of scope.**

Your job is five additions:

1. `public_url(key)` on `StorageClient` + `STORAGE_PUBLIC_BASE_URL`
2. `media` support on `productCreate` / `productUpdate`, plus an `image_id` request field
3. Image limit validation (20 MB / 25 MP) at command time
4. Absolute inventory set behind an `inventory_mode` discriminator, with a **caller-supplied
   quantity per location**
5. `process_shopify_products` → `maybe_begin`, and `create_task` calling it

## Schema delta: one enum, three columns

`inventory_mode` (`add` default | `set`), `shopify_media_id`, `media_status`. That is all.

**No new table. No new task type. No `task_id` column** (`frontend_client_id = task_id` and the
existing ledger already dedupes on it). **No idempotency-key column** — compute it at worker time
from `(sync_item.client_id, location_id)`, both already on the row.

## Five things that are easy to get wrong

1. **Two caller-supplied quantities travel in one request — never cross them.**
   `custom.quantity` is a **product metafield** (item composition). The inventory `quantity` is
   **per location** and drives `inventorySetQuantities`. There is **no quantity constant**; the
   inventory number is caller input, written as an **absolute set that overwrites** existing
   stock. Record `before_available` per location — it is the only record of what was there.
   The regression test deliberately uses **different** numbers (`custom.quantity = "6"`,
   inventory `2` → `available = 2`) so a crossed wiring cannot coincidentally pass. Keep it that way.
2. **`inventory_mode` must not reach any HTTP schema.** Only the pre-order command sets `set`.
3. **Never send `ignoreCompareQuantity` or `compareQuantity`** — send `changeFromQuantity: null`.
4. **The bucket is public — do not presign.** Compose a plain URL. No TTL, no per-attempt minting,
   no `stagedUploadsCreate`. WebP is fine.
5. **An `add`-mode item with no image must emit the document product sync emits today.** Omit the
   `media` key entirely rather than sending `null`.

## Done signal

```
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest app/tests/unit/services/infra/storage -v
pytest app/tests/unit/services/infra/shopify -v
pytest app/tests/unit/services/tasks/shopify -v
pytest app/tests/unit/services/commands/shopify -v
pytest app/tests/integration/services/commands/tasks -v
pytest app/tests
```

Run the **full** suite. Both `create_task` and product sync are live paths.

## Lifecycle (per the skill)

1. Set the plan's `Status` to `implemented`, update `Last updated at`.
2. Write a summary to `backend/docs/architecture/implemented_summaries/`, trace-linked to this
   plan and to the parent plan.
3. Report in the skill's output format: lifecycle state, next transition, document paths touched.

Do **not** archive yet — a human runs the dev-store checklist first.

## ⚠️ Stop after implementation

A human verifies on the dev store before this ships: product is `UNLISTED`, absent from the
storefront, correct price / SKU / metafields / image, `available = 1` at the chosen location, and
visible in Zettle.

## Report explicitly

- Confirmation that `execute_shopify_graphql` is unreachable from `create_task`.
- Confirmation that an `add`-mode sync emits unchanged GraphQL.
- Confirmation that `inventory_mode` appears in no request model.
- Confirmation that `SHOPIFY_APP_SCOPES` is unchanged — this feature needs **no new scopes and no
  merchant reauthorization**.
