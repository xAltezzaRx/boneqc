from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import QCAnalysisStatus


class QCAnalysis(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "qc_analyses"

    study_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "studies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[QCAnalysisStatus] = mapped_column(
        SAEnum(
            QCAnalysisStatus,
            name="qc_analysis_status",
            native_enum=False,
        ),
        nullable=False,
        default=QCAnalysisStatus.CREATED,
        index=True,
    )

    decision: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
