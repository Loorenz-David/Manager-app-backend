from collections.abc import Sequence
from typing import Any

from beyo_manager.services.infra.nevotex.client import fetch_nevotex_raw_products
from beyo_manager.services.infra.nevotex.normalizer import normalize_nevotex_candidates


class NevotexExternalUpholsteryProvider:
    async def search(self, q: str, limit: int) -> Sequence[dict[str, Any]]:
        raw_products = await fetch_nevotex_raw_products(q=q, limit=limit)
        return normalize_nevotex_candidates(raw_products)
