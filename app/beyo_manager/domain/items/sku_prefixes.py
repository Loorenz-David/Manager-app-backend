"""SKU suggestion for the photography Shopify form.

House SKU format: ``<category prefix><N>-<DDMMYY>``, e.g. ``T3-201126``. N restarts
every day per prefix, so the next SKU is the highest N already used today, plus one.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Keyed by item_categories.name. A category missing here gets no suggestion.
ITEM_CATEGORY_SKU_PREFIXES: dict[str, str] = {
    "Armchairs": "Ach",
    "Bar Cabinets": "Bc",
    "Bedside Tables": "Bst",
    "Bookshelves": "Bsh",
    "Carpets": "Cpt",
    "Chest of Drawers": "Chd",
    "Coffee Tables": "Ct",
    "Dining Chairs": "Ch",
    "Dining Tables": "T",
    "Easy Chairs": "Esc",
    "Hall Tables": "Ht",
    "Highboards": "Hb",
    "Lamps": "Lp",
    "Mirrors": "M",
    "Nest Of Tables": "Nt",
    "Porcelain": "Prc",
    "Posters": "Pst",
    "Seating Benches": "Stb",
    "Secretary Cabinets": "Sct",
    "Shelving Units": "Shu",
    "Sideboards": "Sd",
    "Side Tables": "Sdt",
    "Sofas": "Sf",
    "Stools": "Sto",
    "Storage Cabinets": "Stc",
    "Wardrobes": "Wdb",
    "Writing Desks": "Wd",
}

SKU_DATE_CODE_PATTERN = re.compile(r"^\d{6}$")


def sku_prefix_for_category(category_name: str | None) -> str | None:
    if not category_name:
        return None
    return ITEM_CATEGORY_SKU_PREFIXES.get(category_name.strip())


def sku_sequence_pattern(prefix: str, date_code: str) -> str:
    """Regex (Python and Postgres compatible) for SKUs of this prefix and day.

    The number must follow the prefix directly, so ``Sd`` never matches ``Sdt3`` and
    ``Ch`` never matches ``Chd1``. The dash is optional to absorb ``Bsh9121126`` typos.
    """
    return rf"^{re.escape(prefix)}(\d+)-?{re.escape(date_code)}$"


def next_sku_sequence(existing_skus: Iterable[str | None], prefix: str, date_code: str) -> int:
    pattern = re.compile(sku_sequence_pattern(prefix, date_code), re.IGNORECASE)
    highest = 0
    for sku in existing_skus:
        if not sku:
            continue
        match = pattern.match(sku.strip())
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def format_suggested_sku(prefix: str, sequence: int, date_code: str) -> str:
    return f"{prefix}{sequence}-{date_code}"
