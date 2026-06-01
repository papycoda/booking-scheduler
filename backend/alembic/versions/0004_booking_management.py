"""booking management tokens and reschedule requests

Revision ID: 0004_booking_management
Revises: 0003_persistent_inspo_assets
Create Date: 2026-06-01
"""

from alembic import op

revision = "0004_booking_management"
down_revision = "0003_persistent_inspo_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS manage_token_hash VARCHAR(128)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bookings_manage_token_hash ON bookings (manage_token_hash)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_reschedule_requests (
            id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY,
            booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            requested_staff_id UUID NOT NULL REFERENCES staff(id) ON DELETE RESTRICT,
            requested_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
            requested_end_time TIMESTAMP WITH TIME ZONE NOT NULL,
            status VARCHAR(20) DEFAULT 'pending' NOT NULL,
            hold_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            client_note TEXT,
            decision_note TEXT,
            decided_at TIMESTAMP WITH TIME ZONE,
            decided_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            CONSTRAINT valid_reschedule_request_time CHECK (requested_end_time > requested_start_time),
            CONSTRAINT ck_booking_reschedule_requests_status CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_booking_reschedule_requests_booking_id ON booking_reschedule_requests (booking_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_booking_reschedule_requests_tenant_id ON booking_reschedule_requests (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_booking_reschedule_requests_status ON booking_reschedule_requests (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_booking_reschedule_requests_hold "
        "ON booking_reschedule_requests (tenant_id, requested_staff_id, requested_start_time, hold_expires_at)"
    )
    op.execute('ALTER TABLE "booking_reschedule_requests" ENABLE ROW LEVEL SECURITY')
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = current_schema()
                  AND tablename = 'booking_reschedule_requests'
                  AND policyname = 'tenant_isolation_booking_reschedule_requests'
            ) THEN
                CREATE POLICY tenant_isolation_booking_reschedule_requests
                ON "booking_reschedule_requests"
                FOR ALL
                USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
                WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS tenant_isolation_booking_reschedule_requests ON "booking_reschedule_requests"')
    op.execute('ALTER TABLE "booking_reschedule_requests" DISABLE ROW LEVEL SECURITY')
    op.drop_index("idx_booking_reschedule_requests_hold", table_name="booking_reschedule_requests")
    op.drop_index("idx_booking_reschedule_requests_status", table_name="booking_reschedule_requests")
    op.drop_index("idx_booking_reschedule_requests_tenant_id", table_name="booking_reschedule_requests")
    op.drop_index("idx_booking_reschedule_requests_booking_id", table_name="booking_reschedule_requests")
    op.drop_table("booking_reschedule_requests")
    op.drop_index("idx_bookings_manage_token_hash", table_name="bookings")
    op.drop_column("bookings", "manage_token_hash")
