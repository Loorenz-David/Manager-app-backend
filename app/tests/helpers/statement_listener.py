from contextlib import asynccontextmanager
from typing import Any
from sqlalchemy import event


@asynccontextmanager
async def record_statements(session):
    statements = []

    def listener(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    engine = session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", listener)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", listener)


@asynccontextmanager
async def record_statement_calls(session):
    """Like `record_statements`, but keeps each statement's bound parameters too.

    Added batch B2 (master plan §6.1/§6.5 blocker B3): `record_statements` discards
    `_parameters`, so no caller of it can assert on a bound value (only on the
    compiled statement text, which carries `$1`/`$2` placeholders, never the value
    itself — plan 6 C7(a)). `record_statements` and `count_writes` are left
    byte-identical above; batch A's `test_repair_stock_report.py` is the one existing
    caller of `record_statements` and must stay green.
    """
    calls: list[tuple[str, Any]] = []

    def listener(_connection, _cursor, statement, parameters, _context, _executemany):
        calls.append((statement, parameters))

    engine = session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", listener)
    try:
        yield calls
    finally:
        event.remove(engine, "before_cursor_execute", listener)


def count_writes(statements, tables: set[str]) -> int:
    return sum(
        1
        for statement in statements
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        and any(table in statement for table in tables)
    )
