"""link jobs to qc analyses

Revision ID: d9f3a8c2b147
Revises: 4d1aa01d01ab
Create Date: 2026-09-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f3a8c2b147"
down_revision: Union[str, Sequence[str], None] = "4d1aa01d01ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "qc_analysis_id",
            sa.UUID(),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_analysis_jobs_qc_analysis_id"),
        "analysis_jobs",
        ["qc_analysis_id"],
        unique=False,
    )

    op.create_foreign_key(
        op.f(
            "fk_analysis_jobs_qc_analysis_id_qc_analyses"
        ),
        "analysis_jobs",
        "qc_analyses",
        ["qc_analysis_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f(
            "fk_analysis_jobs_qc_analysis_id_qc_analyses"
        ),
        "analysis_jobs",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_analysis_jobs_qc_analysis_id"),
        table_name="analysis_jobs",
    )

    op.drop_column(
        "analysis_jobs",
        "qc_analysis_id",
    )
