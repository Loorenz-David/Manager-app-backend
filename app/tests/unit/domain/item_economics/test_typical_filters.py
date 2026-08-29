from fractions import Fraction

import pytest

from beyo_manager.domain.item_economics.typical_constants import TYPICAL_MIN_SAMPLE_SIZE
from beyo_manager.domain.item_economics import typical_constants
from beyo_manager.domain.item_economics import budget_division
from beyo_manager.domain.item_economics.typical_filters import (
    COMPARABILITY_PROFILE,
    RECONCILIATION_METHOD,
    SectionTypicalEvidence,
    SelectedTypical,
    TypicalFilterSpec,
    TypicalResolutionPolicy,
    apply_business_fallback,
    derive_spec_from_primary_item,
    median,
    parse_spec_from_query_params,
    reconcile_task_typicals,
    resolve_section_typical,
)
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item


def evidence(section="section", narrowed_count=7, narrowed=600, section_count=61, section_value=900):
    return SectionTypicalEvidence(section, narrowed, narrowed_count, section_value, section_count)


def test_empty_collections_are_canonical_and_hashable():
    for field in ("item_category_ids", "major_categories", "designers"):
        spec = TypicalFilterSpec(**{field: frozenset()})
        assert spec == TypicalFilterSpec()
        assert hash(spec) == hash(TypicalFilterSpec())
        assert spec.is_narrowing is False


def test_ranges_validate_each_boundary_and_keep_unbounded_sides():
    for field in ("width_cm", "height_cm", "depth_cm"):
        with pytest.raises(ValueError):
            TypicalFilterSpec(**{field: (81, 80)})
        assert TypicalFilterSpec(**{field: (80, 80)}).is_narrowing is True
        assert TypicalFilterSpec(**{field: (60, None)}).is_narrowing is True
        assert TypicalFilterSpec(**{field: (None, 80)}).is_narrowing is True


def test_none_none_range_is_recorded_and_narrowing():
    spec = TypicalFilterSpec(width_cm=(None, None))
    assert spec.is_narrowing is True
    assert spec != TypicalFilterSpec()


def test_frozen_spec_is_the_value_dedupe_key():
    assert len(
        {
            TypicalFilterSpec(item_category_ids=frozenset({"a", "b"})),
            TypicalFilterSpec(item_category_ids=frozenset({"b", "a"})),
        }
    ) == 1
    assert len(
        {
            TypicalFilterSpec(item_category_ids=frozenset({"a"})),
            TypicalFilterSpec(item_category_ids=frozenset({"b"})),
        }
    ) == 2


def test_constants_move_without_changing_exports_or_values():
    assert budget_division.TYPICAL_METHOD is typical_constants.TYPICAL_METHOD
    assert budget_division.TYPICAL_WINDOW_DAYS is typical_constants.TYPICAL_WINDOW_DAYS
    assert budget_division.TYPICAL_MIN_SAMPLE_SIZE is typical_constants.TYPICAL_MIN_SAMPLE_SIZE
    assert typical_constants.TYPICAL_METHOD == "median_completed_section_totals"
    assert typical_constants.TYPICAL_WINDOW_DAYS == 90
    assert typical_constants.TYPICAL_MIN_SAMPLE_SIZE == 5


def test_derive_spec_is_total_on_real_item_instances():
    assert derive_spec_from_primary_item(None) == TypicalFilterSpec()
    no_category = Item(client_id="itm_no_category", item_category_id=None)
    categorized = Item(client_id="itm_category", item_category_id="cat_a")
    assert derive_spec_from_primary_item(no_category) == TypicalFilterSpec()
    assert derive_spec_from_primary_item(categorized) == TypicalFilterSpec(
        item_category_ids=frozenset({"cat_a"})
    )


