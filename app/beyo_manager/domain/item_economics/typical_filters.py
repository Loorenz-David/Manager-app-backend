"""Pure item-aware typical-time filtering and reconciliation rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import Protocol


from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.errors.validation import ValidationError

from beyo_manager.domain.item_economics.typical_constants import TYPICAL_MIN_SAMPLE_SIZE


COMPARABILITY_PROFILE = "primary_item_category_v1"
RECONCILIATION_METHOD = "uniform_basis_v1"


class _PrimaryItem(Protocol):
    item_category_id: str | None


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

    def __post_init__(self) -> None:
        for field_name in ("item_category_ids", "major_categories", "designers"):
            value = getattr(self, field_name)
            if value is not None and not value:
                object.__setattr__(self, field_name, None)

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
    return TypicalFilterSpec(item_category_ids=frozenset({category_id}))


def _optional_values(params: Mapping[str, object], key: str) -> frozenset[str] | None:
    raw = params.get(key)
    if raw is None:
        return None
    if isinstance(raw, (str, bytes)):
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
    try:
        return TypicalFilterSpec(
            item_category_ids=_optional_values(params, "item_category_ids"),
            major_categories=_optional_categories(params),
            width_cm=_optional_range(params, "width_cm_min", "width_cm_max"),
            height_cm=_optional_range(params, "height_cm_min", "height_cm_max"),
            depth_cm=_optional_range(params, "depth_cm_min", "depth_cm_max"),
            can_have_upholstery=params.get("can_have_upholstery"),
            designers=_optional_values(params, "designers"),
        )
    except ValueError as exc:
        raise ValidationError("Typical filter range is invalid.") from exc


@dataclass(frozen=True)
class SectionTypicalEvidence:
    working_section_id: str
    narrowed_typical_worker_seconds: int | None
    narrowed_sample_count: int
    section_typical_worker_seconds: int | None
    section_sample_count: int

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
        if evidence.has_usable_narrowed:
            return SelectedTypical(
                evidence.working_section_id,
                evidence.narrowed_typical_worker_seconds,
                "item_narrowed",
                evidence,
                False,
                evidence.narrowed_sample_count,
            )
        if evidence.has_section:
            return SelectedTypical(
                evidence.working_section_id,
                evidence.section_typical_worker_seconds,
                "section_wide",
                evidence,
                False,
                evidence.section_sample_count,
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
        if evidence.has_narrowed:
            return SelectedTypical(
                evidence.working_section_id,
                evidence.narrowed_typical_worker_seconds,
                "item_narrowed",
                evidence,
                False,
                evidence.narrowed_sample_count,
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
    narrowed_uniform = (
        effective_spec.is_narrowing
        and bool(participating_section_ids)
        and all(evidence[section_id].has_usable_narrowed for section_id in participating_section_ids)
    )
    task_basis = "item_narrowed_uniform" if narrowed_uniform else "section_wide_uniform"
    selected: dict[str, SelectedTypical] = {}

    for section_id in section_ids:
        section_evidence = evidence[section_id]
        if section_id in participating_section_ids:
            if narrowed_uniform:
                selected[section_id] = SelectedTypical(
                    section_id,
                    section_evidence.narrowed_typical_worker_seconds,
                    "item_narrowed",
                    section_evidence,
                    True,
                    section_evidence.narrowed_sample_count,
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

    return TaskTypicalSelection(
        task_basis,
        RECONCILIATION_METHOD,
        COMPARABILITY_PROFILE,
        effective_spec if effective_spec.is_narrowing else None,
        participating_section_ids,
        selected,
    )


def apply_business_fallback(
    selected_values: Sequence[int | None], *, terminal: Fraction
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
