import pytest

from beyo_manager.domain.app_update_presentations.action_route import (
    validate_action_route,
)
from beyo_manager.errors.validation import ValidationError


@pytest.mark.unit
def test_none_is_allowed():
    validate_action_route(None)


@pytest.mark.unit
@pytest.mark.parametrize("route", ["/products/search", "/tasks/123", "/"])
def test_relative_paths_allowed(route):
    validate_action_route(route)


@pytest.mark.unit
@pytest.mark.parametrize(
    "route",
    [
        "",
        "products",  # no leading slash
        "//evil.com",  # protocol-relative
        "https://evil.com",
        "http://evil.com",
        "javascript://alert(1)",
    ],
)
def test_unsafe_routes_rejected(route):
    with pytest.raises(ValidationError):
        validate_action_route(route)