def test_evidence_predicates_cover_floor_zero_and_none():
    floor = TYPICAL_MIN_SAMPLE_SIZE
    rows = [
        (SectionTypicalEvidence("a", 600, floor - 1, 900, floor), False, True, False),
        (SectionTypicalEvidence("b", 600, floor, 900, floor - 1), True, False, True),
        (SectionTypicalEvidence("c", 0, floor, 900, floor), True, True, False),
        (SectionTypicalEvidence("d", 1, floor, 900, floor), True, True, True),
        (SectionTypicalEvidence("e", None, floor, 900, floor), True, True, False),
    ]
    for row, has_narrowed, has_section, usable in rows:
        assert row.has_narrowed is has_narrowed
        assert row.has_section is has_section
        assert row.has_usable_narrowed is usable


@pytest.mark.parametrize(
    ("spec", "narrowed", "section", "policy", "expected", "assert_full_object"),
    [
        (TypicalFilterSpec(width_cm=(1, 2)), (7, 540), (61, 600), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("item_narrowed", 540, 7), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (7, 0), (61, 600), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("section_wide", 600, 61), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (2, None), (61, 600), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("section_wide", 600, 61), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (2, None), (3, None), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("insufficient_sample", None, 3), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (7, 540), (61, 600), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("item_narrowed", 540, 7), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (7, 0), (61, 600), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("item_narrowed", 0, 7), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (2, None), (61, 600), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("insufficient_sample", None, 2), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (7, 540), (3, None), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("item_narrowed", 540, 7), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (7, 540), (3, None), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("item_narrowed", 540, 7), False),
        (TypicalFilterSpec(width_cm=(1, 2)), (2, None), (3, None), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("insufficient_sample", None, 2), False),
        (TypicalFilterSpec(), (61, 600), (61, 600), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("section_wide", 600, 61), True),
        (TypicalFilterSpec(), (3, None), (4, 800), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("insufficient_sample", None, 4), False),
        (TypicalFilterSpec(), (61, 600), (61, 600), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("section_wide", 600, 61), True),
        (TypicalFilterSpec(), (61, 600), (3, None), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("insufficient_sample", None, 3), False),
    ],
)
def test_resolution_grid(spec, narrowed, section, policy, expected, assert_full_object):
    source_evidence = SectionTypicalEvidence("section", narrowed[1], narrowed[0], section[1], section[0])
    result = resolve_section_typical(
        source_evidence,
        spec,
        policy,
    )
    if assert_full_object:
        assert result == SelectedTypical(
            working_section_id="section",
            typical_worker_seconds=expected[1],
            typical_basis=expected[0],
            evidence=source_evidence,
            participates=False,
            sample_count=expected[2],
        )
    else:
        assert (result.typical_basis, result.typical_worker_seconds, result.sample_count) == expected


def test_reconciliation_uses_uniform_usable_narrowed_basis_and_materializes_missing_rows():
    evidence_by_section = {
        "a": evidence("a", 7, 600, 61, 900),
        "b": evidence("b", 7, 0, 61, 1200),
    }
    result = reconcile_task_typicals(
        evidence_by_section,
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset({"a", "b", "ghost"}),
        frozenset({"a", "b", "ghost"}),
    )
    assert result.task_typical_basis == "section_wide_uniform"
    assert result.selected["ghost"].typical_basis == "insufficient_sample"
    assert result.selected["ghost"].typical_worker_seconds is None
    assert result.selected["ghost"].evidence == SectionTypicalEvidence("ghost", None, 0, None, 0)
    assert result.selected["ghost"].evidence.narrowed_sample_count == 0
    assert result.selected["ghost"].evidence.section_sample_count == 0
    assert result.selected["ghost"].evidence.narrowed_typical_worker_seconds is None
    assert result.selected["ghost"].evidence.section_typical_worker_seconds is None
    assert result.selected["ghost"].sample_count == 0
    assert result.selected["ghost"].participates is True
    assert (
        result.selected["a"].typical_worker_seconds,
        result.selected["a"].typical_basis,
        result.selected["a"].sample_count,
        result.selected["a"].participates,
    ) == (900, "section_wide", 61, True)
    assert (
        result.selected["b"].typical_worker_seconds,
        result.selected["b"].typical_basis,
        result.selected["b"].sample_count,
        result.selected["b"].participates,
    ) == (1200, "section_wide", 61, True)
    assert (
        result.selected["ghost"].typical_worker_seconds,
        result.selected["ghost"].typical_basis,
        result.selected["ghost"].sample_count,
        result.selected["ghost"].participates,
    ) == (None, "insufficient_sample", 0, True)


