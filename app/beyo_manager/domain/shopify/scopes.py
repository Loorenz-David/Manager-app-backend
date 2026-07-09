from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ShopifyScopeComparison:
    requested: tuple[str, ...]
    granted: tuple[str, ...]
    missing: tuple[str, ...]
    extra: tuple[str, ...]

    @property
    def is_outdated(self) -> bool:
        return bool(self.missing)


def normalize_scope(scope: str) -> str:
    return scope.strip().lower()


def parse_scope_config(scope_config: str) -> tuple[str, ...]:
    if not scope_config.strip():
        return ()
    return normalize_scopes(scope_config.split(","))


def normalize_scopes(scopes: Iterable[str]) -> tuple[str, ...]:
    normalized = {normalize_scope(scope) for scope in scopes if normalize_scope(scope)}
    return tuple(sorted(normalized))


def _expand_implied_scopes(scopes: Iterable[str]) -> tuple[str, ...]:
    expanded = set(normalize_scopes(scopes))
    for scope in tuple(expanded):
        if not scope.startswith("write_"):
            continue
        expanded.add(f"read_{scope.removeprefix('write_')}")
    return tuple(sorted(expanded))


def compare_requested_and_granted_scopes(
    requested_scopes: Iterable[str],
    granted_scopes: Iterable[str],
) -> ShopifyScopeComparison:
    requested = normalize_scopes(requested_scopes)
    granted = normalize_scopes(granted_scopes)
    comparable_granted = _expand_implied_scopes(granted)
    requested_set = set(requested)
    granted_set = set(comparable_granted)
    missing = tuple(sorted(requested_set - granted_set))
    extra = tuple(sorted(set(granted) - requested_set))
    return ShopifyScopeComparison(
        requested=requested,
        granted=granted,
        missing=missing,
        extra=extra,
    )


def has_all_required_scopes(requested_scopes: Iterable[str], granted_scopes: Iterable[str]) -> bool:
    return not compare_requested_and_granted_scopes(requested_scopes, granted_scopes).is_outdated
