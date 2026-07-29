# HANDOFF_TO_FRONTEND — Pre-order tasks that provision a Shopify product

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_preorder_shopify_product_20260727`
- Created at (UTC): `2026-07-27T00:00:00Z`
- Status: backend implemented; **pending dev-store verification** (see "Before you rely on this")
- Source plans (archived): `PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`,
  `PLAN_shopify_preorder_phase_0_dev_store_verification_20260727.md`
- Research record: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_product_20260727.md`
- Related handoff: `HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` (the locations endpoint lives there)

---

## What this adds

`POST /api/v1/tasks` now accepts an **optional** `shopify_preorder` section. When present, creating
the task also provisions a product in Shopify — title, SKU, price, metafields, image, and stock at
the location(s) you choose — so staff can sell it in Zettle at the till.

**Nothing about existing task creation changes.** Omit the section and the endpoint behaves exactly
as it does today, including the response shape.

---

## Availability rules

| Rule | Behaviour if broken |
|---|---|
| `task_type` must be `pre_order` | `400`, task **not** created |
| Role must be `admin`, `manager` or `seller` | `403`, task **not** created |

Both checks run **before anything is written**, so a rejected request leaves no partial task. A
`worker` cannot submit the section.

---

## Request — the new keys

```jsonc
POST /api/v1/tasks
{
  "task_type": "pre_order",
  "title": "Custom TC3 sofa",
  // …all your existing task-creation fields, unchanged…

  "shopify_preorder": {
    "shop_integration_id": "shpint_01ABC…",          // required
    "product": {
      "title": "Custom TC3",                          // required
      "sku": "CustomTC3",                             // required
      "price": "5200.00",                             // required — decimal string, full price
      "description": "<p>Optional long description</p>",  // HTML — see "description" below
      "product_category": "Sofa",
      "tags": ["custom", "preorder"],
      "metafields": {                                 // see "Metafields" below
        "notes": "handle with care"                   // do NOT send "quantity" — derived
      },
      "image_id": "img_01XYZ…",                       // or image_url — never both
      "image_alt_text": "Custom TC3 in green"
    },
    "inventory": [                                    // required, at least one entry
      { "location_id": "gid://shopify/Location/99221471562", "quantity": 1 }
    ]
  }
}
```

### Field notes

**`shop_integration_id`** — from `GET /api/v1/integrations/shopify/shops`. One shop per pre-order.

**`price`** — a **decimal string**, never a number. `"5200.00"`, not `5200.00`. It is the **full
product price**, not per-unit, and the backend writes it to Shopify byte-for-byte. It is never
multiplied or divided by anything.

**`description`** — optional, a single string at the top level of `product` (sibling of `title`,
`sku`, `price`). It maps straight to Shopify's **`descriptionHtml`**, which means:

- **It is interpreted as HTML, not plain text.** A string with `\n` line breaks renders as one run-on
  paragraph on the product page. If the seller types multiple lines, convert them — `<p>…</p>` per
  paragraph, or `<br>` per line — before sending.
- **We do not sanitize or escape it.** Whatever you send is what Shopify stores. If the text comes
  from a free-text field, escape `&`, `<` and `>` yourself, otherwise a stray `<` silently eats the
  rest of the description.
- Leading/trailing whitespace is trimmed, and a whitespace-only string is treated as absent.
- No length limit on our side.

> **You cannot clear a description by sending an empty one.** Omitting the field — or sending `""`
> or `null` — makes the backend leave `descriptionHtml` out of the Shopify mutation entirely. On a
> **new** product that means no description. On a **reused** product (same task-item article number
> already present as a Shopify barcode) the existing description survives untouched. To actually
> blank one out, someone has to edit it in the Shopify admin.

**`image_id` / `image_url`** — mutually exclusive, both optional.
- `image_id` (preferred) — an existing `img_…` from the image upload flow. The backend resolves it
  to a public URL itself.
- `image_url` — an absolute `https://` URL for an externally hosted image.
- Shopify **fetches** the image from that URL; you are not uploading bytes to us twice.
- Accepted formats include WebP, PNG, JPEG, GIF, HEIC, SVG. Limits: **20 MB** and
  **25 megapixels / 5000×5000 px** — validated up front, so an oversized image fails the request
  rather than failing silently later.

**`inventory`** — a list of `{location_id, quantity}`. Get locations from
`GET /api/v1/integrations/shopify/locations?shop_integration_ids=shpint_…`.
- `location_id` must be a Shopify Location GID: `gid://shopify/Location/<digits>`.
- `quantity` is an integer `0…1000000`. **`1` is the sensible default for a pre-order** — one
  physical unit someone ordered — but the value is yours to choose.
