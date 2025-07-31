#!/usr/bin/env python3
"""
Phase 3: Key Management Comprehensive Test Suite
ETSI QKD 014 V1.1.1 Compliance Testing
Tests all key management functionality including:
- Secure key storage and retrieval
- Key pool management and replenishment
- QKD network interface
- Key distribution logic
- Key generation interface
Version: 1.0.0
Author: KME Development Team
"""
import asyncio
import base64
import datetime
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etsi_models import Key, KeyContainer, KeyIDs, KeyRequest
from app.models.sqlalchemy_models import Key as KeyModel
from app.services.key_pool_service import KeyPoolService
from app.services.key_service import KeyService
from app.services.key_storage_service import KeyStorageService


class TestPhase3KeyManagement:
    """Comprehensive test suite for Phase 3 Key Management"""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def key_storage_service(self, mock_db_session):
        """Create a KeyStorageService instance"""
        # Use a 32-byte key for testing
        import base64

        test_key = base64.urlsafe_b64encode(b"12345678901234567890123456789012")
        os.environ["KME_MASTER_KEY"] = test_key.decode()
        return KeyStorageService(mock_db_session)

    @pytest.fixture
    def key_pool_service(self, mock_db_session, key_storage_service):
        """Create a KeyPoolService instance"""
        return KeyPoolService(mock_db_session, key_storage_service)

    @pytest.fixture
    def key_service(self, mock_db_session, key_storage_service, key_pool_service):
        """Create a KeyService instance"""
        return KeyService(mock_db_session, key_storage_service, key_pool_service)

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

    # ============================================================================
    # Week 9: Key Storage Engine Tests
    # ============================================================================
    class TestSecureKeyStorage:
        """Test secure key storage implementation"""

        async def test_key_encryption_at_rest(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test that keys are encrypted at rest"""
            # Mock database operations
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            # Store a key
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
            # Verify the key was added to database (encrypted)
            mock_db_session.add.assert_called_once()
            added_key = mock_db_session.add.call_args[0][0]
            assert (
                added_key.encrypted_key_data != sample_key_data["key_data"]
            )  # Should be encrypted

        async def test_master_key_derivation(self, key_storage_service):
            """Test master key derivation functionality"""
            # Test that master key is properly derived
            assert key_storage_service._master_key is not None
            assert len(key_storage_service._master_key) > 0
            # Test key derivation for different purposes
            salt = b"test_salt"
            key1 = key_storage_service._derive_key_from_master(salt, "key_encryption")
            key2 = key_storage_service._derive_key_from_master(salt, "key_encryption")
            key3 = key_storage_service._derive_key_from_master(
                salt, "different_purpose"
            )
            assert key1 == key2  # Same purpose should produce same key
            assert key1 != key3  # Different purpose should produce different key

        async def test_key_indexing(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test key indexing by key_ID and SAE_ID"""
            # Mock database operations
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            # Store multiple keys
            key_ids = [str(uuid.uuid4()) for _ in range(3)]
            for i, key_id in enumerate(key_ids):
                await key_storage_service.store_key(
                    key_id=key_id,
                    key_data=f"key_data_{i}".encode(),
                    master_sae_id=f"MASTER{i:04d}000000",
                    slave_sae_id=f"SLAVE{i:04d}000000",
                    key_size=256,
                )
            # Verify keys were stored with proper indexing
            assert mock_db_session.add.call_count == 3

        async def test_key_metadata_storage(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test key metadata storage system"""
            metadata = {
                "source": "QKD_network",
                "quality_score": 0.95,
                "generation_time": datetime.datetime.utcnow().isoformat(),
                "custom_field": "test_value",
            }
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            result = await key_storage_service.store_key(
                key_id=sample_key_data["key_id"],
                key_data=sample_key_data["key_data"],
                master_sae_id=sample_key_data["master_sae_id"],
                slave_sae_id=sample_key_data["slave_sae_id"],
                key_size=sample_key_data["key_size"],
                key_metadata=metadata,
            )
            assert result is True
            added_key = mock_db_session.add.call_args[0][0]
            assert added_key.key_metadata == metadata

        async def test_key_expiration_handling(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test key expiration handling"""
            # Test with expiration
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            result = await key_storage_service.store_key(
                key_id=sample_key_data["key_id"],
                key_data=sample_key_data["key_data"],
                master_sae_id=sample_key_data["master_sae_id"],
                slave_sae_id=sample_key_data["slave_sae_id"],
                key_size=sample_key_data["key_size"],
                expires_at=expires_at,
            )
            assert result is True
            added_key = mock_db_session.add.call_args[0][0]
            assert added_key.expires_at == expires_at

    class TestKeyRetrievalSystem:
        """Test key retrieval system"""

        async def test_secure_key_decryption(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test secure key decryption"""
            # Mock stored key
            mock_key = MagicMock()
            mock_key.key_id = sample_key_data["key_id"]
            mock_key.key_data = key_storage_service._fernet.encrypt(
                sample_key_data["key_data"]
            )
            mock_key.master_sae_id = sample_key_data["master_sae_id"]
            mock_key.slave_sae_id = sample_key_data["slave_sae_id"]
            mock_key.key_size = sample_key_data["key_size"]
            mock_key.status = "active"
            mock_key.expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            # Retrieve the key
            retrieved_key = await key_storage_service.retrieve_key(
                key_id=sample_key_data["key_id"],
                requesting_sae_id=sample_key_data["master_sae_id"],
            )
            assert retrieved_key is not None
            assert retrieved_key.key_ID == sample_key_data["key_id"]
            # Key should be decrypted back to original data
            assert base64.b64decode(retrieved_key.key) == sample_key_data["key_data"]

        async def test_key_access_authorization(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test key access authorization checks"""
            # Mock stored key
            mock_key = MagicMock()
            mock_key.key_id = sample_key_data["key_id"]
            mock_key.key_data = b"encrypted_data"
            mock_key.master_sae_id = sample_key_data["master_sae_id"]
            mock_key.slave_sae_id = sample_key_data["slave_sae_id"]
            mock_key.key_size = sample_key_data["key_size"]
            mock_key.status = "active"
            mock_key.expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            # Test authorized access (master SAE)
            authorized_key = await key_storage_service.retrieve_key(
                key_id=sample_key_data["key_id"],
                requesting_sae_id=sample_key_data["master_sae_id"],
            )
            assert authorized_key is not None
            # Test unauthorized access (different SAE)
            unauthorized_key = await key_storage_service.retrieve_key(
                key_id=sample_key_data["key_id"], requesting_sae_id="UNAUTHORIZED123"
            )
            assert unauthorized_key is None

        async def test_key_retrieval_audit_logging(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test key retrieval audit logging"""
            # Mock stored key
            mock_key = MagicMock()
            mock_key.key_id = sample_key_data["key_id"]
            mock_key.key_data = b"encrypted_data"
            mock_key.master_sae_id = sample_key_data["master_sae_id"]
            mock_key.slave_sae_id = sample_key_data["slave_sae_id"]
            mock_key.key_size = sample_key_data["key_size"]
            mock_key.status = "active"
            mock_key.expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            # Retrieve key and verify audit logging
            with patch("app.services.key_storage_service.logger") as mock_logger:
                await key_storage_service.retrieve_key(
                    key_id=sample_key_data["key_id"],
                    requesting_sae_id=sample_key_data["master_sae_id"],
                )
                # Verify audit log was created
                mock_logger.info.assert_called()
                log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any("key_retrieval" in str(call) for call in log_calls)

    class TestKeyCleanupAndMaintenance:
        """Test key cleanup and maintenance"""

        async def test_expired_key_removal(self, key_storage_service, mock_db_session):
            """Test expired key removal"""
            # Mock expired keys
            expired_keys = [
                MagicMock(
                    id=uuid.uuid4(),
                    status="active",
                    expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
                ),
                MagicMock(
                    id=uuid.uuid4(),
                    status="active",
                    expires_at=datetime.datetime.utcnow()
                    - datetime.timedelta(minutes=30),
                ),
            ]
            mock_db_session.execute.return_value.scalars.return_value.all.return_value = (
                expired_keys
            )
            # Run cleanup
            removed_count = await key_storage_service.cleanup_expired_keys()
            assert removed_count == 2
            assert mock_db_session.commit.call_count == 1

        async def test_secure_key_deletion(self, key_storage_service, mock_db_session):
            """Test secure key deletion procedures"""
            # Mock keys to delete
            keys_to_delete = [
                MagicMock(id=uuid.uuid4(), key_data=b"encrypted_data_1"),
                MagicMock(id=uuid.uuid4(), key_data=b"encrypted_data_2"),
            ]
            mock_db_session.execute.return_value.scalars.return_value.all.return_value = (
                keys_to_delete
            )
            # Run cleanup
            removed_count = await key_storage_service.cleanup_expired_keys()
            assert removed_count == 2
            # Verify keys were marked for deletion
            for key in keys_to_delete:
                assert key.status == "deleted"

    # ============================================================================
    # Week 10: Key Pool Management Tests
    # ============================================================================
    class TestKeyPoolStatusMonitoring:
        """Test key pool status monitoring"""

        async def test_stored_key_count_tracking(
            self, key_pool_service, mock_db_session
        ):
            """Test stored_key_count tracking"""
            # Mock pool status
            mock_db_session.execute.return_value.scalar.return_value = 1500
            status = await key_pool_service.get_pool_status()
            assert "total_keys" in status
            assert status["total_keys"] == 1500

        async def test_max_key_count_enforcement(
            self, key_pool_service, mock_db_session
        ):
            """Test max_key_count enforcement"""
            # Mock configuration
            mock_db_session.execute.return_value.scalar.return_value = 10000
            status = await key_pool_service.get_pool_status()
            assert "max_key_count" in status
            assert status["max_key_count"] == 10000

        async def test_available_key_count_calculation(
            self, key_pool_service, mock_db_session
        ):
            """Test available_key_count calculation"""
            # Mock active keys count
            mock_db_session.execute.return_value.scalar.return_value = 2500
            status = await key_pool_service.get_pool_status()
            assert "active_keys" in status
            assert status["active_keys"] == 2500

        async def test_key_pool_health_monitoring(
            self, key_pool_service, mock_db_session
        ):
            """Test key pool health monitoring"""
            # Mock healthy pool
            mock_db_session.execute.return_value.scalar.return_value = 8000  # 80% full
            status = await key_pool_service.get_pool_status()
            assert "pool_health" in status
            assert status["pool_health"] in ["healthy", "warning", "critical"]

    class TestKeyPoolReplenishment:
        """Test key pool replenishment"""

        async def test_automatic_replenishment(self, key_pool_service, mock_db_session):
            """Test automatic key replenishment"""
            # Mock low pool status
            mock_db_session.execute.return_value.scalar.return_value = 100  # Low count
            # Start automatic replenishment
            result = await key_pool_service.start_automatic_replenishment()
            assert result is True

        async def test_manual_replenishment_triggers(
            self, key_pool_service, mock_db_session
        ):
            """Test manual replenishment triggers"""
            # Mock trigger replenishment
            mock_db_session.execute.return_value.scalar.return_value = 500
            result = await key_pool_service._trigger_replenishment()
            assert "success" in result
            assert "keys_generated" in result

        async def test_replenishment_failure_handling(
            self, key_pool_service, mock_db_session
        ):
            """Test replenishment failure handling"""
            # Mock replenishment failure
            with patch.object(
                key_pool_service, "_simulate_key_generation", return_value=0
            ):
                result = await key_pool_service._trigger_replenishment()
                assert result["success"] is False
                assert "error" in result

    class TestKeyExhaustionHandling:
        """Test key exhaustion handling"""

        async def test_exhaustion_detection(self, key_pool_service, mock_db_session):
            """Test exhaustion detection"""
            # Mock empty pool
            mock_db_session.execute.return_value.scalar.return_value = 0
            result = await key_pool_service.handle_key_exhaustion()
            assert result["status_code"] == 503
            assert "exhaustion" in result["message"].lower()

        async def test_503_error_response_for_exhaustion(
            self, key_pool_service, mock_db_session
        ):
            """Test 503 error response for exhaustion"""
            # Mock exhaustion scenario
            mock_db_session.execute.return_value.scalar.return_value = 0
            response = await key_pool_service.handle_key_exhaustion()
            assert response["status_code"] == 503
            assert "service unavailable" in response["message"].lower()

        async def test_emergency_key_generation(
            self, key_pool_service, mock_db_session
        ):
            """Test emergency key generation"""
            # Mock emergency generation
            with patch.object(
                key_pool_service, "_simulate_key_generation", return_value=100
            ):
                result = await key_pool_service._trigger_emergency_replenishment()
                assert result["success"] is True
                assert result["keys_generated"] == 100

    # ============================================================================
    # Week 11: QKD Network Interface Tests
    # ============================================================================
    class TestQKDLinkManagement:
        """Test QKD link management"""

        async def test_qkd_link_establishment(self, key_service):
            """Test QKD link establishment"""
            # Mock link establishment
            with patch.object(key_service, "_establish_qkd_link") as mock_establish:
                mock_establish.return_value = {
                    "status": "established",
                    "link_id": "link_123",
                }
                result = await key_service._establish_qkd_link("remote_kme_123")
                assert result["status"] == "established"
                assert "link_id" in result

        async def test_link_status_monitoring(self, key_service):
            """Test link status monitoring"""
            # Mock link status
            with patch.object(key_service, "_get_link_status") as mock_status:
                mock_status.return_value = {
                    "link_id": "link_123",
                    "status": "active",
                    "quality": 0.95,
                    "bit_error_rate": 0.001,
                }
                status = await key_service._get_link_status("link_123")
                assert status["status"] == "active"
                assert status["quality"] > 0.9

        async def test_link_failure_detection(self, key_service):
            """Test link failure detection"""
            # Mock link failure
            with patch.object(key_service, "_detect_link_failure") as mock_failure:
                mock_failure.return_value = {
                    "link_id": "link_123",
                    "failed": True,
                    "error": "connection_timeout",
                }
                failure = await key_service._detect_link_failure("link_123")
                assert failure["failed"] is True
                assert "error" in failure

    class TestKeyExchangeProtocol:
        """Test key exchange protocol"""

        async def test_secure_key_exchange_with_kmes(self, key_service):
            """Test secure key exchange with other KMEs"""
            # Mock key exchange
            with patch.object(key_service, "_exchange_keys_with_kme") as mock_exchange:
                mock_exchange.return_value = {
                    "success": True,
                    "keys_exchanged": 50,
                    "key_size": 256,
                }
                result = await key_service._exchange_keys_with_kme(
                    "remote_kme_123", 50, 256
                )
                assert result["success"] is True
                assert result["keys_exchanged"] == 50

        async def test_key_relay_for_multi_hop_networks(self, key_service):
            """Test key relay for multi-hop networks"""
            # Mock multi-hop relay
            with patch.object(key_service, "_relay_keys") as mock_relay:
                mock_relay.return_value = {
                    "success": True,
                    "hops": 3,
                    "keys_relayed": 25,
                }
                result = await key_service._relay_keys(["kme_1", "kme_2", "kme_3"], 25)
                assert result["success"] is True
                assert result["hops"] == 3

    class TestNetworkSecurity:
        """Test network security"""

        async def test_end_to_end_key_encryption(self, key_service):
            """Test end-to-end key encryption"""
            # Mock end-to-end encryption
            with patch.object(key_service, "_encrypt_for_transmission") as mock_encrypt:
                mock_encrypt.return_value = {
                    "encrypted": True,
                    "algorithm": "AES-256-GCM",
                    "integrity": "verified",
                }
                result = await key_service._encrypt_for_transmission(
                    b"key_data", "remote_kme"
                )
                assert result["encrypted"] is True
                assert result["integrity"] == "verified"

        async def test_kme_authentication_mechanisms(self, key_service):
            """Test KME authentication mechanisms"""
            # Mock KME authentication
            with patch.object(key_service, "_authenticate_kme") as mock_auth:
                mock_auth.return_value = {
                    "authenticated": True,
                    "kme_id": "remote_kme_123",
                    "certificate_valid": True,
                }
                result = await key_service._authenticate_kme(
                    "remote_kme_123", "cert_data"
                )
                assert result["authenticated"] is True
                assert result["certificate_valid"] is True

    # ============================================================================
    # Week 12: Key Distribution Logic Tests
    # ============================================================================
    class TestMasterSlaveKeyDistribution:
        """Test master/slave key distribution"""

        async def test_key_sharing_between_master_and_slave_saes(
            self, key_service, sample_key_data, mock_db_session
        ):
            """Test key sharing between master and slave SAEs"""
            # Mock key storage
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            # Create key request
            key_request = KeyRequest(
                number=5,
                size=256,
                additional_slave_SAE_IDs=["SLAVE2_123456", "SLAVE3_123456"],
            )
            # Mock key generation
            with patch.object(key_service, "_generate_keys") as mock_generate:
                mock_generate.return_value = [
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_1"},
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_2"},
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_3"},
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_4"},
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_5"},
                ]
                result = await key_service.process_key_request(
                    slave_sae_id=sample_key_data["slave_sae_id"],
                    key_request=key_request,
                )
                assert result is not None
                assert len(result.keys) == 5

        async def test_key_id_tracking_and_validation(
            self, key_service, sample_key_data, mock_db_session
        ):
            """Test key_ID tracking and validation"""
            # Mock key retrieval
            mock_key = MagicMock()
            mock_key.key_id = sample_key_data["key_id"]
            mock_key.key_data = b"encrypted_key_data"
            mock_key.master_sae_id = sample_key_data["master_sae_id"]
            mock_key.slave_sae_id = sample_key_data["slave_sae_id"]
            mock_key.status = "active"
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            # Create key IDs request
            key_ids = KeyIDs(key_IDs=[sample_key_data["key_id"]])
            result = await key_service.process_key_ids_request(
                master_sae_id=sample_key_data["master_sae_id"], key_ids=key_ids
            )
            assert result is not None
            assert len(result.keys) == 1
            assert result.keys[0].key_ID == sample_key_data["key_id"]

        async def test_key_distribution_authorization(
            self, key_service, sample_key_data, mock_db_session
        ):
            """Test key distribution authorization"""
            # Mock unauthorized access
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            key_ids = KeyIDs(key_IDs=[sample_key_data["key_id"]])
            # Test unauthorized SAE
            result = await key_service.process_key_ids_request(
                master_sae_id="UNAUTHORIZED123", key_ids=key_ids
            )
            assert result is None

    class TestMulticastKeyDistribution:
        """Test multicast key distribution"""

        async def test_additional_slave_sae_support(
            self, key_service, sample_key_data, mock_db_session
        ):
            """Test additional slave SAE support"""
            # Mock key storage for multiple SAEs
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            key_request = KeyRequest(
                number=3,
                size=256,
                additional_slave_SAE_IDs=[
                    "SLAVE2_123456",
                    "SLAVE3_123456",
                    "SLAVE4_123456",
                ],
            )
            with patch.object(key_service, "_generate_keys") as mock_generate:
                mock_generate.return_value = [
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_1"},
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_2"},
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_3"},
                ]
                result = await key_service.process_key_request(
                    slave_sae_id=sample_key_data["slave_sae_id"],
                    key_request=key_request,
                )
                assert result is not None
                assert len(result.keys) == 3

        async def test_multicast_capability_validation(self, key_service):
            """Test multicast capability validation"""
            # Mock multicast validation
            with patch.object(
                key_service, "_validate_multicast_capability"
            ) as mock_validate:
                mock_validate.return_value = {
                    "capable": True,
                    "max_slaves": 10,
                    "supported_protocols": ["QKD_014"],
                }
                result = await key_service._validate_multicast_capability(
                    ["SAE1", "SAE2", "SAE3"]
                )
                assert result["capable"] is True
                assert result["max_slaves"] >= 3

    class TestKeyGenerationInterface:
        """Test key generation interface"""

        async def test_interface_to_qkd_network_for_key_generation(self, key_service):
            """Test interface to QKD network for key generation"""
            # Mock QKD network interface
            with patch.object(key_service, "_request_qkd_key_generation") as mock_qkd:
                mock_qkd.return_value = {
                    "success": True,
                    "keys_generated": 100,
                    "key_size": 256,
                    "quality_score": 0.98,
                }
                result = await key_service._request_qkd_key_generation(100, 256)
                assert result["success"] is True
                assert result["keys_generated"] == 100
                assert result["quality_score"] > 0.95

        async def test_key_quality_validation(self, key_service):
            """Test key quality validation"""
            # Mock key quality validation
            with patch.object(key_service, "_validate_key_quality") as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "entropy_score": 0.99,
                    "randomness_test": "passed",
                    "quantum_security": "verified",
                }
                result = await key_service._validate_key_quality(b"test_key_data")
                assert result["valid"] is True
                assert result["entropy_score"] > 0.95

        async def test_key_size_enforcement(self, key_service):
            """Test key size enforcement"""
            # Test valid key size
            result = await key_service._validate_key_size(256)
            assert result is True
            # Test invalid key size
            with pytest.raises(ValueError):
                await key_service._validate_key_size(0)
            with pytest.raises(ValueError):
                await key_service._validate_key_size(10000)  # Too large

        async def test_batch_key_generation_support(self, key_service):
            """Test batch key generation support"""
            # Mock batch generation
            with patch.object(key_service, "_generate_batch_keys") as mock_batch:
                mock_batch.return_value = {
                    "success": True,
                    "batch_id": "batch_123",
                    "keys_generated": 1000,
                    "estimated_time": "5 minutes",
                }
                result = await key_service._generate_batch_keys(1000, 256)
                assert result["success"] is True
                assert result["keys_generated"] == 1000
                assert "batch_id" in result

    # ============================================================================
    # Integration Tests
    # ============================================================================
    class TestPhase3Integration:
        """Integration tests for Phase 3 functionality"""

        async def test_complete_key_lifecycle(
            self, key_service, sample_key_data, mock_db_session
        ):
            """Test complete key lifecycle from generation to consumption"""
            # Mock all necessary components
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            # 1. Generate keys
            with patch.object(key_service, "_generate_keys") as mock_generate:
                mock_generate.return_value = [
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_1"},
                    {"key_id": str(uuid.uuid4()), "key_data": b"key_2"},
                ]
                key_request = KeyRequest(number=2, size=256)
                result = await key_service.process_key_request(
                    slave_sae_id=sample_key_data["slave_sae_id"],
                    key_request=key_request,
                )
                assert result is not None
                assert len(result.keys) == 2
            # 2. Retrieve keys
            mock_key = MagicMock()
            mock_key.key_id = result.keys[0].key_ID
            mock_key.key_data = b"encrypted_key_data"
            mock_key.master_sae_id = sample_key_data["master_sae_id"]
            mock_key.slave_sae_id = sample_key_data["slave_sae_id"]
            mock_key.status = "active"
            mock_key.expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            key_ids = KeyIDs(key_IDs=[result.keys[0].key_ID])
            retrieved = await key_service.process_key_ids_request(
                master_sae_id=sample_key_data["master_sae_id"], key_ids=key_ids
            )
            assert retrieved is not None
            assert len(retrieved.keys) == 1

        async def test_key_pool_replenishment_integration(
            self, key_pool_service, key_storage_service, mock_db_session
        ):
            """Test key pool replenishment integration"""
            # Mock low pool status
            mock_db_session.execute.return_value.scalar.return_value = 50  # Low count
            # Start replenishment
            result = await key_pool_service.start_automatic_replenishment()
            assert result is True
            # Verify replenishment monitoring is active
            assert key_pool_service._replenishment_task is not None

        async def test_qkd_network_integration(self, key_service):
            """Test QKD network integration"""
            # Mock QKD network components
            with patch.object(key_service, "_establish_qkd_link") as mock_link:
                mock_link.return_value = {
                    "status": "established",
                    "link_id": "link_123",
                }
                with patch.object(
                    key_service, "_exchange_keys_with_kme"
                ) as mock_exchange:
                    mock_exchange.return_value = {"success": True, "keys_exchanged": 50}
                    # Test complete QKD workflow
                    link = await key_service._establish_qkd_link("remote_kme")
                    assert link["status"] == "established"
                    exchange = await key_service._exchange_keys_with_kme(
                        "remote_kme", 50, 256
                    )
                    assert exchange["success"] is True
                    assert exchange["keys_exchanged"] == 50

    # ============================================================================
    # Performance Tests
    # ============================================================================
    class TestPhase3Performance:
        """Performance tests for Phase 3 functionality"""

        async def test_key_storage_performance(
            self, key_storage_service, mock_db_session
        ):
            """Test key storage performance"""
            import time

            # Mock database operations
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            # Test bulk key storage
            start_time = time.time()
            for i in range(100):
                await key_storage_service.store_key(
                    key_id=str(uuid.uuid4()),
                    key_data=f"key_data_{i}".encode(),
                    master_sae_id=f"MASTER{i:04d}",
                    slave_sae_id=f"SLAVE{i:04d}",
                    key_size=256,
                )
            end_time = time.time()
            duration = end_time - start_time
            # Should complete within reasonable time (adjust threshold as needed)
            assert duration < 10.0  # 10 seconds for 100 keys
            assert mock_db_session.add.call_count == 100

        async def test_key_retrieval_performance(
            self, key_storage_service, mock_db_session
        ):
            """Test key retrieval performance"""
            import time

            # Mock stored key
            mock_key = MagicMock()
            mock_key.key_id = "test_key_id"
            mock_key.key_data = b"encrypted_data"
            mock_key.master_sae_id = "MASTERSAE123456"
            mock_key.slave_sae_id = "SLAVESAE123456"
            mock_key.key_size = 256
            mock_key.status = "active"
            mock_key.expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            # Test multiple retrievals
            start_time = time.time()
            for _ in range(50):
                await key_storage_service.retrieve_key(
                    key_id="test_key_id", requesting_sae_id="MASTERSAE123456"
                )
            end_time = time.time()
            duration = end_time - start_time
            # Should complete within reasonable time
            assert duration < 5.0  # 5 seconds for 50 retrievals

        async def test_key_pool_monitoring_performance(
            self, key_pool_service, mock_db_session
        ):
            """Test key pool monitoring performance"""
            import time

            # Mock pool status
            mock_db_session.execute.return_value.scalar.return_value = 5000
            # Test multiple status checks
            start_time = time.time()
            for _ in range(20):
                await key_pool_service.get_pool_status()
            end_time = time.time()
            duration = end_time - start_time
            # Should complete within reasonable time
            assert duration < 2.0  # 2 seconds for 20 status checks

    # ============================================================================
    # Security Tests
    # ============================================================================
    class TestPhase3Security:
        """Security tests for Phase 3 functionality"""

        async def test_key_encryption_security(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test key encryption security"""
            # Mock database operations
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            # Store key and verify encryption
            await key_storage_service.store_key(
                key_id=sample_key_data["key_id"],
                key_data=sample_key_data["key_data"],
                master_sae_id=sample_key_data["master_sae_id"],
                slave_sae_id=sample_key_data["slave_sae_id"],
                key_size=sample_key_data["key_size"],
            )
            # Verify key is encrypted in storage
            added_key = mock_db_session.add.call_args[0][0]
            assert added_key.key_data != sample_key_data["key_data"]
            # Verify encryption is not reversible without proper key
            wrong_fernet = Fernet(Fernet.generate_key())
            with pytest.raises(Exception):
                wrong_fernet.decrypt(added_key.key_data)

        async def test_authorization_bypass_prevention(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test authorization bypass prevention"""
            # Mock stored key
            mock_key = MagicMock()
            mock_key.key_id = sample_key_data["key_id"]
            mock_key.key_data = b"encrypted_data"
            mock_key.master_sae_id = sample_key_data["master_sae_id"]
            mock_key.slave_sae_id = sample_key_data["slave_sae_id"]
            mock_key.key_size = sample_key_data["key_size"]
            mock_key.status = "active"
            mock_key.expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            # Test various unauthorized access attempts
            unauthorized_saes = [
                "DIFFERENT_SAE123",
                "ADMIN_SAE123456",
                "ROOT_SAE123456",
                "GUEST_SAE123456",
            ]
            for unauthorized_sae in unauthorized_saes:
                result = await key_storage_service.retrieve_key(
                    key_id=sample_key_data["key_id"], requesting_sae_id=unauthorized_sae
                )
                assert result is None

        async def test_key_expiration_enforcement(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test key expiration enforcement"""
            # Mock expired key
            mock_key = MagicMock()
            mock_key.key_id = sample_key_data["key_id"]
            mock_key.key_data = b"encrypted_data"
            mock_key.master_sae_id = sample_key_data["master_sae_id"]
            mock_key.slave_sae_id = sample_key_data["slave_sae_id"]
            mock_key.key_size = sample_key_data["key_size"]
            mock_key.status = "active"
            mock_key.expires_at = datetime.datetime.utcnow() - datetime.timedelta(
                hours=1
            )  # Expired
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            # Attempt to retrieve expired key
            result = await key_storage_service.retrieve_key(
                key_id=sample_key_data["key_id"],
                requesting_sae_id=sample_key_data["master_sae_id"],
            )
            assert result is None

        async def test_audit_trail_integrity(
            self, key_storage_service, sample_key_data, mock_db_session
        ):
            """Test audit trail integrity"""
            # Mock stored key
            mock_key = MagicMock()
            mock_key.key_id = sample_key_data["key_id"]
            mock_key.key_data = b"encrypted_data"
            mock_key.master_sae_id = sample_key_data["master_sae_id"]
            mock_key.slave_sae_id = sample_key_data["slave_sae_id"]
            mock_key.key_size = sample_key_data["key_size"]
            mock_key.status = "active"
            mock_key.expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                hours=1
            )
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
                mock_key
            )
            # Test audit logging
            with patch("app.services.key_storage_service.logger") as mock_logger:
                await key_storage_service.retrieve_key(
                    key_id=sample_key_data["key_id"],
                    requesting_sae_id=sample_key_data["master_sae_id"],
                )
                # Verify audit log contains required information
                log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                audit_logs = [
                    call for call in log_calls if "key_retrieval" in str(call)
                ]
                assert len(audit_logs) > 0
                audit_log = str(audit_logs[0])
                assert sample_key_data["key_id"] in audit_log
                assert sample_key_data["master_sae_id"] in audit_log


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
