"""merge 2fa and ai enhancements

Revision ID: 0d655842570e
Revises: 5f35b9bff03b, f1a2b3c4d5e6
Create Date: 2026-03-11 15:12:28.422449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d655842570e'
down_revision: Union[str, None] = ('5f35b9bff03b', 'f1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
