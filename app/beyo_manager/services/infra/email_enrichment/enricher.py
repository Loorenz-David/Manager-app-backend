from __future__ import annotations

import re
from collections.abc import Callable

from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext


VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class ContentEnricher:
    def __init__(self, var_map: dict[str, Callable[[EnrichmentContext], str]]):
        self._var_map = var_map

    def enrich(self, text: str, context: EnrichmentContext) -> str:
        def _replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            parser = self._var_map.get(var_name)
            if parser is None:
                return match.group(0)
            return parser(context)

        return VAR_PATTERN.sub(_replace, text)

