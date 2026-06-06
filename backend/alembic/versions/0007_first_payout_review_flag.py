"""add first payout review completed at

Revision ID: 0007_first_payout_review
Revises: 0006_automated_payouts
Create Date: 2024-06-03

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0007_first_payout_review'
down_revision: Union[str, None] = '0006_automated_payouts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS "
        "first_payout_review_completed_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS first_payout_review_completed_at")
