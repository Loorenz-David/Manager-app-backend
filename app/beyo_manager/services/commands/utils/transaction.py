from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def maybe_begin(session: AsyncSession):
    """Join the active transaction if one exists; open a new one otherwise.

    Owner mode (no active transaction): opens session.begin(); commits on normal
    exit; rolls back on exception — identical to `async with ctx.session.begin()`.

    Subordinate mode (active transaction already open): yields immediately with no
    session call. The block body runs inside the caller's transaction. On normal
    exit nothing happens — no commit, no rollback. The owning caller's maybe_begin
    commits everything when its own block exits.

    Never call session.commit() or session.rollback() inside this block.
    session.flush() is the only explicit session call permitted when a
    DB-generated value (e.g. client_id) is needed before the block exits.
    """
    if session.in_transaction():
        yield
    else:
        async with session.begin():
            yield
