"""
PostgreSQL database connection management using asyncpg.
"""
import logging
from typing import Optional
import asyncpg

from config.settings import Settings

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database connection manager with connection pooling."""

    def __init__(self, database_url: str, min_size: int = 2, max_size: int = 10):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection string
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create database connection pool."""
        if self._pool is not None:
            logger.warning("Database pool already exists")
            return

        try:
            logger.info(f"Creating database connection pool (min={self.min_size}, max={self.max_size})...")
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=60
            )
            logger.info("Database connection pool created successfully")

            # Test connection
            async with self._pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Connected to: {version[:50]}...")

        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self._pool is None:
            logger.warning("No database pool to close")
            return

        try:
            logger.info("Closing database connection pool...")
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
            raise

    @property
    def pool(self) -> asyncpg.Pool:
        """
        Get the connection pool.

        Returns:
            AsyncPG connection pool

        Raises:
            RuntimeError: If pool is not initialized
        """
        if self._pool is None:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        return self._pool

    async def execute(self, query: str, *args) -> str:
        """
        Execute a query without returning results.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Query execution status
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """
        Execute a query and fetch all results.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            List of records
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Execute a query and fetch one result.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Single record or None
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """
        Execute a query and fetch a single value.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Single value
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database instance
_db: Optional[Database] = None


def get_database() -> Database:
    """
    Get or create the global database instance.

    Returns:
        Database instance

    Raises:
        RuntimeError: If database is not initialized
    """
    global _db
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


def init_database(settings: Settings) -> Database:
    """
    Initialize the global database instance.

    Args:
        settings: Application settings

    Returns:
        Initialized database instance
    """
    global _db
    _db = Database(
        database_url=settings.database_url,
        min_size=settings.database_min_pool_size,
        max_size=settings.database_max_pool_size
    )
    return _db


async def close_database() -> None:
    """Close the global database instance."""
    global _db
    if _db is not None:
        await _db.disconnect()
        _db = None
