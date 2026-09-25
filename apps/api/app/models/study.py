from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import StudyStatus


class Study(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "studies"

    status: Mapped[StudyStatus] = mapped_column(
        SAEnum(StudyStatus, name="study_status", native_enum=False),
        nullable=False,
        default=StudyStatus.UPLOADED,
        index=True,
    )

    privacy_group_id: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_object_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        unique=True,
    )

    preview_object_key: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    dicom_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
