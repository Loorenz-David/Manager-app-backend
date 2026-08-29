"""Pure item-aware typical-time filtering and reconciliation rules."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import Protocol


from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.errors.validation import ValidationError

from beyo_manager.domain.item_economics.typical_constants import TYPICAL_MIN_SAMPLE_SIZE


COMPARABILITY_PROFILE = "primary_item_category_v1"
# v2: the properties comparability ladder gained owner-declared facet rungs
# between the full profile and the category tier.
COMPARABILITY_PROFILE_PROPERTIES = "primary_item_category_properties_v2"
RECONCILIATION_METHOD = "uniform_basis_v1"

# The owner-declared partial-match fallbacks, most important first. Each entry
# is a set of property keys that carries predictive weight on its own; a rung
# exists for an item only when its snapshot has every key of the facet. Order
# in this tuple IS the priority order between the full profile and the
# category tier. Never derived from data — extending it is an owner decision.
PROPERTY_FACET_LADDER: tuple[tuple[str, ...], ...] = (("upholstery",), ("extension_type",))


class _PrimaryItem(Protocol):
    item_category_id: str | None
    properties_signature: str | None
    properties: dict | None


@dataclass(frozen=True)
class PropertiesFacet:
    """One ladder rung: the facet's keys and the current item's values for them.

    ``match_json`` is the canonical JSON object of exactly those key/value
    pairs — hashable for spec dedup and directly usable as a JSONB containment
    operand, so the rung means "history whose snapshot contains these pairs".
    """

    keys: tuple[str, ...]
    match_json: str

    @property
    def name(self) -> str:
        return "+".join(self.keys)

    def match_values(self) -> dict:
        return json.loads(self.match_json)


def derive_property_facets(properties: object) -> tuple[PropertiesFacet, ...]:
    """Build the item's available ladder rungs, in declared priority order."""
    if not isinstance(properties, dict):
        return ()
    facets = []
    for keys in PROPERTY_FACET_LADDER:
        if all(key in properties for key in keys):
            match = {key: properties[key] for key in keys}
            facets.append(
                PropertiesFacet(keys, json.dumps(match, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
            )
    return tuple(facets)


@dataclass(frozen=True)
class TypicalFilterSpec:
    """A canonical description of the population for which typicals are measured.

    A range of ``(None, None)`` records that the dimension is present and known;
    it is not equivalent to an unset dimension and therefore remains narrowing.
    """

    item_category_ids: frozenset[str] | None = None
    major_categories: frozenset[ItemMajorCategoryEnum] | None = None
    width_cm: tuple[int | None, int | None] | None = None
    height_cm: tuple[int | None, int | None] | None = None
    depth_cm: tuple[int | None, int | None] | None = None
    can_have_upholstery: bool | None = None
    designers: frozenset[str] | None = None
    # Refines an already-narrowing spec into its most specific comparability
    # tier (same category AND same properties profile). It is deliberately not
    # a narrowing dimension on its own: a spec carrying only a signature stays
    # non-narrowing and the signature is inert.
    properties_signature: str | None = None
    # The item's available partial-match rungs, in ladder priority order. Only
    # ever carried beside a signature; cleared otherwise so facets can never
    # outlive the profile they fall back from.
    properties_facets: tuple[PropertiesFacet, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("item_category_ids", "major_categories", "designers"):
            value = getattr(self, field_name)
            if value is not None and not value:
                object.__setattr__(self, field_name, None)
        if self.properties_signature is not None and not self.properties_signature:
            object.__setattr__(self, "properties_signature", None)
        if self.properties_facets and self.properties_signature is None:
            object.__setattr__(self, "properties_facets", ())

        for field_name in ("width_cm", "height_cm", "depth_cm"):
            value = getattr(self, field_name)
            if value is not None:
                lo, hi = value
                if lo is not None and hi is not None and lo > hi:
                    raise ValueError(f"{field_name} lower bound must not exceed upper bound")

    @property
    def is_narrowing(self) -> bool:
        return any(
            value is not None
            for value in (
                self.item_category_ids,
                self.major_categories,
                self.width_cm,
                self.height_cm,
                self.depth_cm,
                self.can_have_upholstery,
                self.designers,
            )
        )


def derive_spec_from_primary_item(item: _PrimaryItem | None) -> TypicalFilterSpec:
    category_id = getattr(item, "item_category_id", None)
    if category_id is None:
        return TypicalFilterSpec()
    signature = getattr(item, "properties_signature", None)
    return TypicalFilterSpec(
        item_category_ids=frozenset({category_id}),
        properties_signature=signature,
        properties_facets=(
            derive_property_facets(getattr(item, "properties", None)) if signature is not None else ()
        ),
    )


def _optional_values(params: Mapping[str, object], key: str) -> frozenset[str] | None:
    raw = params.get(key)
    if raw is None:
        return None
    if isinstance(raw, (str, bytes, bytearray, memoryview, Mapping)):
        raise ValidationError(f"{key} must be a sequence of values.")
    try:
        values = iter(raw)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValidationError(f"{key} must be a sequence of values.") from exc
    return frozenset(str(value) for value in values)


def _optional_categories(params: Mapping[str, object]) -> frozenset[ItemMajorCategoryEnum] | None:
    raw = params.get("major_categories")
    if raw is None:
        return None
    if isinstance(raw, (str, bytes, bytearray, memoryview, Mapping)):
        raise ValidationError("major_categories must be a sequence of values.")
    categories: set[ItemMajorCategoryEnum] = set()
    try:
        for value in raw:  # type: ignore[union-attr]
            categories.add(value if isinstance(value, ItemMajorCategoryEnum) else ItemMajorCategoryEnum(value))
    except (TypeError, ValueError) as exc:
        raise ValidationError("major_categories contains an unknown value.") from exc
    return frozenset(categories)


def _optional_range(
    params: Mapping[str, object], minimum_key: str, maximum_key: str
) -> tuple[int | None, int | None] | None:
    lo = params.get(minimum_key)
    hi = params.get(maximum_key)
    if lo is None and hi is None:
        return None
    try:
        return int(lo) if lo is not None else None, int(hi) if hi is not None else None
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{minimum_key}/{maximum_key} must be integers.") from exc


def parse_spec_from_query_params(params: Mapping[str, object]) -> TypicalFilterSpec:
    upholstery = params.get("can_have_upholstery")
    if upholstery is not None and not isinstance(upholstery, bool):
        raise ValidationError("can_have_upholstery must be a boolean.")
    try:
        return TypicalFilterSpec(
            item_category_ids=_optional_values(params, "item_category_ids"),
            major_categories=_optional_categories(params),
            width_cm=_optional_range(params, "width_cm_min", "width_cm_max"),
            height_cm=_optional_range(params, "height_cm_min", "height_cm_max"),
            depth_cm=_optional_range(params, "depth_cm_min", "depth_cm_max"),
            can_have_upholstery=upholstery,
            designers=_optional_values(params, "designers"),
        )
    except ValueError as exc:
        raise ValidationError("Typical filter range is invalid.") from exc


@dataclass(frozen=True)
class FacetEvidence:
    """One facet rung's medians for one section, aligned by index with the spec's facets."""

    typical_worker_seconds: int | None
    sample_count: int
    typical_unit_worker_seconds: Fraction | None = None

    @property
    def has_samples(self) -> bool:
        return self.sample_count >= TYPICAL_MIN_SAMPLE_SIZE

    @property
    def has_usable(self) -> bool:
        return (
            self.has_samples
            and self.typical_worker_seconds is not None
            and self.typical_worker_seconds > 0
        )


@dataclass(frozen=True)
class SectionTypicalEvidence:
    working_section_id: str
    narrowed_typical_worker_seconds: int | None
    narrowed_sample_count: int
    section_typical_worker_seconds: int | None
    section_sample_count: int
    # Per-unit twins of the two medians above: the same populations normalized by
    # each historical task's PRIMARY-item quantity (clamped to >= 1). They qualify
    # under the same sample gates and never influence basis selection.
    narrowed_typical_unit_worker_seconds: Fraction | None = None
    section_typical_unit_worker_seconds: Fraction | None = None
    # The most specific tier: same category AND same properties signature.
    # Populated only when the spec carried a signature; zero/None otherwise.
    properties_typical_worker_seconds: int | None = None
    properties_sample_count: int = 0
    properties_typical_unit_worker_seconds: Fraction | None = None
    # Facet rungs between the full profile and the category tier, aligned by
    # index with the spec's properties_facets; empty when the spec had none.
    facet_evidence: tuple[FacetEvidence, ...] = ()

    @property
    def has_narrowed(self) -> bool:
        return self.narrowed_sample_count >= TYPICAL_MIN_SAMPLE_SIZE

    @property
    def has_section(self) -> bool:
        return self.section_sample_count >= TYPICAL_MIN_SAMPLE_SIZE

    @property
    def has_usable_narrowed(self) -> bool:
        return (
            self.has_narrowed
            and self.narrowed_typical_worker_seconds is not None
            and self.narrowed_typical_worker_seconds > 0
        )

    @property
    def has_properties(self) -> bool:
        return self.properties_sample_count >= TYPICAL_MIN_SAMPLE_SIZE

    @property
    def has_usable_properties(self) -> bool:
        return (
            self.has_properties
            and self.properties_typical_worker_seconds is not None
            and self.properties_typical_worker_seconds > 0
        )


class TypicalResolutionPolicy(Enum):
    BROADEN_TO_SECTION = "broaden_to_section"
    ANSWER_AS_ASKED = "answer_as_asked"


@dataclass(frozen=True)
class SelectedTypical:
    working_section_id: str
    typical_worker_seconds: int | None
    typical_basis: str
    evidence: SectionTypicalEvidence
    participates: bool
    sample_count: int
    # The per-unit value of the same basis the raw typical was selected from.
    # Consumers scale it by the current task's quantity for absolute projections;
    # division weights keep reading typical_worker_seconds.
    typical_unit_worker_seconds: Fraction | None = None


def resolve_section_typical(
    evidence: SectionTypicalEvidence,
    spec: TypicalFilterSpec,
    policy: TypicalResolutionPolicy,
) -> SelectedTypical:
    if not spec.is_narrowing:
        if evidence.has_section:
            return SelectedTypical(
                evidence.working_section_id,
                evidence.section_typical_worker_seconds,
                "section_wide",
                evidence,
                False,
                evidence.section_sample_count,
                evidence.section_typical_unit_worker_seconds,
            )
        return SelectedTypical(
            evidence.working_section_id,
            None,
            "insufficient_sample",
            evidence,
            False,
            evidence.section_sample_count,
        )

    if policy is TypicalResolutionPolicy.BROADEN_TO_SECTION:
        if spec.properties_signature is not None and evidence.has_usable_properties:
            return SelectedTypical(
                evidence.working_section_id,
                evidence.properties_typical_worker_seconds,
                "item_properties_narrowed",
                evidence,
                False,
                evidence.properties_sample_count,
                evidence.properties_typical_unit_worker_seconds,
            )
        for facet_index in range(len(spec.properties_facets)):
            facet = (
                evidence.facet_evidence[facet_index]
                if facet_index < len(evidence.facet_evidence)
                else None
            )
            if facet is not None and facet.has_usable:
                return SelectedTypical(
                    evidence.working_section_id,
                    facet.typical_worker_seconds,
                    "item_facet_narrowed",
                    evidence,
                    False,
                    facet.sample_count,
                    facet.typical_unit_worker_seconds,
                )
        if evidence.has_usable_narrowed:
            return SelectedTypical(
                evidence.working_section_id,
                evidence.narrowed_typical_worker_seconds,
                "item_narrowed",
                evidence,
                False,
                evidence.narrowed_sample_count,
                evidence.narrowed_typical_unit_worker_seconds,
            )
        if evidence.has_section:
            return SelectedTypical(
                evidence.working_section_id,
                evidence.section_typical_worker_seconds,
                "section_wide",
                evidence,
                False,
                evidence.section_sample_count,
                evidence.section_typical_unit_worker_seconds,
            )
        return SelectedTypical(
            evidence.working_section_id,
            None,
            "insufficient_sample",
            evidence,
            False,
            evidence.section_sample_count,
        )

    if policy is TypicalResolutionPolicy.ANSWER_AS_ASKED:
        if spec.properties_signature is not None:
            if evidence.has_properties:
                return SelectedTypical(
                    evidence.working_section_id,
                    evidence.properties_typical_worker_seconds,
                    "item_properties_narrowed",
                    evidence,
                    False,
                    evidence.properties_sample_count,
                    evidence.properties_typical_unit_worker_seconds,
                )
            return SelectedTypical(
                evidence.working_section_id,
                None,
                "insufficient_sample",
                evidence,
                False,
                evidence.properties_sample_count,
            )
        if evidence.has_narrowed:
            return SelectedTypical(
                evidence.working_section_id,
                evidence.narrowed_typical_worker_seconds,
                "item_narrowed",
                evidence,
                False,
                evidence.narrowed_sample_count,
                evidence.narrowed_typical_unit_worker_seconds,
            )
        return SelectedTypical(
            evidence.working_section_id,
            None,
            "insufficient_sample",
            evidence,
            False,
            evidence.narrowed_sample_count,
        )

    raise TypeError(f"Unsupported typical resolution policy: {policy!r}")


@dataclass(frozen=True)
class TaskTypicalSelection:
    task_typical_basis: str
    reconciliation_method: str
    comparability_profile: str
    applied_filter: TypicalFilterSpec | None
    participating_section_ids: frozenset[str]
    selected: Mapping[str, SelectedTypical]
    # The facet name (e.g. "upholstery") when the participating basis is a
    # facet rung; None on every other basis.
    facet: str | None = None


def _zero_evidence(section_id: str) -> SectionTypicalEvidence:
    return SectionTypicalEvidence(section_id, None, 0, None, 0)


def reconcile_task_typicals(
    evidence_by_section: Mapping[str, SectionTypicalEvidence],
    spec: TypicalFilterSpec | None,
    participating_section_ids: frozenset[str],
    section_ids: frozenset[str],
) -> TaskTypicalSelection:
    effective_spec = spec if spec is not None else TypicalFilterSpec()
    evidence = {
        section_id: evidence_by_section.get(section_id, _zero_evidence(section_id))
        for section_id in section_ids
    }
    properties_uniform = (
        effective_spec.is_narrowing
        and effective_spec.properties_signature is not None
        and bool(participating_section_ids)
        and all(evidence[section_id].has_usable_properties for section_id in participating_section_ids)
    )

    def _facet_usable(section_id: str, facet_index: int) -> bool:
        facets = evidence[section_id].facet_evidence
        return facet_index < len(facets) and facets[facet_index].has_usable

    facet_uniform_index: int | None = None
    if not properties_uniform and effective_spec.is_narrowing and participating_section_ids:
        for index in range(len(effective_spec.properties_facets)):
            if all(_facet_usable(section_id, index) for section_id in participating_section_ids):
                facet_uniform_index = index
                break
    narrowed_uniform = (
        not properties_uniform
        and facet_uniform_index is None
        and effective_spec.is_narrowing
        and bool(participating_section_ids)
        and all(evidence[section_id].has_usable_narrowed for section_id in participating_section_ids)
    )
    if properties_uniform:
        task_basis = "item_properties_narrowed_uniform"
    elif facet_uniform_index is not None:
        task_basis = "item_facet_narrowed_uniform"
    elif narrowed_uniform:
        task_basis = "item_narrowed_uniform"
    else:
        task_basis = "section_wide_uniform"
    selected: dict[str, SelectedTypical] = {}

    for section_id in section_ids:
        section_evidence = evidence[section_id]
        if section_id in participating_section_ids:
            if properties_uniform:
                selected[section_id] = SelectedTypical(
                    section_id,
                    section_evidence.properties_typical_worker_seconds,
                    "item_properties_narrowed",
                    section_evidence,
                    True,
                    section_evidence.properties_sample_count,
                    section_evidence.properties_typical_unit_worker_seconds,
                )
            elif facet_uniform_index is not None:
                facet = section_evidence.facet_evidence[facet_uniform_index]
                selected[section_id] = SelectedTypical(
                    section_id,
                    facet.typical_worker_seconds,
                    "item_facet_narrowed",
                    section_evidence,
                    True,
                    facet.sample_count,
                    facet.typical_unit_worker_seconds,
                )
            elif narrowed_uniform:
                selected[section_id] = SelectedTypical(
                    section_id,
                    section_evidence.narrowed_typical_worker_seconds,
                    "item_narrowed",
                    section_evidence,
                    True,
                    section_evidence.narrowed_sample_count,
                    section_evidence.narrowed_typical_unit_worker_seconds,
                )
            else:
                selected[section_id] = SelectedTypical(
                    section_id,
                    section_evidence.section_typical_worker_seconds,
                    (
                        "section_wide"
                        if section_evidence.has_section
                        else "insufficient_sample"
                    ),
                    section_evidence,
                    True,
                    section_evidence.section_sample_count,
                    (
                        section_evidence.section_typical_unit_worker_seconds
                        if section_evidence.has_section
                        else None
                    ),
                )
        else:
            selected[section_id] = replace(
                resolve_section_typical(
                    section_evidence,
                    effective_spec,
                    TypicalResolutionPolicy.BROADEN_TO_SECTION,
                ),
                participates=False,
            )

    comparability_profile = (
        COMPARABILITY_PROFILE_PROPERTIES
        if effective_spec.is_narrowing and effective_spec.properties_signature is not None
        else COMPARABILITY_PROFILE
    )
    return TaskTypicalSelection(
        task_basis,
        RECONCILIATION_METHOD,
        comparability_profile,
        effective_spec if effective_spec.is_narrowing else None,
        participating_section_ids,
        selected,
        (
            effective_spec.properties_facets[facet_uniform_index].name
            if facet_uniform_index is not None
            else None
        ),
    )


def applied_projection_quantity(quantity: int | None) -> int:
    """Clamp a current-task quantity to the >= 1 divisor convention (legacy zero rows)."""
    return max(1, quantity if quantity is not None else 1)


def project_typical_seconds(
    unit_seconds: Fraction | None, quantity: int | None
) -> int | None:
    """Scale one per-unit typical to the current quantity, half-even to integer seconds."""
    if unit_seconds is None:
        return None
    return round(unit_seconds * applied_projection_quantity(quantity))


def apply_business_fallback(
    selected_values: Sequence[int | Fraction | None], *, terminal: Fraction
) -> list[Fraction]:
    if not isinstance(terminal, Fraction):
        raise TypeError("terminal must be a Fraction")
    usable = [Fraction(value) for value in selected_values if value is not None and value > 0]
    fallback = median(usable) if usable else terminal
    return [Fraction(value) if value is not None and value > 0 else fallback for value in selected_values]


def median(values: Sequence[Fraction]) -> Fraction:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2
