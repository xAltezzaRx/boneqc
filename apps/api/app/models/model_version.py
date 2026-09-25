from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ModelVersionStatus


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_versions"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "version",
            name="uq_model_versions_name_version",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    task: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    status: Mapped[ModelVersionStatus] = mapped_column(
        SAEnum(
            ModelVersionStatus,
            name="model_version_status",
            native_enum=False,
        ),
        nullable=False,
        default=ModelVersionStatus.EXPERIMENTAL,
        index=True,
    )

    git_commit: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    dataset_version: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    weights_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    metrics: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
