"""Make connection URLs safe to log.

`DATABASE_URL` and `REDIS_URL` carry their password inline. The startup log used to
print them verbatim, which put the database password into every log sink.

`redact_url` rebuilds the URL from its parsed parts and never copies the password
across, so there is no replace-the-password step that could miss an encoding of it.
The query string is dropped rather than filtered, because drivers accept credentials
there too (`?password=...`, `?sslpassword=...`). Anything that does not parse cleanly
becomes a fixed placeholder: the raw input is never a fallback.
"""

from __future__ import annotations

from urllib.parse import urlsplit

UNSET_URL = "<unset>"
UNPARSEABLE_URL = "<unparseable-url>"
REDACTED_PASSWORD = "***"


def redact_url(url: str | None) -> str:
    if not url:
        return UNSET_URL
    try:
        parts = urlsplit(url)
        if not parts.scheme or not parts.netloc:
            return UNPARSEABLE_URL

        host = parts.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        port = parts.port  # raises ValueError on a malformed port

        userinfo = parts.username or ""
        if parts.password is not None:
            userinfo = f"{userinfo}:{REDACTED_PASSWORD}"

        netloc = f"{userinfo}@{host}" if userinfo else host
        if port is not None:
            netloc = f"{netloc}:{port}"

        redacted = f"{parts.scheme}://{netloc}{parts.path}"
        if parts.query:
            redacted = f"{redacted}?<query-redacted>"
        return redacted
    except Exception:
        return UNPARSEABLE_URL
