#!/usr/bin/env python3
"""
Health Monitoring Tests

Tests for enhanced health monitoring including database, Redis, and QKD network checks.
"""

import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text

from app.core.health import HealthCheck, HealthMonitor, HealthStatus


class TestHealthMonitoring:
    """Test health monitoring functionality"""

    def setup_method(self):
        """Setup test method"""
        self.health_monitor = HealthMonitor()

    @pytest.mark.asyncio
    async def test_basic_system_health_check(self):
        """Test basic system health check"""
        health_check = await self.health_monitor._check_basic_system()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "basic_system"
        assert health_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "python_version" in health_check.details
        assert "platform" in health_check.details

    @pytest.mark.asyncio
    async def test_memory_usage_health_check(self):
        """Test memory usage health check"""
        health_check = await self.health_monitor._check_memory_usage()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "memory_usage"
        assert health_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "usage_percent" in health_check.details
        assert "total_gb" in health_check.details
        assert "available_gb" in health_check.details

    @pytest.mark.asyncio
    async def test_disk_usage_health_check(self):
        """Test disk usage health check"""
        health_check = await self.health_monitor._check_disk_usage()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "disk_usage"
        assert health_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "usage_percent" in health_check.details
        assert "total_gb" in health_check.details
        assert "free_gb" in health_check.details

    @pytest.mark.asyncio
    async def test_cpu_usage_health_check(self):
        """Test CPU usage health check"""
        health_check = await self.health_monitor._check_cpu_usage()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "cpu_usage"
        assert health_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "usage_percent" in health_check.details
        assert "cpu_count" in health_check.details

    @pytest.mark.asyncio
    async def test_network_connectivity_health_check(self):
        """Test network connectivity health check"""
        health_check = await self.health_monitor._check_network_connectivity()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "network_connectivity"
        assert health_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "bytes_sent" in health_check.details
        assert "bytes_recv" in health_check.details

    @pytest.mark.asyncio
    @patch("app.core.database.database_manager")
    async def test_database_health_check_success(self, mock_db_manager):
        """Test successful database health check"""
        # Mock database session and results
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [1]  # SELECT 1 result
        mock_session.execute.return_value = mock_result

        mock_db_manager.get_session_context.return_value.__aenter__.return_value = (
            mock_session
        )
        mock_db_manager.engine.pool.size.return_value = 10
        mock_db_manager.engine.pool.checkedin.return_value = 8
        mock_db_manager.engine.pool.checkedout.return_value = 2
        mock_db_manager.engine.pool.overflow.return_value = 0

        # Mock table check
        mock_table_result = MagicMock()
        mock_table_result.fetchall.return_value = [
            ["sae_entities"],
            ["keys"],
            ["key_requests"],
        ]
        mock_session.execute.side_effect = [
            mock_result,  # SELECT 1
            MagicMock(fetchone=lambda: ["PostgreSQL 15.1"]),  # version()
            mock_table_result,  # table check
        ]

        health_check = await self.health_monitor._check_database_health()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "database_health"
        assert health_check.status == HealthStatus.HEALTHY
        assert "database_version" in health_check.details
        assert "response_time_ms" in health_check.details
        assert "tables_found" in health_check.details
        assert len(health_check.details["tables_found"]) == 3

    @pytest.mark.asyncio
    @patch("app.core.database.database_manager")
    async def test_database_health_check_failure(self, mock_db_manager):
        """Test database health check failure"""
        # Mock database connection failure
        mock_db_manager.get_session_context.side_effect = Exception(
            "Database connection failed"
        )

        health_check = await self.health_monitor._check_database_health()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "database_health"
        assert health_check.status == HealthStatus.UNHEALTHY
        assert "error" in health_check.details
        assert "Database connection failed" in health_check.message

    @pytest.mark.asyncio
    @patch("redis.asyncio.from_url")
    async def test_redis_health_check_success(self, mock_redis_from_url):
        """Test successful Redis health check"""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.set.return_value = True
        mock_client.get.return_value = "health_check_value"
        mock_client.delete.return_value = 1
        mock_client.info.return_value = {
            "redis_version": "7.0.0",
            "connected_clients": 5,
            "used_memory_human": "1.2M",
            "uptime_in_seconds": 3600,
        }
        mock_client.close.return_value = None

        mock_redis_from_url.return_value = mock_client

        with patch("app.core.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.redis_pool_size = 10
            mock_get_settings.return_value = mock_settings

            health_check = await self.health_monitor._check_redis_health()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "redis_health"
        assert health_check.status == HealthStatus.HEALTHY
        assert "redis_version" in health_check.details
        assert "response_time_ms" in health_check.details
        assert "operations_tested" in health_check.details

    @pytest.mark.asyncio
    @patch("redis.asyncio.from_url")
    async def test_redis_health_check_failure(self, mock_redis_from_url):
        """Test Redis health check failure"""
        # Mock Redis connection failure
        mock_redis_from_url.side_effect = Exception("Redis connection failed")

        with patch("app.core.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.redis_pool_size = 10
            mock_get_settings.return_value = mock_settings

            health_check = await self.health_monitor._check_redis_health()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "redis_health"
        assert health_check.status == HealthStatus.UNHEALTHY
        assert "error" in health_check.details
        assert "Redis connection failed" in health_check.message

    @pytest.mark.asyncio
    @patch("app.services.key_generation_service.get_key_generator")
    async def test_qkd_network_health_check_success(self, mock_get_generator):
        """Test successful QKD network health check"""
        # Mock key generator
        mock_generator = AsyncMock()
        mock_generator.__class__.__name__ = "QKDKeyGenerator"
        mock_generator.get_system_status.return_value = {
            "qkd_connected": True,
            "qkd_network_url": "qkd://localhost:8080",
        }
        mock_generator.generate_keys.return_value = [b"test_key_data"]
        mock_generator.get_generation_metrics.return_value = {
            "key_generation_rate": 1000,
            "last_generation_time": datetime.datetime.utcnow(),
            "total_keys_generated": 5000,
        }

        mock_get_generator.return_value = mock_generator

        with patch("app.core.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.qkd_links = ["link1", "link2"]
            mock_settings.qkd_key_generation_rate = 1000
            mock_get_settings.return_value = mock_settings

            health_check = await self.health_monitor._check_qkd_network_health()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "qkd_network_health"
        assert health_check.status == HealthStatus.HEALTHY
        assert "generator_type" in health_check.details
        assert "qkd_connected" in health_check.details
        assert "key_generation_working" in health_check.details

    @pytest.mark.asyncio
    @patch("app.services.key_generation_service.get_key_generator")
    async def test_qkd_network_health_check_mock_generator(self, mock_get_generator):
        """Test QKD network health check with mock generator"""
        # Mock key generator (mock generator indicates no real QKD hardware)
        mock_generator = AsyncMock()
        mock_generator.__class__.__name__ = "MockKeyGenerator"
        mock_generator.get_system_status.return_value = {
            "qkd_connected": False,
            "qkd_network_url": "mock://qkd-system",
        }
        mock_generator.generate_keys.return_value = [b"mock_key_data"]
        mock_generator.get_generation_metrics.return_value = {
            "key_generation_rate": 100,
            "last_generation_time": datetime.datetime.utcnow(),
            "total_keys_generated": 100,
        }

        mock_get_generator.return_value = mock_generator

        with patch("app.core.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.qkd_links = ["link1", "link2"]
            mock_settings.qkd_key_generation_rate = 1000
            mock_get_settings.return_value = mock_settings

            health_check = await self.health_monitor._check_qkd_network_health()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "qkd_network_health"
        assert health_check.status == HealthStatus.DEGRADED
        assert "mock QKD generator" in health_check.message
        assert (
            "Mock generator indicates no real QKD hardware connected"
            in health_check.details["note"]
        )

    @pytest.mark.asyncio
    async def test_system_resources_health_check(self):
        """Test system resources health check"""
        health_check = await self.health_monitor._check_system_resources()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "system_resources"
        assert health_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "cpu" in health_check.details
        assert "memory" in health_check.details
        assert "disk" in health_check.details

    @pytest.mark.asyncio
    async def test_performance_metrics_health_check(self):
        """Test performance metrics health check"""
        health_check = await self.health_monitor._check_performance_metrics()

        assert isinstance(health_check, HealthCheck)
        assert health_check.name == "performance_metrics"
        assert health_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "cpu_percent" in health_check.details
        assert "memory_percent" in health_check.details
        assert "disk_io" in health_check.details
        assert "network_io" in health_check.details

    def test_overall_health_status_determination(self):
        """Test overall health status determination"""
        # Test with all healthy checks
        healthy_checks = [
            HealthCheck("test1", HealthStatus.HEALTHY, "Healthy"),
            HealthCheck("test2", HealthStatus.HEALTHY, "Healthy"),
        ]
        status = self.health_monitor._determine_overall_status(healthy_checks)
        assert status == HealthStatus.HEALTHY

        # Test with degraded checks
        degraded_checks = [
            HealthCheck("test1", HealthStatus.HEALTHY, "Healthy"),
            HealthCheck("test2", HealthStatus.DEGRADED, "Degraded"),
        ]
        status = self.health_monitor._determine_overall_status(degraded_checks)
        assert status == HealthStatus.DEGRADED

        # Test with unhealthy checks
        unhealthy_checks = [
            HealthCheck("test1", HealthStatus.HEALTHY, "Healthy"),
            HealthCheck("test2", HealthStatus.UNHEALTHY, "Unhealthy"),
        ]
        status = self.health_monitor._determine_overall_status(unhealthy_checks)
        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_complete_system_health_check(self):
        """Test complete system health check"""
        health_result = await self.health_monitor.check_system_health()

        assert isinstance(health_result, dict)
        assert "status" in health_result
        assert "timestamp" in health_result
        assert "checks" in health_result
        assert isinstance(health_result["checks"], list)
        assert len(health_result["checks"]) > 0

        # Verify all checks have required fields
        for check in health_result["checks"]:
            assert "name" in check
            assert "status" in check
            assert "message" in check
            assert "timestamp" in check

    @pytest.mark.asyncio
    async def test_health_summary(self):
        """Test health summary generation"""
        summary = await self.health_monitor.get_health_summary()

        assert isinstance(summary, dict)
        assert "status" in summary
        assert "last_check" in summary
        assert "total_checks" in summary
        assert "healthy_checks" in summary
        assert "degraded_checks" in summary
        assert "unhealthy_checks" in summary


if __name__ == "__main__":
    pytest.main([__file__])
