#!/usr/bin/env python3
"""
Recreate Database Tables

Recreates all database tables using SQLAlchemy models.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import DatabaseManager
from app.models.sqlalchemy_models import Base


async def recreate_tables():
    """Recreate all database tables"""
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Drop all tables first
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        # Create all tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Database tables recreated successfully")
        await db_manager.close()
        return True

    except Exception as e:
        print(f"❌ Failed to recreate database tables: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(recreate_tables())
    sys.exit(0 if success else 1)
