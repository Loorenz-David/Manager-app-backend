from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class OutboundMessage:
    from_address: str
    from_name: str | None
    to_addresses: list[str]
    cc_addresses: list[str]
    bcc_addresses: list[str]
    subject: str
    text_body: str | None
    html_body: str | None
    rfc_message_id: str
    in_reply_to: str | None
    references: list[str]


@dataclass
class SendResult:
    success: bool
    error: str | None = None


@dataclass
class BatchSendResult:
    results: list[SendResult] = field(default_factory=list)


@dataclass
class InboundMessage:
    provider_uid: int
    provider_folder: str
    from_address: str
    from_name: str | None
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str | None
    text_body: str | None
    text_body_clean: str | None
    html_body: str | None
    body_preview: str | None
    rfc_message_id: str | None
    in_reply_to: str | None
    references: list[str]
    raw_headers: dict
    received_at: datetime | None


@dataclass
class SyncResult:
    success: bool
    new_messages: list[InboundMessage] = field(default_factory=list)
    new_last_seen_uid: int = 0
    new_uidvalidity: int | None = None
    error: str | None = None


@dataclass
class TargetedSyncResult:
    success: bool
    messages: list[InboundMessage] = field(default_factory=list)
    matched_uid_count: int = 0
    error: str | None = None


@dataclass
class ConnectionTestResult:
    smtp_ok: bool
    imap_ok: bool
    smtp_error: str | None = None
    imap_error: str | None = None

    @property
    def reachable(self) -> bool:
        return self.smtp_ok and self.imap_ok


class EmailProviderProtocol(Protocol):
    async def test_connection(self) -> ConnectionTestResult: ...
    async def send_email(self, message: OutboundMessage) -> SendResult: ...
    async def send_email_batch(self, messages: list[OutboundMessage]) -> BatchSendResult: ...
    async def sync_inbox(self, folder: str, uidvalidity: int | None, last_seen_uid: int) -> SyncResult: ...
    async def search_by_header_ids(
        self,
        folder: str,
        rfc_message_ids: list[str],
    ) -> TargetedSyncResult: ...
