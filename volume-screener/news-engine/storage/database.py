"""
Async SQLAlchemy Database Connection Setup.

Uses async SQLAlchemy for FastAPI compatibility.
Supports both SQLite (dev) and PostgreSQL (prod).
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from pathlib import Path

# Import config for centralized database URL
try:
    from config import config
    DATABASE_URL = config.database.database_url
    # Convert sqlite:/// to sqlite+aiosqlite:///
    if DATABASE_URL.startswith("sqlite:///"):
        DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
except ImportError:
    # Fallback if config not available
    DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "news_v4.db"
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"

print(f"📁 Database: {DATABASE_URL}")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("NEWS_ENGINE_DEBUG", "false").lower() == "true",
    future=True,
)

# Async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get async database session.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database - create all tables.
    Call this on application startup.
    """
    async with engine.begin() as conn:
        # Import models to register them with Base
        from . import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")


async def close_db() -> None:
    """
    Close database connections.
    Call this on application shutdown.
    """
    await engine.dispose()
    print("🔒 Database connections closed")
