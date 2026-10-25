"""merge report chunk migration heads

Revision ID: 73bd97511a49
Revises: 362cde975bfe, 65e7a1d7095c
Create Date: 2026-10-25 10:45:45.787493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73bd97511a49'
down_revision: Union[str, Sequence[str], None] = ('362cde975bfe', '65e7a1d7095c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
