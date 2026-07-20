"""CSV provider adapter for the one-time Connecteam user mapping backfill."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path

from beyo_manager.errors.base import DomainError

EXPECTED_HEADERS = ("userId", "firstName", "lastName")


class ConnecteamCsvError(DomainError):
    """Base error for a malformed or unavailable Connecteam users CSV."""

    http_status = 400

    def __init__(self, message: str, *, path: Path) -> None:
        self.path = path
        super().__init__(message)


class ConnecteamCsvFormatError(ConnecteamCsvError):
    """The CSV cannot be interpreted using the canonical contract."""


class ConnecteamCsvRowError(ConnecteamCsvError):
    """A CSV data row violates the typed row contract."""

    def __init__(self, message: str, *, path: Path, row_number: int) -> None:
        self.row_number = row_number
        super().__init__(message, path=path)


@dataclass(frozen=True)
class ConnecteamCsvUser:
    user_id: int
    first_name: str
    last_name: str
    row_number: int


def _normalize_header(value: str) -> str:
    return re.sub(r"[\s_]+", "", value.lstrip("\ufeff")).casefold()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise ConnecteamCsvError(
            f"CSV file '{path}' was not found; expected headers: {', '.join(EXPECTED_HEADERS)}.",
            path=path,
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise ConnecteamCsvError(
            f"CSV file '{path}' could not be read; expected headers: {', '.join(EXPECTED_HEADERS)}.",
            path=path,
        ) from exc


def _detect_delimiter(text: str, path: Path) -> str:
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    if not first_line:
        raise ConnecteamCsvFormatError(
            f"CSV file '{path}' is empty; expected headers: {', '.join(EXPECTED_HEADERS)}.",
            path=path,
        )
    comma_count = first_line.count(",")
    semicolon_count = first_line.count(";")
    if comma_count == 0 and semicolon_count == 0:
        raise ConnecteamCsvFormatError(
            f"CSV file '{path}' has no comma or semicolon delimiter; expected headers: {', '.join(EXPECTED_HEADERS)}.",
            path=path,
        )
    return ";" if semicolon_count > comma_count else ","


def read_connecteam_users_csv(path: Path) -> list[ConnecteamCsvUser]:
    """Read canonical Connecteam user fields without leaking provider columns."""

    path = Path(path)
    text = _read_text(path)
    delimiter = _detect_delimiter(text, path)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
        header = next(reader)
    except (csv.Error, StopIteration) as exc:
        raise ConnecteamCsvFormatError(
            f"CSV file '{path}' has no readable header; expected headers: {', '.join(EXPECTED_HEADERS)}.",
            path=path,
        ) from exc

    header_indexes = {
        _normalize_header(value): index for index, value in enumerate(header)
    }
    required = {
        "userid": "userId",
        "firstname": "firstName",
        "lastname": "lastName",
    }
    missing = [canonical for normalized, canonical in required.items() if normalized not in header_indexes]
    if missing:
        found = ", ".join(value.strip() or "<blank>" for value in header)
        raise ConnecteamCsvFormatError(
            f"CSV file '{path}' is missing required headers: {', '.join(missing)}; "
            f"found: {found}; expected headers: {', '.join(EXPECTED_HEADERS)}.",
            path=path,
        )

    rows_by_user_id: dict[int, ConnecteamCsvUser] = {}
    ordered_rows: list[ConnecteamCsvUser] = []
    try:
        for row_number, values in enumerate(reader, start=2):
            if not values or not any(value.strip() for value in values):
                continue
            try:
                raw_user_id = values[header_indexes["userid"]].strip()
                first_name = values[header_indexes["firstname"]].strip()
                last_name = values[header_indexes["lastname"]].strip()
            except IndexError as exc:
                raise ConnecteamCsvRowError(
                    f"CSV file '{path}' row {row_number} is missing a required cell; "
                    f"expected headers: {', '.join(EXPECTED_HEADERS)}.",
                    path=path,
                    row_number=row_number,
                ) from exc
            if not raw_user_id:
                raise ConnecteamCsvRowError(
                    f"CSV file '{path}' row {row_number} has a missing userId; "
                    f"expected an integer userId.",
                    path=path,
                    row_number=row_number,
                )
            try:
                user_id = int(raw_user_id)
            except ValueError as exc:
                raise ConnecteamCsvRowError(
                    f"CSV file '{path}' row {row_number} has non-integer userId '{raw_user_id}'; "
                    f"expected an integer userId.",
                    path=path,
                    row_number=row_number,
                ) from exc

            parsed = ConnecteamCsvUser(user_id, first_name, last_name, row_number)
            previous = rows_by_user_id.get(user_id)
            if previous is not None and (
                previous.first_name == parsed.first_name and previous.last_name == parsed.last_name
            ):
                continue
            rows_by_user_id.setdefault(user_id, parsed)
            ordered_rows.append(parsed)
    except csv.Error as exc:
        raise ConnecteamCsvFormatError(
            f"CSV file '{path}' contains malformed CSV data; expected headers: {', '.join(EXPECTED_HEADERS)}.",
            path=path,
        ) from exc

    return ordered_rows
