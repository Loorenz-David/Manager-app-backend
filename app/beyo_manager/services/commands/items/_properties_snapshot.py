"""Apply an externally-owned properties snapshot to an Item row.

The three snapshot columns move together and are never set independently: the
signature is always derived from the blob by compute_properties_signature, and
properties_snapshot_at records when *this* profile was established. Keeping the
derivation in one place is what stops a caller from writing a blob whose stored
signature no longer describes it — the narrowing tier reads the signature alone,
so a divergence there is silent and mis-groups the item's typical samples.
"""

from datetime import datetime, timezone

from beyo_manager.domain.items.properties_signature import compute_properties_signature
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item


def apply_properties_snapshot(
    item: Item,
    properties: dict | None,
    *,
    now: datetime | None = None,
) -> bool:
    """Write properties, its derived signature and the snapshot timestamp onto item.

    Returns True when the row actually changed, so callers can decide whether the
    write is worth an audit record. Safe to call unconditionally — every case that
    isn't a real new snapshot returns False without touching the row.

    An empty payload is not a snapshot. None (key absent, or an explicit null) and
    {} alike mean "ingestion had nothing to say", so neither writes and neither
    clears an existing snapshot: a frontend that always serializes the full item
    object must not wipe a profile just by defaulting the field. There is
    deliberately no clear path through here — un-snapshotting an item is not
    something task or item creation is allowed to do as a side effect.

    A snapshot whose signature matches the one already stored is likewise a no-op:
    it carries no new information, and bumping properties_snapshot_at for it would
    turn "when this profile was established" into "when ingestion last spoke".
    """
    if properties is None:
        return False
    if not isinstance(properties, dict):
        raise ValidationError("properties must be an object.")
    if not properties:
        return False

    signature = compute_properties_signature(properties)
    if item.properties_signature == signature and item.properties_snapshot_at is not None:
        return False

    item.properties = properties
    item.properties_signature = signature
    item.properties_snapshot_at = now or datetime.now(timezone.utc)
    return True


__all__ = ["apply_properties_snapshot"]
