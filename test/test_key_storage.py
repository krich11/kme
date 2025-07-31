#!/usr/bin/env python3
"""
Test Key Storage Service - ETSI QKD 014 V1.1.1 Compliance

Tests the key storage and retrieval functionality according to ETSI specifications
"""

import asyncio
import datetime
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etsi_models import Key
from app.services.key_storage_service import KeyStorageService


class TestKeyStorageService:
    """Test cases for KeyStorageService"""

    @pytest.fixture
    async def mock_db_session(self):
        """Create a mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        # Create a mock result object that properly handles async operations
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock()

        # Create a mock scalars result that properly handles async operations
        mock_scalars_result = MagicMock()
        mock_scalars_result.all = AsyncMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars_result)

        # Configure the execute method to return the mock result
        session.execute = AsyncMock(return_value=mock_result)

        return session

    @pytest.fixture
    def key_storage_service(self, mock_db_session):
        """Create a KeyStorageService instance with mock dependencies"""
        # Generate a proper Fernet key for testing
        import base64
        import secrets

        test_key_material = secrets.token_bytes(32)
        test_key_b64 = base64.urlsafe_b64encode(test_key_material).decode("utf-8")

        # Mock the environment variable for master key
        os.environ["KME_MASTER_KEY"] = test_key_b64

        service = KeyStorageService(mock_db_session)
        return service

    @pytest.fixture
    def sample_key_data(self):
        """Sample key data for testing"""
        return {
            "key_id": str(uuid.uuid4()),
            "key_data": b"test_key_data_32_bytes_long_for_testing",
            "master_sae_id": "MASTERSAE1234567",
            "slave_sae_id": "SLAVESAE12345678",
            "key_size": 256,
            "expires_at": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            "metadata": {"test": "metadata"},
        }

    async def test_initialize_encryption(self, key_storage_service):
        """Test encryption initialization"""
        assert key_storage_service._master_key is not None
        assert key_storage_service._fernet is not None

    async def test_store_key_success(
        self, key_storage_service, sample_key_data, mock_db_session
    ):
        """Test successful key storage"""
        # Mock the database query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await key_storage_service.store_key(
            key_id=sample_key_data["key_id"],
            key_data=sample_key_data["key_data"],
            master_sae_id=sample_key_data["master_sae_id"],
            slave_sae_id=sample_key_data["slave_sae_id"],
            key_size=sample_key_data["key_size"],
            expires_at=sample_key_data["expires_at"],
            key_metadata=sample_key_data["metadata"],
        )

        assert result is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    async def test_store_key_invalid_parameters(self, key_storage_service):
        """Test key storage with invalid parameters"""
        # Test invalid key_id
        with pytest.raises(ValueError, match="key_id must be a valid UUID"):
            await key_storage_service.store_key(
                key_id="invalid-uuid",
                key_data=b"test_data",
                master_sae_id="MASTERSAE1234567",
                slave_sae_id="SLAVESAE12345678",
                key_size=256,
            )

        # Test empty key_data
        with pytest.raises(ValueError, match="key_data cannot be empty"):
            await key_storage_service.store_key(
                key_id=str(uuid.uuid4()),
                key_data=b"",
                master_sae_id="MASTERSAE1234567",
                slave_sae_id="SLAVESAE12345678",
                key_size=256,
            )

        # Test invalid master_sae_id length
        with pytest.raises(
            ValueError, match="master_sae_id must be exactly 16 characters"
        ):
            await key_storage_service.store_key(
                key_id=str(uuid.uuid4()),
                key_data=b"test_data",
                master_sae_id="TOOSHORT",
                slave_sae_id="SLAVESAE12345678",
                key_size=256,
            )

        # Test invalid slave_sae_id length
        with pytest.raises(
            ValueError, match="slave_sae_id must be exactly 16 characters"
        ):
            await key_storage_service.store_key(
                key_id=str(uuid.uuid4()),
                key_data=b"test_data",
                master_sae_id="MASTERSAE1234567",
                slave_sae_id="TOOSHORT",
                key_size=256,
            )

    async def test_retrieve_key_success(
        self, key_storage_service, sample_key_data, mock_db_session
    ):
        """Test successful key retrieval"""
        # Create a mock key model
        mock_key_model = MagicMock()
        mock_key_model.key_id = sample_key_data["key_id"]
        mock_key_model.encrypted_key_data = key_storage_service._fernet.encrypt(
            sample_key_data["key_data"]
        )
        # Calculate the correct hash for the key data
        import hashlib

        mock_key_model.key_hash = hashlib.sha256(
            sample_key_data["key_data"]
        ).hexdigest()
        mock_key_model.master_sae_id = sample_key_data["master_sae_id"]
        mock_key_model.slave_sae_id = sample_key_data["slave_sae_id"]
        mock_key_model.expires_at = sample_key_data["expires_at"]
        mock_key_model.is_active = True

        # Mock the database query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            mock_key_model
        )

        result = await key_storage_service.retrieve_key(
            key_id=sample_key_data["key_id"],
            requesting_sae_id=sample_key_data["master_sae_id"],
            master_sae_id=sample_key_data["master_sae_id"],
        )

        assert result is not None
        assert isinstance(result, Key)
        assert result.key_ID == sample_key_data["key_id"]

    async def test_retrieve_key_not_found(self, key_storage_service, mock_db_session):
        """Test key retrieval when key is not found"""
        # Mock the database query to return None
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await key_storage_service.retrieve_key(
            key_id=str(uuid.uuid4()),
            requesting_sae_id="MASTERSAE1234567",
            master_sae_id="MASTERSAE1234567",
        )

        assert result is None

    async def test_retrieve_key_expired(
        self, key_storage_service, sample_key_data, mock_db_session
    ):
        """Test key retrieval when key has expired"""
        # Create a mock key model with expired timestamp
        mock_key_model = MagicMock()
        mock_key_model.key_id = sample_key_data["key_id"]
        mock_key_model.expires_at = datetime.datetime.utcnow() - datetime.timedelta(
            hours=1
        )
        mock_key_model.is_active = True

        # Mock the database query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            mock_key_model
        )

        result = await key_storage_service.retrieve_key(
            key_id=sample_key_data["key_id"],
            requesting_sae_id=sample_key_data["master_sae_id"],
            master_sae_id=sample_key_data["master_sae_id"],
        )

        assert result is None

    async def test_retrieve_key_unauthorized(
        self, key_storage_service, sample_key_data, mock_db_session
    ):
        """Test key retrieval when SAE is not authorized"""
        # Create a mock key model
        mock_key_model = MagicMock()
        mock_key_model.key_id = sample_key_data["key_id"]
        mock_key_model.master_sae_id = "DIFFERENTSAE1234"
        mock_key_model.slave_sae_id = "SLAVESAE12345678"
        mock_key_model.expires_at = sample_key_data["expires_at"]
        mock_key_model.is_active = True

        # Mock the database query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            mock_key_model
        )

        result = await key_storage_service.retrieve_key(
            key_id=sample_key_data["key_id"],
            requesting_sae_id="UNAUTHORIZED1234",
            master_sae_id=sample_key_data["master_sae_id"],
        )

        assert result is None

    async def test_get_key_pool_status(self, key_storage_service, mock_db_session):
        """Test key pool status retrieval"""
        # Mock the database query results
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [
            1,
            2,
            3,
        ]  # 3 keys

        result = await key_storage_service.get_key_pool_status()

        assert "total_keys" in result
        assert "active_keys" in result
        assert "expired_keys" in result
        assert "last_updated" in result

    async def test_cleanup_expired_keys(self, key_storage_service, mock_db_session):
        """Test expired key cleanup"""
        # Mock expired keys
        mock_expired_key = MagicMock()
        mock_expired_key.is_active = True

        mock_db_session.execute.return_value.scalars.return_value.all.return_value = [
            mock_expired_key
        ]

        result = await key_storage_service.cleanup_expired_keys()

        assert result == 1
        mock_db_session.commit.assert_called_once()

    async def test_authorization_logic(self, key_storage_service):
        """Test key access authorization logic"""
        # Create a mock key model
        mock_key_model = MagicMock()
        mock_key_model.master_sae_id = "MASTERSAE1234567"
        mock_key_model.slave_sae_id = "SLAVESAE12345678"

        # Test master SAE access (should be authorized)
        assert (
            key_storage_service._is_authorized_to_access_key(
                mock_key_model, "MASTERSAE1234567", "MASTERSAE1234567"
            )
            is True
        )

        # Test slave SAE access (should be authorized)
        assert (
            key_storage_service._is_authorized_to_access_key(
                mock_key_model, "SLAVESAE12345678", "MASTERSAE1234567"
            )
            is True
        )

        # Test unauthorized SAE access (should not be authorized)
        assert (
            key_storage_service._is_authorized_to_access_key(
                mock_key_model, "UNAUTHORIZED1234", "MASTERSAE1234567"
            )
            is False
        )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