- Duplicate `location_id` entries are rejected.
- **This is the only quantity your form collects.** The `custom.quantity` metafield is derived from
  it (see the box below).

> ### ⚠️ You enter the quantity **once** — the `quantity` metafield is derived
>
> `inventory[].quantity` is the only quantity your form collects. The backend writes it to Shopify
> in **two** places from that single value:
>
> | Written to | Value |
> |---|---|
> | Shopify **stock** at each location | that location's `quantity` |
> | the `custom.quantity` **metafield** | the **sum** across all locations |
>
> With one location at `quantity: 2` → stock `2`, `custom.quantity` `"2"`. With two locations at
> `2` and `3` → stock `2` and `3` respectively, `custom.quantity` `"5"`.
>
> **Do not send `metafields.quantity`.** The request is rejected with `400` if you do — deliberately
> louder than silently overwriting it, so a form that still sends it gets told rather than watching
> its value disappear.

### Metafields

Same shape the product-sync endpoint already accepts: a flat object keyed by metafield key. Use the
`{type, value}` form when the metafield needs a specific type; a bare string works otherwise.

```json
"metafields": {
  "notes": "handle with care",
  "finish": { "type": "single_line_text_field", "value": "oiled oak" }
}
```

They land in Shopify's `custom` namespace.

**The `quantity` key is reserved** — the backend owns it (see the box above). Every other key passes
through untouched.

### The location selector

Load from `GET /api/v1/integrations/shopify/locations?shop_integration_ids=shpint_…`. Each location
returns:

```json
{
  "location_id": "gid://shopify/Location/99221471562",
  "name": "Västberga Warehouse",
  "is_active": true,
  "ships_inventory": true,
  "is_fulfillment_service": false
}
```

**Only offer locations where `is_active === true && is_fulfillment_service === false.`** Anything
else is rejected by the backend at execution time, which turns a fixable form error into a late
failure the seller can't see. `ships_inventory` is informational — do not filter on it.

Show the location **name plus a stable identifier** so two similarly named warehouses are
distinguishable. `Västberga Warehouse` is the expected default for this merchant, but keep it
user-changeable and don't hard-code the GID.

---

## Response — immediate

Task creation returns as fast as it always did. **No Shopify call happens during the request.**

```jsonc
{
  "client_id": "tsk_01ABC…",
  "task_scalar_id": 412,

  "shopify_preorder": {                    // present only when the section was submitted
    "queued": true,
    "preorder_operation_id": "shpsi_01DEF…",   // correlation id — keep it
    "task_id": "tsk_01ABC…",
    "shop_integration_id": "shpint_01ABC…",
    "shopify_task_id": "exe_01GHI…",           // internal execution task
    "inventory": [
      { "location_id": "gid://shopify/Location/99221471562", "quantity": 1 }
    ]
  }
}
```

`queued: true` means **accepted and durably recorded** — not that Shopify has the product yet. Show
a pending state and wait for the socket event.

---

## What happens in the background (the short version)

The task and the Shopify intent are written in **one database transaction**, so a task never exists
without its pre-order intent, and vice versa. A background worker then picks it up and talks to
Shopify: it finds or creates the product by the task item's article number (written as the Shopify
barcode), sets the variant's SKU and price, attaches the image, writes the metafields, and sets the
stock at your chosen location(s). SKU is product data, not identity; duplicate SKUs are allowed.

The backend sends `product.tags` exactly as supplied. This is where to add a `preorder` or other
merchant-facing tag. It does not generate a `managerbeyo-sync-*` retry tag.

Two consequences worth designing for:

- **It is asynchronous.** Typically seconds, but a busy queue or a Shopify retry can make it longer.
  Don't block the UI on it.
- **It is retried automatically** on transient Shopify failures. A pre-order that hasn't emitted an
  event yet may still be in flight.

That is all you need. The durability and retry mechanics are backend concerns. If a product has no
barcode, a retried create cannot safely recover through SKU because SKU is not unique.

---

## Socket event — completion

**Event:** `shopify.preorder.processed`
**Room:** the workspace room you already join.
**Emitted:** once per pre-order, on success **and** on failure.

