"""deposits and inspo assets

Revision ID: 0002_deposits_and_inspo
Revises: 0001_initial_schema
Create Date: 2026-05-29
"""

from alembic import op

revision = "0002_deposits_and_inspo"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS default_deposit_amount INTEGER DEFAULT 0 NOT NULL")
    _create_check_constraint_if_missing("tenants", "ck_tenants_default_deposit_nonnegative", "default_deposit_amount >= 0")

    op.execute("ALTER TABLE services ADD COLUMN IF NOT EXISTS pricing_mode VARCHAR(20) DEFAULT 'fixed' NOT NULL")
    op.execute("ALTER TABLE services ADD COLUMN IF NOT EXISTS deposit_policy VARCHAR(20) DEFAULT 'tenant_default' NOT NULL")
    op.execute("ALTER TABLE services ADD COLUMN IF NOT EXISTS deposit_amount INTEGER")
    _create_check_constraint_if_missing("services", "ck_services_pricing_mode", "pricing_mode IN ('fixed', 'from', 'consultation')")
    _create_check_constraint_if_missing("services", "ck_services_deposit_policy", "deposit_policy IN ('tenant_default', 'custom', 'disabled')")
    _create_check_constraint_if_missing("services", "ck_services_deposit_amount_nonnegative", "deposit_amount IS NULL OR deposit_amount >= 0")

    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS deposit_amount INTEGER DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS price_status VARCHAR(20) DEFAULT 'fixed' NOT NULL")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS quoted_price INTEGER")
    _create_check_constraint_if_missing("bookings", "ck_bookings_price_status", "price_status IN ('fixed', 'pending_quote', 'quoted')")
    _create_check_constraint_if_missing("bookings", "ck_bookings_deposit_amount_nonnegative", "deposit_amount >= 0")
    _create_check_constraint_if_missing("bookings", "ck_bookings_quoted_price_nonnegative", "quoted_price IS NULL OR quoted_price >= 0")

    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_type VARCHAR(20) DEFAULT 'deposit' NOT NULL")
    _create_check_constraint_if_missing("payments", "ck_payments_payment_type", "payment_type IN ('deposit', 'full')")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_inspo_assets (
            booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            original_filename VARCHAR(255) NOT NULL,
            stored_filename VARCHAR(255) NOT NULL,
            content_type VARCHAR(100) NOT NULL,
            size_bytes INTEGER NOT NULL,
            url VARCHAR(500) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_booking_inspo_assets_booking_id ON booking_inspo_assets (booking_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_booking_inspo_assets_tenant_id ON booking_inspo_assets (tenant_id)")
    op.execute('ALTER TABLE "booking_inspo_assets" ENABLE ROW LEVEL SECURITY')
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = current_schema()
                  AND tablename = 'booking_inspo_assets'
                  AND policyname = 'tenant_isolation_booking_inspo_assets'
            ) THEN
                CREATE POLICY tenant_isolation_booking_inspo_assets
                ON "booking_inspo_assets"
                FOR ALL
                USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
                WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
            END IF;
        END $$;
        """
    )


def _create_check_constraint_if_missing(table_name: str, constraint_name: str, expression: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = '{table_name}'::regclass
                  AND conname = '{constraint_name}'
            ) THEN
                ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} CHECK ({expression});
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS tenant_isolation_booking_inspo_assets ON "booking_inspo_assets"')
    op.execute('ALTER TABLE "booking_inspo_assets" DISABLE ROW LEVEL SECURITY')
    op.drop_index("idx_booking_inspo_assets_tenant_id", table_name="booking_inspo_assets")
    op.drop_index("idx_booking_inspo_assets_booking_id", table_name="booking_inspo_assets")
    op.drop_table("booking_inspo_assets")

    op.drop_constraint("ck_payments_payment_type", "payments", type_="check")
    op.drop_column("payments", "payment_type")

    op.drop_constraint("ck_bookings_quoted_price_nonnegative", "bookings", type_="check")
    op.drop_constraint("ck_bookings_deposit_amount_nonnegative", "bookings", type_="check")
    op.drop_constraint("ck_bookings_price_status", "bookings", type_="check")
    op.drop_column("bookings", "quoted_price")
    op.drop_column("bookings", "price_status")
    op.drop_column("bookings", "deposit_amount")

    op.drop_constraint("ck_services_deposit_amount_nonnegative", "services", type_="check")
    op.drop_constraint("ck_services_deposit_policy", "services", type_="check")
    op.drop_constraint("ck_services_pricing_mode", "services", type_="check")
    op.drop_column("services", "deposit_amount")
    op.drop_column("services", "deposit_policy")
    op.drop_column("services", "pricing_mode")

    op.drop_constraint("ck_tenants_default_deposit_nonnegative", "tenants", type_="check")
    op.drop_column("tenants", "default_deposit_amount")
