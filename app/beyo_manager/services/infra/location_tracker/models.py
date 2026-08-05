from dataclasses import dataclass


@dataclass(frozen=True)
class ItemLocationTarget:
    article_number: str | None = None
    sku: str | None = None
    #: Per target, not per change: one position can carry several items and only some of them
    #: came back damaged. Always serialized, true or false, so the tracker never infers a default.
    needs_fixing: bool = False


@dataclass(frozen=True)
class ItemPositionChange:
    position: str
    item_targets: list[ItemLocationTarget]
    username: str | None = None


@dataclass(frozen=True)
class LocationItem:
    item_article_number: str | None
    sku: str | None
    item_position: str | None
