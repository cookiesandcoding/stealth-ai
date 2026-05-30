import asyncpg
import logging
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=settings.DATABASE_URL,
                    min_size=5,
                    max_size=20,
                    max_inactive_connection_lifetime=300.0
                )
                logger.info("Successfully established connection pool to PostgreSQL.")
            except Exception as e:
                logger.error(f"Failed to create PostgreSQL connection pool: {e}")
                raise e

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Closed PostgreSQL connection pool.")

    async def fetch_rows(self, query: str, *args) -> List[Dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Database pool is not connected.")
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, *args)
            return [dict(r) for r in records]

    async def fetch_row(self, query: str, *args) -> Optional[Dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Database pool is not connected.")
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, *args)
            return dict(record) if record else None

    async def execute(self, query: str, *args) -> str:
        if not self.pool:
            raise RuntimeError("Database pool is not connected.")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

db = Database()
