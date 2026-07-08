from __future__ import annotations

from beyo_manager.errors.base import DomainError


class ShopifyOAuthCallbackError(DomainError):
    http_status = 422

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        shop_domain: str | None = None,
        redirect_key: str | None = "default",
    ) -> None:
        self.error_code = error_code
        self.shop_domain = shop_domain
        self.redirect_key = redirect_key
        super().__init__(message)