def test_reconciliation_requires_every_participant_to_have_a_usable_narrowed_value():
    result = reconcile_task_typicals(
        {
            "zero": evidence("zero", 5, 0, 61, 900),
            "usable": evidence("usable", 7, 600, 61, 1200),
        },
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset({"zero", "usable"}),
        frozenset({"zero", "usable"}),
    )
    assert result.task_typical_basis == "section_wide_uniform"


def test_reconciliation_row_c_has_a_below_floor_participant_fixture():
    result = reconcile_task_typicals(
        {
            "below_floor": evidence("below_floor", 3, None, 61, 900),
            "usable": evidence("usable", 7, 600, 61, 1200),
        },
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset({"below_floor", "usable"}),
        frozenset({"below_floor", "usable"}),
    )
    assert result.task_typical_basis == "section_wide_uniform"
    assert (
        result.selected["below_floor"].typical_worker_seconds,
        result.selected["below_floor"].typical_basis,
        result.selected["below_floor"].sample_count,
        result.selected["below_floor"].participates,
    ) == (900, "section_wide", 61, True)
    assert (
        result.selected["usable"].typical_worker_seconds,
        result.selected["usable"].typical_basis,
        result.selected["usable"].sample_count,
        result.selected["usable"].participates,
    ) == (1200, "section_wide", 61, True)


def test_reconciliation_excluded_sections_resolve_independently_and_empty_is_not_uniform_narrowed():
    selected = reconcile_task_typicals(
        {"excluded": evidence("excluded", 7, 600, 2, None)},
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset(),
        frozenset({"excluded"}),
    )
    assert selected.task_typical_basis == "section_wide_uniform"
    assert selected.selected["excluded"].typical_basis == "item_narrowed"
    assert selected.selected["excluded"].participates is False


def test_reconciliation_excludes_thin_rows_from_the_uniform_quantifier():
    selected = reconcile_task_typicals(
        {
            "participant": evidence("participant", 7, 600, 61, 900),
            "excluded": evidence("excluded", 2, None, 61, 900),
        },
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset({"participant"}),
        frozenset({"participant", "excluded"}),
    )
    assert selected.task_typical_basis == "item_narrowed_uniform"
    assert selected.selected["excluded"].typical_basis == "section_wide"
    assert (
        selected.selected["participant"].typical_worker_seconds,
        selected.selected["participant"].typical_basis,
        selected.selected["participant"].sample_count,
        selected.selected["participant"].participates,
    ) == (600, "item_narrowed", 7, True)
    assert (
        selected.selected["excluded"].typical_worker_seconds,
        selected.selected["excluded"].typical_basis,
        selected.selected["excluded"].sample_count,
        selected.selected["excluded"].participates,
    ) == (900, "section_wide", 61, False)


def test_reconciliation_uses_excluded_evidence_independently_in_the_other_direction():
    selected = reconcile_task_typicals(
        {
            "participant": evidence("participant", 2, None, 61, 900),
            "excluded": evidence("excluded", 7, 600, 61, 900),
        },
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset({"participant"}),
        frozenset({"participant", "excluded"}),
    )
    assert selected.task_typical_basis == "section_wide_uniform"
    assert selected.selected["excluded"].typical_basis == "item_narrowed"
    assert (
        selected.selected["participant"].typical_worker_seconds,
        selected.selected["participant"].typical_basis,
        selected.selected["participant"].sample_count,
        selected.selected["participant"].participates,
    ) == (900, "section_wide", 61, True)
    assert (
        selected.selected["excluded"].typical_worker_seconds,
        selected.selected["excluded"].typical_basis,
        selected.selected["excluded"].sample_count,
        selected.selected["excluded"].participates,
    ) == (600, "item_narrowed", 7, False)


