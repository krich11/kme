#!/usr/bin/env python3
"""
KME Database Connection Module

Version: 1.0.0
Author: KME Development Team
Description: Database connection and session management for KME
License: [To be determined]

ToDo List:
- [x] Create database connection module
- [x] Add async PostgreSQL support
- [x] Add connection pooling
- [x] Add session management
- [x] Add database initialization
- [x] Add connection health checks
- [x] Add error handling
- [ ] Add database migration support
- [ ] Add backup/restore functionality
- [ ] Add performance optimization
- [ ] Add connection monitoring
- [ ] Add query optimization
- [ ] Add transaction management
- [ ] Add database testing
- [ ] Add connection pooling tuning
- [ ] Add database security features

Progress: 50% (7/15 tasks completed)
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import QueuePool

from .config import settings
from .logging import logger


class DatabaseManager:
    """Database connection manager for KME"""

    def __init__(self):
        """Initialize database manager"""
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker | None = None
        self._connection_pool = None
        self._is_initialized = False

    async def initialize(self) -> bool:
        """Initialize database connection"""
        try:
            logger.info(
                "Initializing database connection",
                database_url=settings.database_url.split("@")[0] + "@***",
            )

            # Create async engine with connection pooling
            self.engine = create_async_engine(
                settings.database_url,
                echo=settings.database_echo,  # Enable SQL logging based on config
                poolclass=QueuePool,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_pre_ping=settings.database_pool_pre_ping,  # Verify connections before use
                pool_recycle=settings.database_pool_recycle,  # Recycle connections
                pool_timeout=settings.database_pool_timeout,  # Connection timeout
                connect_args={
                    "server_settings": {
                        "application_name": "kme_app",
                        "timezone": "UTC",
                    }
                },
            )

            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )

            # Test connection
            await self._test_connection()

            self._is_initialized = True
            logger.info("Database connection initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize database connection", error=str(e))
            return False

    async def _test_connection(self) -> bool:
        """Test database connection"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error("Database connection test failed", error=str(e))
            raise

    async def get_session(self) -> AsyncSession:
        """Get database session"""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.session_factory()

    @asynccontextmanager
    async def get_session_context(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with context manager"""
        session = await self.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def health_check(self) -> dict[str, Any]:
        """Perform database health check"""
        try:
            if not self._is_initialized:
                return {
                    "status": "unhealthy",
                    "message": "Database not initialized",
                    "details": {"error": "Database manager not initialized"},
                }

            # Test connection
            async with self.get_session_context() as session:
                result = await session.execute(text("SELECT 1 as test"))
                result.fetchone()

                # Get connection pool info
                pool_info = {
                    "pool_size": self.engine.pool.size(),
                    "checked_in": self.engine.pool.checkedin(),
                    "checked_out": self.engine.pool.checkedout(),
                    "overflow": self.engine.pool.overflow(),
                    "invalid": self.engine.pool.invalid(),
                }

                return {
                    "status": "healthy",
                    "message": "Database connection is operational",
                    "details": {
                        "pool_info": pool_info,
                        "database_url": settings.database_url.split("@")[0] + "@***",
                        "pool_size": settings.database_pool_size,
                        "max_overflow": settings.database_max_overflow,
                    },
                }

        except OperationalError as e:
            return {
                "status": "unhealthy",
                "message": "Database connection failed",
                "details": {"error": str(e)},
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": "Database health check failed",
                "details": {"error": str(e)},
            }

    async def close(self):
        """Close database connections"""
        try:
            if self.engine:
                await self.engine.dispose()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error("Error closing database connections", error=str(e))

    async def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Execute a raw SQL query"""
        try:
            async with self.get_session_context() as session:
                result = await session.execute(text(query), params or {})
                return result
        except Exception as e:
            logger.error("Query execution failed", query=query, error=str(e))
            raise

    async def get_database_info(self) -> dict[str, Any]:
        """Get database information"""
        try:
            async with self.get_session_context() as session:
                # Get PostgreSQL version
                version_result = await session.execute(text("SELECT version()"))
                version = version_result.scalar()

                # Get database size
                size_result = await session.execute(
                    text(
                        """
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """
                    )
                )
                size = size_result.scalar()

                # Get table count
                table_count_result = await session.execute(
                    text(
                        """
                    SELECT count(*) FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
                    )
                )
                table_count = table_count_result.scalar()

                # Get connection info
                connection_info_result = await session.execute(
                    text(
                        """
                    SELECT
                        count(*) as active_connections,
                        state,
                        application_name
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    GROUP BY state, application_name
                """
                    )
                )
                connection_info = [
                    dict(row) for row in connection_info_result.fetchall()
                ]

                return {
                    "version": version,
                    "database_size": size,
                    "table_count": table_count,
                    "connection_info": connection_info,
                    "pool_info": {
                        "pool_size": self.engine.pool.size(),
                        "checked_in": self.engine.pool.checkedin(),
                        "checked_out": self.engine.pool.checkedout(),
                        "overflow": self.engine.pool.overflow(),
                        "invalid": self.engine.pool.invalid(),
                    }
                    if self.engine
                    else None,
                }

        except Exception as e:
            logger.error("Failed to get database info", error=str(e))
            return {"error": str(e)}

    async def cleanup_expired_connections(self):
        """Clean up expired database connections"""
        try:
            if self.engine:
                # This will trigger connection cleanup
                await self.engine.dispose()
                logger.info("Expired connections cleaned up")
        except Exception as e:
            logger.error("Failed to cleanup expired connections", error=str(e))


# Global database manager instance
database_manager = DatabaseManager()


async def get_database_session() -> AsyncSession:
    """Get database session (dependency injection)"""
    return await database_manager.get_session()


async def initialize_database() -> bool:
    """Initialize database connection"""
    return await database_manager.initialize()


async def close_database():
    """Close database connections"""
    await database_manager.close()


async def get_database_health() -> dict[str, Any]:
    """Get database health status"""
    return await database_manager.health_check()


async def get_database_info() -> dict[str, Any]:
    """Get database information"""
    return await database_manager.get_database_info()


# Database event handlers
async def on_startup():
    """Database startup event handler"""
    logger.info("Starting database initialization")
    success = await initialize_database()
    if success:
        logger.info("Database initialization completed successfully")
    else:
        logger.error("Database initialization failed")
        raise RuntimeError("Database initialization failed")


async def on_shutdown():
    """Database shutdown event handler"""
    logger.info("Closing database connections")
    await close_database()
    logger.info("Database connections closed")


# Database utilities
class DatabaseUtils:
    """Database utility functions"""

    @staticmethod
    async def execute_transaction(queries: list, params: list | None = None) -> bool:
        """Execute multiple queries in a transaction"""
        try:
            async with database_manager.get_session_context() as session:
                for i, query in enumerate(queries):
                    query_params = params[i] if params and i < len(params) else {}
                    await session.execute(text(query), query_params)
                return True
        except Exception as e:
            logger.error("Transaction execution failed", error=str(e))
            return False

    @staticmethod
    async def backup_database(backup_path: str) -> bool:
        """Backup database (placeholder for future implementation)"""
        logger.info("Database backup requested", backup_path=backup_path)
        # TODO: Implement database backup functionality
        return True

    @staticmethod
    async def restore_database(backup_path: str) -> bool:
        """Restore database (placeholder for future implementation)"""
        logger.info("Database restore requested", backup_path=backup_path)
        # TODO: Implement database restore functionality
        return True

    @staticmethod
    async def optimize_database() -> bool:
        """Optimize database (placeholder for future implementation)"""
        logger.info("Database optimization requested")
        # TODO: Implement database optimization (VACUUM, ANALYZE, etc.)
        return True
