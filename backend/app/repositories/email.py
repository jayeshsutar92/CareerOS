from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email


class EmailRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_draft(
        self,
        *,
        user_id: UUID,
        subject: str,
        body: str,
        recruiter_id: UUID | None = None,
        application_id: UUID | None = None,
    ) -> Email:
        email = Email(
            user_id=user_id,
            subject=subject,
            body=body,
            status="draft",
            recruiter_id=recruiter_id,
            application_id=application_id,
        )
        self.session.add(email)
        await self.session.commit()
        await self.session.refresh(email)
        return email

    async def get_by_id(self, email_id: UUID) -> Email | None:
        result = await self.session.execute(select(Email).where(Email.id == email_id))
        return result.scalar_one_or_none()

    async def list_by_user_id(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Email], int]:
        stmt = select(Email).where(Email.user_id == user_id)
        count_stmt = select(func.count(Email.id)).where(Email.user_id == user_id)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(Email.created_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
