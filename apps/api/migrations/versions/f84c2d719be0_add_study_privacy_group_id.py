"""add study privacy group id

Revision ID: f84c2d719be0
Revises: 0c72b5f91a3d
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f84c2d719be0"
down_revision: str | None = (
    "0c72b5f91a3d"
)

branch_labels: (
    str | Sequence[str] | None
) = None

depends_on: (
    str | Sequence[str] | None
) = None


def upgrade() -> None:
    op.add_column(
        "studies",
        sa.Column(
            "privacy_group_id",
            sa.String(length=80),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_studies_privacy_group_id",
        "studies",
        ["privacy_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_studies_privacy_group_id",
        table_name="studies",
    )

    op.drop_column(
        "studies",
        "privacy_group_id",
    )
