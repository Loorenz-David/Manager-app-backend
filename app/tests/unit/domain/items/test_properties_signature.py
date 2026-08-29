"""The signature is structural canonicalization only; values are trusted verbatim."""

import pytest

from beyo_manager.domain.items.properties_signature import compute_properties_signature


def test_signature_is_deterministic_and_key_order_insensitive_recursively():
    a = {"wood": "oak", "upholstery": {"seat": True, "back": False}}
    b = {"upholstery": {"back": False, "seat": True}, "wood": "oak"}
    assert compute_properties_signature(a) == compute_properties_signature(b)
    assert len(compute_properties_signature(a)) == 64
    assert compute_properties_signature(a) == compute_properties_signature(dict(a))


def test_values_are_verbatim_so_spelling_units_and_list_order_discriminate():
    base = {"wood": "oak", "finishes": ["wax", "stain"]}
    assert compute_properties_signature(base) != compute_properties_signature({"wood": "Oak", "finishes": ["wax", "stain"]})
    assert compute_properties_signature(base) != compute_properties_signature({"wood": "oak", "finishes": ["stain", "wax"]})
    assert compute_properties_signature({"height": 90}) != compute_properties_signature({"height": "90"})


def test_empty_snapshot_has_a_signature_distinct_from_any_property_set():
    assert compute_properties_signature({}) != compute_properties_signature({"wood": "oak"})
    assert compute_properties_signature({}) == compute_properties_signature({})


def test_unicode_values_hash_stably_without_ascii_escaping_ambiguity():
    assert compute_properties_signature({"fabric": "bouclé"}) == compute_properties_signature({"fabric": "bouclé"})
    assert compute_properties_signature({"fabric": "bouclé"}) != compute_properties_signature({"fabric": "boucle"})


@pytest.mark.parametrize("bad", [None, "wood=oak", ["wood", "oak"], 5])
def test_non_dict_snapshots_are_rejected_not_hashed(bad):
    with pytest.raises(TypeError):
        compute_properties_signature(bad)
