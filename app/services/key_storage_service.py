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
import os
import secrets
import uuid
from typing import Any, Dict, List, Optional, Tuple

import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etsi_models import Key
from app.models.sqlalchemy_models import Key as KeyModel

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
        # Generate 32 bytes of random data
        key_material = secrets.token_bytes(32)
        # Encode as base64 for storage
        return base64.urlsafe_b64encode(key_material)

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
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        if self._master_key is None:
            raise RuntimeError("Master key not initialized")
        purpose_bytes = purpose.encode("utf-8")
        return kdf.derive(self._master_key + purpose_bytes)

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
        if not key_id or not uuid.UUID(key_id):
            raise ValueError("key_id must be a valid UUID")

        if not key_data:
            raise ValueError("key_data cannot be empty")

        if not master_sae_id or len(master_sae_id) != 16:
            raise ValueError("master_sae_id must be exactly 16 characters")

        if not slave_sae_id or len(slave_sae_id) != 16:
            raise ValueError("slave_sae_id must be exactly 16 characters")

        try:
            # Generate salt for this key
            salt = secrets.token_bytes(16)

            # Encrypt the key data
            if self._fernet is None:
                raise RuntimeError("Fernet cipher not initialized")
            encrypted_key_data = self._fernet.encrypt(key_data)

            # Create key hash for integrity verification
            key_hash = hashlib.sha256(key_data).hexdigest()

            # Set default expiration if not provided (24 hours from now)
            if not expires_at:
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=24)

            # Create key model instance
            key_model = KeyModel(
                key_id=key_id,
                encrypted_key_data=encrypted_key_data,
                key_hash=key_hash,
                salt=salt,
                master_sae_id=master_sae_id,
                slave_sae_id=slave_sae_id,
                key_size=key_size,
                created_at=datetime.datetime.utcnow(),
                expires_at=expires_at,
                key_metadata=key_metadata or {},
                is_active=True,
            )

            # Store in database
            self.db_session.add(key_model)
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
        Retrieve a key with authorization check

        Args:
            key_id: UUID of the key to retrieve
            requesting_sae_id: SAE ID requesting the key
            master_sae_id: SAE ID of the master SAE (for validation)

        Returns:
            Key: ETSI-compliant Key object if authorized, None otherwise

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
        if not key_id or not uuid.UUID(key_id):
            raise ValueError("key_id must be a valid UUID")

        if not requesting_sae_id or len(requesting_sae_id) != 16:
            raise ValueError("requesting_sae_id must be exactly 16 characters")

        try:
            # Query for the key
            query = select(KeyModel).where(
                and_(
                    KeyModel.key_id == key_id,
                    KeyModel.is_active.is_(True),
                )
            )

            result = await self.db_session.execute(query)
            key_model = result.scalar_one_or_none()

            if not key_model:
                self.logger.warning(
                    "Key not found",
                    key_id=key_id,
                )
                return None

            # Check if key has expired
            if (
                key_model.expires_at
                and key_model.expires_at < datetime.datetime.utcnow()
            ):
                self.logger.warning(
                    "Key has expired",
                    key_id=key_id,
                    expires_at=key_model.expires_at.isoformat(),
                )
                return None

            # Check authorization
            if not self._is_authorized_to_access_key(
                key_model, requesting_sae_id, master_sae_id
            ):
                self.logger.warning(
                    "Unauthorized key access attempt",
                    key_id=key_id,
                    requesting_sae_id=requesting_sae_id,
                    master_sae_id=master_sae_id,
                )
                return None

            # Decrypt the key data
            if self._fernet is None:
                raise RuntimeError("Fernet cipher not initialized")
            try:
                decrypted_key_data = self._fernet.decrypt(
                    bytes(key_model.encrypted_key_data)
                )
            except Exception as e:
                self.logger.error(
                    "Failed to decrypt key data",
                    key_id=key_id,
                    error=str(e),
                )
                raise RuntimeError(f"Key decryption failed: {e}")

            # Verify key integrity
            if hashlib.sha256(decrypted_key_data).hexdigest() != key_model.key_hash:
                self.logger.error(
                    "Key integrity check failed",
                    key_id=key_id,
                )
                raise RuntimeError("Key integrity verification failed")

            # Create ETSI-compliant Key object
            key = Key(
                key_ID=key_id,
                key=base64.b64encode(decrypted_key_data).decode("utf-8"),
                key_ID_extension=None,
                key_extension=None,
                key_size=int(key_model.key_size)
                if key_model.key_size is not None
                else None,
                created_at=key_model.created_at,  # type: ignore[arg-type]
                expires_at=key_model.expires_at,  # type: ignore[arg-type]
                source_kme_id=str(key_model.master_sae_id)
                if key_model.master_sae_id is not None
                else None,
                target_kme_id=str(key_model.slave_sae_id)
                if key_model.slave_sae_id is not None
                else None,
                key_metadata=dict(key_model.key_metadata)
                if key_model.key_metadata is not None
                else None,
            )

            self.logger.info(
                "Key retrieved successfully",
                key_id=key_id,
                requesting_sae_id=requesting_sae_id,
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
        key_model: KeyModel,
        requesting_sae_id: str,
        master_sae_id: str | None = None,
    ) -> bool:
        """
        Check if SAE is authorized to access the key

        Args:
            key_model: Key model from database
            requesting_sae_id: SAE ID requesting access
            master_sae_id: SAE ID of the master SAE (for validation)

        Returns:
            bool: True if authorized, False otherwise
        """
        # Master SAE can always access keys it created
        if requesting_sae_id == key_model.master_sae_id:
            return True

        # Slave SAE can access keys if it's the intended recipient
        if requesting_sae_id == key_model.slave_sae_id:
            return True

        # Additional validation if master_sae_id is provided
        if master_sae_id and master_sae_id != key_model.master_sae_id:
            return False

        return False

    async def get_key_pool_status(self) -> dict[str, Any]:
        """
        Get current key pool status

        Returns:
            Dict containing key pool statistics
        """
        try:
            # Count total keys
            total_query = select(KeyModel).where(KeyModel.is_active.is_(True))
            total_result = await self.db_session.execute(total_query)
            total_keys = len(total_result.scalars().all())

            # Count non-expired keys
            now = datetime.datetime.utcnow()
            active_query = select(KeyModel).where(
                and_(
                    KeyModel.is_active.is_(True),
                    KeyModel.expires_at > now,
                )
            )
            active_result = await self.db_session.execute(active_query)
            active_keys = len(active_result.scalars().all())

            # Count expired keys
            expired_query = select(KeyModel).where(
                and_(
                    KeyModel.is_active.is_(True),
                    KeyModel.expires_at <= now,
                )
            )
            expired_result = await self.db_session.execute(expired_query)
            expired_keys = len(expired_result.scalars().all())

            return {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "expired_keys": expired_keys,
                "last_updated": datetime.datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Failed to get key pool status", error=str(e))
            raise RuntimeError(f"Key pool status retrieval failed: {e}")

    async def cleanup_expired_keys(self) -> int:
        """
        Remove expired keys from storage

        Returns:
            int: Number of keys removed
        """
        try:
            now = datetime.datetime.utcnow()

            # Find expired keys
            expired_query = select(KeyModel).where(
                and_(
                    KeyModel.is_active.is_(True),
                    KeyModel.expires_at <= now,
                )
            )
            expired_result = await self.db_session.execute(expired_query)
            expired_keys = expired_result.scalars().all()

            # Mark as inactive (soft delete for audit purposes)
            removed_count = 0
            for key_model in expired_keys:
                key_model.is_active = False  # type: ignore[assignment]
                removed_count += 1

            await self.db_session.commit()

            self.logger.info(
                "Cleaned up expired keys",
                removed_count=removed_count,
            )

            return removed_count

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error("Failed to cleanup expired keys", error=str(e))
            raise RuntimeError(f"Key cleanup failed: {e}")

    async def get_keys_by_sae_id(
        self,
        sae_id: str,
        is_master: bool = False,
        limit: int | None = None,
    ) -> list[Key]:
        """
        Get all keys for a specific SAE

        Args:
            sae_id: SAE ID to query for
            is_master: True if querying for master SAE, False for slave SAE
            limit: Maximum number of keys to return

        Returns:
            List of Key objects
        """
        try:
            if is_master:
                query = select(KeyModel).where(
                    and_(
                        KeyModel.master_sae_id == sae_id,
                        KeyModel.is_active.is_(True),
                    )
                )
            else:
                query = select(KeyModel).where(
                    and_(
                        KeyModel.slave_sae_id == sae_id,
                        KeyModel.is_active.is_(True),
                    )
                )

            if limit:
                query = query.limit(limit)

            result = await self.db_session.execute(query)
            key_models = result.scalars().all()

            keys = []
            for key_model in key_models:
                # Skip expired keys
                if (
                    key_model.expires_at
                    and key_model.expires_at < datetime.datetime.utcnow()
                ):
                    continue

                # Decrypt and create Key object
                if self._fernet is None:
                    raise RuntimeError("Fernet cipher not initialized")
                try:
                    decrypted_key_data = self._fernet.decrypt(
                        bytes(key_model.encrypted_key_data)
                    )
                    key = Key(
                        key_ID=str(key_model.key_id),
                        key=base64.b64encode(decrypted_key_data).decode("utf-8"),
                        key_ID_extension=None,
                        key_extension=None,
                        key_size=int(key_model.key_size)
                        if key_model.key_size is not None
                        else None,
                        created_at=key_model.created_at,  # type: ignore[arg-type]
                        expires_at=key_model.expires_at,  # type: ignore[arg-type]
                        source_kme_id=str(key_model.master_sae_id)
                        if key_model.master_sae_id is not None
                        else None,
                        target_kme_id=str(key_model.slave_sae_id)
                        if key_model.slave_sae_id is not None
                        else None,
                        key_metadata=dict(key_model.key_metadata)
                        if key_model.key_metadata is not None
                        else None,
                    )
                    keys.append(key)
                except Exception as e:
                    self.logger.warning(
                        "Failed to decrypt key during SAE query",
                        key_id=key_model.key_id,
                        error=str(e),
                    )
                    continue

            return keys

        except Exception as e:
            self.logger.error(
                "Failed to get keys by SAE ID",
                sae_id=sae_id,
                is_master=is_master,
                error=str(e),
            )
            raise RuntimeError(f"SAE key query failed: {e}")
