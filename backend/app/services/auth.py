from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import TokenType, create_token, decode_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def register(self, payload: RegisterRequest) -> tuple[User, TokenPair]:
        existing_user = await self.get_user_by_email(payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return user, self.create_token_pair(user)

    async def authenticate(self, payload: LoginRequest) -> tuple[User, TokenPair]:
        user = await self.get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
            )

        return user, self.create_token_pair(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = self.decode_expected_token(refresh_token, TokenType.REFRESH)
        user = await self.get_user_from_token_payload(payload)
        token_version = int(payload.get("token_version", -1))
        if token_version != user.refresh_token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self.create_token_pair(user)

    async def logout(self, user: User) -> None:
        user.refresh_token_version += 1
        await self.session.commit()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def create_token_pair(self, user: User) -> TokenPair:
        access_token = create_token(
            subject=str(user.id),
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=self.settings.access_token_expire_minutes),
        )
        refresh_token = create_token(
            subject=str(user.id),
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(days=self.settings.refresh_token_expire_days),
            extra_claims={"token_version": user.refresh_token_version},
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def decode_expected_token(self, token: str, token_type: TokenType) -> dict:
        try:
            payload = decode_token(token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if payload.get("type") != token_type.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload

    async def get_user_from_token_payload(self, payload: dict) -> User:
        subject = payload.get("sub")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user_id = UUID(subject)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        user = await self.get_user_by_id(user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
