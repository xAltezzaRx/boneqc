"""add study annotations

Revision ID: 0c72b5f91a3d
Revises: 61a4d8ef2c90
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0c72b5f91a3d"
down_revision: str | None = (
    "61a4d8ef2c90"
)

branch_labels: (
    str | Sequence[str] | None
) = None

depends_on: (
    str | Sequence[str] | None
) = None


def upgrade() -> None:
    op.create_table(
        "study_annotations",
        sa.Column(
            "study_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "reviewer_user_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "schema_version",
            sa.String(length=32),
            nullable=False,
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
            ["reviewer_user_id"],
            ["users.id"],
            name=(
                "fk_study_annotations_"
                "reviewer_user_id_users"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["study_id"],
            ["studies.id"],
            name=(
                "fk_study_annotations_"
                "study_id_studies"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_study_annotations",
        ),
    )

    op.create_index(
        "ix_study_annotations_study_id",
        "study_annotations",
        ["study_id"],
        unique=False,
    )

    op.create_index(
        "ix_study_annotations_reviewer_user_id",
        "study_annotations",
        ["reviewer_user_id"],
        unique=False,
    )

    op.create_index(
        "ix_study_annotations_schema_version",
        "study_annotations",
        ["schema_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_study_annotations_schema_version",
        table_name="study_annotations",
    )

    op.drop_index(
        "ix_study_annotations_reviewer_user_id",
        table_name="study_annotations",
    )

    op.drop_index(
        "ix_study_annotations_study_id",
        table_name="study_annotations",
    )

    op.drop_table(
        "study_annotations"
    )
