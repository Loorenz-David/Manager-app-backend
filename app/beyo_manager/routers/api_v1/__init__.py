from fastapi import FastAPI

from beyo_manager.routers.api_v1 import (
    audit,
    auth,
    bootstrap,
    case_types,
    cases,
    customers,
    email_connections,
    email_templates,
    email_threads,
    files,
    health,
    history,
    images,
    issue_types,
    items,
    item_categories,
    item_upholsteries,
    location_tracker,
    notifications,
    reset,
    shopify,
    shopify_webhooks,
    tasks,
    upholsteries,
    upholstery_categories,
    upholstery_inventories,
    upholstery_order_needs,
    upholstery_orders,
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
    app.include_router(
        shopify.router,
        prefix="/api/v1/integrations/shopify",
        tags=["shopify"],
    )
    app.include_router(
        shopify_webhooks.router,
        prefix="/api/v1/shopify",
        tags=["shopify-webhooks"],
    )
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
    app.include_router(case_types.router)
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
    app.include_router(upholstery_orders.router)
    app.include_router(upholstery_order_needs.router)
    app.include_router(upholstery_categories.router)
    app.include_router(upholsteries.router)
    app.include_router(item_upholsteries.router)
    app.include_router(item_upholsteries.requirements_router)
    app.include_router(items.router, prefix="/api/v1/items", tags=["items"])
    app.include_router(item_categories.router)
    app.include_router(issue_types.router)
    app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
    app.include_router(
        email_connections.router,
        prefix="/api/v1/email-connections",
        tags=["email-connections"],
    )
    app.include_router(
        email_threads.router,
        prefix="/api/v1/email-threads",
        tags=["email-threads"],
    )
    app.include_router(
        email_templates.router,
        prefix="/api/v1/email-templates",
        tags=["email-templates"],
    )
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(
        location_tracker.router,
        prefix="/api/v1/location-tracker",
        tags=["location-tracker"],
    )
    # Add domain routers here as you build them:
