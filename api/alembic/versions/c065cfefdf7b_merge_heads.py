"""merge heads

Revision ID: c065cfefdf7b
Revises: fa4d329fc2bc, fbd93f7f7ba2
Create Date: 2026-02-14 08:19:15.972107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c065cfefdf7b'
down_revision: Union[str, Sequence[str], None] = ('fa4d329fc2bc', 'fbd93f7f7ba2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
