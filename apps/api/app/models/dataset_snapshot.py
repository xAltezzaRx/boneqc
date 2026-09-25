from uuid import UUID

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
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


class DatasetSnapshot(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "dataset_snapshots"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "version",
            name=(
                "uq_dataset_snapshots_"
                "name_version"
            ),
        ),
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    version: Mapped[str] = mapped_column(
        String(100),
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

    manifest_fingerprint: Mapped[
        str
    ] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    split_seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    train_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    val_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    test_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    group_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    train_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    val_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    test_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    study_ids: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text(
            "'[]'::jsonb"
        ),
    )

    manifest: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text(
            "'[]'::jsonb"
        ),
    )
