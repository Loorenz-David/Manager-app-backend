"""Deterministic signature over an item's canonical properties snapshot."""

from __future__ import annotations

import hashlib
import json


def compute_properties_signature(properties: dict) -> str:
    """Hash a properties snapshot into its complexity-profile signature.

    Canonicalization is structural only — keys are sorted recursively and the
    serialization is byte-stable. Values are trusted verbatim: semantic
    normalization (casing, units, synonyms) is the ingestion app's contract,
    so two payloads differing only in spelling are two different profiles.
    List order is likewise significant.
    """
    if not isinstance(properties, dict):
        raise TypeError("properties must be a dict; an item without a snapshot has no signature")
    # `sort_keys=True` is load-bearing beyond this module: Stock Report's row-identity
    # guarantee (intention §4A MC-3 / plan 7 C4(a) — "two Scanner payloads differing only
    # in JSON key order are one row") is armed by this argument and by nothing else.
    # Removing it silently turns that identity invariant into duplicate stock rows.
    # See master plan §6.5 "Foreign load-bearing dependencies" (lesson L-25).
    canonical = json.dumps(
        properties, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["compute_properties_signature"]
