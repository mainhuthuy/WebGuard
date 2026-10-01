"""add mode column to scans

Revision ID: 9c3e1f7a2b64
Revises: 5b945b868eff
Create Date: 2026-10-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c3e1f7a2b64'
down_revision: Union[str, Sequence[str], None] = '5b945b868eff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: scans.mode ('quick' | 'full'), existing rows default to 'full'."""
    with op.batch_alter_table('scans', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('mode', sa.String(length=16), server_default='full', nullable=False)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('scans', schema=None) as batch_op:
        batch_op.drop_column('mode')
