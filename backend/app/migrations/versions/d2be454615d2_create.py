"""create

Revision ID: d2be454615d2
Revises: 
Create Date: 2025-08-13 12:44:47.868951

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd2be454615d2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "optimized",
        sa.Column("id", postgresql.UUID(as_uuid=True)),
        sa.Column("g", sa.Float(), nullable=False),
        sa.Column("do", sa.Float(), nullable=False),
        sa.Column("cpamm", sa.String(length=512), nullable=False),
        sa.Column("dosage", sa.Integer(), nullable=False),
        sa.Column("amax", sa.Float(), nullable=False),
        sa.Column("b", sa.Float(), nullable=False),
        sa.Column("gama", sa.Float(), nullable=False),
        sa.Column("gof", sa.Float(), nullable=False),
        sa.Column("optimization_time", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("optimized")
