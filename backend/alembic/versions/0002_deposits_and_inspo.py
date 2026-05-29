"""deposits and inspo assets

Revision ID: 0002_deposits_and_inspo
Revises: 0001_initial_schema
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_deposits_and_inspo"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("default_deposit_amount", sa.Integer(), server_default="0", nullable=False))
    op.create_check_constraint("ck_tenants_default_deposit_nonnegative", "tenants", "default_deposit_amount >= 0")

    op.add_column("services", sa.Column("pricing_mode", sa.String(length=20), server_default="fixed", nullable=False))
    op.add_column("services", sa.Column("deposit_policy", sa.String(length=20), server_default="tenant_default", nullable=False))
    op.add_column("services", sa.Column("deposit_amount", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_services_pricing_mode", "services", "pricing_mode IN ('fixed', 'from', 'consultation')")
    op.create_check_constraint("ck_services_deposit_policy", "services", "deposit_policy IN ('tenant_default', 'custom', 'disabled')")
    op.create_check_constraint("ck_services_deposit_amount_nonnegative", "services", "deposit_amount IS NULL OR deposit_amount >= 0")

    op.add_column("bookings", sa.Column("deposit_amount", sa.Integer(), server_default="0", nullable=False))
    op.add_column("bookings", sa.Column("price_status", sa.String(length=20), server_default="fixed", nullable=False))
    op.add_column("bookings", sa.Column("quoted_price", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_bookings_price_status", "bookings", "price_status IN ('fixed', 'pending_quote', 'quoted')")
    op.create_check_constraint("ck_bookings_deposit_amount_nonnegative", "bookings", "deposit_amount >= 0")
    op.create_check_constraint("ck_bookings_quoted_price_nonnegative", "bookings", "quoted_price IS NULL OR quoted_price >= 0")

    op.add_column("payments", sa.Column("payment_type", sa.String(length=20), server_default="deposit", nullable=False))
    op.create_check_constraint("ck_payments_payment_type", "payments", "payment_type IN ('deposit', 'full')")

    op.create_table(
        "booking_inspo_assets",
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], name="fk_booking_inspo_assets_booking_id_bookings", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_booking_inspo_assets_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_booking_inspo_assets"),
    )
    op.create_index("idx_booking_inspo_assets_booking_id", "booking_inspo_assets", ["booking_id"], unique=False)
    op.create_index("idx_booking_inspo_assets_tenant_id", "booking_inspo_assets", ["tenant_id"], unique=False)
    op.execute('ALTER TABLE "booking_inspo_assets" ENABLE ROW LEVEL SECURITY')
    op.execute(
        '''
        CREATE POLICY tenant_isolation_booking_inspo_assets
        ON "booking_inspo_assets"
        FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        '''
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