def test_reconciliation_non_narrowing_spec_stays_section_wide_for_participants():
    result = reconcile_task_typicals(
        {
            "a": evidence("a", 7, 600, 61, 900),
            "b": evidence("b", 7, 600, 61, 1200),
        },
        TypicalFilterSpec(),
        frozenset({"a", "b"}),
        frozenset({"a", "b"}),
    )
    assert result.task_typical_basis == "section_wide_uniform"
    assert result.applied_filter is None
    assert (
        result.selected["a"].typical_worker_seconds,
        result.selected["a"].typical_basis,
        result.selected["a"].sample_count,
        result.selected["a"].participates,
    ) == (900, "section_wide", 61, True)
    assert (
        result.selected["b"].typical_worker_seconds,
        result.selected["b"].typical_basis,
        result.selected["b"].sample_count,
        result.selected["b"].participates,
    ) == (1200, "section_wide", 61, True)


def test_reconciliation_none_spec_is_unfiltered_and_narrowing_is_carried_by_identity():
    evidence_by_section = {"a": evidence("a")}
    no_spec = reconcile_task_typicals(evidence_by_section, None, frozenset({"a"}), frozenset({"a"}))
    assert no_spec.task_typical_basis == "section_wide_uniform"
    assert no_spec.applied_filter is None

    spec = TypicalFilterSpec(item_category_ids=frozenset({"cat"}))
    narrowed = reconcile_task_typicals(evidence_by_section, spec, frozenset({"a"}), frozenset({"a"}))
    assert narrowed.task_typical_basis == "item_narrowed_uniform"
    assert narrowed.applied_filter is spec
    assert narrowed.reconciliation_method == RECONCILIATION_METHOD
    assert narrowed.comparability_profile == COMPARABILITY_PROFILE
    assert (
        narrowed.selected["a"].typical_worker_seconds,
        narrowed.selected["a"].typical_basis,
        narrowed.selected["a"].sample_count,
        narrowed.selected["a"].participates,
    ) == (600, "item_narrowed", 7, True)


def test_missing_participant_row_forces_section_wide_uniform_basis():
    result = reconcile_task_typicals(
        {"present": evidence("present", 7, 600, 61, 900)},
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset({"present", "ghost"}),
        frozenset({"present", "ghost"}),
    )
    assert result.task_typical_basis == "section_wide_uniform"


def test_reconciliation_preserves_sql_values_without_pace_model():
    result = reconcile_task_typicals(
        {name: evidence(name, 7, value, 61, 1000) for name, value in (("a", 600), ("b", 900), ("c", 300))},
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset({"a", "b", "c"}),
        frozenset({"a", "b", "c"}),
    )
    assert {row.typical_worker_seconds for row in result.selected.values()} == {300, 600, 900}
    assert all(row.sample_count == 7 for row in result.selected.values())


def test_business_fallback_has_typed_distinct_terminals_and_zero_is_unusable():
    with pytest.raises(TypeError):
        apply_business_fallback([600, 900], terminal=1)  # type: ignore[arg-type]
    assert apply_business_fallback([None, None], terminal=Fraction(1, 1)) == [Fraction(1), Fraction(1)]
    assert apply_business_fallback([None, None], terminal=Fraction(0, 1)) == [Fraction(0), Fraction(0)]
    assert apply_business_fallback([0, 600, 900], terminal=Fraction(1, 1)) == [Fraction(750), Fraction(600), Fraction(900)]


