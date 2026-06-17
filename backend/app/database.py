from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from app.config import settings
from app.models.base import Base
# Import all models so they are registered with Base.metadata
from app.models.instance import Instance  # noqa: F401
from app.models.instance_key import InstanceKey  # noqa: F401
from app.models.instance_domain import InstanceDomain  # noqa: F401
from app.models.email import Email  # noqa: F401

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            poolclass=NullPool,
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def init_db(self):
        """Initialize database tables if they don't exist"""
        try:
            logger.info("Initializing database...")

            async with self.engine.begin() as conn:
                # Enable pg_trgm extension for text search
                logger.info("Creating pg_trgm extension if not exists...")
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

                # Create all tables if they don't exist
                logger.info("Creating tables if they don't exist...")
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialization completed successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database instance
db = Database()
