import asyncio

from beyo_manager.services.infra.email_providers.base import (
    BatchSendResult,
    ConnectionTestResult,
    OutboundMessage,
    SendResult,
    SyncResult,
    TargetedSyncResult,
)
from beyo_manager.services.infra.email_providers.smtp_imap.imap_reader import ImapReader
from beyo_manager.services.infra.email_providers.smtp_imap.smtp_sender import SmtpSender


class SmtpImapEmailProvider:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_security: str,
        smtp_username: str,
        smtp_password: str,
        imap_host: str,
        imap_port: int,
        imap_security: str,
        imap_username: str,
        imap_password: str,
    ):
        self._smtp = SmtpSender(smtp_host, smtp_port, smtp_security, smtp_username, smtp_password)
        self._imap = ImapReader(imap_host, imap_port, imap_security, imap_username, imap_password)

    async def test_connection(self) -> ConnectionTestResult:
        smtp_ok, smtp_error = await asyncio.to_thread(self._smtp.test)
        imap_ok, imap_error = await asyncio.to_thread(self._imap.test)
        return ConnectionTestResult(
            smtp_ok=smtp_ok,
            imap_ok=imap_ok,
            smtp_error=smtp_error,
            imap_error=imap_error,
        )

    async def send_email(self, message: OutboundMessage) -> SendResult:
        return await asyncio.to_thread(self._smtp.send, message)

    async def send_email_batch(self, messages: list[OutboundMessage]) -> BatchSendResult:
        results = await asyncio.to_thread(self._smtp.send_batch, messages)
        return BatchSendResult(results=results)

    async def sync_inbox(self, folder: str, uidvalidity: int | None, last_seen_uid: int) -> SyncResult:
        return await asyncio.to_thread(self._imap.sync, folder, uidvalidity, last_seen_uid)

    async def search_by_header_ids(
        self,
        folder: str,
        rfc_message_ids: list[str],
    ) -> TargetedSyncResult:
        return await asyncio.to_thread(self._imap.search_by_header_ids, folder, rfc_message_ids)
