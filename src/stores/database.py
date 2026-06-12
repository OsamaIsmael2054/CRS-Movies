import asyncpg

from src.helpers.config import settings


async def create_pool(*, min_size: int = 1, max_size: int = 10) -> asyncpg.Pool:
    """Create an asyncpg connection pool against the configured database."""
    return await asyncpg.create_pool(
        dsn=settings.database_url, min_size=min_size, max_size=max_size
    )


async def connect() -> asyncpg.Connection:
    """Open a single connection (used by one-shot scripts like the loader)."""
    return await asyncpg.connect(dsn=settings.database_url)
