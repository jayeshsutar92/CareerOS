from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.contact import (
    ContactDiscoveryRequest,
    ContactDiscoveryResponse,
    ContactListResponse,
    ContactRead,
    ContactRoleCategory,
    ContactSortField,
    SortOrder,
)
from app.services.contact import ContactService

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post(
    "/discover", response_model=ContactDiscoveryResponse, status_code=status.HTTP_202_ACCEPTED
)
async def discover_contacts(
    payload: ContactDiscoveryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ContactDiscoveryResponse:
    return await ContactService(session, current_user.id).discover(payload)


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    company_name: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    role_category: ContactRoleCategory | None = None,
    sort_by: ContactSortField = "created_at",
    sort_order: SortOrder = "desc",
) -> ContactListResponse:
    return await ContactService(session, current_user.id).list(
        page=page,
        page_size=page_size,
        search=search,
        company_name=company_name,
        role_category=role_category,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/search", response_model=ContactListResponse)
async def search_contacts(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    q: Annotated[str, Query(min_length=1, max_length=255)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ContactListResponse:
    return await ContactService(session, current_user.id).list(
        page=page,
        page_size=page_size,
        search=q,
        company_name=None,
        role_category=None,
        sort_by="created_at",
        sort_order="desc",
    )


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ContactRead:
    contact = await ContactService(session, current_user.id).get(contact_id)
    return ContactRead.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await ContactService(session, current_user.id).delete(contact_id)

