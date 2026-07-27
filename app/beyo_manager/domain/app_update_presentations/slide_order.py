"""Slide / media ordering helpers. Pure, no I/O."""

from collections.abc import Sequence

from beyo_manager.errors.validation import ValidationError


def resequenced_orders(ordered_ids: Sequence[str]) -> dict[str, int]:
    """Map each id to a contiguous 1-based ``sequence_order`` by list position.

    Rejects duplicate ids.
    """
    if len(set(ordered_ids)) != len(ordered_ids):
        raise ValidationError("Reorder list contains duplicate ids.")
    return {client_id: position for position, client_id in enumerate(ordered_ids, start=1)}


def assert_contiguous_sequence(sequence_values: Sequence[int]) -> None:
    """Assert the values form ``1..N`` with no gaps or duplicates."""
    expected = list(range(1, len(sequence_values) + 1))
    if sorted(sequence_values) != expected:
        raise ValidationError(
            "Sequence values must be contiguous starting at 1 with no gaps."
        )
