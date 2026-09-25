from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import (
    AnnotationConsensusStatus,
)


class StudyAnnotationConsensus(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = (
        "study_annotation_consensus"
    )

    study_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "studies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    created_by_user_id: Mapped[
        UUID | None
    ] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    reviewed_by_user_id: Mapped[
        UUID | None
    ] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    status: Mapped[
        AnnotationConsensusStatus
    ] = mapped_column(
        SAEnum(
            AnnotationConsensusStatus,
            name=(
                "annotation_consensus_status"
            ),
            native_enum=False,
        ),
        nullable=False,
        default=(
            AnnotationConsensusStatus.DRAFT
        ),
        index=True,
    )

    source_annotation_ids: Mapped[
        list
    ] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text(
            "'[]'::jsonb"
        ),
    )

    labels: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text(
            "'[]'::jsonb"
        ),
    )

    reviewed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