def test_parser_handles_typed_params_absence_none_enums_and_client_errors():
    assert parse_spec_from_query_params({}) == TypicalFilterSpec()
    assert parse_spec_from_query_params({"item_category_ids": ["a", "b"]}).item_category_ids == frozenset({"a", "b"})
    assert parse_spec_from_query_params({"width_cm_min": 60, "width_cm_max": 80}).width_cm == (60, 80)
    assert parse_spec_from_query_params({"width_cm_min": 60}).width_cm == (60, None)
    assert parse_spec_from_query_params({"width_cm_max": 80}).width_cm == (None, 80)
    assert parse_spec_from_query_params({"width_cm_min": None, "item_category_ids": None}) == TypicalFilterSpec()
    assert parse_spec_from_query_params(
        {"major_categories": [ItemMajorCategoryEnum.WOOD.value, ItemMajorCategoryEnum.SEAT.value]}
    ).major_categories == frozenset(
        {ItemMajorCategoryEnum.WOOD, ItemMajorCategoryEnum.SEAT}
    )
    assert parse_spec_from_query_params({"can_have_upholstery": True}).can_have_upholstery is True
    assert parse_spec_from_query_params({"can_have_upholstery": False}).can_have_upholstery is False
    assert parse_spec_from_query_params({"designers": ["dsg_a", "dsg_b"]}).designers == frozenset({"dsg_a", "dsg_b"})
    assert parse_spec_from_query_params({"unknown": "ignored"}) == TypicalFilterSpec()
    assert parse_spec_from_query_params({"item_category_ids": []}) == TypicalFilterSpec()
    with pytest.raises(ValidationError):
        parse_spec_from_query_params({"width_cm_min": 81, "width_cm_max": 80})
    with pytest.raises(ValidationError):
        parse_spec_from_query_params({"major_categories": ["stone"]})


@pytest.mark.parametrize(
    "params",
    [
        {"item_category_ids": "cat_a"},
        {"designers": "dsg_a"},
        {"item_category_ids": 5},
    ],
)
def test_parser_rejects_bare_strings_and_non_iterable_repeatable_values(params):
    with pytest.raises(ValidationError):
        parse_spec_from_query_params(params)


@pytest.mark.parametrize(
    ("params", "family"),
    [
        ({"item_category_ids": bytearray(b"ab")}, "item_category_ids"),
        ({"item_category_ids": memoryview(b"ab")}, "item_category_ids"),
        ({"item_category_ids": {"cat_a": 1}}, "item_category_ids"),
        ({"major_categories": {"wood": 1}}, "major_categories"),
        ({"major_categories": ItemMajorCategoryEnum.WOOD.value}, "major_categories"),
    ],
)
def test_parser_rejects_mapping_and_byte_iterable_repeatable_values(params, family):
    match = (
        "must be a sequence of values"
        if family == "major_categories" and isinstance(params["major_categories"], str)
        else family
    )
    with pytest.raises(ValidationError, match=match):
        parse_spec_from_query_params(params)


def test_parser_rejects_non_boolean_upholstery_value():
    with pytest.raises(ValidationError, match="can_have_upholstery"):
        parse_spec_from_query_params({"can_have_upholstery": "yes"})


def test_median_preserves_even_odd_and_sorting_rules():
    assert median([Fraction(600), Fraction(900)]) == Fraction(750)
    assert median([Fraction(300), Fraction(600), Fraction(900)]) == Fraction(600)
    assert median([Fraction(900), Fraction(300), Fraction(600)]) == Fraction(600)


# --- properties (item complexity) tier ---------------------------------------


def properties_evidence(
    section="section",
    properties_count=7,
    properties_value=300,
    narrowed_count=7,
    narrowed=600,
    section_count=61,
    section_value=900,
    properties_unit=None,
):
    return SectionTypicalEvidence(
        section,
        narrowed,
        narrowed_count,
        section_value,
        section_count,
        properties_typical_worker_seconds=properties_value,
        properties_sample_count=properties_count,
        properties_typical_unit_worker_seconds=properties_unit,
    )


