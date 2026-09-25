"""add users auth foundation

Revision ID: 61a4d8ef2c90
Revises: d9f3a8c2b147
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "61a4d8ef2c90"
down_revision: str | None = "d9f3a8c2b147"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "username",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "password_hash",
            sa.String(length=512),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_users",
        ),
        sa.UniqueConstraint(
            "username",
            name="uq_users_username",
        ),
    )

    op.create_index(
        "ix_users_role",
        "users",
        ["role"],
        unique=False,
    )

    op.create_index(
        "ix_users_is_active",
        "users",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_is_active",
        table_name="users",
    )

    op.drop_index(
        "ix_users_role",
        table_name="users",
    )

    op.drop_table(
        "users"
    )
