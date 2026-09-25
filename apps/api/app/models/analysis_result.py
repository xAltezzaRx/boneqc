from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AnalysisResultStatus


class AnalysisResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analysis_results"

    study_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    model_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[AnalysisResultStatus] = mapped_column(
        SAEnum(
            AnalysisResultStatus,
            name="analysis_result_status",
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    result_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
