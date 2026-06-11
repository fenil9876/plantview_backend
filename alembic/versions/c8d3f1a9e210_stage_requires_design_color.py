"""stage requires_design_color

Revision ID: c8d3f1a9e210
Revises: b706a7224c81
Create Date: 2026-06-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d3f1a9e210'
down_revision: Union[str, None] = 'b706a7224c81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'stages',
        sa.Column(
            'requires_design_color',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Existing machine stages already required design + color; preserve that behavior.
    op.execute("UPDATE stages SET requires_design_color = true WHERE has_machines = true")
    # Drop the server default now that all rows are populated; the model controls it going forward.
    op.alter_column('stages', 'requires_design_color', server_default=None)


def downgrade() -> None:
    op.drop_column('stages', 'requires_design_color')
