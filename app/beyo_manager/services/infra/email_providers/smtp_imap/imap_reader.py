import imaplib
import logging
import socket

from beyo_manager.domain.emails.enums import EmailSecurityEnum
from beyo_manager.services.infra.email_providers.base import SyncResult, TargetedSyncResult
from beyo_manager.services.infra.email_providers.smtp_imap.mime_parser import MimeParser

logger = logging.getLogger(__name__)

# Fetch at most this many UIDs per sync run to prevent first-sync cold-start stall
# on accounts with large inboxes.
MAX_MESSAGES_PER_SYNC = 100
MAX_IDS_PER_TARGETED_SYNC = 10
MAX_MESSAGES_PER_TARGETED_SYNC = 50


class ImapReader:
    def __init__(self, host: str, port: int, security: str, username: str, password: str):
        self._host = host
        self._port = port
        self._security = security
        self._username = username
        self._password = password

    def sync(self, folder: str, uidvalidity: int | None, last_seen_uid: int) -> SyncResult:
        previous_timeout = socket.getdefaulttimeout()
        client = None
        try:
            socket.setdefaulttimeout(20)
            logger.info(
                "imap_sync_start | host=%s folder=%s last_seen_uid=%s",
                self._host, folder, last_seen_uid,
            )
            client = self._connect()
            client.login(self._username, self._password)
            status, select_data = client.select(folder)
            if status != "OK":
                logger.warning("imap_sync | select_failed | folder=%s", folder)
                return SyncResult(success=False, error=f"Failed to select folder '{folder}'.")
            current_uidvalidity = _parse_uidvalidity(select_data)
            effective_last_seen_uid = last_seen_uid
            if uidvalidity is not None and current_uidvalidity is not None and current_uidvalidity != uidvalidity:
                logger.info("imap_sync | uidvalidity_changed | reset last_seen_uid to 0")
                effective_last_seen_uid = 0

            status, search_data = client.uid("SEARCH", None, f"UID {effective_last_seen_uid + 1}:*")
            if status != "OK":
                logger.warning("imap_sync | search_failed")
                return SyncResult(success=False, error="Failed to search IMAP mailbox.")
            all_uids = [int(value) for value in (search_data[0] or b"").split() if value]
            logger.info(
                "imap_sync | search_result | uid_from=%s total_uids=%d max_per_sync=%d",
                effective_last_seen_uid + 1, len(all_uids), MAX_MESSAGES_PER_SYNC,
            )

            # Take the most recent N to avoid stalling on first-sync cold start
            uids = all_uids[-MAX_MESSAGES_PER_SYNC:] if len(all_uids) > MAX_MESSAGES_PER_SYNC else all_uids
            if len(all_uids) > MAX_MESSAGES_PER_SYNC:
                logger.info(
                    "imap_sync | capped_uids | skipped=%d fetching=%d (oldest skipped UID=%s)",
                    len(all_uids) - MAX_MESSAGES_PER_SYNC, len(uids), all_uids[0],
                )

            parser = MimeParser()
            messages = []
            max_uid = effective_last_seen_uid
            for uid in uids:
                fetch_status, fetch_data = client.uid("FETCH", str(uid), "(UID BODY.PEEK[])")
                if fetch_status != "OK":
                    logger.warning("imap_sync | fetch_failed | uid=%d", uid)
                    continue
                raw_bytes = _extract_body(fetch_data)
                if raw_bytes is None:
                    logger.warning("imap_sync | empty_body | uid=%d", uid)
                    continue
                parsed = parser.parse(raw_bytes, uid, folder)
                logger.info(
                    "imap_sync | message_parsed | uid=%d subject=%r from=%r in_reply_to=%r",
                    uid, parsed.subject, parsed.from_address, parsed.in_reply_to,
                )
                messages.append(parsed)
                max_uid = max(max_uid, uid)

            logger.info(
                "imap_sync_done | folder=%s messages_fetched=%d new_last_seen_uid=%s",
                folder, len(messages), max_uid,
            )
            return SyncResult(
                success=True,
                new_messages=messages,
                new_last_seen_uid=max_uid,
                new_uidvalidity=current_uidvalidity,
            )
        except Exception as exc:
            logger.exception("imap_sync | exception | host=%s folder=%s error=%s", self._host, folder, exc)
            return SyncResult(success=False, error=str(exc))
        finally:
            if client is not None:
                try:
                    client.logout()
                except Exception:
                    pass
            socket.setdefaulttimeout(previous_timeout)

    def test(self) -> tuple[bool, str | None]:
        client = None
        try:
            client = self._connect()
            client.login(self._username, self._password)
            return True, None
        except Exception as exc:
            return False, str(exc)
        finally:
            if client is not None:
                try:
                    client.logout()
                except Exception:
                    pass

    def search_by_header_ids(
        self,
        folder: str,
        rfc_message_ids: list[str],
    ) -> TargetedSyncResult:
        previous_timeout = socket.getdefaulttimeout()
        client = None
        try:
            socket.setdefaulttimeout(20)
            trimmed_ids = [item for item in rfc_message_ids if item][-MAX_IDS_PER_TARGETED_SYNC:]
            client = self._connect()
            client.login(self._username, self._password)
            status, _ = client.select(folder)
            if status != "OK":
                return TargetedSyncResult(success=False, error=f"Failed to select folder '{folder}'.")

            uid_set: set[int] = set()
            for rfc_message_id in trimmed_ids:
                uid_set |= _search_header_uid_set(client, "In-Reply-To", rfc_message_id)
                uid_set |= _search_header_uid_set(client, "References", rfc_message_id)

            if not uid_set:
                return TargetedSyncResult(success=True, messages=[], matched_uid_count=0)

            uids = sorted(uid_set)
            if len(uids) > MAX_MESSAGES_PER_TARGETED_SYNC:
                uids = uids[-MAX_MESSAGES_PER_TARGETED_SYNC:]

            parser = MimeParser()
            messages = []
            for uid in uids:
                fetch_status, fetch_data = client.uid("FETCH", str(uid), "(UID BODY.PEEK[])")
                if fetch_status != "OK":
                    continue
                raw_bytes = _extract_body(fetch_data)
                if raw_bytes is None:
                    continue
                messages.append(parser.parse(raw_bytes, uid, folder))

            return TargetedSyncResult(
                success=True,
                messages=messages,
                matched_uid_count=len(uid_set),
            )
        except Exception as exc:
            logger.exception(
                "imap_targeted_sync | exception | host=%s folder=%s error=%s",
                self._host,
                folder,
                exc,
            )
            return TargetedSyncResult(success=False, error=str(exc))
        finally:
            if client is not None:
                try:
                    client.logout()
                except Exception:
                    pass
            socket.setdefaulttimeout(previous_timeout)

    def _connect(self):
        if self._security == EmailSecurityEnum.SSL.value:
            return imaplib.IMAP4_SSL(self._host, self._port)
        client = imaplib.IMAP4(self._host, self._port)
        if self._security == EmailSecurityEnum.STARTTLS.value:
            client.starttls()
        return client


def _extract_body(fetch_data) -> bytes | None:
    for item in fetch_data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return None


def _parse_uidvalidity(select_data) -> int | None:
    for item in select_data:
        raw = item.decode() if isinstance(item, bytes) else str(item)
        if "UIDVALIDITY" in raw:
            digits = "".join(ch if ch.isdigit() else " " for ch in raw).split()
            if digits:
                return int(digits[-1])
    return None


def _search_header_uid_set(client, header_name: str, value: str) -> set[int]:
    status, search_data = client.uid("SEARCH", "HEADER", header_name, value)
    if status != "OK":
        return set()
    return {int(item) for item in (search_data[0] or b"").split() if item}
