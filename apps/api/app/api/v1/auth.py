from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    OAuth2PasswordRequestForm,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import create_audit_event
from app.auth.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.database.session import get_db_session
from app.models.enums import AuditEventType
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    form: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> TokenResponse:
    user = await authenticate_user(
        session,
        username=form.username,
        password=form.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    await create_audit_event(
        session,
        event_type=AuditEventType.USER_LOGIN,
        entity_type="USER",
        entity_id=user.id,
        actor=user.username,
        payload={
            "role": user.role.value,
        },
    )

    await session.commit()

    return TokenResponse(
        access_token=create_access_token(
            user
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def me(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> UserResponse:
    return UserResponse.model_validate(
        current_user
    )
