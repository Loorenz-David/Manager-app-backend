import smtplib
import ssl

from beyo_manager.domain.emails.enums import EmailSecurityEnum
from beyo_manager.services.infra.email_providers.base import OutboundMessage, SendResult
from beyo_manager.services.infra.email_providers.smtp_imap.mime_builder import MimeBuilder

SMTP_BATCH_WINDOW_SIZE = 50


class SmtpSender:
    def __init__(self, host: str, port: int, security: str, username: str, password: str):
        self._host = host
        self._port = port
        self._security = security
        self._username = username
        self._password = password

    def send(self, message: OutboundMessage) -> SendResult:
        try:
            mime_message = MimeBuilder().build(message)
            recipients = message.to_addresses + message.cc_addresses + message.bcc_addresses
            with self._connect() as smtp:
                smtp.login(self._username, self._password)
                smtp.sendmail(message.from_address, recipients, mime_message.as_string())
            return SendResult(success=True)
        except Exception as exc:
            return SendResult(success=False, error=str(exc))

    def send_batch(self, messages: list[OutboundMessage]) -> list[SendResult]:
        results: list[SendResult] = []
        for start in range(0, len(messages), SMTP_BATCH_WINDOW_SIZE):
            window = messages[start:start + SMTP_BATCH_WINDOW_SIZE]
            results.extend(self._send_window(window))
        return results

    def test(self) -> tuple[bool, str | None]:
        try:
            with self._connect() as smtp:
                smtp.login(self._username, self._password)
            return True, None
        except Exception as exc:
            return False, str(exc)

    def _connect(self):
        timeout = 15
        if self._security == EmailSecurityEnum.SSL.value:
            return smtplib.SMTP_SSL(self._host, self._port, timeout=timeout, context=ssl.create_default_context())
        smtp = smtplib.SMTP(self._host, self._port, timeout=timeout)
        if self._security == EmailSecurityEnum.STARTTLS.value:
            smtp.starttls(context=ssl.create_default_context())
        return smtp

    def _send_window(self, messages: list[OutboundMessage]) -> list[SendResult]:
        results: list[SendResult] = []
        smtp = None
        try:
            smtp = self._connect()
            smtp.login(self._username, self._password)
            for message in messages:
                try:
                    mime_message = MimeBuilder().build(message)
                    recipients = message.to_addresses + message.cc_addresses + message.bcc_addresses
                    smtp.sendmail(message.from_address, recipients, mime_message.as_string())
                    results.append(SendResult(success=True))
                except (smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError) as exc:
                    results.append(SendResult(success=False, error=str(exc)))
        except Exception as exc:
            remaining = len(messages) - len(results)
            results.extend(SendResult(success=False, error=str(exc)) for _ in range(remaining))
        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except Exception:
                    pass
        return results
