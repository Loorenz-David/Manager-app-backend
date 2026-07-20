"""Pure name normalization for exact Connecteam-to-ManagerBeyo matching."""

from __future__ import annotations

import re
import unicodedata


def normalize_username(value: str) -> str:
    """Apply the single exact-match normalization contract."""

    normalized = unicodedata.normalize("NFKC", value)
    normalized = re.sub(r"\s+", " ", normalized.strip())
    return normalized.casefold()


def build_external_full_name(first: str | None, last: str | None) -> str | None:
    parts = [part.strip() for part in (first or "", last or "") if part and part.strip()]
    return " ".join(parts) or None
