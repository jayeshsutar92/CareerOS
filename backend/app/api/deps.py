from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import check_rate_limit, get_rate_limit_identifier
from app.core.security import TokenType
from app.db.session import get_db_session
from app.models.user import User
from app.services.auth import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(session)
    payload = auth_service.decode_expected_token(credentials.credentials, TokenType.ACCESS)
    return await auth_service.get_user_from_token_payload(payload)


async def enforce_rate_limit(request: Request) -> None:
    identifier = get_rate_limit_identifier(request)
    await check_rate_limit(identifier)
