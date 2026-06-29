import asyncio
from collections.abc import Iterable

from beyo_manager.domain.upholstery.enums import UpholsteryExternalProviderEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.upholstery_providers.registry import (
    get_external_upholstery_provider,
    list_external_upholstery_providers,
)

_MAX_LIMIT = 20
_DEFAULT_LIMIT = 7


def _coerce_provider(value: object) -> UpholsteryExternalProviderEnum:
    if isinstance(value, UpholsteryExternalProviderEnum):
        return value
    if isinstance(value, str):
        try:
            return UpholsteryExternalProviderEnum(value.strip())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in UpholsteryExternalProviderEnum)
            raise ValidationError(
                f"Invalid external upholstery provider '{value}'. Allowed values: {allowed}"
            ) from exc
    raise ValidationError("providers must contain valid provider names.")


def _coerce_provider_list(value: object) -> list[UpholsteryExternalProviderEnum]:
    if value is None:
        return []
    if isinstance(value, (str, UpholsteryExternalProviderEnum)):
        if isinstance(value, str):
            raw_items = [item.strip() for item in value.split(",") if item.strip()]
            providers: list[UpholsteryExternalProviderEnum] = []
            for item in raw_items:
                provider = _coerce_provider(item)
                if provider not in providers:
                    providers.append(provider)
            return providers
        return [_coerce_provider(value)]
    if not isinstance(value, Iterable):
        raise ValidationError("providers must be a list of provider names.")
    providers: list[UpholsteryExternalProviderEnum] = []
    for item in value:
        provider = _coerce_provider(item)
        if provider not in providers:
            providers.append(provider)
    return providers


def _resolve_requested_providers(ctx: ServiceContext) -> list[UpholsteryExternalProviderEnum]:
    requested = _coerce_provider_list(ctx.query_params.get("providers"))
    if requested:
        return requested
    return list_external_upholstery_providers()


def _serialize_external_upholstery_candidate(candidate: dict) -> dict:
    serialized = dict(candidate)
    serialized["supplier_name"] = candidate.get("origin")
    serialized["page_link"] = candidate.get("external_url")
    return serialized


async def list_external_upholsteries(ctx: ServiceContext) -> dict:
    q = str(ctx.query_params.get("q", "")).strip()
    if not q:
        raise ValidationError("q is required.")

    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    providers = _resolve_requested_providers(ctx)

    provider_instances = [get_external_upholstery_provider(provider_name) for provider_name in providers]
    provider_results = await asyncio.gather(
        *[provider.search(q=q, limit=limit) for provider in provider_instances]
    )

    upholsteries: list[dict] = []
    for provider_items in provider_results:
        upholsteries.extend(_serialize_external_upholstery_candidate(item) for item in provider_items)

    return {
        "upholsteries": upholsteries,
        "upholsteries_pagination": {
            "has_more": False,
            "limit": limit,
            "offset": 0,
        },
        "providers": [provider.value for provider in providers],
    }
