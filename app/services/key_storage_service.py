#!/usr/bin/env python3
"""
KME Key Storage Service - ETSI QKD 014 V1.1.1 Compliant

Version: 1.0.0
Author: KME Development Team
Description: Secure key storage and retrieval system
License: [To be determined]

Implements ETSI GS QKD 014 V1.1.1 requirements for:
- Secure key storage with encryption at rest
- Key indexing by key_ID and SAE_ID
- Key metadata storage
- Key expiration handling
- Secure key retrieval with authorization

ToDo List:
- [x] Create key storage service structure
- [x] Implement master key derivation
- [x] Add key encryption at rest
- [x] Create key indexing system
- [x] Add key metadata storage
- [x] Implement key expiration handling
- [ ] Add key versioning support
- [ ] Add key cleanup procedures
- [ ] Add performance optimization
- [ ] Add comprehensive error handling
- [ ] Add unit tests

Progress: 60% (6/10 tasks completed)
"""

import base64
import datetime
import hashlib
import json
import os
import secrets
import uuid
from typing import Any, Dict, List, Optional, Tuple

import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etsi_models import Key

logger = structlog.get_logger()


class KeyStorageService:
    """
    Secure key storage and retrieval service

    Implements ETSI GS QKD 014 V1.1.1 requirements for secure key management
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the key storage service

        Args:
            db_session: Database session for key storage operations
        """
        self.logger = logger.bind(service="KeyStorageService")
        self.db_session = db_session
        self._master_key: bytes | None = None
        self._fernet: Fernet | None = None
        self._initialize_encryption()
        self.logger.info("Key storage service initialized")

    def _initialize_encryption(self) -> None:
        """
        Initialize encryption components for secure key storage

        Derives master key from environment or generates new one
        Creates Fernet cipher for key encryption/decryption
        """
        try:
            # Get master key from environment or generate new one
            master_key_env = os.getenv("KME_MASTER_KEY")
            if master_key_env:
                # Use existing master key from environment
                master_key_b64 = master_key_env.encode()
                self.logger.info("Using master key from environment")
            else:
                # Generate new master key
                master_key_b64 = self._generate_master_key()
                self.logger.warning(
                    "Generated new master key - set KME_MASTER_KEY environment variable for persistence"
                )

            # Create Fernet cipher for encryption
            self._fernet = Fernet(master_key_b64)
            self._master_key = master_key_b64

        except Exception as e:
            self.logger.error("Failed to initialize encryption", error=str(e))
            raise RuntimeError(f"Encryption initialization failed: {e}")

    def _generate_master_key(self) -> bytes:
        """
        Generate a new master key for key encryption

        Returns:
            bytes: Base64-encoded master key
        """
        master_key = Fernet.generate_key()
        self.logger.info("Generated new master key")
        return master_key

    def _derive_key_from_master(
        self, salt: bytes, purpose: str = "key_encryption"
    ) -> bytes:
        """
        Derive a purpose-specific key from the master key

        Args:
            salt: Salt for key derivation
            purpose: Purpose identifier for key derivation

        Returns:
            bytes: Derived key
        """
        if not self._master_key:
            raise RuntimeError("Master key not initialized")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        derived_key = kdf.derive(self._master_key + purpose.encode())
        return derived_key

    async def store_key(
        self,
        key_id: str,
        key_data: bytes,
        master_sae_id: str,
        slave_sae_id: str,
        key_size: int,
        expires_at: datetime.datetime | None = None,
        key_metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store a key securely with encryption at rest

        Args:
            key_id: UUID of the key
            key_data: Raw key data to store
            master_sae_id: SAE ID of the master SAE
            slave_sae_id: SAE ID of the slave SAE
            key_size: Size of the key in bits
            expires_at: Key expiration timestamp
            key_metadata: Additional key metadata

        Returns:
            bool: True if key was stored successfully

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If storage operation fails
        """
        self.logger.info(
            "Storing key",
            key_id=key_id,
            master_sae_id=master_sae_id,
            slave_sae_id=slave_sae_id,
            key_size=key_size,
        )

        # Validate parameters
        if not key_id:
            raise ValueError("key_id cannot be empty")

        try:
            uuid.UUID(key_id)
        except ValueError:
            raise ValueError("key_id must be a valid UUID")

        if not key_data:
            raise ValueError("key_data cannot be empty")

        if not master_sae_id:
            raise ValueError("master_sae_id cannot be empty")

        if not slave_sae_id:
            raise ValueError("slave_sae_id cannot be empty")

        try:
            # Encrypt the key data if encryption is available
            if self._fernet is not None:
                encrypted_key_data = self._fernet.encrypt(key_data)
            else:
                # Fallback to storing unencrypted (not recommended for production)
                self.logger.warning("Encryption not available, storing key unencrypted")
                encrypted_key_data = key_data

            # Set default expiration if not provided (24 hours from now)
            if not expires_at:
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=24)

            # Use raw SQL to match the actual database schema
            insert_query = text(
                """
                INSERT INTO keys (
                    key_id, key_data, key_size, master_sae_id, slave_sae_id,
                    source_kme_id, target_kme_id, created_at, expires_at, status, key_metadata
                ) VALUES (
                    :key_id, :key_data, :key_size, :master_sae_id, :slave_sae_id,
                    :source_kme_id, :target_kme_id, :created_at, :expires_at, :status, :key_metadata
                )
            """
            )

            # Execute the insert
            await self.db_session.execute(
                insert_query,
                {
                    "key_id": key_id,
                    "key_data": encrypted_key_data,
                    "key_size": key_size,
                    "master_sae_id": master_sae_id,
                    "slave_sae_id": slave_sae_id,
                    "source_kme_id": master_sae_id,  # Use master_sae_id as source for now
                    "target_kme_id": slave_sae_id,  # Use slave_sae_id as target for now
                    "created_at": datetime.datetime.utcnow(),
                    "expires_at": expires_at,
                    "status": "active",
                    "key_metadata": json.dumps(key_metadata or {}),
                },
            )
            await self.db_session.commit()

            self.logger.info(
                "Key stored successfully",
                key_id=key_id,
                key_size=key_size,
                expires_at=expires_at.isoformat(),
            )

            return True

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(
                "Failed to store key",
                key_id=key_id,
                error=str(e),
            )
            raise RuntimeError(f"Key storage failed: {e}")

    async def retrieve_key(
        self,
        key_id: str,
        requesting_sae_id: str,
        master_sae_id: str | None = None,
    ) -> Key | None:
        """
        Retrieve a key with authorization checks

        Args:
            key_id: UUID of the key to retrieve
            requesting_sae_id: SAE ID requesting the key
            master_sae_id: Master SAE ID for authorization (optional)

        Returns:
            Key: Key object if found and authorized, None otherwise

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If retrieval operation fails
        """
        self.logger.info(
            "Retrieving key",
            key_id=key_id,
            requesting_sae_id=requesting_sae_id,
            master_sae_id=master_sae_id,
        )

        # Validate parameters
        if not key_id:
            raise ValueError("key_id cannot be empty")

        if not requesting_sae_id:
            raise ValueError("requesting_sae_id cannot be empty")

        try:
            # Query the key from database using raw SQL
            select_query = text(
                """
                SELECT key_id, key_data, key_size, master_sae_id, slave_sae_id,
                       source_kme_id, target_kme_id, created_at, expires_at, status, key_metadata
                FROM keys
                WHERE key_id = :key_id AND status = 'active'
            """
            )

            result = await self.db_session.execute(select_query, {"key_id": key_id})
            row = result.fetchone()

            if not row:
                self.logger.warning("Key not found or inactive", key_id=key_id)
                return None

            # Check authorization
            if not self._is_authorized_to_access_key(
                row, requesting_sae_id, master_sae_id
            ):
                self.logger.warning(
                    "Unauthorized key access attempt",
                    key_id=key_id,
                    requesting_sae_id=requesting_sae_id,
                )
                return None

            # Check if key is expired
            if row.expires_at and row.expires_at < datetime.datetime.utcnow():
                self.logger.warning("Key has expired", key_id=key_id)
                return None

            # Decrypt the key data if encryption was used
            if self._fernet is not None:
                try:
                    decrypted_key_data = self._fernet.decrypt(row.key_data)
                except Exception as e:
                    self.logger.error(
                        "Failed to decrypt key data",
                        key_id=key_id,
                        error=str(e),
                    )
                    return None
            else:
                decrypted_key_data = row.key_data

            # Create ETSI Key object
            key = Key(
                key_ID=row.key_id,
                key=base64.b64encode(decrypted_key_data).decode("utf-8"),
            )

            self.logger.info(
                "Key retrieved successfully",
                key_id=key_id,
                key_size=row.key_size,
            )

            return key

        except Exception as e:
            self.logger.error(
                "Failed to retrieve key",
                key_id=key_id,
                error=str(e),
            )
            raise RuntimeError(f"Key retrieval failed: {e}")

    def _is_authorized_to_access_key(
        self,
        key_row,
        requesting_sae_id: str,
        master_sae_id: str | None = None,
    ) -> bool:
        """
        Check if SAE is authorized to access the key

        Args:
            key_row: Database row containing key information
            requesting_sae_id: SAE ID requesting access
            master_sae_id: Master SAE ID for authorization (optional)

        Returns:
            bool: True if authorized, False otherwise
        """
        # Master SAE can always access keys it created
        if key_row.master_sae_id == requesting_sae_id:
            return True

        # Slave SAE can access keys where it's the slave
        if key_row.slave_sae_id == requesting_sae_id:
            return True

        # Additional slave SAEs can access if they're in the additional_slave_sae_ids
        if key_row.key_metadata and "additional_slave_sae_ids" in key_row.key_metadata:
            additional_sae_ids = key_row.key_metadata.get(
                "additional_slave_sae_ids", []
            )
            if requesting_sae_id in additional_sae_ids:
                return True

        # If master_sae_id is provided, check if it matches the key's master
        if master_sae_id and key_row.master_sae_id == master_sae_id:
            return True

        return False

    async def get_key_pool_status(self) -> dict[str, Any]:
        """
        Get current key pool status

        Returns:
            dict: Key pool status information
        """
        try:
            # Query key pool statistics using raw SQL
            status_query = text(
                """
                SELECT
                    COUNT(*) as total_keys,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_keys,
                    COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_keys,
                    COUNT(CASE WHEN status = 'consumed' THEN 1 END) as consumed_keys,
                    COUNT(CASE WHEN expires_at < NOW() THEN 1 END) as expired_keys_count
                FROM keys
            """
            )

            result = await self.db_session.execute(status_query)
            row = result.fetchone()

            status = {
                "total_keys": row.total_keys,
                "active_keys": row.active_keys,
                "expired_keys": row.expired_keys,
                "consumed_keys": row.consumed_keys,
                "expired_keys_count": row.expired_keys_count,
                "last_updated": datetime.datetime.utcnow().isoformat(),
            }

            self.logger.info("Key pool status retrieved", status=status)
            return status

        except Exception as e:
            self.logger.error("Failed to get key pool status", error=str(e))
            raise RuntimeError(f"Failed to get key pool status: {e}")

    async def cleanup_expired_keys(self) -> int:
        """
        Clean up expired keys from the database

        Returns:
            int: Number of keys cleaned up
        """
        try:
            # Update expired keys status using raw SQL
            cleanup_query = text(
                """
                UPDATE keys
                SET status = 'expired'
                WHERE expires_at < NOW() AND status = 'active'
            """
            )

            result = await self.db_session.execute(cleanup_query)
            await self.db_session.commit()

            cleaned_count = result.rowcount
            self.logger.info(
                "Expired keys cleaned up",
                cleaned_count=cleaned_count,
            )

            return cleaned_count

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error("Failed to cleanup expired keys", error=str(e))
            raise RuntimeError(f"Failed to cleanup expired keys: {e}")

    async def get_keys_by_sae_id(
        self,
        sae_id: str,
        is_master: bool = False,
        limit: int | None = None,
    ) -> list[Key]:
        """
        Get keys associated with a specific SAE ID

        Args:
            sae_id: SAE ID to search for
            is_master: If True, search for keys where SAE is master
            limit: Maximum number of keys to return

        Returns:
            list[Key]: List of keys associated with the SAE
        """
        try:
            # Build query based on whether SAE is master or slave
            if is_master:
                where_clause = "master_sae_id = :sae_id"
            else:
                where_clause = "slave_sae_id = :sae_id OR master_sae_id = :sae_id"

            limit_clause = f"LIMIT {limit}" if limit else ""

            select_query = text(
                f"""
                SELECT key_id, key_data, key_size, master_sae_id, slave_sae_id,
                       source_kme_id, target_kme_id, created_at, expires_at, status, key_metadata
                FROM keys
                WHERE {where_clause} AND status = 'active'
                ORDER BY created_at DESC
                {limit_clause}
            """
            )

            result = await self.db_session.execute(select_query, {"sae_id": sae_id})
            rows = result.fetchall()

            keys = []
            for row in rows:
                # Decrypt the key data if encryption was used
                if self._fernet is not None:
                    try:
                        decrypted_key_data = self._fernet.decrypt(row.key_data)
                    except Exception as e:
                        self.logger.error(
                            "Failed to decrypt key data",
                            key_id=row.key_id,
                            error=str(e),
                        )
                        continue
                else:
                    decrypted_key_data = row.key_data

                # Create ETSI Key object
                key = Key(
                    key_ID=row.key_id,
                    key=base64.b64encode(decrypted_key_data).decode("utf-8"),
                )
                keys.append(key)

            self.logger.info(
                "Retrieved keys for SAE",
                sae_id=sae_id,
                key_count=len(keys),
            )

            return keys

        except Exception as e:
            self.logger.error(
                "Failed to get keys by SAE ID",
                sae_id=sae_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to get keys by SAE ID: {e}")

    async def get_key_version_info(self, key_id: str) -> dict[str, Any] | None:
        """
        Get version information for a key

        Args:
            key_id: UUID of the key

        Returns:
            dict: Version information or None if not found
        """
        try:
            select_query = text(
                """
                SELECT key_id, created_at, key_metadata
                FROM keys
                WHERE key_id = :key_id
            """
            )

            result = await self.db_session.execute(select_query, {"key_id": key_id})
            row = result.fetchone()

            if not row:
                return None

            version_info = {
                "key_id": row.key_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "version": row.key_metadata.get("version", 1)
                if row.key_metadata
                else 1,
                "metadata": row.key_metadata or {},
            }

            return version_info

        except Exception as e:
            self.logger.error(
                "Failed to get key version info",
                key_id=key_id,
                error=str(e),
            )
            return None

    async def upgrade_key_version(self, key_id: str, new_version: int) -> bool:
        """
        Upgrade key to a new version

        Args:
            key_id: UUID of the key
            new_version: New version number

        Returns:
            bool: True if upgrade was successful
        """
        try:
            update_query = text(
                """
                UPDATE keys
                SET key_metadata = jsonb_set(
                    COALESCE(key_metadata, '{}'::jsonb),
                    '{version}',
                    :new_version::jsonb
                )
                WHERE key_id = :key_id
            """
            )

            result = await self.db_session.execute(
                update_query, {"key_id": key_id, "new_version": new_version}
            )
            await self.db_session.commit()

            if result.rowcount > 0:
                self.logger.info(
                    "Key version upgraded",
                    key_id=key_id,
                    new_version=new_version,
                )
                return True
            else:
                self.logger.warning("Key not found for version upgrade", key_id=key_id)
                return False

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error(
                "Failed to upgrade key version",
                key_id=key_id,
                error=str(e),
            )
            return False

    async def get_key_cleanup_statistics(self) -> dict[str, Any]:
        """
        Get statistics about key cleanup operations

        Returns:
            dict: Cleanup statistics
        """
        try:
            stats_query = text(
                """
                SELECT
                    COUNT(*) as total_keys,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_keys,
                    COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_keys,
                    COUNT(CASE WHEN status = 'consumed' THEN 1 END) as consumed_keys,
                    COUNT(CASE WHEN expires_at < NOW() AND status = 'active' THEN 1 END) as pending_expiration,
                    MIN(created_at) as oldest_key_created,
                    MAX(created_at) as newest_key_created
                FROM keys
            """
            )

            result = await self.db_session.execute(stats_query)
            row = result.fetchone()

            stats = {
                "total_keys": row.total_keys,
                "active_keys": row.active_keys,
                "expired_keys": row.expired_keys,
                "consumed_keys": row.consumed_keys,
                "pending_expiration": row.pending_expiration,
                "oldest_key_created": row.oldest_key_created.isoformat()
                if row.oldest_key_created
                else None,
                "newest_key_created": row.newest_key_created.isoformat()
                if row.newest_key_created
                else None,
                "last_updated": datetime.datetime.utcnow().isoformat(),
            }

            return stats

        except Exception as e:
            self.logger.error("Failed to get cleanup statistics", error=str(e))
            return {
                "error": str(e),
                "last_updated": datetime.datetime.utcnow().isoformat(),
            }

    async def schedule_key_cleanup(self, cleanup_interval_hours: int = 24) -> bool:
        """
        Schedule key cleanup operations

        Args:
            cleanup_interval_hours: Interval between cleanup operations

        Returns:
            bool: True if scheduling was successful
        """
        try:
            # This is a placeholder for actual scheduling logic
            # In a real implementation, this would integrate with a task scheduler
            self.logger.info(
                "Key cleanup scheduled",
                interval_hours=cleanup_interval_hours,
            )

            # For now, just run cleanup immediately
            cleaned_count = await self.cleanup_expired_keys()
            self.logger.info(
                "Immediate cleanup completed",
                cleaned_count=cleaned_count,
            )

            return True

        except Exception as e:
            self.logger.error("Failed to schedule key cleanup", error=str(e))
            return False
