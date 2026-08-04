"""Fixed policy for Shopify pre-order products.

Pure constants and derivations — no I/O, no session, no Shopify client.

`PREORDER_PRODUCT_STATUS` is deliberately not caller-supplied. A pre-order provisions a product for
the till under a fixed shape; letting the caller vary the status would make two pre-orders mean
different things in Shopify.
"""

from __future__ import annotations

from collections.abc import Iterable

# A pre-order product is UNLISTED, not ACTIVE and not DRAFT. UNLISTED is "active but you need a
# direct link" — visible to sales channels (so Zettle imports it) while absent from storefront
# search, collections and recommendations. DRAFT would hide it from Zettle; ACTIVE would expose it
# on the storefront. Established from the merchant's live catalogue, where every product in the
# Shopify/Zettle workflow is UNLISTED.
PREORDER_PRODUCT_STATUS = "UNLISTED"

# The merchant's `custom.quantity` definition (gid://shopify/MetafieldDefinition/241114906954) is
# a text field, not a number field. The value is written as a string accordingly.
PREORDER_QUANTITY_METAFIELD_KEY = "quantity"
PREORDER_QUANTITY_METAFIELD_TYPE = "single_line_text_field"


def build_preorder_quantity_metafield(inventory_quantities: Iterable[int]) -> dict[str, str]:
    """Build the default `custom.quantity` from the units this pre-order provisions.

    Used only when the caller doesn't supply their own `quantity` metafield. The merchant's live
    products carry a `custom.quantity` that can legitimately differ from available stock (e.g. a
    pack size or display quantity), so a caller-supplied value always wins; this is just the
    fallback that mirrors the **total** inventory the pre-order writes, summed across every
    selected location, for callers who don't need the two to diverge.
    """
    return {
        "type": PREORDER_QUANTITY_METAFIELD_TYPE,
        "value": str(sum(inventory_quantities)),
    }
