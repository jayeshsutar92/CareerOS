from uuid import UUID

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.schemas.contact import ContactSortField, SortOrder


class ContactRepository:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    async def create(self, contact: Contact) -> Contact:
        self.session.add(contact)
        await self.session.commit()
        await self.session.refresh(contact)
        return contact

    async def get_by_id(self, contact_id: UUID) -> Contact | None:
        result = await self.session.execute(
            select(Contact).where(Contact.id == contact_id, Contact.user_id == self.user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_dedupe_key(self, dedupe_key: str) -> Contact | None:
        result = await self.session.execute(
            select(Contact).where(Contact.dedupe_key == dedupe_key, Contact.user_id == self.user_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        company_name: str | None,
        role_category: str | None,
        sort_by: ContactSortField,
        sort_order: SortOrder,
    ) -> tuple[list[Contact], int]:
        statement = self._apply_filters(
            select(Contact),
            search=search,
            company_name=company_name,
            role_category=role_category,
        )
        count_statement = self._apply_filters(
            select(func.count()).select_from(Contact),
            search=search,
            company_name=company_name,
            role_category=role_category,
        )

        sort_column = getattr(Contact, sort_by)
        statement = statement.order_by(
            asc(sort_column) if sort_order == "asc" else desc(sort_column)
        )
        statement = statement.offset((page - 1) * page_size).limit(page_size)

        items_result = await self.session.execute(statement)
        count_result = await self.session.execute(count_statement)
        return list(items_result.scalars().all()), count_result.scalar_one()

    async def commit_and_refresh(self, contact: Contact) -> Contact:
        await self.session.commit()
        await self.session.refresh(contact)
        return contact

    def _apply_filters(
        self,
        statement: Select,
        *,
        search: str | None,
        company_name: str | None,
        role_category: str | None,
    ) -> Select:
        statement = statement.where(Contact.user_id == self.user_id)
        
        if search:
            search_term = f"%{search}%"
            statement = statement.where(
                or_(
                    Contact.name.ilike(search_term),
                    Contact.role.ilike(search_term),
                    Contact.company_name.ilike(search_term),
                    Contact.source_url.ilike(search_term),
                )
            )
        if company_name:
            statement = statement.where(Contact.company_name.ilike(f"%{company_name}%"))
        if role_category:
            statement = statement.where(Contact.role_category == role_category)
        return statement
