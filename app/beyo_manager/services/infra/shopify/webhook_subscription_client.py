from __future__ import annotations

from dataclasses import dataclass

from beyo_manager.domain.shopify.enums import ShopifyWebhookPayloadFormatEnum
from beyo_manager.errors.external_service import ShopifyGraphQLNonRetryableError
from beyo_manager.services.infra.shopify.graphql_client import (
    execute_shopify_graphql,
    raise_for_graphql_user_errors,
)

LIST_WEBHOOK_SUBSCRIPTIONS_QUERY = """
query ListWebhookSubscriptions {
  webhookSubscriptions(first: 250) {
    edges {
      node {
        id
        topic
        format
        endpoint {
          __typename
          ... on WebhookHttpEndpoint {
            callbackUrl
          }
        }
      }
    }
  }
}
"""

CREATE_WEBHOOK_SUBSCRIPTION_MUTATION = """
mutation CreateWebhookSubscription(
  $topic: WebhookSubscriptionTopic!
  $callbackUrl: URL!
  $format: WebhookSubscriptionFormat!
) {
  webhookSubscriptionCreate(
    topic: $topic
    webhookSubscription: {
      callbackUrl: $callbackUrl
      format: $format
    }
  ) {
    userErrors {
      field
      message
    }
    webhookSubscription {
      id
      topic
      format
      endpoint {
        __typename
        ... on WebhookHttpEndpoint {
          callbackUrl
        }
      }
    }
  }
}
"""

DELETE_WEBHOOK_SUBSCRIPTION_MUTATION = """
mutation DeleteWebhookSubscription($id: ID!) {
  webhookSubscriptionDelete(id: $id) {
    deletedWebhookSubscriptionId
    userErrors {
      field
      message
    }
  }
}
"""


@dataclass(frozen=True)
class RemoteWebhookSubscription:
    id: str
    topic: str
    callback_url: str
    payload_format: ShopifyWebhookPayloadFormatEnum


async def list_remote_webhook_subscriptions(
    *,
    shop_domain: str,
    access_token_encrypted: str,
) -> list[RemoteWebhookSubscription]:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=LIST_WEBHOOK_SUBSCRIPTIONS_QUERY,
        variables={},
        operation_name="list_webhook_subscriptions",
    )

    edges = (((data.get("webhookSubscriptions") or {}).get("edges")) or [])
    subscriptions: list[RemoteWebhookSubscription] = []
    for edge in edges:
        node = (edge or {}).get("node") or {}
        mapped = _map_remote_subscription(node)
        if mapped is not None:
            subscriptions.append(mapped)
    return subscriptions


async def create_remote_webhook_subscription(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    topic: str,
    callback_url: str,
    payload_format: ShopifyWebhookPayloadFormatEnum,
) -> RemoteWebhookSubscription:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=CREATE_WEBHOOK_SUBSCRIPTION_MUTATION,
        variables={
            "topic": topic.upper().replace("/", "_"),
            "callbackUrl": callback_url,
            "format": payload_format.value.upper(),
        },
        operation_name="create_webhook_subscription",
    )
    payload = data.get("webhookSubscriptionCreate") or {}
    raise_for_graphql_user_errors(
        user_errors=payload.get("userErrors"),
        operation_name="create_webhook_subscription",
        shop_domain=shop_domain,
    )

    subscription = _map_remote_subscription(payload.get("webhookSubscription") or {})
    if subscription is None:
        raise ShopifyGraphQLNonRetryableError(
            "Shopify webhook subscription create returned no subscription.",
            error_code="missing_subscription",
        )
    return subscription


async def delete_remote_webhook_subscription(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    remote_subscription_id: str,
) -> None:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=DELETE_WEBHOOK_SUBSCRIPTION_MUTATION,
        variables={"id": remote_subscription_id},
        operation_name="delete_webhook_subscription",
    )
    payload = data.get("webhookSubscriptionDelete") or {}
    user_errors = payload.get("userErrors") or []
    if user_errors and _is_not_found_delete_error(user_errors):
        return
    raise_for_graphql_user_errors(
        user_errors=user_errors,
        operation_name="delete_webhook_subscription",
        shop_domain=shop_domain,
    )


def _map_remote_subscription(node: dict) -> RemoteWebhookSubscription | None:
    remote_id = node.get("id")
    topic = node.get("topic")
    endpoint = node.get("endpoint") or {}
    callback_url = endpoint.get("callbackUrl")
    raw_format = (node.get("format") or ShopifyWebhookPayloadFormatEnum.JSON.value).lower()
    if not isinstance(remote_id, str) or not remote_id.strip():
        return None
    if not isinstance(topic, str) or not topic.strip():
        return None
    if not isinstance(callback_url, str) or not callback_url.strip():
        return None
    return RemoteWebhookSubscription(
        id=remote_id,
        topic=topic.lower().replace("_", "/"),
        callback_url=callback_url,
        payload_format=ShopifyWebhookPayloadFormatEnum(raw_format),
    )


def _is_not_found_delete_error(user_errors: list[dict]) -> bool:
    for error in user_errors:
        message = str((error or {}).get("message") or "").lower()
        if "not found" in message:
            return True
    return False
