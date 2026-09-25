"""add annotation consensus

Revision ID: b2d7c8e41f90
Revises: f84c2d719be0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b2d7c8e41f90"

down_revision: str | None = (
    "f84c2d719be0"
)

branch_labels: (
    str | Sequence[str] | None
) = None

depends_on: (
    str | Sequence[str] | None
) = None


def upgrade() -> None:
    op.create_table(
        "study_annotation_consensus",
        sa.Column(
            "study_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by_user_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "schema_version",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=(
                "DRAFT"
            ),
        ),
        sa.Column(
            "source_annotation_ids",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
            server_default=sa.text(
                "'[]'::jsonb"
            ),
        ),
        sa.Column(
            "labels",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
            server_default=sa.text(
                "'[]'::jsonb"
            ),
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=True,
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
            ["study_id"],
            ["studies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_index(
        "ix_consensus_study_id",
        "study_annotation_consensus",
        ["study_id"],
    )

    op.create_index(
        "ix_consensus_created_by",
        "study_annotation_consensus",
        ["created_by_user_id"],
    )

    op.create_index(
        "ix_consensus_reviewed_by",
        "study_annotation_consensus",
        ["reviewed_by_user_id"],
    )

    op.create_index(
        "ix_consensus_schema_version",
        "study_annotation_consensus",
        ["schema_version"],
    )

    op.create_index(
        "ix_consensus_status",
        "study_annotation_consensus",
        ["status"],
    )

    op.create_index(
        "uq_consensus_one_approved_per_study",
        "study_annotation_consensus",
        ["study_id"],
        unique=True,
        postgresql_where=sa.text(
            "status = 'APPROVED'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_consensus_one_approved_per_study",
        table_name=(
            "study_annotation_consensus"
        ),
    )

    op.drop_index(
        "ix_consensus_status",
        table_name=(
            "study_annotation_consensus"
        ),
    )

    op.drop_index(
        "ix_consensus_schema_version",
        table_name=(
            "study_annotation_consensus"
        ),
    )

    op.drop_index(
        "ix_consensus_reviewed_by",
        table_name=(
            "study_annotation_consensus"
        ),
    )

    op.drop_index(
        "ix_consensus_created_by",
        table_name=(
            "study_annotation_consensus"
        ),
    )

    op.drop_index(
        "ix_consensus_study_id",
        table_name=(
            "study_annotation_consensus"
        ),
    )

    op.drop_table(
        "study_annotation_consensus"
    )
