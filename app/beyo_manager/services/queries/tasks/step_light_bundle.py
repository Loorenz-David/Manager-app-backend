"""Shared batched loaders for the *light* step view (step + task + primary item + images).

Reusable entity loaders (maps keyed by id), not a monolithic item builder — each
caller composes its own item shape from these maps, so the two consumers evolve
independently. Extracted from the batched blocks in `list_working_section_steps`.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.context import ServiceContext


@dataclass(frozen=True)
class StepLightBundle:
    steps_by_id: dict[str, TaskStep]
    tasks_by_id: dict[str, Task]
    task_to_primary_item_id: dict[str, str]
    items_by_id: dict[str, Item]
    requirements_by_item: dict[str, list[ItemUpholsteryRequirement]]
    upholstery_by_id: dict[str, ItemUpholstery]
    images_by_item: dict[str, list]


async def load_step_light_bundle(ctx: ServiceContext, step_ids: list[str]) -> StepLightBundle:
    """Batched fetch of everything the light step item needs, keyed by id. Constant query count."""
    if not step_ids:
        return StepLightBundle({}, {}, {}, {}, {}, {}, {})

    steps = (
        await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id.in_(step_ids),
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    steps_by_id = {step.client_id: step for step in steps}

    task_ids = list({step.task_id for step in steps})
    tasks_by_id: dict[str, Task] = {}
    task_to_primary_item_id: dict[str, str] = {}
    items_by_id: dict[str, Item] = {}
    requirements_by_item: dict[str, list[ItemUpholsteryRequirement]] = {}
    upholstery_by_id: dict[str, ItemUpholstery] = {}
    images_by_item: dict[str, list] = {}

    if task_ids:
        tasks = (
            await ctx.session.execute(
                select(Task).where(
                    Task.workspace_id == ctx.workspace_id,
                    Task.client_id.in_(task_ids),
                    Task.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        tasks_by_id = {task.client_id: task for task in tasks}

        task_items = (
            await ctx.session.execute(
                select(TaskItem).where(
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.task_id.in_(task_ids),
                    TaskItem.removed_at.is_(None),
                    TaskItem.role == TaskItemRoleEnum.PRIMARY,
                )
            )
        ).scalars().all()
        task_to_primary_item_id = {ti.task_id: ti.item_id for ti in task_items}

    primary_item_ids = list(task_to_primary_item_id.values())
    if primary_item_ids:
        items = (
            await ctx.session.execute(
                select(Item).where(
                    Item.workspace_id == ctx.workspace_id,
                    Item.client_id.in_(primary_item_ids),
                    Item.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        items_by_id = {item.client_id: item for item in items}

        upholsteries = (
            await ctx.session.execute(
                select(ItemUpholstery).where(
                    ItemUpholstery.workspace_id == ctx.workspace_id,
                    ItemUpholstery.item_id.in_(primary_item_ids),
                    ItemUpholstery.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        upholstery_by_id = {uph.client_id: uph for uph in upholsteries}
        uph_to_item = {uph.client_id: uph.item_id for uph in upholsteries}

        uph_ids = list(uph_to_item.keys())
        if uph_ids:
            reqs = (
                await ctx.session.execute(
                    select(ItemUpholsteryRequirement).where(
                        ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                        ItemUpholsteryRequirement.item_upholstery_id.in_(uph_ids),
                        ItemUpholsteryRequirement.is_deleted.is_(False),
                    )
                )
            ).scalars().all()
            for req in reqs:
                item_id = uph_to_item.get(req.item_upholstery_id)
                if item_id is not None:
                    requirements_by_item.setdefault(item_id, []).append(req)

        img_rows = (
            await ctx.session.execute(
                select(Image, ImageLink.entity_client_id)
                .join(
                    ImageLink,
                    and_(
                        ImageLink.image_id == Image.client_id,
                        ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                        ImageLink.entity_client_id.in_(primary_item_ids),
                    ),
                )
                .options(
                    selectinload(Image.last_event),
                    selectinload(Image.image_annotations),
                )
                .where(Image.deleted_at.is_(None))
                .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
            )
        ).all()
        for image, item_id in img_rows:
            image_list = images_by_item.setdefault(item_id, [])
            if not image_list:
                first_image = serialize_image(image, include_annotations=True)
                first_image.pop("image_annotations", None)
                image_list.append(first_image)
            else:
                image_list.append(serialize_image_light(image))

    return StepLightBundle(
        steps_by_id=steps_by_id,
        tasks_by_id=tasks_by_id,
        task_to_primary_item_id=task_to_primary_item_id,
        items_by_id=items_by_id,
        requirements_by_item=requirements_by_item,
        upholstery_by_id=upholstery_by_id,
        images_by_item=images_by_item,
    )
