"""batch lot_size

Revision ID: d4a1b7c92f3e
Revises: c8d3f1a9e210
Create Date: 2026-06-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a1b7c92f3e'
down_revision: Union[str, None] = 'c8d3f1a9e210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('batches', sa.Column('lot_size', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('batches', 'lot_size')