def test_properties_signature_alone_is_inert_and_empty_string_is_none():
    bare = TypicalFilterSpec(properties_signature="sig-a")
    assert bare.is_narrowing is False
    assert TypicalFilterSpec(properties_signature="") == TypicalFilterSpec()
    assert hash(TypicalFilterSpec(properties_signature="")) == hash(TypicalFilterSpec())
    with_category = TypicalFilterSpec(
        item_category_ids=frozenset({"cat"}), properties_signature="sig-a"
    )
    assert with_category.is_narrowing is True
    assert with_category != TypicalFilterSpec(item_category_ids=frozenset({"cat"}))


def test_derive_spec_carries_signature_only_beside_a_category():
    signed = Item(client_id="itm_signed", item_category_id="cat_a", properties_signature="sig-a")
    unsigned = Item(client_id="itm_unsigned", item_category_id="cat_a", properties_signature=None)
    orphan_signature = Item(client_id="itm_orphan", item_category_id=None, properties_signature="sig-a")
    assert derive_spec_from_primary_item(signed) == TypicalFilterSpec(
        item_category_ids=frozenset({"cat_a"}), properties_signature="sig-a"
    )
    assert derive_spec_from_primary_item(unsigned) == TypicalFilterSpec(
        item_category_ids=frozenset({"cat_a"})
    )
    assert derive_spec_from_primary_item(orphan_signature) == TypicalFilterSpec()


def test_properties_evidence_predicates_cover_floor_zero_and_none():
    floor = TYPICAL_MIN_SAMPLE_SIZE
    rows = [
        (properties_evidence("a", floor - 1, 300), False, False),
        (properties_evidence("b", floor, 300), True, True),
        (properties_evidence("c", floor, 0), True, False),
        (properties_evidence("d", floor, None), True, False),
    ]
    for row, has_properties, usable in rows:
        assert row.has_properties is has_properties
        assert row.has_usable_properties is usable


SIGNED_SPEC = TypicalFilterSpec(item_category_ids=frozenset({"cat"}), properties_signature="sig-a")


@pytest.mark.parametrize(
    ("properties", "narrowed", "section", "policy", "expected"),
    [
        # BROADEN ladder: properties -> narrowed -> section -> insufficient.
        ((7, 300), (9, 600), (61, 900), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("item_properties_narrowed", 300, 7)),
        ((4, None), (9, 600), (61, 900), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("item_narrowed", 600, 9)),
        ((7, 0), (9, 600), (61, 900), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("item_narrowed", 600, 9)),
        ((4, None), (9, 0), (61, 900), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("section_wide", 900, 61)),
        ((4, None), (3, None), (3, None), TypicalResolutionPolicy.BROADEN_TO_SECTION, ("insufficient_sample", None, 3)),
        # ANSWER_AS_ASKED answers at the asked (most specific) tier only.
        ((7, 300), (9, 600), (61, 900), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("item_properties_narrowed", 300, 7)),
        ((7, 0), (9, 600), (61, 900), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("item_properties_narrowed", 0, 7)),
        ((4, None), (9, 600), (61, 900), TypicalResolutionPolicy.ANSWER_AS_ASKED, ("insufficient_sample", None, 4)),
    ],
)
def test_properties_resolution_ladder(properties, narrowed, section, policy, expected):
    source = SectionTypicalEvidence(
        "section",
        narrowed[1],
        narrowed[0],
        section[1],
        section[0],
        properties_typical_worker_seconds=properties[1],
        properties_sample_count=properties[0],
    )
    result = resolve_section_typical(source, SIGNED_SPEC, policy)
    assert (result.typical_basis, result.typical_worker_seconds, result.sample_count) == expected


