"""Version-number calculation for a logical presentation. Pure, no I/O."""

from collections.abc import Iterable


def next_version_number(existing_versions: Iterable[int]) -> int:
    """Return the next version number: ``max(existing) + 1`` (1 when empty)."""
    versions = list(existing_versions)
    if not versions:
        return 1
    return max(versions) + 1
