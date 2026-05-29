from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import set_tenant_context


async def apply_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    await set_tenant_context(session, tenant_id)
