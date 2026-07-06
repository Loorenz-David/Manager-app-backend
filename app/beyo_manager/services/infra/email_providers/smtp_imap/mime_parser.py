from datetime import timezone
from email import message_from_bytes, policy
from email.message import Message
from email.utils import getaddresses, parseaddr, parsedate_to_datetime

from beyo_manager.services.infra.email_providers.base import InboundMessage
from beyo_manager.services.infra.email_providers.smtp_imap.quote_stripper import strip_quoted_reply


class MimeParser:
    def parse(self, raw_bytes: bytes, uid: int, folder: str) -> InboundMessage:
        parsed = message_from_bytes(raw_bytes, policy=policy.default)
        text_body, html_body = _extract_bodies(parsed)
        text_body_clean = strip_quoted_reply(text_body)
        from_name, from_address = parseaddr(parsed.get("From", ""))
        to_addresses = [addr for _, addr in getaddresses(parsed.get_all("To", [])) if addr]
        cc_addresses = [addr for _, addr in getaddresses(parsed.get_all("Cc", [])) if addr]
        references_raw = parsed.get("References", "") or ""
        try:
            received_at = parsedate_to_datetime(parsed.get("Date", "")) if parsed.get("Date") else None
            if received_at and received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, IndexError):
            received_at = None
        return InboundMessage(
            provider_uid=uid,
            provider_folder=folder,
            from_address=from_address or "",
            from_name=from_name or None,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            subject=parsed.get("Subject"),
            text_body=text_body,
            text_body_clean=text_body_clean,
            html_body=html_body,
            body_preview=_build_body_preview(text_body_clean, text_body),
            rfc_message_id=parsed.get("Message-ID"),
            in_reply_to=parsed.get("In-Reply-To"),
            references=[value for value in references_raw.split() if value],
            raw_headers={key: value for key, value in parsed.items()},
            received_at=received_at,
        )


def _extract_bodies(parsed: Message) -> tuple[str | None, str | None]:
    text_body: str | None = None
    html_body: str | None = None

    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_maintype() == "multipart":
                continue
            content_type = part.get_content_type()
            try:
                payload = part.get_content()
            except Exception:
                payload = None
            if not isinstance(payload, str):
                continue
            if content_type == "text/plain" and text_body is None:
                text_body = payload
            elif content_type == "text/html" and html_body is None:
                html_body = payload
    else:
        try:
            payload = parsed.get_content()
        except Exception:
            payload = None
        if isinstance(payload, str):
            if parsed.get_content_type() == "text/html":
                html_body = payload
            else:
                text_body = payload

    return text_body, html_body


def _build_body_preview(text_body_clean: str | None, text_body: str | None) -> str | None:
    if text_body_clean and text_body_clean.strip():
        return text_body_clean[:300]
    return (text_body or "")[:300] or None
