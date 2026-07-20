from pathlib import Path

import pytest

from beyo_manager.domain.connecteam.user_csv_rows import (
    ConnecteamCsvFormatError,
    ConnecteamCsvRowError,
    read_connecteam_users_csv,
)


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_reader_accepts_canonical_headers_and_ignores_extra_columns(tmp_path):
    path = _write(
        tmp_path / "users.csv",
        "userId,firstName,lastName,ignored\n1,Anna,\n2,Bob,Builder,ignored\n",
    )

    rows = read_connecteam_users_csv(path)

    assert [(row.user_id, row.first_name, row.last_name) for row in rows] == [
        (1, "Anna", ""),
        (2, "Bob", "Builder"),
    ]


def test_reader_accepts_variant_headers_bom_and_semicolon(tmp_path):
    path = tmp_path / "users.csv"
    path.write_text("\ufeffUSER ID;First name;LAST_NAME\n7;Ana;\n", encoding="utf-8")

    rows = read_connecteam_users_csv(path)

    assert rows[0].user_id == 7
    assert rows[0].first_name == "Ana"
    assert rows[0].last_name == ""


def test_reader_reports_missing_columns(tmp_path):
    path = _write(tmp_path / "users.csv", "userId,firstName\n1,Ana\n")

    with pytest.raises(ConnecteamCsvFormatError, match="lastName"):
        read_connecteam_users_csv(path)


def test_reader_reports_non_integer_id_with_row_number(tmp_path):
    path = _write(tmp_path / "users.csv", "userId,firstName,lastName\nnope,Ana,\n")

    with pytest.raises(ConnecteamCsvRowError, match=r"row 2"):
        read_connecteam_users_csv(path)


def test_reader_reports_missing_file_and_empty_file(tmp_path):
    with pytest.raises(Exception, match="missing.csv"):
        read_connecteam_users_csv(tmp_path / "missing.csv")

    empty = _write(tmp_path / "empty.csv", "")
    with pytest.raises(ConnecteamCsvFormatError, match="empty"):
        read_connecteam_users_csv(empty)


def test_reader_collapses_identical_duplicate_rows_and_keeps_conflicting_rows(tmp_path):
    path = _write(
        tmp_path / "users.csv",
        "userId,firstName,lastName\n1,Ana,\n1,Ana,\n1,Another,\n",
    )

    rows = read_connecteam_users_csv(path)

    assert [(row.user_id, row.first_name) for row in rows] == [(1, "Ana"), (1, "Another")]
