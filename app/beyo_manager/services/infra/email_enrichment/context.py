from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beyo_manager.models.tables.customers.customer import Customer
    from beyo_manager.models.tables.items.item import Item
    from beyo_manager.models.tables.items.item_category import ItemCategory
    from beyo_manager.models.tables.tasks.task import Task


@dataclass
class EnrichmentContext:
    task: "Task | None" = None
    customer: "Customer | None" = None
    item: "Item | None" = None
    item_category: "ItemCategory | None" = None