```jsonc
{
  "task_id": "tsk_01ABC…",                  // ManagerBeyo task — your correlation key
  "preorder_operation_id": "shpsi_01DEF…",  // matches the create response
  "shopify_task_id": "exe_01GHI…",
  "shop_integration_id": "shpint_01ABC…",

  "status": "succeeded",                    // "succeeded" | "failed"
  "requested_operation": "create",          // "create" | "update" | null

  "shopify_product_id": "gid://shopify/Product/15930838548810",
  "shopify_variant_id": "gid://shopify/ProductVariant/…",
  "shopify_media_id": "gid://shopify/MediaImage/…",   // null when no image was supplied
  "media_status": "READY",                            // UPLOADED | PROCESSING | READY | FAILED | null

  "inventory": {
    "quantities": [
      {
        "location_id": "gid://shopify/Location/99221471562",
        "quantity": 1,                     // what we set it to
        "before_available": 0,             // what was there before (audit)
        "compare_protection": "explicitly_bypassed",
        "outcome": "applied",
        "available": 1
      }
    ]
  },

  "error_code": null,
  "error_message": null
}
```

### Reading it

- **`status: "succeeded"`** — the product exists in Shopify with the stock you asked for. Deep-link
  to it: `https://<shop-domain>/admin/products/<numeric id from shopify_product_id>`.
- **`status: "failed"`** — `error_code` and `error_message` are populated; the other fields show how
  far it got. **Shopify IDs are still returned when present** — a failure late in the process still
  created a real product, so don't render it as "nothing happened".
- **`media_status`** may be `PROCESSING` on success. That's normal — Shopify transcodes images
  asynchronously and the product is usable regardless. Don't gate anything on `READY`.
- **`requested_operation: "update"`** means an existing Shopify product with that exact barcode was
  reused and its price overwritten, rather than a new one created. Worth surfacing.

### Correlating

`task_id` is your key. `preorder_operation_id` matches what the create response returned, if you'd
rather key on that.

### Not affected

Ordinary product syncs still emit `shopify.products.synced` with an **unchanged** payload. Pre-order
rows never appear in it, and vice versa. Existing consumers need no changes.

---

## Error codes

Everything below arrives as `error_code` in the socket event unless marked as an HTTP rejection.

**Worth a specific message:**

| Code | Meaning | Can the seller fix it? |
|---|---|---|
| `preorder_inventory_location_invalid` | The chosen location is gone, inactive, or a fulfillment-service location | Yes — create a new pre-order against a valid location |
| `ambiguous_product_match` | Two or more Shopify variants already share this exact barcode, including variants of the same product | No — someone must make the barcode unique in Shopify Admin |
| `product_image_unresolved` | The `image_id` doesn't exist or was deleted | Yes — re-attach the image |
| `invalid_product_image_url` | The resolved image URL isn't an absolute `https://` URL | Yes |

**Configuration / operational — surface as "contact an admin":**

`missing_shop_integration` · `missing_access_token` · `missing_inventory_scope` (the Shopify
connection needs re-authorising) · `inventory_item_unresolved`

**Generic:** `graphql_user_errors` (Shopify rejected a field — `error_message` has the detail),
`unexpected_error`.

**HTTP rejections at submit time** (task not created): validation errors on `price`, `location_id`,
`quantity`, image limits, duplicate locations, `image_id` + `image_url` together, **`metafields.quantity`
supplied** (it is derived); `400` for a non-`pre_order` task type; `403` for a disallowed role.

---

## Suggested UX

1. Seller picks `pre_order`, fills the task form.
2. Shopify section: choose shop → choose location(s) from the filtered list → quantity (default `1`)
   → product fields → attach image.
3. Submit. Task appears immediately; the Shopify part shows **pending**.
4. On `shopify.preorder.processed`:
   - `succeeded` → mark ready, offer the Shopify Admin deep-link.
   - `failed` → show the mapped message above, and keep the product link if IDs came back.
5. If no event arrives, treat it as still in flight rather than failed — retries are automatic.

---

## Before you rely on this

The backend is implemented and tested, but the **dev-store verification has not run yet**. One
outcome could still change: whether an `UNLISTED` Shopify product stays off the merchant's public
storefront. If it doesn't, the backend needs a scope change and merchant re-authorisation — no
change to any contract in this document, but the feature would be blocked until that's approved.

Nothing else here is expected to move. Build against it.

---

## Questions

Anything ambiguous in this document is a backend bug, not something to guess at — ask and it gets
fixed here rather than diverging in two codebases.
# 2026-07-28 inventory-contract addendum

All Shopify product creation/update requests now use authoritative absolute inventory:
`inventory_quantities[].quantity`. The legacy
`inventory_adjustments[].quantity_to_add` request remains accepted for one release but is
interpreted as absolute, not additive. Do not send both shapes. Selected quantity `0` must be
preserved to clear a location; omitted locations remain unchanged.

Ordinary and pre-order products share the same worker execution. Their completion events remain
distinct because the backend now persists an explicit sync origin rather than inferring pre-orders
from inventory behavior. For `shopify.products.synced`, canonical inventory results contain
`quantities`; clients may accept historical `adjustments` results during the compatibility release.
