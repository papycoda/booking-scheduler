"""automated payout states and retry metadata

Revision ID: 0006_automated_payouts
Revises: 0005_marketplace_payments
Create Date: 2026-06-03
"""

from alembic import op

revision = "0006_automated_payouts"
down_revision = "0005_marketplace_payments"
branch_labels = None
depends_on = None


def _drop_constraint(table: str, name: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")


def _create_check_constraint_if_missing(table: str, name: str, expression: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = '{table}'::regclass
                  AND conname = '{name}'
            ) THEN
                ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression});
            END IF;
        END $$
        """
    )


def upgrade() -> None:
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS payout_bank_name VARCHAR(100)")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payout_attempt_count INTEGER DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS last_payout_attempt_at TIMESTAMPTZ")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS next_payout_attempt_at TIMESTAMPTZ")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS last_payout_error TEXT")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payout_review_reason VARCHAR(100)")

    _drop_constraint("bookings", "ck_bookings_status")
    _create_check_constraint_if_missing(
        "bookings",
        "ck_bookings_status",
        "status IN ('pending_payment', 'confirmed', 'completed', 'cancelled', 'no_show', 'expired')",
    )
    op.execute("ALTER TABLE bookings DROP CONSTRAINT IF EXISTS unique_staff_slot")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS unique_active_staff_slot "
        "ON bookings (tenant_id, staff_id, start_time) "
        "WHERE status IN ('pending_payment', 'confirmed')"
    )

    _drop_constraint("payments", "ck_payments_status")
    _create_check_constraint_if_missing(
        "payments",
        "ck_payments_status",
        "status IN ('pending', 'success', 'failed', 'refunded', 'expired')",
    )

    _drop_constraint("payments", "ck_payments_settlement_status")
    _create_check_constraint_if_missing(
        "payments",
        "ck_payments_settlement_status",
        "settlement_status IN ('not_due', 'needs_setup', 'needs_review', 'queued', 'processing', 'pending', 'paid', 'failed')",
    )


def downgrade() -> None:
    _drop_constraint("payments", "ck_payments_settlement_status")
    _create_check_constraint_if_missing("payments", "ck_payments_settlement_status", "settlement_status IN ('not_due', 'pending', 'paid', 'failed')")
    _drop_constraint("payments", "ck_payments_status")
    _create_check_constraint_if_missing("payments", "ck_payments_status", "status IN ('pending', 'success', 'failed', 'refunded')")
    _drop_constraint("bookings", "ck_bookings_status")
    _create_check_constraint_if_missing("bookings", "ck_bookings_status", "status IN ('pending_payment', 'confirmed', 'completed', 'cancelled', 'no_show')")
    op.execute("DROP INDEX IF EXISTS unique_active_staff_slot")
    op.execute("ALTER TABLE bookings ADD CONSTRAINT unique_staff_slot UNIQUE (tenant_id, staff_id, start_time)")

    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS payout_review_reason")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS last_payout_error")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS next_payout_attempt_at")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS last_payout_attempt_at")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS payout_attempt_count")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS payout_bank_name")
