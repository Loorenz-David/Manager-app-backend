from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.tasks.serializers import serialize_note_with_images
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_note import TaskNote
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext


async def get_task_notes(ctx: ServiceContext) -> dict:
    task_id = ctx.incoming_data.get("task_id")

    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        raise NotFound("Task not found.")

    notes_result = await ctx.session.execute(
        select(TaskNote)
        .where(
            TaskNote.workspace_id == ctx.workspace_id,
            TaskNote.task_id == task.client_id,
            TaskNote.is_deleted.is_(False),
        )
        .order_by(TaskNote.created_at.asc())
    )
    notes = notes_result.scalars().all()

    user_ids = sorted({
        user_id
        for note in notes
        for user_id in [note.created_by_id, note.updated_by_id]
        if user_id
    })
    user_role_map: dict[str, tuple[User, str, str, str, str]] = {}
    if user_ids:
        users_result = await ctx.session.execute(
            select(
                User,
                Role.client_id.label("role_client_id"),
                Role.name.label("role_name"),
                WorkspaceRole.client_id.label("workspace_role_client_id"),
                WorkspaceRole.specialization.label("workspace_role_name"),
            )
            .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
            .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
            .join(Role, Role.client_id == WorkspaceRole.role_id)
            .where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                WorkspaceMembership.is_active.is_(True),
                User.client_id.in_(user_ids),
            )
        )
        for row in users_result.all():
            user_role_map[row.User.client_id] = (
                row.User,
                row.role_client_id,
                row.role_name,
                row.workspace_role_client_id,
                row.workspace_role_name or row.role_name,
            )

    note_ids = [note.client_id for note in notes]
    note_images_map: dict[str, list[Image]] = {}
    if note_ids:
        images_result = await ctx.session.execute(
            select(Image, ImageLink.entity_client_id)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.NOTE,
                    ImageLink.entity_client_id.in_(note_ids),
                ),
            )
            .options(selectinload(Image.last_event), selectinload(Image.image_annotations))
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.entity_client_id.asc(), ImageLink.display_order.asc())
        )
        for image, note_id in images_result.all():
            note_images_map.setdefault(note_id, []).append(image)

    serialized_notes = []
    for note in notes:
        created_by = user_role_map.get(note.created_by_id or "")
        updated_by = user_role_map.get(note.updated_by_id or "")
        serialized_notes.append(
            serialize_note_with_images(
                note,
                created_by_user=created_by[0] if created_by else None,
                created_by_role_client_id=created_by[1] if created_by else None,
                created_by_role_name=created_by[2] if created_by else None,
                created_by_workspace_role_client_id=created_by[3] if created_by else None,
                created_by_workspace_role_name=created_by[4] if created_by else None,
                updated_by_user=updated_by[0] if updated_by else None,
                updated_by_role_client_id=updated_by[1] if updated_by else None,
                updated_by_role_name=updated_by[2] if updated_by else None,
                updated_by_workspace_role_client_id=updated_by[3] if updated_by else None,
                updated_by_workspace_role_name=updated_by[4] if updated_by else None,
                note_images=note_images_map.get(note.client_id, []),
            )
        )

    return {"task_notes": serialized_notes}
