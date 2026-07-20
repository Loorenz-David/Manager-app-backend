import pytest

from beyo_manager.domain.connecteam.normalize_username import (
    build_external_full_name,
    normalize_username,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  Ana   Maria ", "ana maria"),
        ("Ａｎａ", "ana"),
        ("Åsa", "åsa"),
        ("SingleName", "singlename"),
    ],
)
def test_normalize_username(value, expected):
    assert normalize_username(value) == expected


def test_full_name_joins_only_non_empty_parts():
    assert build_external_full_name(" Andrii ", "") == "Andrii"
    assert build_external_full_name("", "Builder") == "Builder"
    assert build_external_full_name(" ", None) is None


@pytest.mark.parametrize("value", ["ana maria", "ana", "maria ana"])
def test_matching_is_not_partial_or_reordered(value):
    assert normalize_username(value) != normalize_username("Ana Maria Builder")
