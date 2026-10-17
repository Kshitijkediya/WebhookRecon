from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Celery tasks run each job with asyncio.run(), which creates a new event loop
# per task. Pooled asyncpg connections stay tied to the loop that opened them,
# so the worker uses NullPool: every session opens a fresh connection and
# closes it when done.
worker_engine = create_async_engine(settings.database_url, poolclass=NullPool)

WorkerSessionLocal = async_sessionmaker(
    bind=worker_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