def test_properties_tier_never_fires_without_a_signature_even_with_evidence():
    source = properties_evidence("section", 9, 300, 9, 600, 61, 900)
    spec = TypicalFilterSpec(item_category_ids=frozenset({"cat"}))
    for policy in (TypicalResolutionPolicy.BROADEN_TO_SECTION, TypicalResolutionPolicy.ANSWER_AS_ASKED):
        result = resolve_section_typical(source, spec, policy)
        assert result.typical_basis == "item_narrowed"
        assert result.typical_worker_seconds == 600


def test_properties_selection_carries_its_unit_twin():
    source = properties_evidence("section", 7, 300, properties_unit=Fraction(150))
    result = resolve_section_typical(
        source, SIGNED_SPEC, TypicalResolutionPolicy.BROADEN_TO_SECTION
    )
    assert result.typical_basis == "item_properties_narrowed"
    assert result.typical_unit_worker_seconds == Fraction(150)


def test_reconciliation_properties_uniform_needs_every_participant_and_discloses_profile():
    from beyo_manager.domain.item_economics.typical_filters import COMPARABILITY_PROFILE_PROPERTIES

    uniform = reconcile_task_typicals(
        {
            "a": properties_evidence("a", 7, 300, properties_unit=Fraction(100)),
            "b": properties_evidence("b", 6, 450, section_value=1200),
        },
        SIGNED_SPEC,
        frozenset({"a", "b"}),
        frozenset({"a", "b"}),
    )
    assert uniform.task_typical_basis == "item_properties_narrowed_uniform"
    assert uniform.comparability_profile == COMPARABILITY_PROFILE_PROPERTIES
    assert (
        uniform.selected["a"].typical_basis,
        uniform.selected["a"].typical_worker_seconds,
        uniform.selected["a"].sample_count,
        uniform.selected["a"].typical_unit_worker_seconds,
        uniform.selected["a"].participates,
    ) == ("item_properties_narrowed", 300, 7, Fraction(100), True)

    # One participant below the properties gate: whole task falls to the
    # category tier (all have usable narrowed), profile still discloses that
    # properties comparability was applied.
    fallback = reconcile_task_typicals(
        {
            "a": properties_evidence("a", 7, 300),
            "b": properties_evidence("b", 3, None),
        },
        SIGNED_SPEC,
        frozenset({"a", "b"}),
        frozenset({"a", "b"}),
    )
    assert fallback.task_typical_basis == "item_narrowed_uniform"
    assert fallback.comparability_profile == COMPARABILITY_PROFILE_PROPERTIES
    assert fallback.selected["a"].typical_basis == "item_narrowed"
    assert fallback.selected["a"].typical_worker_seconds == 600

    # Without a signature nothing changes, including the disclosed profile.
    unsigned = reconcile_task_typicals(
        {
            "a": evidence("a"),
            "b": evidence("b"),
        },
        TypicalFilterSpec(item_category_ids=frozenset({"cat"})),
        frozenset({"a", "b"}),
        frozenset({"a", "b"}),
    )
    assert unsigned.task_typical_basis == "item_narrowed_uniform"
    assert unsigned.comparability_profile == COMPARABILITY_PROFILE


def test_reconciliation_excluded_section_broadens_down_the_full_ladder():
    result = reconcile_task_typicals(
        {
            "participant": properties_evidence("participant", 7, 300),
            "excluded_props": properties_evidence("excluded_props", 8, 500),
            "excluded_thin": properties_evidence("excluded_thin", 2, None),
        },
        SIGNED_SPEC,
        frozenset({"participant"}),
        frozenset({"participant", "excluded_props", "excluded_thin"}),
    )
    assert result.task_typical_basis == "item_properties_narrowed_uniform"
    assert result.selected["excluded_props"].typical_basis == "item_properties_narrowed"
    assert result.selected["excluded_props"].typical_worker_seconds == 500
    assert result.selected["excluded_props"].participates is False
    assert result.selected["excluded_thin"].typical_basis == "item_narrowed"
    assert result.selected["excluded_thin"].typical_worker_seconds == 600
