from sqlalchemy import Select, or_
from sqlalchemy.orm import InstrumentedAttribute


def apply_string_filter(
    stmt: Select,
    q: str | None,
    string_filters: str | None,
    allowed_columns: dict[str, InstrumentedAttribute],
) -> Select:
    if not q:
        return stmt
    if string_filters:
        column_names = [c.strip() for c in string_filters.split(",") if c.strip()]
    else:
        column_names = list(allowed_columns.keys())
    valid = [allowed_columns[col] for col in column_names if col in allowed_columns]
    if not valid:
        return stmt
    return stmt.where(or_(*[col.ilike(f"%{q}%") for col in valid]))
