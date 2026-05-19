from fastapi import FastAPI

from beyo_manager.routers.api_v1 import (
    audit,
    auth,
    bootstrap,
    cases,
    customers,
    files,
    health,
    history,
    images,
    items,
    item_upholsteries,
    notifications,
    reset,
    tasks,
    upholstery_inventories,
    users,
    user_working_sections,
    working_section_memberships,
    working_sections,
)


def register_v1_routers(app: FastAPI) -> None:
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
    app.include_router(bootstrap.router, prefix="/api/v1/bootstrap", tags=["bootstrap"])
    app.include_router(reset.router, prefix="/api/v1/reset", tags=["reset"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
    app.include_router(history.router, prefix="/api/v1/history", tags=["history"])
    app.include_router(images.router, prefix="/api/v1/images", tags=["images"])
    app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
    app.include_router(
        working_sections.router,
        prefix="/api/v1/working-sections",
        tags=["working-sections"],
    )
    app.include_router(
        user_working_sections.router,
        prefix="/api/v1/users",
        tags=["user-working-sections"],
    )
    app.include_router(
        working_section_memberships.router,
        prefix="/api/v1/working-sections",
        tags=["working-section-memberships"],
    )
    app.include_router(upholstery_inventories.router)
    app.include_router(item_upholsteries.router)
    app.include_router(item_upholsteries.requirements_router)
    app.include_router(items.router, prefix="/api/v1/items", tags=["items"])
    app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    # Add domain routers here as you build them:
