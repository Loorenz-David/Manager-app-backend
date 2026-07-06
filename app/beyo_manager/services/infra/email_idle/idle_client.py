from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from beyo_manager.domain.emails.enums import EmailSecurityEnum

logger = logging.getLogger(__name__)


class IdleNotSupportedError(RuntimeError):
    pass


@dataclass(slots=True)
class IdlePushEvent:
    raw: str

    @property
    def indicates_new_mail(self) -> bool:
        upper = self.raw.upper()
        return "EXISTS" in upper or "RECENT" in upper


class AioImapIdleClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        security: str,
        username: str,
        password: str,
        timeout_seconds: int = 20,
    ) -> None:
        self._host = host
        self._port = port
        self._security = security
        self._username = username
        self._password = password
        self._timeout_seconds = timeout_seconds
        self._client: Any | None = None

    async def connect_and_login(self) -> None:
        aioimaplib = await self._import_library()
        client_cls = getattr(
            aioimaplib,
            "IMAP4_SSL" if self._security == EmailSecurityEnum.SSL.value else "IMAP4",
        )
        self._client = client_cls(self._host, self._port, timeout=self._timeout_seconds)
        wait_hello = getattr(self._client, "wait_hello_from_server", None)
        if wait_hello is not None:
            await wait_hello()
        if self._security == EmailSecurityEnum.STARTTLS.value:
            await self._await_ok(await self._client.starttls())
        await self._await_ok(await self._client.login(self._username, self._password))

    async def select_folder(self, folder: str) -> None:
        await self._await_ok(await self._client.select(folder))

    async def ensure_idle_supported(self) -> None:
        client = self._require_client()
        has_capability = getattr(client, "has_capability", None)
        if callable(has_capability):
            if has_capability("IDLE"):
                return
            raise IdleNotSupportedError("IMAP server does not advertise IDLE capability.")

        response = await client.capability()
        capabilities = self._flatten_response(response).upper()
        if "IDLE" not in capabilities:
            raise IdleNotSupportedError("IMAP server does not advertise IDLE capability.")

    async def idle_once(
        self,
        *,
        renew_seconds: int,
        stop_event: asyncio.Event,
    ) -> list[IdlePushEvent]:
        client = self._require_client()
        idle_task = await client.idle_start(timeout=renew_seconds)
        events: list[IdlePushEvent] = []
        deadline = asyncio.get_running_loop().time() + renew_seconds
        try:
            while not stop_event.is_set():
                timeout = max(0.1, deadline - asyncio.get_running_loop().time())
                if timeout <= 0:
                    break
                try:
                    push = await asyncio.wait_for(
                        client.wait_server_push(),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    break
                if not push:
                    break
                event = IdlePushEvent(raw=self._flatten_response(push))
                events.append(event)
                # Return promptly on push so the watcher can debounce/enqueue sync
                # without waiting for the full IDLE renew timeout.
                break
            return events
        finally:
            client.idle_done()
            if idle_task is not None:
                try:
                    await asyncio.wait_for(idle_task, timeout=5)
                except Exception:
                    logger.debug("email_idle | idle_task_finish_failed", exc_info=True)

    async def logout(self) -> None:
        client = self._client
        self._client = None
        if client is None:
            return
        for method_name in ("logout", "close"):
            method = getattr(client, method_name, None)
            if method is None:
                continue
            try:
                result = method()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.debug("email_idle | client_close_failed", exc_info=True)
            break

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("IDLE client not connected.")
        return self._client

    async def _import_library(self):
        try:
            import aioimaplib  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("aioimaplib is required for the email IDLE watcher.") from exc
        return aioimaplib

    async def _await_ok(self, response: Any) -> None:
        text = self._flatten_response(response)
        if "OK" not in text.upper():
            raise RuntimeError(text or "IMAP command failed.")

    def _flatten_response(self, response: Any) -> str:
        if response is None:
            return ""
        if isinstance(response, bytes):
            return response.decode(errors="ignore")
        if isinstance(response, str):
            return response
        if isinstance(response, (list, tuple, set)):
            return " ".join(self._flatten_response(item) for item in response)
        if hasattr(response, "lines"):
            return self._flatten_response(response.lines)
        if hasattr(response, "result"):
            return self._flatten_response(response.result)
        if hasattr(response, "data"):
            return self._flatten_response(response.data)
        return str(response)
