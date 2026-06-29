from collections.abc import Sequence
from typing import Any, Protocol


class ExternalUpholsteryProvider(Protocol):
    async def search(self, q: str, limit: int) -> Sequence[dict[str, Any]]:
        """Return normalized upholstery candidates for the external source."""
