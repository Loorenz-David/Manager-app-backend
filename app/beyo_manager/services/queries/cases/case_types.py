from sqlalchemy import select

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.cases.serializers import serialize_case_type_entry
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.cases.case_type import CaseType
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.string_filter import apply_string_filter

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

_ALLOWED_STRING_COLUMNS = {
    "name": CaseType.name,
    "description": CaseType.description,
}


def _parse_entity_types(raw_value: str | None) -> list[CaseLinkEntityTypeEnum]:
    if not raw_value:
        return []

    parsed: list[CaseLinkEntityTypeEnum] = []
    invalid: list[str] = []
    for value in [entry.strip() for entry in raw_value.split(",") if entry.strip()]:
        try:
            parsed.append(CaseLinkEntityTypeEnum(value))
        except ValueError:
            invalid.append(value)

    if invalid:
        allowed = ", ".join(entry.value for entry in CaseLinkEntityTypeEnum)
        invalid_values = ", ".join(invalid)
        raise ValidationError(f"Invalid entity_type value(s): {invalid_values}. Allowed values: {allowed}")

    return parsed


async def list_case_types(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    entity_types = _parse_entity_types(ctx.query_params.get("entity_type"))

    stmt = select(CaseType)

    if entity_types:
        stmt = stmt.where(CaseType.entity_type.in_(entity_types))

    stmt = apply_string_filter(stmt, q, None, _ALLOWED_STRING_COLUMNS)

    stmt = stmt.order_by(CaseType.name.asc(), CaseType.client_id.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "case_types": [serialize_case_type_entry(row) for row in page],
        "case_types_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_case_type(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(CaseType).where(CaseType.client_id == client_id)
    )
    case_type = result.scalar_one_or_none()
    if case_type is None:
        raise NotFound("Case type not found.")

    return {"case_type": serialize_case_type_entry(case_type)}
