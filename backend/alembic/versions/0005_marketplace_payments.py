"""marketplace payment collection and settlement fields

Revision ID: 0005_marketplace_payments
Revises: 0004_booking_management
Create Date: 2026-06-01
"""

from alembic import op

revision = "0005_marketplace_payments"
down_revision = "0004_booking_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS payout_bank_code VARCHAR(20)")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS payout_account_number VARCHAR(20)")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS payout_account_name VARCHAR(255)")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS payout_recipient_code VARCHAR(100)")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS payment_setup_status VARCHAR(20) DEFAULT 'not_started' NOT NULL")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'tenants'::regclass
                  AND conname = 'ck_tenants_payment_setup_status'
            ) THEN
                ALTER TABLE tenants ADD CONSTRAINT ck_tenants_payment_setup_status
                CHECK (payment_setup_status IN ('not_started', 'bank_added', 'split_ready'));
            END IF;
        END $$
        """
    )

    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS provider VARCHAR(30) DEFAULT 'paystack' NOT NULL")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS collection_mode VARCHAR(30) DEFAULT 'platform_collected' NOT NULL")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS platform_fee_amount INTEGER DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS business_net_amount INTEGER DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS settlement_status VARCHAR(20) DEFAULT 'not_due' NOT NULL")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payout_transfer_reference VARCHAR(100)")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payout_transfer_code VARCHAR(100)")
    constraints = {
        "ck_payments_provider": "provider IN ('paystack')",
        "ck_payments_collection_mode": "collection_mode IN ('platform_collected', 'direct_split')",
        "ck_payments_settlement_status": "settlement_status IN ('not_due', 'pending', 'paid', 'failed')",
        "ck_payments_platform_fee_nonnegative": "platform_fee_amount >= 0",
        "ck_payments_business_net_nonnegative": "business_net_amount >= 0",
    }
    for name, expression in constraints.items():
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conrelid = 'payments'::regclass
                      AND conname = '{name}'
                ) THEN
                    ALTER TABLE payments ADD CONSTRAINT {name} CHECK ({expression});
                END IF;
            END $$
            """
        )


def downgrade() -> None:
    for name in (
        "ck_payments_business_net_nonnegative",
        "ck_payments_platform_fee_nonnegative",
        "ck_payments_settlement_status",
        "ck_payments_collection_mode",
        "ck_payments_provider",
    ):
        op.execute(f"ALTER TABLE payments DROP CONSTRAINT IF EXISTS {name}")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS payout_transfer_code")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS payout_transfer_reference")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS settlement_status")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS business_net_amount")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS platform_fee_amount")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS collection_mode")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS provider")
    op.execute("ALTER TABLE tenants DROP CONSTRAINT IF EXISTS ck_tenants_payment_setup_status")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS payment_setup_status")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS payout_recipient_code")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS payout_account_name")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS payout_account_number")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS payout_bank_code")
