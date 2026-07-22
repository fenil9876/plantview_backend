"""colours move under designs: batch_design_colors replaces batch_color_targets

Revision ID: c1f7a2e04b93
Revises: a7d93c4e6b21
Create Date: 2026-07-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f7a2e04b93'
down_revision: Union[str, None] = 'a7d93c4e6b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'batch_design_colors',
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('design_id', sa.Integer(), nullable=False),
        sa.Column('color_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ['batch_id', 'design_id'],
            ['batch_designs.batch_id', 'batch_designs.design_id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['color_id'], ['colors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('batch_id', 'design_id', 'color_id'),
    )

    # Carry the old lot-wide colour split onto the lot's lowest-numbered design so
    # the planned totals survive. Splits on lots with no design attached have
    # nowhere to hang and are dropped — those colours stay selectable, they just
    # lose their planned quantity.
    op.execute(
        """
        INSERT INTO batch_design_colors (batch_id, design_id, color_id, quantity)
        SELECT t.batch_id, d.design_id, t.color_id, t.quantity
          FROM batch_color_targets t
          JOIN (SELECT batch_id, MIN(design_id) AS design_id
                  FROM batch_designs
                 GROUP BY batch_id) d ON d.batch_id = t.batch_id
        """
    )

    op.drop_table('batch_color_targets')


def downgrade() -> None:
    op.create_table(
        'batch_color_targets',
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('color_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['color_id'], ['colors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('batch_id', 'color_id'),
    )
    # Roll the per-design colours back up to one row per (batch, colour). The
    # design each colour belonged to is lost, as is any colour with no quantity.
    op.execute(
        """
        INSERT INTO batch_color_targets (batch_id, color_id, quantity)
        SELECT batch_id, color_id, SUM(quantity)
          FROM batch_design_colors
         WHERE quantity IS NOT NULL
         GROUP BY batch_id, color_id
        """
    )
    op.drop_table('batch_design_colors')
