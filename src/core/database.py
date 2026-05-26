import asyncpg

from src.core.config import settings

# A single connection pool shared across all requests
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Create the pool once and reuse it for every request."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.DATABASE_URL)
    return _pool


async def get_db():
    """FastAPI dependency – hands a connection from the pool to each request."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
