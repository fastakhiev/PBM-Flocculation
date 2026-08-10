"""add EQMOM initial moments

Revision ID: 7a2e4f9c1d30
Revises: d2be454615d2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a2e4f9c1d30"
down_revision: Union[str, Sequence[str], None] = "d2be454615d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("optimized", sa.Column("moments_json", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("optimized", "moments_json")
