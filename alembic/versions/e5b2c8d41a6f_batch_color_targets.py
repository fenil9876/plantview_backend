"""batch color targets (lot-level color split)

Revision ID: e5b2c8d41a6f
Revises: d4a1b7c92f3e
Create Date: 2026-06-11 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b2c8d41a6f'
down_revision: Union[str, None] = 'd4a1b7c92f3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'batch_color_targets',
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('color_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ['batch_id'], ['batches.id'],
            name=op.f('fk_batch_color_targets_batch_id_batches'), ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['color_id'], ['colors.id'],
            name=op.f('fk_batch_color_targets_color_id_colors'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('batch_id', 'color_id', name=op.f('pk_batch_color_targets')),
    )


def downgrade() -> None:
    op.drop_table('batch_color_targets')
