from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
