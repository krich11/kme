#!/usr/bin/env python3
"""
Test Week 9-10 Key Management Implementation

This test verifies that the key storage and pool management
functionality for Weeks 9-10 works correctly.
"""

import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.etsi_models import Key, KeyRequest
from app.models.sqlalchemy_models import Key as KeyModel
from app.services.key_pool_service import KeyPoolService
from app.services.key_service import KeyService
from app.services.key_storage_service import KeyStorageService


class TestWeek910KeyManagement:
    """Test Week 9-10 key management implementation"""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def key_storage_service(self, mock_db_session):
        """Create key storage service instance"""
        return KeyStorageService(mock_db_session)

    @pytest.fixture
    def key_pool_service(self, mock_db_session, key_storage_service):
        """Create key pool service instance"""
        return KeyPoolService(mock_db_session, key_storage_service)

    @pytest.fixture
    def key_service(self, mock_db_session):
        """Create key service instance"""
        return KeyService(mock_db_session)

    def test_key_storage_service_initialization(self, key_storage_service):
        """Test key storage service initialization"""
        assert key_storage_service is not None
        assert key_storage_service.db_session is not None
        assert key_storage_service._fernet is not None

    def test_key_pool_service_initialization(self, key_pool_service):
        """Test key pool service initialization"""
        assert key_pool_service is not None
        assert key_pool_service.db_session is not None
        assert key_pool_service.key_storage_service is not None

    def test_key_service_initialization(self, key_service):
        """Test key service initialization"""
        assert key_service is not None
        assert key_service.db_session is not None
        assert key_service.key_storage_service is not None
        assert key_service.key_pool_service is not None

    @pytest.mark.asyncio
    async def test_key_version_info_retrieval(
        self, key_storage_service, mock_db_session
    ):
        """Test key version information retrieval"""
        # Mock key model
        mock_key_model = MagicMock()
        mock_key_model.key_id = "test-key-id"
        mock_key_model.version = 2
        mock_key_model.created_at = datetime.datetime.utcnow()
        mock_key_model.updated_at = datetime.datetime.utcnow()
        mock_key_model.encryption_version = 1
        mock_key_model.key_format_version = 1

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key_model
        mock_db_session.execute.return_value = mock_result

        # Test version info retrieval
        version_info = await key_storage_service.get_key_version_info("test-key-id")

        assert version_info is not None
        assert version_info["key_id"] == "test-key-id"
        assert version_info["version"] == 2
        assert "created_at" in version_info
        assert "last_updated" in version_info

    @pytest.mark.asyncio
    async def test_key_version_upgrade(self, key_storage_service, mock_db_session):
        """Test key version upgrade functionality"""
        # Mock key model
        mock_key_model = MagicMock()
        mock_key_model.key_id = "test-key-id"
        mock_key_model.encrypted_key_data = b"mock-encrypted-data"

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_key_model
        mock_db_session.execute.return_value = mock_result

        # Mock the Fernet decrypt and encrypt methods
        with patch.object(
            key_storage_service._fernet, "decrypt", return_value=b"decrypted-key-data"
        ):
            with patch.object(
                key_storage_service._fernet,
                "encrypt",
                return_value=b"new-encrypted-data",
            ):
                # Test version upgrade
                success = await key_storage_service.upgrade_key_version(
                    "test-key-id", 3
                )

                assert success is True
                mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_statistics_retrieval(
        self, key_storage_service, mock_db_session
    ):
        """Test cleanup statistics retrieval"""
        # Mock query results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock()] * 5  # 5 keys
        mock_db_session.execute.return_value = mock_result

        # Test cleanup statistics
        stats = await key_storage_service.get_key_cleanup_statistics()

        assert stats is not None
        assert "total_keys" in stats
        assert "expired_keys" in stats
        assert "expiring_soon" in stats
        assert "cleanup_needed" in stats
        assert "last_cleanup_check" in stats

    @pytest.mark.asyncio
    async def test_pool_health_metrics(self, key_pool_service, mock_db_session):
        """Test pool health metrics calculation"""
        # Mock pool status and configuration
        with patch.object(key_pool_service, "get_pool_status") as mock_status:
            with patch.object(
                key_pool_service, "_get_pool_configuration"
            ) as mock_config:
                mock_status.return_value = {
                    "active_keys": 500,
                    "total_keys": 1000,
                }
                mock_config.return_value = {
                    "max_key_count": 1000,
                    "min_key_threshold": 100,
                }

                # Mock rate calculations
                with patch.object(
                    key_pool_service, "_calculate_consumption_rate", return_value=10.5
                ):
                    with patch.object(
                        key_pool_service,
                        "_calculate_generation_rate",
                        return_value=12.0,
                    ):
                        with patch.object(
                            key_pool_service,
                            "_calculate_replenishment_frequency",
                            return_value=6.0,
                        ):
                            # Test health metrics
                            health_metrics = (
                                await key_pool_service.get_pool_health_metrics()
                            )

                            assert health_metrics is not None
                            assert "health_status" in health_metrics
                            assert "availability_ratio" in health_metrics
                            assert "consumption_rate_per_hour" in health_metrics
                            assert "generation_rate_per_hour" in health_metrics
                            assert "recommendations" in health_metrics

    @pytest.mark.asyncio
    async def test_pool_alerting_setup(self, key_pool_service):
        """Test pool alerting system setup"""
        alert_thresholds = {
            "min_keys": 100,
            "max_consumption_rate": 50,
            "health_warning_threshold": 0.5,
        }

        # Test alerting setup
        success = await key_pool_service.setup_pool_alerting(alert_thresholds)

        assert success is True
        assert hasattr(key_pool_service, "_alert_thresholds")

    @pytest.mark.asyncio
    async def test_alert_conditions_check(self, key_pool_service):
        """Test alert conditions checking"""
        # Setup alerting first
        alert_thresholds = {"min_keys": 100, "max_consumption_rate": 50}
        await key_pool_service.setup_pool_alerting(alert_thresholds)

        # Mock pool status and health metrics
        with patch.object(key_pool_service, "get_pool_status") as mock_status:
            with patch.object(
                key_pool_service, "get_pool_health_metrics"
            ) as mock_health:
                mock_status.return_value = {"active_keys": 50}  # Below threshold
                mock_health.return_value = {
                    "health_status": "critical",
                    "consumption_rate_per_hour": 60,  # Above threshold
                }

                # Test alert conditions
                alerts = await key_pool_service.check_alert_conditions()

                assert len(alerts) > 0
                assert any(alert["type"] == "availability" for alert in alerts)
                assert any(alert["type"] == "health" for alert in alerts)

    @pytest.mark.asyncio
    async def test_pool_performance_optimization(self, key_pool_service):
        """Test pool performance optimization"""
        # Mock health metrics
        with patch.object(key_pool_service, "get_pool_health_metrics") as mock_health:
            with patch.object(key_pool_service, "get_pool_status") as mock_status:
                with patch.object(
                    key_pool_service, "_get_pool_configuration"
                ) as mock_config:
                    mock_health.return_value = {
                        "consumption_rate_per_hour": 60,  # High consumption
                        "health_status": "critical",
                    }
                    mock_status.return_value = {"active_keys": 200}
                    mock_config.return_value = {"max_key_count": 1000}

                    # Test performance optimization
                    optimization = await key_pool_service.optimize_pool_performance()

                    assert optimization is not None
                    assert "optimizations_applied" in optimization
                    assert "optimizations" in optimization
                    assert len(optimization["optimizations"]) > 0

    @pytest.mark.asyncio
    async def test_key_service_integration(self, key_service, mock_db_session):
        """Test key service integration with storage and pool services"""
        # Mock key storage and pool services
        with patch.object(
            key_service.key_storage_service, "store_key", return_value=True
        ):
            with patch.object(
                key_service.key_pool_service,
                "check_key_availability",
                return_value=True,
            ):
                # Test key generation and storage
                keys = await key_service._generate_and_store_keys(
                    number=5,
                    size=256,
                    master_sae_id="A1B2C3D4E5F6A7B8",
                    slave_sae_id="C1D2E3F4A5B6C7D8",
                )

                assert len(keys) == 5
                assert all(isinstance(key, Key) for key in keys)
                assert all(key.key_size == 256 for key in keys)

    @pytest.mark.asyncio
    async def test_key_retrieval_integration(self, key_service, mock_db_session):
        """Test key retrieval integration"""
        # Set current context
        key_service._current_requesting_sae_id = "A1B2C3D4E5F6A7B8"
        key_service._current_master_sae_id = "A1B2C3D4E5F6A7B8"

        # Mock key storage service with valid UUID
        mock_key = Key(
            key_ID="550e8400-e29b-41d4-a716-446655440000",  # Valid UUID
            key="dGVzdC1rZXktZGF0YQ==",  # base64 encoded "test-key-data"
            key_size=256,
            created_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        )

        with patch.object(
            key_service.key_storage_service, "retrieve_key", return_value=mock_key
        ):
            # Test key retrieval
            retrieved_keys = await key_service._retrieve_keys_by_ids(
                ["550e8400-e29b-41d4-a716-446655440000"]
            )

            assert len(retrieved_keys) == 1
            assert retrieved_keys[0].key_ID == "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_key_pool_status_integration(self, key_service):
        """Test key pool status integration"""
        # Mock all service methods
        with patch.object(
            key_service.key_pool_service, "get_pool_status"
        ) as mock_status:
            with patch.object(
                key_service.key_pool_service, "get_pool_health_metrics"
            ) as mock_health:
                with patch.object(
                    key_service.key_storage_service, "get_key_cleanup_statistics"
                ) as mock_cleanup:
                    with patch.object(
                        key_service.key_pool_service, "check_alert_conditions"
                    ) as mock_alerts:
                        mock_status.return_value = {
                            "active_keys": 500,
                            "total_keys": 1000,
                        }
                        mock_health.return_value = {"health_status": "healthy"}
                        mock_cleanup.return_value = {
                            "total_keys": 1000,
                            "expired_keys": 0,
                        }
                        mock_alerts.return_value = []

                        # Test pool status integration
                        status = await key_service.get_key_pool_status()

                        assert status is not None
                        assert "pool_status" in status
                        assert "health_metrics" in status
                        assert "cleanup_statistics" in status
                        assert "active_alerts" in status
                        assert "timestamp" in status

    @pytest.mark.asyncio
    async def test_key_management_optimization(self, key_service):
        """Test key management optimization"""
        # Mock all service methods
        with patch.object(
            key_service.key_pool_service, "optimize_pool_performance"
        ) as mock_optimize:
            with patch.object(
                key_service.key_storage_service,
                "schedule_key_cleanup",
                return_value=True,
            ):
                with patch.object(
                    key_service.key_pool_service, "get_pool_health_metrics"
                ) as mock_health:
                    mock_optimize.return_value = {"optimizations_applied": 2}
                    mock_health.return_value = {
                        "recommendations": ["Test recommendation"]
                    }

                    # Test optimization
                    optimization = await key_service.optimize_key_management()

                    assert optimization is not None
                    assert "pool_optimization" in optimization
                    assert "cleanup_scheduled" in optimization
                    assert "recommendations" in optimization

    @pytest.mark.asyncio
    async def test_monitoring_setup(self, key_service):
        """Test monitoring setup"""
        alert_thresholds = {
            "min_keys": 100,
            "max_consumption_rate": 50,
        }

        # Mock all service methods
        with patch.object(
            key_service.key_pool_service, "setup_pool_alerting", return_value=True
        ):
            with patch.object(
                key_service.key_storage_service,
                "schedule_key_cleanup",
                return_value=True,
            ):
                with patch.object(
                    key_service.key_pool_service,
                    "start_automatic_replenishment",
                    return_value=True,
                ):
                    # Test monitoring setup
                    success = await key_service.setup_key_management_monitoring(
                        alert_thresholds
                    )

                    assert success is True


if __name__ == "__main__":
    pytest.main([__file__])
