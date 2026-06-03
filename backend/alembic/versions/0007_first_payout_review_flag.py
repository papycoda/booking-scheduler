"""add first payout review completed at

Revision ID: 0007_first_payout_review
Revises: 0006
Create Date: 2024-06-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007_first_payout_review'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column(
        'first_payout_review_completed_at',
        sa.DateTime(timezone=True),
        nullable=True
    ))


def downgrade() -> None:
    op.drop_column('tenants', 'first_payout_review_completed_at')
