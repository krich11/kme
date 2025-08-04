#!/usr/bin/env python3
"""
Test SAE Registration Fix
"""

import asyncio
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import after path setup
from app.core.database import database_manager  # noqa: E402
from app.services.status_service import StatusService  # noqa: E402


async def test_sae_registration():
    """Test SAE registration for the specific SAE ID"""
    try:
        # Initialize database
        await database_manager.initialize()

        async with database_manager.get_session_context() as session:
            service = StatusService(session)

            # Test the specific SAE ID
            sae_id = "qnFFr9m6Re3EWs7C"
            result = await service._is_sae_registered(sae_id)

            print(f"SAE {sae_id} registered: {result}")

            if result:
                print("✅ SAE registration fix working!")
            else:
                print("❌ SAE still not registered")

    except Exception as e:
        print(f"❌ Error testing SAE registration: {e}")
    finally:
        await database_manager.close()


if __name__ == "__main__":
    asyncio.run(test_sae_registration())
