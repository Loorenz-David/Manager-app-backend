from contextlib import asynccontextmanager
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


def count_writes(statements, tables: set[str]) -> int:
    return sum(
        1
        for statement in statements
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        and any(table in statement for table in tables)
    )
