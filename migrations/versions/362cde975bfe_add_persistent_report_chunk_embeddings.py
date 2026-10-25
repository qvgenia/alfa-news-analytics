"""add persistent report chunk embeddings

Revision ID: 362cde975bfe
Revises: 3e7ad7658788
Create Date: 2026-10-25 10:08:03.879534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '362cde975bfe'
down_revision: Union[str, Sequence[str], None] = '3e7ad7658788'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
