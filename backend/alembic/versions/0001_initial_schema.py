"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-27
"""

from alembic import op

from app.database import Base
from app.models import *  # noqa: F401,F403 - imports register SQLAlchemy metadata for initial schema

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

TENANT_SCOPED_TABLES = (
    "tenants",
    "users",
    "staff",
    "services",
    "staff_services",
    "clients",
    "bookings",
    "payments",
    "availability_schedules",
    "availability_overrides",
    "notification_log",
)


def _tenant_policy_expression(table_name: str) -> str:
    tenant_setting = "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
    if table_name == "tenants":
        return f"id = {tenant_setting}"
    return f"tenant_id = {tenant_setting}"


def upgrade() -> None:
    bind = op.get_bind()

    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    Base.metadata.create_all(bind=bind)

    for table_name in TENANT_SCOPED_TABLES:
        policy_expression = _tenant_policy_expression(table_name)
        op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
        op.execute(
            f'''
            CREATE POLICY tenant_isolation_{table_name}
            ON "{table_name}"
            FOR ALL
            USING ({policy_expression})
            WITH CHECK ({policy_expression})
            '''
        )


def downgrade() -> None:
    bind = op.get_bind()

    for table_name in reversed(TENANT_SCOPED_TABLES):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table_name} ON "{table_name}"')
        op.execute(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY')

    Base.metadata.drop_all(bind=bind)

    op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
