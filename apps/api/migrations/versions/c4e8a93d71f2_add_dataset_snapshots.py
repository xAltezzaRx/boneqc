"""add dataset snapshots

Revision ID: c4e8a93d71f2
Revises: b2d7c8e41f90
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c4e8a93d71f2"

down_revision: str | None = (
    "b2d7c8e41f90"
)

branch_labels: (
    str | Sequence[str] | None
) = None

depends_on: (
    str | Sequence[str] | None
) = None


def upgrade() -> None:
    op.create_table(
        "dataset_snapshots",
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "manifest_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "split_seed",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "train_ratio",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "val_ratio",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "test_ratio",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "sample_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "group_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "train_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "val_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "test_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "study_ids",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
            server_default=sa.text(
                "'[]'::jsonb"
            ),
        ),
        sa.Column(
            "manifest",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
            server_default=sa.text(
                "'[]'::jsonb"
            ),
        ),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=False,
            server_default=sa.text(
                "now()"
            ),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=False,
            server_default=sa.text(
                "now()"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "name",
            "version",
            name=(
                "uq_dataset_snapshots_"
                "name_version"
            ),
        ),
    )

    op.create_index(
        "ix_dataset_snapshots_name",
        "dataset_snapshots",
        ["name"],
    )

    op.create_index(
        "ix_dataset_snapshots_version",
        "dataset_snapshots",
        ["version"],
    )

    op.create_index(
        "ix_dataset_snapshots_created_by",
        "dataset_snapshots",
        ["created_by_user_id"],
    )

    op.create_index(
        "ix_dataset_snapshots_fingerprint",
        "dataset_snapshots",
        ["manifest_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dataset_snapshots_fingerprint",
        table_name="dataset_snapshots",
    )

    op.drop_index(
        "ix_dataset_snapshots_created_by",
        table_name="dataset_snapshots",
    )

    op.drop_index(
        "ix_dataset_snapshots_version",
        table_name="dataset_snapshots",
    )

    op.drop_index(
        "ix_dataset_snapshots_name",
        table_name="dataset_snapshots",
    )

    op.drop_table(
        "dataset_snapshots"
    )
