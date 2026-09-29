"""Read-only check that stored encrypted fields decrypt with this FIELD_ENCRYPTION_KEY.

    python -m scripts.verify_field_encryption
    # container: docker compose run --rm --no-deps -T api python -m scripts.verify_field_encryption

Run after restoring a production-derived database (staging's initial load, the
production rehearsal, the cutover restore). These columns hold Fernet tokens written
by `services/infra/crypto/field_encryption.py`; only the key they were written with
opens them, and a restore copies the tokens byte for byte.

Prints counts per column and the client ids of rows that fail. Never a decrypted value
and never ciphertext. The transaction is read-only.

Exit codes: 0 every stored value decrypts, 1 at least one does not, 2
FIELD_ENCRYPTION_KEY missing or not a Fernet key, 3 no encrypted value found (nothing
proven), 4 the schema is not migrated (a checked table is missing).
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import asyncpg
from cryptography.fernet import Fernet, InvalidToken

from beyo_manager.config import settings

# (table, column). Every column that encrypt_field() writes.
ENCRYPTED_COLUMNS = (
    ("email_connections", "smtp_password_encrypted"),
    ("email_connections", "imap_password_encrypted"),
    ("shopify_shop_integrations", "access_token_encrypted"),
)
# services/infra/shopify/graphql_client.py uses a stored value with one of these
# prefixes as a raw Shopify token, without decrypting it.
RAW_SHOPIFY_TOKEN_PREFIXES = ("shpat_", "shpca_", "shpua_", "shppa_")
_MAX_LISTED_FAILURES = 20


@dataclass
class ColumnResult:
    name: str
    rows: int = 0
    empty: int = 0
    decrypted: int = 0
    stored_unencrypted: int = 0
    failed_ids: list[str] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return len(self.failed_ids)

    def line(self) -> str:
        parts = [f"{self.rows} rows"]
        if self.empty:
            parts.append(f"{self.empty} empty")
        parts.append(f"{self.decrypted} decrypt")
        parts.append(f"{self.failed} fail")
        if self.stored_unencrypted:
            parts.append(f"{self.stored_unencrypted} stored unencrypted")
        text = f"{self.name}: " + ", ".join(parts)
        if self.failed_ids:
            listed = ", ".join(self.failed_ids[:_MAX_LISTED_FAILURES])
            more = "" if self.failed <= _MAX_LISTED_FAILURES else f" (+{self.failed - _MAX_LISTED_FAILURES} more)"
            text += f"\n  failing client_id: {listed}{more}"
        return text


def classify(name: str, rows: Iterable[tuple[str, str | None]], decrypt: Callable[[bytes], bytes]) -> ColumnResult:
    """Count how the (client_id, stored value) pairs of one column open. Keeps no plaintext."""
    result = ColumnResult(name)
    for client_id, value in rows:
        result.rows += 1
        if value is None or value == "":
            result.empty += 1
        elif value.startswith(RAW_SHOPIFY_TOKEN_PREFIXES):
            result.stored_unencrypted += 1
        else:
            try:
                decrypt(value.encode())
            except (InvalidToken, ValueError, TypeError):
                result.failed_ids.append(client_id)
            else:
                result.decrypted += 1
    return result


def exit_code(results: list[ColumnResult]) -> int:
    if any(r.failed for r in results):
        return 1
    if not any(r.decrypted or r.stored_unencrypted for r in results):
        return 3
    return 0


async def _read_column(connection: asyncpg.Connection, table: str, column: str) -> list[tuple[str, str | None]]:
    # Identifiers come from ENCRYPTED_COLUMNS above, never from input.
    records = await connection.fetch(f'SELECT client_id, "{column}" AS value FROM "{table}" ORDER BY client_id')
    return [(record["client_id"], record["value"]) for record in records]


async def _verify() -> int:
    if not settings.field_encryption_key:
        print("FIELD_ENCRYPTION_KEY is not set", file=sys.stderr)
        return 2
    try:
        fernet = Fernet(settings.field_encryption_key.encode())
    except (ValueError, TypeError):
        print("FIELD_ENCRYPTION_KEY is not a valid Fernet key", file=sys.stderr)
        return 2

    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(
        dsn, timeout=10, server_settings={"application_name": "managerbeyo:verify_field_encryption"}
    )
    try:
        async with connection.transaction(readonly=True):
            results = [
                classify(f"{table}.{column}", await _read_column(connection, table, column), fernet.decrypt)
                for table, column in ENCRYPTED_COLUMNS
            ]
    except asyncpg.UndefinedTableError as exc:
        print(f"schema not migrated: {exc}", file=sys.stderr)
        return 4
    finally:
        await connection.close()

    for result in results:
        print(result.line())
    code = exit_code(results)
    print({
        0: "OK: every stored encrypted value decrypts with this FIELD_ENCRYPTION_KEY",
        1: "FAILED: some stored values do not decrypt with this FIELD_ENCRYPTION_KEY",
        3: "NOTHING PROVEN: no encrypted value is stored in this database",
    }[code])
    if any(r.stored_unencrypted for r in results):
        print("NOTE: some Shopify tokens are stored unencrypted (raw shp*_ values)")
    return code


def main() -> int:
    return asyncio.run(_verify())


if __name__ == "__main__":
    sys.exit(main())
