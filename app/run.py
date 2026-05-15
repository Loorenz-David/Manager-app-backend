import socket
import uvicorn
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()  # Load .env before reading PORT or any other env var

from scripts.wait_for_services import wait_for_services


def _find_free_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"No free port found in range {preferred}–{preferred + 19}. Free a port and retry."
    )


if __name__ == "__main__":
    asyncio.run(wait_for_services())
    requested_port = int(os.getenv("PORT", "8000"))
    port = _find_free_port(requested_port)
    if port != requested_port:
        print(f"[run] Port {requested_port} is in use — using {port} instead.")
        print(f"[run] Update PORT={port} in .env to make this permanent.")
    uvicorn.run(
        "beyo_manager.asgi:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("UVICORN_RELOAD", "0") == "1",
    )
