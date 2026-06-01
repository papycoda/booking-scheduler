"""persistent inspo assets

Revision ID: 0003_persistent_inspo_assets
Revises: 0002_deposits_and_inspo
Create Date: 2026-06-01
"""

from alembic import op

revision = "0003_persistent_inspo_assets"
down_revision = "0002_deposits_and_inspo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE booking_inspo_assets ADD COLUMN IF NOT EXISTS data BYTEA")


def downgrade() -> None:
    op.execute("ALTER TABLE booking_inspo_assets DROP COLUMN IF EXISTS data")
