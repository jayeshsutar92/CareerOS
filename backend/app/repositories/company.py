from uuid import UUID

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.company import CompanySortField, SortOrder


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, company: Company) -> Company:
        self.session.add(company)
        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def get_by_id(self, company_id: UUID) -> Company | None:
        result = await self.session.execute(select(Company).where(Company.id == company_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Company | None:
        result = await self.session.execute(
            select(Company).where(func.lower(Company.name) == name.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_website_url(self, website_url: str) -> Company | None:
        result = await self.session.execute(
            select(Company).where(Company.website_url == website_url)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        name: str | None,
        has_website: bool | None,
        sort_by: CompanySortField,
        sort_order: SortOrder,
    ) -> tuple[list[Company], int]:
        statement = self._apply_filters(
            select(Company), search=search, name=name, has_website=has_website
        )
        count_statement = self._apply_filters(
            select(func.count()).select_from(Company),
            search=search,
            name=name,
            has_website=has_website,
        )

        sort_column = getattr(Company, sort_by)
        statement = statement.order_by(
            asc(sort_column) if sort_order == "asc" else desc(sort_column)
        )
        statement = statement.offset((page - 1) * page_size).limit(page_size)

        items_result = await self.session.execute(statement)
        count_result = await self.session.execute(count_statement)
        return list(items_result.scalars().all()), count_result.scalar_one()

    async def delete(self, company: Company) -> None:
        await self.session.delete(company)
        await self.session.commit()

    async def commit_and_refresh(self, company: Company) -> Company:
        await self.session.commit()
        await self.session.refresh(company)
        return company

    def _apply_filters(
        self,
        statement: Select,
        *,
        search: str | None,
        name: str | None,
        has_website: bool | None,
    ) -> Select:
        if search:
            search_term = f"%{search}%"
            statement = statement.where(
                or_(
                    Company.name.ilike(search_term),
                    Company.description.ilike(search_term),
                    Company.website_url.ilike(search_term),
                )
            )
        if name:
            statement = statement.where(Company.name.ilike(f"%{name}%"))
        if has_website is True:
            statement = statement.where(Company.website_url.is_not(None))
        elif has_website is False:
            statement = statement.where(Company.website_url.is_(None))
        return statement
