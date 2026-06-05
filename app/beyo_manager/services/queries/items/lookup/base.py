from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ItemLookupResult:
    article_number: str
    sku: str | None
    item_category_id: str | None
    quantity: int
    external_id: str | None
    external_source: str | None
    images: list = field(default_factory=list)


class ItemLookupHandler(ABC):
    """Strategy interface for item lookup sources.

    Return None when the article number is not found in this source.
    Raise only unexpected exceptions — the orchestrator captures them via
    asyncio.gather(return_exceptions=True), logs a warning, and excludes
    this source's result without failing the whole request.
    """

    @abstractmethod
    async def lookup(
        self,
        article_number: str | None,
        sku: str | None,
        session: AsyncSession,
        workspace_id: str,
    ) -> ItemLookupResult | None: ...
