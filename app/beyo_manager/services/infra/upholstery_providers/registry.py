from beyo_manager.domain.upholstery.enums import UpholsteryExternalProviderEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.infra.upholstery_providers.base import (
    ExternalUpholsteryProvider,
)
from beyo_manager.services.infra.upholstery_providers.fargotex import (
    FargotexExternalUpholsteryProvider,
)
from beyo_manager.services.infra.upholstery_providers.nevotex import (
    NevotexExternalUpholsteryProvider,
)
from beyo_manager.services.infra.upholstery_providers.ohlssons_tyger import (
    OhlssonsTygerExternalUpholsteryProvider,
)

_PROVIDERS: dict[UpholsteryExternalProviderEnum, ExternalUpholsteryProvider] = {
    UpholsteryExternalProviderEnum.NEVOTEX: NevotexExternalUpholsteryProvider(),
    UpholsteryExternalProviderEnum.OHLSSONS_TYGER: OhlssonsTygerExternalUpholsteryProvider(),
    UpholsteryExternalProviderEnum.FARGOTEX: FargotexExternalUpholsteryProvider(),
}


def list_external_upholstery_providers() -> list[UpholsteryExternalProviderEnum]:
    return list(_PROVIDERS.keys())


def get_external_upholstery_provider(
    provider: UpholsteryExternalProviderEnum,
) -> ExternalUpholsteryProvider:
    try:
        return _PROVIDERS[provider]
    except KeyError as exc:
        allowed = ", ".join(item.value for item in _PROVIDERS)
        raise ValidationError(
            f"Unsupported upholstery external provider '{provider.value}'. Allowed values: {allowed}"
        ) from exc
