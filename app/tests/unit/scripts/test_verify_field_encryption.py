"""scripts.verify_field_encryption: counts how stored Fernet tokens open, never their content."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from scripts import verify_field_encryption as verify

_PLAINTEXT = "stand-in-mailbox-password"


@pytest.fixture
def written_key() -> Fernet:
    return Fernet(Fernet.generate_key())


@pytest.mark.unit
def test_values_written_with_the_same_key_decrypt(written_key):
    rows = [("ec_1", written_key.encrypt(_PLAINTEXT.encode()).decode()), ("ec_2", None)]

    result = verify.classify("email_connections.smtp_password_encrypted", rows, written_key.decrypt)

    assert (result.rows, result.empty, result.decrypted, result.failed) == (2, 1, 1, 0)
    assert verify.exit_code([result]) == 0


@pytest.mark.unit
def test_a_different_key_fails_and_names_rows_without_their_content(written_key):
    ciphertext = written_key.encrypt(_PLAINTEXT.encode()).decode()
    other_key = Fernet(Fernet.generate_key())

    result = verify.classify("email_connections.imap_password_encrypted", [("ec_1", ciphertext)], other_key.decrypt)

    assert result.failed_ids == ["ec_1"]
    assert verify.exit_code([result]) == 1
    line = result.line()
    assert "ec_1" in line
    assert _PLAINTEXT not in line and ciphertext not in line


@pytest.mark.unit
def test_raw_shopify_tokens_are_counted_not_decrypted(written_key):
    rows = [("ssi_1", "shpat_stand-in-token")]

    result = verify.classify("shopify_shop_integrations.access_token_encrypted", rows, written_key.decrypt)

    assert (result.stored_unencrypted, result.failed, result.decrypted) == (1, 0, 0)
    assert "stand-in-token" not in result.line()


@pytest.mark.unit
def test_an_empty_database_proves_nothing(written_key):
    result = verify.classify("email_connections.smtp_password_encrypted", [], written_key.decrypt)

    assert verify.exit_code([result]) == 3


@pytest.mark.unit
def test_the_checked_columns_are_every_column_encrypt_field_writes():
    """Guards the list against a new encrypted column that nobody added here."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[3] / "beyo_manager"
    written = set()
    for path in root.rglob("*.py"):
        for match in re.finditer(r"(\w+_encrypted)\s*=\s*encrypt_field\(", path.read_text(encoding="utf-8")):
            written.add(match.group(1))
    assert written == {column for _, column in verify.ENCRYPTED_COLUMNS}
