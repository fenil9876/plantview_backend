"""batch soft delete

Revision ID: f2c4a8d15b70
Revises: e5b2c8d41a6f
Create Date: 2026-07-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2c4a8d15b70'
down_revision: Union[str, None] = 'e5b2c8d41a6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('batches', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('batches', sa.Column('deleted_by', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_batches_deleted_at'), 'batches', ['deleted_at'])
    op.create_foreign_key(
        'fk_batches_deleted_by_users', 'batches', 'users', ['deleted_by'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_batches_deleted_by_users', 'batches', type_='foreignkey')
    op.drop_index(op.f('ix_batches_deleted_at'), table_name='batches')
    op.drop_column('batches', 'deleted_by')
    op.drop_column('batches', 'deleted_at')
