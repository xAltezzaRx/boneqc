from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AnalysisJobStatus


class AnalysisJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_jobs"

    study_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    qc_analysis_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("qc_analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[AnalysisJobStatus] = mapped_column(
        SAEnum(
            AnalysisJobStatus,
            name="analysis_job_status",
            native_enum=False,
        ),
        nullable=False,
        default=AnalysisJobStatus.QUEUED,
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
