from fastapi import FastAPI

from beyo_manager.routers.api_v1 import (
    audit,
    auth,
    bootstrap,
    cases,
    files,
    health,
    images,
    notifications,
    reset,
    working_sections,
)


def register_v1_routers(app: FastAPI) -> None:
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
    app.include_router(bootstrap.router, prefix="/api/v1/bootstrap", tags=["bootstrap"])
    app.include_router(reset.router, prefix="/api/v1/reset", tags=["reset"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
    app.include_router(images.router, prefix="/api/v1/images", tags=["images"])
    app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
    app.include_router(
        working_sections.router,
        prefix="/api/v1/working-sections",
        tags=["working-sections"],
    )
    # Add domain routers here as you build them:
    # app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
