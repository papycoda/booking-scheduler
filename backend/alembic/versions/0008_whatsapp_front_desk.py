"""whatsapp front desk and inbox

Revision ID: 0008_whatsapp_front_desk
Revises: 0007_first_payout_review
Create Date: 2026-07-18
"""

from alembic import op

revision = "0008_whatsapp_front_desk"
down_revision = "0007_first_payout_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR(20)")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS front_desk_intro TEXT")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS front_desk_hours TEXT")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS front_desk_service_areas TEXT")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS front_desk_prep_notes TEXT")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS front_desk_policies TEXT")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS front_desk_escalation_rules TEXT")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tenants_whatsapp_number ON tenants (whatsapp_number)")

    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS checkout_url VARCHAR(500)")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS initialization_error TEXT")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS initialization_attempts INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS last_initialization_attempt_at TIMESTAMPTZ")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS whatsapp_conversations (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            customer_phone VARCHAR(20) NOT NULL,
            customer_name VARCHAR(255),
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            state VARCHAR(50) NOT NULL DEFAULT 'collecting_booking_details',
            summary TEXT,
            booking_context JSONB NOT NULL DEFAULT '{}'::jsonb,
            booking_id UUID REFERENCES bookings(id) ON DELETE SET NULL,
            assigned_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            last_message_at TIMESTAMPTZ,
            last_inbound_at TIMESTAMPTZ,
            last_outbound_at TIMESTAMPTZ,
            closed_reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_whatsapp_conversations_tenant_phone ON whatsapp_conversations (tenant_id, customer_phone)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_whatsapp_conversations_tenant_id ON whatsapp_conversations (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_whatsapp_conversations_last_message_at ON whatsapp_conversations (last_message_at)")
    op.execute("ALTER TABLE whatsapp_conversations ADD CONSTRAINT ck_whatsapp_conversations_status CHECK (status IN ('open', 'human_active', 'closed'))")
    op.execute(
        "ALTER TABLE whatsapp_conversations ADD CONSTRAINT ck_whatsapp_conversations_state CHECK (state IN ('collecting_booking_details', 'awaiting_time_choice', 'awaiting_checkout_email', 'awaiting_atomic_confirmation', 'payment_link_pending', 'handoff_pending', 'human_active', 'closed'))"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            conversation_id UUID NOT NULL REFERENCES whatsapp_conversations(id) ON DELETE CASCADE,
            direction VARCHAR(10) NOT NULL,
            author_type VARCHAR(20) NOT NULL,
            body TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'received',
            provider_message_id VARCHAR(100),
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            sender_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            sent_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_whatsapp_messages_provider_message_id ON whatsapp_messages (provider_message_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_conversation_id ON whatsapp_messages (conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_tenant_id ON whatsapp_messages (tenant_id)")
    op.execute("ALTER TABLE whatsapp_messages ADD CONSTRAINT ck_whatsapp_messages_direction CHECK (direction IN ('inbound', 'outbound'))")
    op.execute("ALTER TABLE whatsapp_messages ADD CONSTRAINT ck_whatsapp_messages_author_type CHECK (author_type IN ('customer', 'assistant', 'owner', 'system'))")
    op.execute("ALTER TABLE whatsapp_messages ADD CONSTRAINT ck_whatsapp_messages_status CHECK (status IN ('queued', 'sent', 'failed', 'received'))")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS whatsapp_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS whatsapp_conversations CASCADE")
    op.execute("DROP INDEX IF EXISTS uq_tenants_whatsapp_number")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS last_initialization_attempt_at")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS initialization_attempts")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS initialization_error")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS checkout_url")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS front_desk_escalation_rules")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS front_desk_policies")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS front_desk_prep_notes")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS front_desk_service_areas")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS front_desk_hours")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS front_desk_intro")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS whatsapp_number")
