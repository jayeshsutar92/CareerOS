from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.api.deps import get_current_admin_user
from app.db.session import get_db_session
from app.models.user import User
from app.models.company import Company
from app.models.contact import Contact
from app.models.email import Email
from app.models.company_intelligence import CompanyIntelligence
from app.core.redis import get_redis_client
import json

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/statistics")
async def get_statistics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    users_count = await session.scalar(select(func.count(User.id)))
    companies_count = await session.scalar(select(func.count(Company.id)))
    contacts_count = await session.scalar(select(func.count(Contact.id)))
    emails_count = await session.scalar(select(func.count(Email.id)))
    
    return {
        "users": users_count,
        "companies": companies_count,
        "contacts": contacts_count,
        "emails": emails_count,
    }

@router.get("/users")
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "is_admin": u.is_admin, "is_active": u.is_active, "created_at": u.created_at} for u in users]

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
    await session.execute(delete(User).where(User.id == user_id))
    await session.commit()
    logger.info("Admin deleted user", extra={"action": "admin_deleted_user", "deleted_user_id": str(user_id), "admin_id": str(admin_user.id)})

@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    await session.execute(delete(Company).where(Company.id == company_id))
    await session.commit()
    logger.info("Admin deleted company globally", extra={"action": "admin_deleted_company", "company_id": str(company_id), "admin_id": str(admin_user.id)})

@router.get("/companies")
async def list_companies(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    result = await session.execute(select(CompanyIntelligence).order_by(CompanyIntelligence.created_at.desc()).limit(100))
    comps = result.scalars().all()
    return [{"id": str(c.id), "company_name": c.company_name, "status": c.status, "user_id": str(c.user_id), "created_at": c.created_at} for c in comps]

@router.get("/contacts")
async def list_contacts(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    result = await session.execute(select(Contact).order_by(Contact.created_at.desc()).limit(100))
    contacts = result.scalars().all()
    return [{"id": str(c.id), "name": c.name, "company_id": str(c.company_id), "user_id": str(c.user_id), "created_at": c.created_at} for c in contacts]

@router.get("/emails")
async def list_emails(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    result = await session.execute(select(Email).order_by(Email.created_at.desc()).limit(100))
    emails = result.scalars().all()
    return [{"id": str(e.id), "subject": e.subject, "status": e.status, "user_id": str(e.user_id), "created_at": e.created_at} for e in emails]

@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact_admin(
    contact_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    await session.execute(delete(Contact).where(Contact.id == contact_id))
    await session.commit()

@router.delete("/emails/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_admin(
    email_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    admin_user: User = Depends(get_current_admin_user),
):
    await session.execute(delete(Email).where(Email.id == email_id))
    await session.commit()

@router.get("/tasks")
async def list_tasks(
    admin_user: User = Depends(get_current_admin_user),
):
    redis = get_redis_client()
    keys = []
    cursor = 0
    while True:
        cursor, matched_keys = await redis.scan(cursor, match="workers:*:result:*", count=100)
        keys.extend(matched_keys)
        if cursor == 0:
            break
            
    tasks = []
    for key in keys:
        if isinstance(key, bytes):
            key = key.decode("utf-8")
        parts = key.split(":")
        if len(parts) >= 4:
            user_id = parts[1]
            task_id = parts[3]
            data = await redis.get(key)
            if data:
                try:
                    task_data = json.loads(data)
                    tasks.append({
                        "id": task_id,
                        "user_id": user_id,
                        "status": task_data.get("status", "unknown"),
                    })
                except Exception:
                    pass
    return tasks

@router.delete("/tasks/{user_id}/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_admin(
    user_id: str,
    task_id: str,
    admin_user: User = Depends(get_current_admin_user),
):
    redis = get_redis_client()
    await redis.delete(f"workers:{user_id}:result:{task_id}")
    await redis.delete(f"workers:result:{task_id}")

