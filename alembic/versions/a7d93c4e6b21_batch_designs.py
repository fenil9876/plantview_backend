"""batch designs (lot-level design pick-list, no quantity)

Revision ID: a7d93c4e6b21
Revises: f2c4a8d15b70
Create Date: 2026-07-20 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d93c4e6b21'
down_revision: Union[str, None] = 'f2c4a8d15b70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'batch_designs',
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('design_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['design_id'], ['designs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('batch_id', 'design_id'),
    )


def downgrade() -> None:
    op.drop_table('batch_designs')
