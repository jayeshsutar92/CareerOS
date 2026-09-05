import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template
from app.schemas.template import TemplateCreate


class TemplateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, template_id: uuid.UUID) -> Template | None:
        result = await self.session.execute(
            select(Template).where(Template.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Template | None:
        result = await self.session.execute(
            select(Template).where(Template.name == name)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[Template]:
        result = await self.session.execute(
            select(Template).order_by(Template.name)
        )
        return result.scalars().all()

    async def create(self, template_in: TemplateCreate) -> Template:
        db_obj = Template(
            name=template_in.name,
            subject=template_in.subject,
            body=template_in.body
        )
        self.session.add(db_obj)
        await self.session.flush()
        return db_obj
