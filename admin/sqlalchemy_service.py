#!/usr/bin/env python3
"""
SQLAlchemy Service for KME Admin Tool

Provides SQLAlchemy-based database operations for the admin tool.
"""

import json
import logging

# Import SQLAlchemy models
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402
from app.models.sqlalchemy_models import SAE  # noqa: E402

logger = logging.getLogger(__name__)


class SQLAlchemyService:
    """SQLAlchemy service for admin tool database operations"""

    def __init__(self):
        """Initialize SQLAlchemy service"""
        # Convert postgresql:// to postgresql+asyncpg:// for async operations
        database_url = settings.database_url
        if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_session(self) -> AsyncSession:
        """Get async database session"""
        return self.async_session()

    async def load_saes(self) -> list[dict[str, Any]]:
        """Load all SAEs from database using SQLAlchemy"""
        try:
            async with await self.get_session() as session:
                result = await session.execute(select(SAE).order_by(SAE.sae_id))
                saes = result.scalars().all()

                sae_list = []
                for sae in saes:
                    sae_dict = {
                        "id": str(sae.id),
                        "sae_id": sae.sae_id,
                        "kme_id": sae.kme_id,
                        "certificate_info": {
                            "hash": sae.certificate_hash,
                            "subject": sae.certificate_subject,
                            "issuer": sae.certificate_issuer,
                            "valid_until": sae.certificate_valid_until.isoformat()
                            if sae.certificate_valid_until
                            else None,
                        },
                        "registration_date": sae.registration_date.isoformat(),
                        "last_seen": sae.last_seen.isoformat()
                        if sae.last_seen
                        else None,
                        "status": sae.status,
                        "created_at": sae.created_at.isoformat(),
                        "updated_at": sae.updated_at.isoformat(),
                    }
                    sae_list.append(sae_dict)

                return sae_list
        except Exception as e:
            logger.error(f"Failed to load SAEs from database: {e}")
            return []

    async def add_sae(self, sae_data: dict[str, Any]) -> bool:
        """Add SAE to database using SQLAlchemy"""
        try:
            async with await self.get_session() as session:
                # Create new SAE object
                sae = SAE(
                    id=uuid.uuid4(),
                    sae_id=sae_data["sae_id"],
                    kme_id=sae_data.get("kme_id", settings.kme_id),
                    certificate_hash=sae_data.get("certificate_hash", ""),
                    certificate_subject=sae_data.get("certificate_subject", ""),
                    certificate_issuer=sae_data.get("certificate_issuer", ""),
                    certificate_valid_until=datetime.fromisoformat(
                        sae_data.get("registration_date", datetime.now().isoformat())
                    )
                    if sae_data.get("registration_date")
                    else None,
                    registration_date=datetime.fromisoformat(
                        sae_data.get("registration_date", datetime.now().isoformat())
                    ),
                    last_seen=datetime.now(),
                    status=sae_data.get("status", "active"),
                )

                session.add(sae)
                await session.commit()

                logger.info(f"SAE {sae_data['sae_id']} added to database")
                return True
        except Exception as e:
            logger.error(f"Failed to add SAE to database: {e}")
            return False

    async def get_sae_by_id(self, sae_id: str) -> dict[str, Any] | None:
        """Get SAE by ID from database using SQLAlchemy"""
        try:
            async with await self.get_session() as session:
                result = await session.execute(select(SAE).where(SAE.sae_id == sae_id))
                sae = result.scalar_one_or_none()

                if sae:
                    return {
                        "id": str(sae.id),
                        "sae_id": sae.sae_id,
                        "kme_id": sae.kme_id,
                        "certificate_info": {
                            "hash": sae.certificate_hash,
                            "subject": sae.certificate_subject,
                            "issuer": sae.certificate_issuer,
                            "valid_until": sae.certificate_valid_until.isoformat()
                            if sae.certificate_valid_until
                            else None,
                        },
                        "registration_date": sae.registration_date.isoformat(),
                        "last_seen": sae.last_seen.isoformat()
                        if sae.last_seen
                        else None,
                        "status": sae.status,
                        "created_at": sae.created_at.isoformat(),
                        "updated_at": sae.updated_at.isoformat(),
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get SAE from database: {e}")
            return None

    async def is_sae_registered(self, sae_id: str) -> bool:
        """Check if SAE is registered in database using SQLAlchemy"""
        try:
            async with await self.get_session() as session:
                result = await session.execute(
                    select(SAE).where(SAE.sae_id == sae_id, SAE.status == "active")
                )
                sae = result.scalar_one_or_none()
                return sae is not None
        except Exception as e:
            logger.error(f"Failed to check SAE registration: {e}")
            return False

    async def update_sae_status(self, sae_id: str, new_status: str) -> bool:
        """Update SAE status using SQLAlchemy"""
        try:
            async with await self.get_session() as session:
                result = await session.execute(
                    update(SAE)
                    .where(SAE.sae_id == sae_id)
                    .values(status=new_status, updated_at=datetime.now())
                )
                await session.commit()

                if result.rowcount > 0:
                    logger.info(f"Updated SAE {sae_id} status to {new_status}")
                    return True
                else:
                    logger.warning(f"SAE {sae_id} not found for status update")
                    return False
        except Exception as e:
            logger.error(f"Failed to update SAE status: {e}")
            return False

    async def revoke_sae(self, sae_id: str) -> bool:
        """Revoke SAE using SQLAlchemy"""
        try:
            async with await self.get_session() as session:
                result = await session.execute(
                    update(SAE)
                    .where(SAE.sae_id == sae_id)
                    .values(status="revoked", updated_at=datetime.now())
                )
                await session.commit()

                if result.rowcount > 0:
                    logger.info(f"Revoked SAE {sae_id}")
                    return True
                else:
                    logger.warning(f"SAE {sae_id} not found for revocation")
                    return False
        except Exception as e:
            logger.error(f"Failed to revoke SAE: {e}")
            return False

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()


# Global service instance
_sqlalchemy_service: SQLAlchemyService | None = None


def get_sqlalchemy_service() -> SQLAlchemyService:
    """Get global SQLAlchemy service instance"""
    global _sqlalchemy_service
    if _sqlalchemy_service is None:
        _sqlalchemy_service = SQLAlchemyService()
    return _sqlalchemy_service


async def close_sqlalchemy_service():
    """Close global SQLAlchemy service"""
    global _sqlalchemy_service
    if _sqlalchemy_service:
        await _sqlalchemy_service.close()
        _sqlalchemy_service = None
