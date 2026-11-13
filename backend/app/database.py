from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import MetaData, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import settings

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)


engine = create_async_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
    connect_args=settings.asyncpg_connect_args,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def _session_info(session: AsyncSession) -> dict | None:
    info = getattr(session, "info", None)
    if isinstance(info, dict):
        return info
    return None


async def _set_transaction_setting(session: AsyncSession, name: str, value: str) -> None:
    await session.execute(text("SELECT set_config(:name, :value, true)"), {"name": name, "value": value})


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    info = _session_info(session)
    if info is not None:
        info["tenant_id"] = str(tenant_id)
        info["rls_bypass"] = "off"
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
    await _set_transaction_setting(session, "app.rls_bypass", "off")


@asynccontextmanager
async def suspend_row_security(session: AsyncSession) -> AsyncGenerator[None, None]:
    """Allow a trusted path to read across businesses, then restore isolation."""
    info = _session_info(session)
    previous = "off"
    if info is not None:
        previous = str(info.get("rls_bypass", "off"))
        info["rls_bypass"] = "on"
    if isinstance(session, AsyncSession):
        await _set_transaction_setting(session, "app.rls_bypass", "on")
    try:
        yield
    finally:
        if info is not None:
            info["rls_bypass"] = previous
        if isinstance(session, AsyncSession):
            await _set_transaction_setting(session, "app.rls_bypass", previous)


@event.listens_for(Session, "after_begin")
def _apply_rls_on_begin(session: Session, _transaction, connection) -> None:
    bypass = str(session.info.get("rls_bypass", "off"))
    connection.execute(text("SELECT set_config('app.rls_bypass', :bypass, true)"), {"bypass": bypass})
    tenant_id = session.info.get("tenant_id")
    if tenant_id:
        connection.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
