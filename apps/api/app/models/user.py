from sqlalchemy import Boolean, Enum as SAEnum
from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import UserRole


class User(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role",
            native_enum=False,
        ),
        nullable=False,
        default=UserRole.OPERATOR,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )
