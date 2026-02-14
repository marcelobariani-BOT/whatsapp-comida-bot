"""add conversation_state

Revision ID: 41fb75590f24
Revises: c065cfefdf7b
Create Date: 2026-02-14 09:21:03.731159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41fb75590f24'
down_revision: Union[str, Sequence[str], None] = 'c065cfefdf7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
