# HANDOFF_TO_FRONTEND — Item image URLs are now stable, and pre-orders need `image_id`

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_image_urls_and_preorder_images_20260728`
- Created at (UTC): `2026-07-28T00:00:00Z`
- Status: implemented on the backend
- Related handoff: `HANDOFF_TO_FRONTEND_task_preorder_shopify_product_20260727.md` (the full pre-order contract)

---

## TL;DR

1. **Item image URLs no longer expire.** You can cache them, store them, and pass them around. Every
   other image type (case, message, note) is unchanged — still presigned, still 24 h.
2. **Pre-orders need `image_id`, not `image_url`.** If you want the Shopify product to have a photo,
   send the item image's `client_id`. Sending it was optional before and got silently skipped — that
   is why products have been created without images.

No breaking changes. Item images that used to work keep working; they just stop expiring.

---

## Part 1 — Item image URLs are stable

### What changed

Previously **every** image URL was a presigned S3 link with a 24-hour expiry, including item photos.
Item photos are now served as plain, unsigned URLs that do not expire.

```
Before:  https://bucket.s3.eu-north-1.amazonaws.com/images/ws_…/item/itm_…/photo.webp
           ?X-Amz-Algorithm=…&X-Amz-Signature=…&X-Amz-Expires=86400

After:   https://bucket.s3.eu-north-1.amazonaws.com/images/ws_…/item/itm_…/photo.webp
```

### Which images

| Image type | URL | Expires |
|---|---|---|
| **Item photos** | plain, unsigned | **never** |
| Case images | presigned | 24 h |
| Case-conversation-message images | presigned | 24 h |
| Note images | presigned | 24 h |
| Externally-sourced images (already absolute URLs) | as-is | n/a |

### What you can do now that you couldn't

- **Cache item image URLs indefinitely** — put them in local storage, a service worker, a static
  manifest, anywhere. They stay valid.
- **Stop refetching just to refresh a URL.** No more expiry handling for item photos.
- **Pass the URL to a third party** if you ever need to.

None of that is safe for case/message/note images — those still expire in 24 h and must be refetched.

### What you must not do

**Do not send an item's `image_url` back to us as `shopify_preorder.product.image_url`.** See Part 2.

### Nothing to change today

Existing item images already worked and keep working. This is purely an improvement — no migration
on your side, no version gate. Existing item photos were backfilled, so this applies retroactively.

### `GET /api/v1/images/{image_client_id}/download-url`

For a public (item) image this now returns:

```json
{ "download_url": "https://…/photo.webp", "expires_in": null }
```

`expires_in: null` means **never expires** — distinct from `0`, which would mean already expired.
For all other image types the response is unchanged: a presigned URL and a countdown in seconds.

---

## Part 2 — Send `image_id` when creating a pre-order

### The problem

Pre-order Shopify products have been created **without images**, because the request didn't include
one. The backend does not auto-discover the item's photos — it only uses what you send.

### The fix

In the task-creation request, put the item image's **`client_id`** into
`shopify_preorder.product.image_id`.

```jsonc
{
  "task_type": "pre_order",
  "item": { "sku": "PRE_ORDER-2", "item_category_id": "itc_…" },

  "shopify_preorder": {
    "shop_integration_id": "shpint_…",
    "product": {
      "title": "PRE_ORDER-2",
      "sku": "PRE_ORDER-2",
      "price": "2000.00",
      "image_id": "img_01ABC…",              // ← the client_id, NOT the image_url
      "image_alt_text": "Green armchair"     // optional but recommended
    },
    "inventory": [
      { "location_id": "gid://shopify/Location/90742587722", "quantity": 1 }
    ]
  }
}
```

### Where to get it

Straight out of the task/item responses you already render. Both the full and light image shapes
carry `client_id`:

```jsonc
"item_images": [
  {
    "client_id": "img_01ABC…",        // ← this is image_id
    "image_url": "https://…/photo.webp",
    "width_px": 2000,
    "height_px": 1500,
    "file_size_bytes": 812345
  }
]
```

### Why `image_id` and not `image_url`

Both fields exist and they are **mutually exclusive** — sending both is a `400`. They are not
interchangeable:

- **`image_id`** — we look the image up, **validate it** against Shopify's limits at request time,
  and resolve the URL at the moment we talk to Shopify. If the bucket or CDN ever changes, in-flight
  pre-orders keep working.
- **`image_url`** — a pass-through for genuinely external images we don't host. It must be an
  absolute **HTTPS** URL, and it gets **no size validation** — an oversized one fails later, inside
  the worker, as a `product_image_unresolved` / `invalid_product_image_url` error instead of an
  immediate `400`.

So for anything a user uploaded through our app: `image_id`.

### Validation, and what you can pre-check

When you send `image_id`, the request is rejected immediately if:

| Condition | Response |
|---|---|
| Image doesn't exist or is deleted | `404` — `Image not found.` |
| Over 20 MB | `400` — `Shopify product images cannot exceed 20 MB.` |
| Over 25 MP, or either side over 5000 px | `400` — `Shopify product images cannot exceed 25 MP or 5000×5000 pixels.` |

You already have `width_px`, `height_px` and `file_size_bytes` in the same payload, so you can grey
out an oversized image in the picker rather than surfacing a rejected task creation.

### What happens after

The image rides along in the same Shopify mutation that creates the product. The completion socket
event (`shopify.preorder.processed`) reports:

- `shopify_media_id` — the Shopify media object, or `null` if no image was sent
- `media_status` — `UPLOADED` / `PROCESSING` / `READY`

**`PROCESSING` on success is normal.** Shopify transcodes asynchronously; the product is usable
immediately. Don't gate anything on `READY`.

---

## Also new: `product_category` is derived

You no longer need to send `shopify_preorder.product.product_category`. If the task has an `item`
with an `item_category_id`, Shopify's product type defaults to that **category's name**.

Send `product_category` explicitly only when you want it to differ from the item's category — an
explicit value always wins.

---

## Quick checklist

- [ ] Stop any expiry/refresh handling for **item** image URLs (keep it for case, message and note images)
- [ ] Add `image_id` to the pre-order product payload, taken from `item_images[].client_id`
- [ ] Optionally add `image_alt_text`
- [ ] Optionally pre-validate 20 MB / 25 MP from the fields already in the response
- [ ] Drop `product_category` from the pre-order payload unless you're deliberately overriding it
- [ ] Handle `expires_in: null` from the download-url endpoint as "never expires"

---

## Questions

Anything ambiguous here is a backend bug, not something to guess at — ask and it gets fixed in this
document rather than diverging across two codebases.
