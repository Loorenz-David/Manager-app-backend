# CANONICAL REFERENCE — copy this file for every new command.
#
# Rules (enforced by contract 06_commands):
#   1. Parse request before opening the transaction.
#   2. All DB reads and writes go inside async with ctx.session.begin().
#   3. Event dispatch happens AFTER the begin() block exits (after commit).
#   4. Never read ctx.incoming_data directly inside the command body.
from beyo_manager.services.commands._canonical.requests.create_record_request import (
    RecordCreateRequest,
    parse_create_record_request,
)
from beyo_manager.services.context import ServiceContext


async def create_record(ctx: ServiceContext) -> dict:
    request: RecordCreateRequest = parse_create_record_request(ctx.incoming_data)

    async with ctx.session.begin():
        # All DB reads and writes here — never ctx.incoming_data inside this block.
        pass

    # Event dispatch here, after commit.
    return {}
