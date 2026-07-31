"""add UUID defaults to WhatsApp records

Revision ID: 0009_whatsapp_uuid_defaults
Revises: 0008_whatsapp_front_desk
Create Date: 2026-07-18
"""

from alembic import op


revision = "0009_whatsapp_uuid_defaults"
down_revision = "0008_whatsapp_front_desk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE whatsapp_conversations ALTER COLUMN id SET DEFAULT uuid_generate_v4()"
    )
    op.execute(
        "ALTER TABLE whatsapp_messages ALTER COLUMN id SET DEFAULT uuid_generate_v4()"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE whatsapp_messages ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE whatsapp_conversations ALTER COLUMN id DROP DEFAULT")
