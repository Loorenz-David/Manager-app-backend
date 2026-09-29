"""API routes that use stored credentials respect OUTBOUND_INTEGRATIONS_ENABLED.

The five services behind these routes sign in to a stored mailbox or call a Shopify
shop with its stored token, from the request path rather than a task. With outbound
integrations disabled (staging, local) they refuse before touching the database, the
credentials or the network. Enabled (production), they behave exactly as before.

Defence in depth only: staging's network egress allow-list is the boundary (D33).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from beyo_manager.config import settings
from beyo_manager.errors.external_service import OutboundIntegrationsDisabledError
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
# Aliased: pytest would collect a module-level name starting with test_ as a test.
from beyo_manager.services.commands.emails.test_email_connection import (
    test_email_connection as email_connection_test_service,
)
from beyo_manager.services.commands.shopify.create_shopify_metafield_preferences import (
    create_shopify_metafield_preferences,
)
from beyo_manager.services.queries.shopify.get_shopify_locations import get_shopify_locations
from beyo_manager.services.queries.shopify.get_shopify_metafield_preferences import (
    get_shopify_metafield_preferences,
)
from beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity import (
    lookup_shopify_customers_by_product_identity,
)
from beyo_manager.services.run_service import run_service

# Route → service. Every route that reaches a third party with stored credentials.
GUARDED = {
    "POST /api/v1/email-connections/{connection_id}/test": email_connection_test_service,
    "GET /api/v1/integrations/shopify/locations": get_shopify_locations,
    "GET /api/v1/integrations/shopify/metafield-preferences": get_shopify_metafield_preferences,
    "POST /api/v1/integrations/shopify/metafield-preferences": create_shopify_metafield_preferences,
    "POST /api/v1/integrations/shopify/customers/by-product-identity": lookup_shopify_customers_by_product_identity,
}


class _Untouchable:
    """A context whose every attribute fails: proves the refusal comes first."""

    def __getattr__(self, name):
        raise AssertionError(f"service touched ctx.{name} although outbound is disabled")


@pytest.fixture
def outbound_disabled(monkeypatch):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", False)


@pytest.fixture
def outbound_enabled(monkeypatch):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", True)


@pytest.mark.unit
@pytest.mark.parametrize("route", GUARDED)
async def test_refused_before_any_database_credential_or_network_use(route, outbound_disabled):
    with pytest.raises(OutboundIntegrationsDisabledError):
        await GUARDED[route](_Untouchable())


@pytest.mark.unit
@pytest.mark.parametrize("route", GUARDED)
async def test_refusal_is_a_503_outcome_not_a_crash(route, outbound_disabled):
    ctx = SimpleNamespace(user_id="usr_1", workspace_id="ws_1", incoming_data={}, query_params={})
    ctx.session = MagicMock(side_effect=AssertionError("session used"))

    outcome = await run_service(GUARDED[route], ctx)

    assert outcome.success is False
    assert isinstance(outcome.error, OutboundIntegrationsDisabledError)
    assert outcome.error.http_status == 503


def _enabled_ctx(**overrides) -> SimpleNamespace:
    session = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)),
    )
    ctx = SimpleNamespace(
        user_id="usr_1", workspace_id="ws_1", role_name="admin",
        incoming_data={}, query_params={}, session=session,
    )
    for name, value in overrides.items():
        setattr(ctx, name, value)
    return ctx


@pytest.mark.unit
@pytest.mark.parametrize(
    ("route", "ctx_overrides", "existing_refusal"),
    [
        # Each reaches its own, unchanged first check. The integration tests of these
        # services cover the full enabled behaviour.
        ("POST /api/v1/email-connections/{connection_id}/test", {"incoming_data": {"connection_client_id": "ec_missing"}}, NotFound),
        ("GET /api/v1/integrations/shopify/locations", {}, ValidationError),
        ("GET /api/v1/integrations/shopify/metafield-preferences", {}, ValidationError),
        ("POST /api/v1/integrations/shopify/metafield-preferences", {}, ValidationError),
        ("POST /api/v1/integrations/shopify/customers/by-product-identity", {}, ValidationError),
    ],
)
async def test_enabled_keeps_the_existing_behaviour(route, ctx_overrides, existing_refusal, outbound_enabled):
    with pytest.raises(existing_refusal):
        await GUARDED[route](_enabled_ctx(**ctx_overrides))


@pytest.mark.unit
def test_every_guarded_route_exists_with_that_method():
    """The table above names real routes; renaming one must update it."""
    from beyo_manager import create_app

    app = create_app()
    routes = {
        f"{method} {route.path}"
        for route in app.routes
        for method in getattr(route, "methods", set()) or set()
    }
    assert set(GUARDED) <= routes, set(GUARDED) - routes
