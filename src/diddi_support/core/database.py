from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from diddi_support.core.config import settings

engine = (
    create_async_engine(settings.database_url, pool_pre_ping=True)
    if settings.database_url
    else None
)
session_factory = async_sessionmaker(engine, expire_on_commit=False) if engine else None


async def get_session_optional() -> AsyncIterator[AsyncSession | None]:
    if session_factory is None:
        yield None
        return
    async with session_factory() as session:
        yield session
