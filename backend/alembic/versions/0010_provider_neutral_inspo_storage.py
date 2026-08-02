"""provider neutral inspiration image storage

Revision ID: 0010_inspo_storage
Revises: 0009_whatsapp_uuid_defaults
Create Date: 2026-08-02
"""

from alembic import op


revision = "0010_inspo_storage"
down_revision = "0009_whatsapp_uuid_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE booking_inspo_assets ADD COLUMN IF NOT EXISTS storage_provider VARCHAR(30) NOT NULL DEFAULT 'database'")
    op.execute("ALTER TABLE booking_inspo_assets ADD COLUMN IF NOT EXISTS storage_key VARCHAR(500)")
    op.execute("ALTER TABLE booking_inspo_assets ADD COLUMN IF NOT EXISTS storage_format VARCHAR(20)")


def downgrade() -> None:
    op.execute("ALTER TABLE booking_inspo_assets DROP COLUMN IF EXISTS storage_format")
    op.execute("ALTER TABLE booking_inspo_assets DROP COLUMN IF EXISTS storage_key")
    op.execute("ALTER TABLE booking_inspo_assets DROP COLUMN IF EXISTS storage_provider")
