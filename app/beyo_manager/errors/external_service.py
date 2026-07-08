from beyo_manager.errors.base import DomainError


class ExternalServiceError(DomainError):
    http_status = 502

    def __init__(self, message: str = "External service request failed.") -> None:
        super().__init__(message)


class ShopifyGraphQLError(ExternalServiceError):
    def __init__(
        self,
        message: str = "Shopify GraphQL request failed.",
        *,
        retryable: bool,
        error_code: str,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.error_code = error_code


class ShopifyGraphQLRetryableError(ShopifyGraphQLError):
    def __init__(
        self,
        message: str = "Shopify GraphQL request failed.",
        *,
        error_code: str = "shopify_graphql_retryable_error",
    ) -> None:
        super().__init__(message, retryable=True, error_code=error_code)


class ShopifyGraphQLNonRetryableError(ShopifyGraphQLError):
    def __init__(
        self,
        message: str = "Shopify GraphQL request failed.",
        *,
        error_code: str = "shopify_graphql_non_retryable_error",
    ) -> None:
        super().__init__(message, retryable=False, error_code=error_code)
