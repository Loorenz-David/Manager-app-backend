from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.queries.items.lookup.base import ItemLookupHandler, ItemLookupResult


class InternalDbLookupHandler(ItemLookupHandler):
    async def lookup(
        self,
        article_number: str | None,
        sku: str | None,
        session: AsyncSession,
        workspace_id: str,
    ) -> ItemLookupResult | None:
        identifier_conditions = []
        if article_number:
            identifier_conditions.append(Item.article_number == article_number)
        if sku:
            identifier_conditions.append(Item.sku == sku)

        result = await session.execute(
            select(Item).where(
                Item.workspace_id == workspace_id,
                Item.is_deleted.is_(False),
                or_(*identifier_conditions),
            ).limit(1)
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None

        img_result = await session.execute(
            select(Image)
            .join(
                ImageLink,
                and_(
                    ImageLink.image_id == Image.client_id,
                    ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                    ImageLink.entity_client_id == item.client_id,
                ),
            )
            .options(selectinload(Image.last_event))
            .where(Image.deleted_at.is_(None))
            .order_by(ImageLink.display_order.asc())
        )
        image_rows = img_result.scalars().all()
        images = [
            serialize_image(img) if i == 0 else serialize_image_light(img)
            for i, img in enumerate(image_rows)
        ]

        return ItemLookupResult(
            article_number=item.article_number,
            sku=item.sku,
            item_category_id=item.item_category_id,
            quantity=item.quantity,
            external_id=item.external_id,
            external_source=None,
            images=images,
        )
