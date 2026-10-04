"""add mode column to scans

Revision ID: 9c3e1f7a2b64
Revises: 5b945b868eff
Create Date: 2026-10-01 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9c3e1f7a2b64'
down_revision: str | Sequence[str] | None = '5b945b868eff'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
