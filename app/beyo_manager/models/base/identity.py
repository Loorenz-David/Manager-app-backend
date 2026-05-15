from typing import ClassVar

from ulid import ULID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


def generate_id(prefix: str) -> str:
    """Generate a prefixed ULID string — e.g. generate_id('usr') → 'usr_01ARZ...' """
    return f"{prefix}_{ULID()}"


class IdentityMixin:
    """Adds client_id as the primary key to any addressable model.

    Combine with Base and the model class:
        class MyModel(IdentityMixin, Base): ...
    """
    CLIENT_ID_PREFIX: ClassVar[str] = "obj"

    @declared_attr
    def client_id(cls) -> Mapped[str]:
        prefix = cls.CLIENT_ID_PREFIX
        return mapped_column(
            String(64),
            primary_key=True,
            default=lambda: generate_id(prefix),
        )
