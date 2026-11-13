"""force row level security for the table owner

Revision ID: 0008_force_row_level_security
Revises: 0007_first_payout_review
Create Date: 2026-11-13
"""

from alembic import op

revision = "0008_force_row_level_security"
down_revision = "0007_first_payout_review"
branch_labels = None
depends_on = None

TENANT_TABLES = (
    ("tenants", "id"),
    ("users", "tenant_id"),
    ("staff", "tenant_id"),
    ("services", "tenant_id"),
    ("clients", "tenant_id"),
    ("bookings", "tenant_id"),
    ("booking_reschedule_requests", "tenant_id"),
    ("booking_inspo_assets", "tenant_id"),
    ("payments", "tenant_id"),
    ("availability_schedules", "tenant_id"),
    ("availability_overrides", "tenant_id"),
    ("notification_log", "tenant_id"),
)


def _policy_expression(column: str) -> str:
    return (
        "current_setting('app.rls_bypass', true) = 'on' "
        f"OR {column} = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
    )


def upgrade() -> None:
    for table_name, column in TENANT_TABLES:
        expression = _policy_expression(column)
        op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table_name} ON "{table_name}"')
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table_name}
            ON "{table_name}"
            FOR ALL
            USING ({expression})
            WITH CHECK ({expression})
            """
        )


def downgrade() -> None:
    for table_name, column in reversed(TENANT_TABLES):
        expression = f"{column} = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table_name} ON "{table_name}"')
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table_name}
            ON "{table_name}"
            FOR ALL
            USING ({expression})
            WITH CHECK ({expression})
            """
        )
        op.execute(f'ALTER TABLE "{table_name}" NO FORCE ROW LEVEL SECURITY')
