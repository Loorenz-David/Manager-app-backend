import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from beyo_manager.config import settings

_startup_logger = logging.getLogger("beyo_manager.startup")


_REQUIRED_SETTINGS = ["secret_key", "jwt_secret_key", "database_url", "redis_url"]


def _validate_config() -> None:
    missing = [k for k in _REQUIRED_SETTINGS if not getattr(settings, k, None)]
    if missing:
        raise RuntimeError(
            f"Missing required config keys: {', '.join(missing)}"
        )


def _register_event_handlers() -> None:
    from beyo_manager.services.infra.events import register
    from beyo_manager.services.infra.events.handlers.socket_handler import handle as socket_handle
    from beyo_manager.services.infra.events.handlers.audit_handler import handle as audit_handle
    from beyo_manager.services.infra.events.handlers.webhook_handler import handle as webhook_handle
    register(socket_handle)
    register(audit_handle)
    register(webhook_handle)


def _register_routers(app: FastAPI) -> None:
    from beyo_manager.routers.api_v1 import register_v1_routers
    register_v1_routers(app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from beyo_manager.models.database import init_db, close_db
    await init_db()
    _startup_logger.info(
        "startup | env=%s database_url=%s redis_url=%s "
        "db_pool_size=%d db_max_overflow=%d db_pool_recycle=%d",
        settings.environment,
        settings.database_url,
        settings.redis_url,
        settings.db_pool_size,
        settings.db_max_overflow,
        settings.db_pool_recycle,
    )
    _register_event_handlers()
    yield
    await close_db()


def create_app() -> FastAPI:
    from beyo_manager.routers.middleware.no_cache import NoCacheMiddleware
    from beyo_manager.routers.middleware.sleep import SleepMiddleware
    from beyo_manager.routers.middleware.timeout import TimeoutMiddleware

    app = FastAPI(lifespan=lifespan)

    # Registered last → executes first on request
    from beyo_manager.routers.middleware.backend_permission import BackendPermissionMiddleware
    app.add_middleware(BackendPermissionMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Content-Type", "Authorization"],
    )
    # Gzip: compresses responses > 1 KB
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    # No-cache: Cache-Control: no-store on /api/ responses
    app.add_middleware(NoCacheMiddleware)
    # Sleep: touches ActivityTracker on every request — wakes the app if sleeping
    app.add_middleware(SleepMiddleware)
    # Timeout: hard deadline, returns 504 on breach
    app.add_middleware(TimeoutMiddleware)

    _register_routers(app)
    if settings.storage_provider == 'local':
        from beyo_manager.routers.dev.storage import router as _dev_storage_router
        app.include_router(_dev_storage_router)
    _validate_config()

    import socketio
    from beyo_manager.sockets import sio
    import beyo_manager.sockets as sockets_module
    from beyo_manager.sockets.register import register_socket_handlers

    register_socket_handlers()
    sockets_module.socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
    return app
