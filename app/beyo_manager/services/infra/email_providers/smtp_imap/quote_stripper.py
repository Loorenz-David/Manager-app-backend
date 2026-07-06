from __future__ import annotations

import logging
import re

try:
    from email_reply_parser import EmailReplyParser
except ImportError:  # pragma: no cover - exercised only when dependency is absent locally.
    EmailReplyParser = None

logger = logging.getLogger(__name__)

_fallback_warning_logged = False


_QUOTE_HEADER_PATTERNS = (
    # Bounded + DOTALL: real clients (e.g. Gmail) wrap "On <date>, <name> <email>"
    # and "wrote:" onto separate physical lines when the header is long, so this
    # cannot be anchored to a single line with ^...$.
    re.compile(r"On\b.{0,300}?wrote:", re.IGNORECASE | re.DOTALL),
    re.compile(r"(?im)^\s*-----Original Message-----\s*$"),
    re.compile(r"(?im)^\s*From:\s.+\nSent:\s.+\nTo:\s.+\nSubject:\s.+$"),
)


def strip_quoted_reply(text: str | None) -> str | None:
    if text is None or text == "":
        return text

    if EmailReplyParser is not None:
        parsed = EmailReplyParser.parse_reply(text)
        if parsed != text:
            return parsed.strip()
        return text

    _warn_fallback_active()
    return _strip_quoted_reply_fallback(text)


def _warn_fallback_active() -> None:
    global _fallback_warning_logged
    if not _fallback_warning_logged:
        logger.warning(
            "quote_stripper | email_reply_parser not installed — using regex fallback for quote stripping"
        )
        _fallback_warning_logged = True


def _strip_quoted_reply_fallback(text: str) -> str:
    quote_start = _find_quote_start(text)
    if quote_start is None:
        return text
    return text[:quote_start].strip()


def _find_quote_start(text: str) -> int | None:
    for pattern in _QUOTE_HEADER_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.start()

    lines = text.splitlines(keepends=True)
    offset = 0
    for index, line in enumerate(lines):
        if line.lstrip().startswith(">"):
            consecutive_quoted_lines = 1
            probe = index + 1
            while probe < len(lines) and lines[probe].lstrip().startswith(">"):
                consecutive_quoted_lines += 1
                probe += 1
            if consecutive_quoted_lines >= 2:
                return offset
        offset += len(line)

    return None
