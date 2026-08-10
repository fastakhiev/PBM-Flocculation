"""add immutable optimization audit records

Revision ID: c6d9e8f2a401
Revises: b4c8d2a19e61
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6d9e8f2a401"
down_revision: Union[str, Sequence[str], None] = "b4c8d2a19e61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("optimized", sa.Column("audit_run_id", sa.String(length=64), nullable=True))
    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("software_version", sa.String(length=64), nullable=False),
        sa.Column("protocol_version", sa.String(length=64), nullable=False),
        sa.Column("algorithm", sa.String(length=128), nullable=False),
        sa.Column("experimental_sha256", sa.String(length=64), nullable=False),
        sa.Column("moments_sha256", sa.String(length=64), nullable=False),
        sa.Column("report_json", sa.String(length=65535), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )


def downgrade() -> None:
    op.drop_table("optimization_runs")
    op.drop_column("optimized", "audit_run_id")
