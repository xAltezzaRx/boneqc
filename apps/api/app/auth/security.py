from collections.abc import AsyncIterator, Callable
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import (
    reset_current_actor,
    set_current_actor,
)
from app.core.config import get_settings
from app.database.session import get_db_session
from app.models.enums import UserRole
from app.models.user import User


password_hash = PasswordHash.recommended()

# Running one real verification for unknown usernames makes
# username enumeration through simple timing differences harder.
DUMMY_HASH = password_hash.hash(
    "boneqc-dummy-password-never-used"
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)


def normalize_username(
    username: str,
) -> str:
    return username.strip().lower()


def hash_password(
    password: str,
) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    encoded_password: str,
) -> bool:
    try:
        return password_hash.verify(
            plain_password,
            encoded_password,
        )
    except Exception:
        return False


async def authenticate_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
) -> User | None:
    normalized = normalize_username(
        username
    )

    user = await session.scalar(
        select(User).where(
            User.username == normalized
        )
    )

    if user is None:
        verify_password(
            password,
            DUMMY_HASH,
        )
        return None

    if not verify_password(
        password,
        user.password_hash,
    ):
        return None

    if not user.is_active:
        return None

    return user


def create_access_token(
    user: User,
) -> str:
    settings = get_settings()

    now = datetime.now(
        timezone.utc
    )

    expires = now + timedelta(
        minutes=settings.jwt_access_token_minutes
    )

    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "type": "access",
        "iat": now,
        "exp": expires,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(
    token: str,
) -> dict:
    settings = get_settings()

    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[
            settings.jwt_algorithm
        ],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={
            "require": [
                "sub",
                "iat",
                "exp",
                "iss",
                "aud",
            ]
        },
    )


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "INVALID_AUTHENTICATION",
        },
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


async def get_current_user(
    token: Annotated[
        str,
        Depends(oauth2_scheme),
    ],
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> User:
    try:
        payload = decode_access_token(
            token
        )

        if payload.get("type") != "access":
            raise InvalidTokenError(
                "Invalid token type"
            )

        user_id = UUID(
            str(payload["sub"])
        )

    except (
        InvalidTokenError,
        ValueError,
        KeyError,
    ) as exc:
        raise credentials_exception() from exc

    user = await session.get(
        User,
        user_id,
    )

    if user is None:
        raise credentials_exception()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "USER_DISABLED",
            },
        )

    return user



async def bind_current_actor(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> AsyncIterator[User]:
    token = set_current_actor(
        current_user.username
    )

    try:
        yield current_user
    finally:
        reset_current_actor(token)


def require_roles(
    *allowed_roles: UserRole,
) -> Callable:
    allowed = set(
        allowed_roles
    )

    async def dependency(
        current_user: Annotated[
            User,
            Depends(bind_current_actor),
        ],
    ) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                },
            )

        return current_user

    return dependency
