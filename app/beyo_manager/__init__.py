import asyncio
import contextlib
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from beyo_manager.config import settings
from beyo_manager.core.logging.config import configure_logging

configure_logging()

_startup_logger = logging.getLogger("beyo_manager.startup")


_REQUIRED_SETTINGS = ["secret_key", "jwt_secret_key", "database_url", "redis_url"]


def _validate_config() -> None:
    missing = [k for k in _REQUIRED_SETTINGS if not getattr(settings, k, None)]
    if missing:
        raise RuntimeError(
            f"Missing required config keys: {', '.join(missing)}"
        )


def _register_event_handlers() -> None:
    """Kept as an explicit startup step for readability; the work is idempotent and has
    already happened on import of the events package. See `events/bootstrap.py` — a startup
    hook could not be the guarantee, because four of the nine workers never run one.
    """
    from beyo_manager.services.infra.events import register_default_handlers
    register_default_handlers()


def _register_routers(app: FastAPI) -> None:
    from beyo_manager.routers.api_v1 import register_v1_routers
    register_v1_routers(app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from beyo_manager.core.logging.redaction import redact_url
    from beyo_manager.models.database import init_db, close_db
    await init_db()
    _startup_logger.info(
        "startup | env=%s database_url=%s redis_url=%s "
        "db_pool_size=%d db_max_overflow=%d db_pool_recycle=%d",
        settings.environment,
        redact_url(settings.database_url),
        redact_url(settings.redis_url),
        settings.db_pool_size,
        settings.db_max_overflow,
        settings.db_pool_recycle,
    )
    _register_event_handlers()
    heartbeat = _start_api_heartbeat()
    try:
        yield
    finally:
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat
    await close_db()


def _start_api_heartbeat() -> "asyncio.Task[None]":
    """Beat `{prefix}:system:api_heartbeat` while this process serves (see api_heartbeat)."""
    from beyo_manager.services.infra.activity.api_heartbeat import run_api_heartbeat
    from beyo_manager.sockets.manager import manager

    return asyncio.create_task(
        run_api_heartbeat(started_at=time.time(), socket_counts=manager.connection_counts),
        name="api_heartbeat",
    )


def create_app() -> FastAPI:
    from beyo_manager.routers.middleware.activity import ActivityMiddleware
    from beyo_manager.routers.middleware.no_cache import NoCacheMiddleware
    from beyo_manager.routers.middleware.timeout import TimeoutMiddleware

    app = FastAPI(lifespan=lifespan)

    # add_middleware inserts at position 0, so the LAST one added is the OUTERMOST.
    # Request order, outer → inner:
    #   Timeout → Activity → NoCache → GZip → CORS → BackendPermission → routes.
    # BackendPermission, added first, is the innermost: it runs last on a request.
    from beyo_manager.routers.middleware.backend_permission import BackendPermissionMiddleware
    app.add_middleware(BackendPermissionMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        # X-Beyo-Activity: the client's user/background marking (see ActivityMiddleware);
        # a cross-origin preflight fails without it.
        allow_headers=["Content-Type", "Authorization", "X-Beyo-Activity"],
    )
    # Gzip: compresses responses > 1 KB
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    # No-cache: Cache-Control: no-store on /api/ responses
    app.add_middleware(NoCacheMiddleware)
    # Activity: records human activity (validated identity + user intent); with
    # SLEEP_MODE_ENABLED also the legacy ActivityTracker.touch() on every request
    app.add_middleware(ActivityMiddleware)
    # Timeout: hard deadline, returns 504 on breach
    app.add_middleware(TimeoutMiddleware)

    _register_routers(app)
    if settings.storage_provider == 'local':
        from beyo_manager.routers.dev.storage import router as _dev_storage_router
        app.include_router(_dev_storage_router)
    _validate_config()

    import socketio
    from beyo_manager.sockets import get_sio, mark_socket_server_process
    import beyo_manager.sockets as sockets_module
    from beyo_manager.sockets.register import register_socket_handlers

    # This process holds the websocket connections; every other process must publish through
    # Redis instead. `realtime_push` reads this to pick its transport.
    mark_socket_server_process()
    register_socket_handlers()
    sockets_module.socket_app = socketio.ASGIApp(get_sio(), other_asgi_app=app)
    return app
