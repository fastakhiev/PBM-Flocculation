"""add model shear rate

Revision ID: b4c8d2a19e61
Revises: 7a2e4f9c1d30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c8d2a19e61"
down_revision: Union[str, Sequence[str], None] = "7a2e4f9c1d30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("optimized", sa.Column("model_g", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("optimized", "model_g")
