from sqlalchemy import select

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.cases.serializers import serialize_case_type_entry
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.cases.case_type import CaseType
from beyo_manager.services.commands.cases.requests import parse_create_case_type_request
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext


async def create_case_type(ctx: ServiceContext) -> dict:
    request = parse_create_case_type_request(ctx.incoming_data or {})

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "cty")

    try:
        entity_type = CaseLinkEntityTypeEnum(request.entity_type)
    except ValueError as exc:
        allowed = ", ".join(value.value for value in CaseLinkEntityTypeEnum)
        raise ValidationError(f"Invalid entity_type '{request.entity_type}'. Allowed values: {allowed}") from exc

    async with ctx.session.begin():
        case_type_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            duplicate = await ctx.session.get(CaseType, request.client_id)
            if duplicate is not None:
                raise ConflictError("Provided client_id is already in use.")
            case_type_kwargs["client_id"] = request.client_id

        conflict = await ctx.session.execute(
            select(CaseType).where(
                CaseType.name == request.name,
                CaseType.entity_type == entity_type,
            )
        )
        if conflict.scalar_one_or_none() is not None:
            raise ConflictError("A case type with this name and entity_type already exists.")

        case_type = CaseType(
            **case_type_kwargs,
            name=request.name,
            image_url=request.image_url,
            description=request.description,
            entity_type=entity_type,
        )
        ctx.session.add(case_type)
        await ctx.session.flush()

    return {"case_type": serialize_case_type_entry(case_type)}
