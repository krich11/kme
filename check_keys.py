#!/usr/bin/env python3
import asyncio

from sqlalchemy import select

from app.core.database import database_manager
from app.models.sqlalchemy_models import Key


async def check_keys():
    await database_manager.initialize()
    async with database_manager.get_session_context() as session:
        result = await session.execute(select(Key).limit(10))
        print("Keys in database:")
        for k in result.scalars():
            print(
                f"ID: {k.key_id}, Master: {k.master_sae_id}, Slave: {k.slave_sae_id}, Active: {k.is_active}, Consumed: {k.is_consumed}"
            )
    await database_manager.close()


if __name__ == "__main__":
    asyncio.run(check_keys())
