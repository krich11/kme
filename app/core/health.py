#!/usr/bin/env python3
"""
KME Health Monitoring Module

Version: 1.0.0
Author: KME Development Team
Description: Health monitoring and status checking for KME system
License: [To be determined]

ToDo List:
- [x] Create health check endpoints
- [ ] Add database health checks
- [ ] Implement Redis health checks
- [ ] Add QKD network health checks
- [ ] Create system resource monitoring
- [ ] Add performance health checks
- [ ] Implement health status aggregation
- [ ] Add health check scheduling
- [ ] Create health alerting
- [ ] Add health metrics collection

Progress: 10% (1/10 tasks completed)
"""

import asyncio
import datetime
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import psutil

from .logging import logger, performance_logger


class HealthStatus(Enum):
    """Health status enumeration"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result"""

    name: str
    status: HealthStatus
    message: str
    details: dict[str, Any] | None = None
    timestamp: datetime.datetime | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.utcnow()


class HealthMonitor:
    """Health monitoring system for KME"""

    def __init__(self):
        """Initialize health monitor"""
        self.checks: list[HealthCheck] = []
        self.last_check_time: datetime.datetime | None = None

    async def check_system_health(self) -> dict[str, Any]:
        """Check overall system health"""
        logger.info("Starting system health check")

        # Run all health checks
        checks = await asyncio.gather(
            self._check_basic_system(),
            self._check_memory_usage(),
            self._check_disk_usage(),
            self._check_cpu_usage(),
            self._check_network_connectivity(),
            self._check_database_health(),
            self._check_redis_health(),
            self._check_qkd_network_health(),
            self._check_system_resources(),
            self._check_performance_metrics(),
            return_exceptions=True,
        )

        # Process results
        health_checks: list[HealthCheck] = []
        for check in checks:
            if isinstance(check, Exception):
                health_checks.append(
                    HealthCheck(
                        name="system_check",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check failed: {str(check)}",
                        details={"error": str(check)},
                    )
                )
            elif isinstance(check, HealthCheck):
                health_checks.append(check)
            else:
                # Handle unexpected types
                health_checks.append(
                    HealthCheck(
                        name="system_check",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Unexpected check type: {type(check)}",
                        details={"error": f"Expected HealthCheck, got {type(check)}"},
                    )
                )

        self.checks = health_checks
        self.last_check_time = datetime.datetime.utcnow()

        # Determine overall status
        overall_status = self._determine_overall_status(health_checks)

        # Log health status
        performance_logger.log_system_health(
            component="overall_system",
            status=overall_status.value,
            details={
                "total_checks": len(health_checks),
                "healthy_checks": len(
                    [c for c in health_checks if c.status == HealthStatus.HEALTHY]
                ),
                "degraded_checks": len(
                    [c for c in health_checks if c.status == HealthStatus.DEGRADED]
                ),
                "unhealthy_checks": len(
                    [c for c in health_checks if c.status == HealthStatus.UNHEALTHY]
                ),
            },
        )

        return {
            "status": overall_status.value,
            "timestamp": self.last_check_time.isoformat(),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "details": check.details,
                    "timestamp": check.timestamp.isoformat()
                    if check.timestamp
                    else None,
                }
                for check in health_checks
            ],
        }

    async def _check_basic_system(self) -> HealthCheck:
        """Check basic system functionality"""
        try:
            # Basic system check
            return HealthCheck(
                name="basic_system",
                status=HealthStatus.HEALTHY,
                message="Basic system functionality is operational",
                details={
                    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                    "platform": sys.platform,
                    "uptime_seconds": psutil.boot_time(),
                },
            )
        except Exception as e:
            return HealthCheck(
                name="basic_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Basic system check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_memory_usage(self) -> HealthCheck:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent

            if usage_percent < 80:
                status = HealthStatus.HEALTHY
                message = "Memory usage is normal"
            elif usage_percent < 90:
                status = HealthStatus.DEGRADED
                message = "Memory usage is elevated"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Memory usage is critical"

            return HealthCheck(
                name="memory_usage",
                status=status,
                message=message,
                details={
                    "usage_percent": usage_percent,
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                },
            )
        except Exception as e:
            return HealthCheck(
                name="memory_usage",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_disk_usage(self) -> HealthCheck:
        """Check disk usage"""
        try:
            disk = psutil.disk_usage("/")
            usage_percent = disk.percent

            if usage_percent < 80:
                status = HealthStatus.HEALTHY
                message = "Disk usage is normal"
            elif usage_percent < 90:
                status = HealthStatus.DEGRADED
                message = "Disk usage is elevated"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Disk usage is critical"

            return HealthCheck(
                name="disk_usage",
                status=status,
                message=message,
                details={
                    "usage_percent": usage_percent,
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                },
            )
        except Exception as e:
            return HealthCheck(
                name="disk_usage",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_cpu_usage(self) -> HealthCheck:
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent < 70:
                status = HealthStatus.HEALTHY
                message = "CPU usage is normal"
            elif cpu_percent < 85:
                status = HealthStatus.DEGRADED
                message = "CPU usage is elevated"
            else:
                status = HealthStatus.UNHEALTHY
                message = "CPU usage is critical"

            return HealthCheck(
                name="cpu_usage",
                status=status,
                message=message,
                details={
                    "usage_percent": cpu_percent,
                    "cpu_count": psutil.cpu_count(),
                    "cpu_freq": psutil.cpu_freq()._asdict()
                    if psutil.cpu_freq()
                    else None,
                },
            )
        except Exception as e:
            return HealthCheck(
                name="cpu_usage",
                status=HealthStatus.UNHEALTHY,
                message=f"CPU check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_network_connectivity(self) -> HealthCheck:
        """Check network connectivity"""
        try:
            # Basic network check
            network_stats = psutil.net_io_counters()

            return HealthCheck(
                name="network_connectivity",
                status=HealthStatus.HEALTHY,
                message="Network connectivity is operational",
                details={
                    "bytes_sent": network_stats.bytes_sent,
                    "bytes_recv": network_stats.bytes_recv,
                    "packets_sent": network_stats.packets_sent,
                    "packets_recv": network_stats.packets_recv,
                },
            )
        except Exception as e:
            return HealthCheck(
                name="network_connectivity",
                status=HealthStatus.UNHEALTHY,
                message=f"Network check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_database_health(self) -> HealthCheck:
        """Check database connectivity and health"""
        try:
            # Import here to avoid circular imports
            from .config import settings
            from .database import database_manager

            start_time = datetime.datetime.utcnow()

            # Test database connection
            async with database_manager.get_session_context() as db_session:
                # Test basic connectivity with a simple query
                from sqlalchemy import text

                # Test 1: Basic connectivity
                result = await db_session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                if not row or row[0] != 1:
                    raise Exception("Database connectivity test failed")

                # Test 2: Check database version
                result = await db_session.execute(text("SELECT version()"))
                version_row = result.fetchone()
                db_version = version_row[0] if version_row else "unknown"

                # Test 3: Check key tables exist
                result = await db_session.execute(
                    text(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name IN ('sae_entities', 'keys', 'key_requests')
                    """
                    )
                )
                tables = [row[0] for row in result.fetchall()]

                # Test 4: Check connection pool status
                if database_manager.engine is None:
                    pool_status = {
                        "pool_size": 0,
                        "checked_in": 0,
                        "checked_out": 0,
                        "overflow": 0,
                        "note": "Engine not initialized",
                    }
                else:
                    pool_status = {
                        "pool_size": database_manager.engine.pool.size(),  # type: ignore[attr-defined]
                        "checked_in": database_manager.engine.pool.checkedin(),  # type: ignore[attr-defined]
                        "checked_out": database_manager.engine.pool.checkedout(),  # type: ignore[attr-defined]
                        "overflow": database_manager.engine.pool.overflow(),  # type: ignore[attr-defined]
                    }

                end_time = datetime.datetime.utcnow()
                response_time = (
                    end_time - start_time
                ).total_seconds() * 1000  # milliseconds

                # Determine health status based on response time and table availability
                if response_time > 1000:  # More than 1 second
                    status = HealthStatus.DEGRADED
                    message = f"Database response time is slow ({response_time:.2f}ms)"
                elif len(tables) < 3:  # Missing some expected tables
                    status = HealthStatus.DEGRADED
                    message = f"Database schema incomplete - found {len(tables)}/3 expected tables"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Database connectivity and schema are healthy"

                return HealthCheck(
                    name="database_health",
                    status=status,
                    message=message,
                    details={
                        "database_url": settings.database_url.split("@")[0] + "@***"
                        if "@" in settings.database_url
                        else "***",
                        "database_type": "postgresql",
                        "database_version": db_version,
                        "response_time_ms": round(response_time, 2),
                        "connection_pool_size": settings.database_pool_size,
                        "max_overflow": settings.database_max_overflow,
                        "pool_status": pool_status,
                        "tables_found": tables,
                        "expected_tables": ["sae_entities", "keys", "key_requests"],
                        "tables_count": len(tables),
                    },
                )

        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return HealthCheck(
                name="database_health",
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)}",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "database_url": "***" if "settings" in locals() else "unknown",
                },
            )

    async def _check_redis_health(self) -> HealthCheck:
        """Check Redis connectivity and health"""
        try:
            # Import here to avoid circular imports
            from .config import settings

            start_time = datetime.datetime.utcnow()

            # Try to import redis and test connection
            try:
                import redis.asyncio as redis
            except ImportError:
                # Redis not available, return degraded status
                return HealthCheck(
                    name="redis_health",
                    status=HealthStatus.DEGRADED,
                    message="Redis client not available - redis package not installed",
                    details={
                        "redis_url": settings.redis_url.split("@")[0] + "@***"
                        if "@" in settings.redis_url
                        else "***",
                        "redis_type": "redis",
                        "connection_pool_size": settings.redis_pool_size,
                        "note": "Install redis package for full Redis health monitoring",
                    },
                )

            # Parse Redis URL
            redis_url = settings.redis_url
            if redis_url.startswith("redis://"):
                # Basic Redis connection test
                try:
                    # Create Redis client
                    redis_client = redis.from_url(
                        redis_url,
                        max_connections=settings.redis_pool_size,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                    )

                    # Test 1: Basic connectivity (PING)
                    ping_result = await redis_client.ping()
                    if not ping_result:
                        raise Exception("Redis PING failed")

                    # Test 2: Basic operations
                    test_key = "kme_health_check_test"
                    test_value = "health_check_value"

                    # Set a test value
                    await redis_client.set(
                        test_key, test_value, ex=60
                    )  # Expire in 60 seconds

                    # Get the test value
                    retrieved_value = await redis_client.get(test_key)
                    if retrieved_value != test_value:
                        raise Exception("Redis GET/SET operations failed")

                    # Delete the test value
                    await redis_client.delete(test_key)

                    # Test 3: Check Redis info
                    info = await redis_client.info()
                    redis_version = info.get("redis_version", "unknown")
                    connected_clients = info.get("connected_clients", 0)
                    used_memory = info.get("used_memory_human", "unknown")
                    uptime_seconds = info.get("uptime_in_seconds", 0)

                    # Test 4: Check Redis memory usage
                    memory_info = await redis_client.info("memory")
                    memory_usage = memory_info.get("used_memory_human", "unknown")
                    memory_peak = memory_info.get("used_memory_peak_human", "unknown")

                    end_time = datetime.datetime.utcnow()
                    response_time = (
                        end_time - start_time
                    ).total_seconds() * 1000  # milliseconds

                    # Close Redis connection
                    await redis_client.close()

                    # Determine health status based on response time and operations
                    if response_time > 500:  # More than 500ms
                        status = HealthStatus.DEGRADED
                        message = f"Redis response time is slow ({response_time:.2f}ms)"
                    else:
                        status = HealthStatus.HEALTHY
                        message = "Redis connectivity and operations are healthy"

                    return HealthCheck(
                        name="redis_health",
                        status=status,
                        message=message,
                        details={
                            "redis_url": redis_url.split("@")[0] + "@***"
                            if "@" in redis_url
                            else "***",
                            "redis_type": "redis",
                            "redis_version": redis_version,
                            "response_time_ms": round(response_time, 2),
                            "connection_pool_size": settings.redis_pool_size,
                            "connected_clients": connected_clients,
                            "uptime_seconds": uptime_seconds,
                            "memory_usage": memory_usage,
                            "memory_peak": memory_peak,
                            "operations_tested": ["ping", "set", "get", "delete"],
                        },
                    )

                except Exception as redis_error:
                    raise Exception(f"Redis connection failed: {str(redis_error)}")

            else:
                # Redis URL not configured or invalid
                return HealthCheck(
                    name="redis_health",
                    status=HealthStatus.DEGRADED,
                    message="Redis URL not configured or invalid",
                    details={
                        "redis_url": "not_configured",
                        "redis_type": "redis",
                        "connection_pool_size": settings.redis_pool_size,
                        "note": "Configure REDIS_URL environment variable for Redis health monitoring",
                    },
                )

        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return HealthCheck(
                name="redis_health",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis health check failed: {str(e)}",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "redis_url": "***" if "settings" in locals() else "unknown",
                },
            )

    async def _check_qkd_network_health(self) -> HealthCheck:
        """Check QKD network connectivity and health"""
        try:
            # Import here to avoid circular imports
            from .config import settings

            start_time = datetime.datetime.utcnow()

            # Test QKD key generation service
            try:
                from ..services.key_generation_service import get_key_generator

                key_generator = get_key_generator()
                generator_type = key_generator.__class__.__name__

                # Test 1: Get QKD system status
                system_status = await key_generator.get_system_status()

                # Test 2: Test key generation capability
                try:
                    # Try to generate a small test key
                    test_keys = await key_generator.generate_keys(number=1, size=64)
                    key_generation_working = (
                        len(test_keys) == 1 and len(test_keys[0]) >= 8
                    )
                except Exception as key_gen_error:
                    key_generation_working = False
                    key_gen_error_msg = str(key_gen_error)

                # Test 3: Check QKD network connectivity
                qkd_connected = system_status.get("qkd_connected", False)
                qkd_network_url = system_status.get("qkd_network_url", "unknown")

                # Test 4: Get QKD metrics
                try:
                    generation_metrics = await key_generator.get_generation_metrics()
                    key_generation_rate = generation_metrics.get(
                        "key_generation_rate", 0
                    )
                    last_generation_time = generation_metrics.get(
                        "last_generation_time"
                    )
                    total_keys_generated = generation_metrics.get(
                        "total_keys_generated", 0
                    )
                except Exception:
                    key_generation_rate = 0
                    last_generation_time = None
                    total_keys_generated = 0

                end_time = datetime.datetime.utcnow()
                response_time = (
                    end_time - start_time
                ).total_seconds() * 1000  # milliseconds

                # Determine health status based on QKD connectivity and key generation
                if not qkd_connected and generator_type == "QKDKeyGenerator":
                    status = HealthStatus.UNHEALTHY
                    message = "QKD network is not connected"
                elif not key_generation_working:
                    status = HealthStatus.DEGRADED
                    message = "QKD key generation is not working"
                elif response_time > 2000:  # More than 2 seconds
                    status = HealthStatus.DEGRADED
                    message = (
                        f"QKD network response time is slow ({response_time:.2f}ms)"
                    )
                elif generator_type == "MockKeyGenerator":
                    status = HealthStatus.DEGRADED
                    message = (
                        "Using mock QKD generator - not connected to real QKD network"
                    )
                else:
                    status = HealthStatus.HEALTHY
                    message = "QKD network connectivity and key generation are healthy"

                return HealthCheck(
                    name="qkd_network_health",
                    status=status,
                    message=message,
                    details={
                        "qkd_links": settings.qkd_links,
                        "key_generation_rate": key_generation_rate,
                        "generator_type": generator_type,
                        "qkd_connected": qkd_connected,
                        "qkd_network_url": qkd_network_url,
                        "key_generation_working": key_generation_working,
                        "response_time_ms": round(response_time, 2),
                        "total_keys_generated": total_keys_generated,
                        "last_generation_time": last_generation_time.isoformat()
                        if last_generation_time
                        else None,
                        "system_status": system_status,
                        "key_gen_error": key_gen_error_msg
                        if not key_generation_working
                        else None,
                        "note": "Mock generator indicates no real QKD hardware connected"
                        if generator_type == "MockKeyGenerator"
                        else None,
                    },
                )

            except ImportError:
                # QKD service not available
                return HealthCheck(
                    name="qkd_network_health",
                    status=HealthStatus.DEGRADED,
                    message="QKD key generation service not available",
                    details={
                        "qkd_links": settings.qkd_links,
                        "key_generation_rate": settings.qkd_key_generation_rate,
                        "generator_type": "unknown",
                        "qkd_connected": False,
                        "qkd_network_url": "unknown",
                        "note": "QKD key generation service not properly configured",
                    },
                )

        except Exception as e:
            logger.error(f"QKD network health check failed: {str(e)}")
            return HealthCheck(
                name="qkd_network_health",
                status=HealthStatus.UNHEALTHY,
                message=f"QKD network health check failed: {str(e)}",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "qkd_links": settings.qkd_links if "settings" in locals() else [],
                    "key_generation_rate": settings.qkd_key_generation_rate
                    if "settings" in locals()
                    else 0,
                },
            )

    async def _check_system_resources(self) -> HealthCheck:
        """Check detailed system resources"""
        try:
            # Get detailed system information
            cpu_info = {
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "cpu_percent": psutil.cpu_percent(interval=1, percpu=True),
                "load_average": psutil.getloadavg()
                if hasattr(psutil, "getloadavg")
                else None,
            }

            memory_info = {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "free": psutil.virtual_memory().free,
                "percent": psutil.virtual_memory().percent,
                "swap_total": psutil.swap_memory().total,
                "swap_used": psutil.swap_memory().used,
                "swap_free": psutil.swap_memory().free,
                "swap_percent": psutil.swap_memory().percent,
            }

            disk_info = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[partition.mountpoint] = {
                        "device": partition.device,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                    }
                except PermissionError:
                    continue

            # Determine overall resource status
            memory_healthy = memory_info["percent"] < 80
            cpu_percent_list = cpu_info["cpu_percent"]
            if isinstance(cpu_percent_list, list):
                cpu_healthy = max(cpu_percent_list) < 70
            else:
                cpu_healthy = cpu_percent_list < 70  # type: ignore[operator]
            # Check disk health with proper type handling
            disk_healthy = True
            for disk in disk_info.values():
                if isinstance(disk, dict) and "percent" in disk:
                    percent = disk["percent"]
                    if isinstance(percent, (int, float)):
                        if percent >= 80:  # type: ignore[operator]
                            disk_healthy = False
                            break

            if memory_healthy and cpu_healthy and disk_healthy:
                status = HealthStatus.HEALTHY
                message = "System resources are healthy"
            elif memory_healthy and cpu_healthy:
                status = HealthStatus.DEGRADED
                message = "System resources are degraded (disk usage high)"
            else:
                status = HealthStatus.UNHEALTHY
                message = "System resources are unhealthy"

            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                details={
                    "cpu": cpu_info,
                    "memory": memory_info,
                    "disk": disk_info,
                    "resource_summary": {
                        "memory_healthy": memory_healthy,
                        "cpu_healthy": cpu_healthy,
                        "disk_healthy": disk_healthy,
                    },
                },
            )
        except Exception as e:
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"System resources check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_performance_metrics(self) -> HealthCheck:
        """Check performance metrics and thresholds"""
        try:
            # Get performance metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()

            # Performance thresholds
            cpu_threshold = 70
            memory_threshold = 80
            disk_io_threshold = 1000000  # 1MB/s
            network_io_threshold = 1000000  # 1MB/s

            # Check performance against thresholds
            cpu_ok = cpu_percent < cpu_threshold
            memory_ok = memory_percent < memory_threshold

            # Handle case where disk_io might be None
            disk_io_ok = True  # Default to OK if disk_io is None
            if disk_io is not None:
                disk_io_ok = (
                    disk_io.read_bytes + disk_io.write_bytes
                ) < disk_io_threshold

            network_io_ok = (
                network_io.bytes_sent + network_io.bytes_recv
            ) < network_io_threshold

            # Determine overall performance status
            if cpu_ok and memory_ok and disk_io_ok and network_io_ok:
                status = HealthStatus.HEALTHY
                message = "Performance metrics are within acceptable ranges"
            elif cpu_ok and memory_ok:
                status = HealthStatus.DEGRADED
                message = "Performance metrics are degraded (I/O high)"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Performance metrics are outside acceptable ranges"

            # Log performance metrics
            disk_io_bytes = 0
            if disk_io is not None:
                disk_io_bytes = disk_io.read_bytes + disk_io.write_bytes

            performance_logger.log_performance_metric(
                metric_name="system_performance",
                value=cpu_percent,
                unit="percent",
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_io_bytes": disk_io_bytes,
                    "network_io_bytes": network_io.bytes_sent + network_io.bytes_recv,
                },
            )

            return HealthCheck(
                name="performance_metrics",
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_io": {
                        "read_bytes": disk_io.read_bytes if disk_io is not None else 0,
                        "write_bytes": disk_io.write_bytes
                        if disk_io is not None
                        else 0,
                        "read_count": disk_io.read_count if disk_io is not None else 0,
                        "write_count": disk_io.write_count
                        if disk_io is not None
                        else 0,
                    },
                    "network_io": {
                        "bytes_sent": network_io.bytes_sent,
                        "bytes_recv": network_io.bytes_recv,
                        "packets_sent": network_io.packets_sent,
                        "packets_recv": network_io.packets_recv,
                    },
                    "thresholds": {
                        "cpu_threshold": cpu_threshold,
                        "memory_threshold": memory_threshold,
                        "disk_io_threshold": disk_io_threshold,
                        "network_io_threshold": network_io_threshold,
                    },
                    "status_checks": {
                        "cpu_ok": cpu_ok,
                        "memory_ok": memory_ok,
                        "disk_io_ok": disk_io_ok,
                        "network_io_ok": network_io_ok,
                    },
                },
            )
        except Exception as e:
            return HealthCheck(
                name="performance_metrics",
                status=HealthStatus.UNHEALTHY,
                message=f"Performance metrics check failed: {str(e)}",
                details={"error": str(e)},
            )

    def _determine_overall_status(self, checks: list[HealthCheck]) -> HealthStatus:
        """Determine overall health status based on individual checks"""
        if not checks:
            return HealthStatus.UNKNOWN

        # Count statuses
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.UNKNOWN: 0,
        }

        for check in checks:
            status_counts[check.status] += 1

        # Determine overall status
        if status_counts[HealthStatus.UNHEALTHY] > 0:
            return HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED] > 0:
            return HealthStatus.DEGRADED
        elif status_counts[HealthStatus.HEALTHY] > 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    async def get_health_summary(self) -> dict[str, Any]:
        """Get health summary"""
        if not self.last_check_time:
            await self.check_system_health()

        return {
            "status": self._determine_overall_status(self.checks).value,
            "last_check": self.last_check_time.isoformat()
            if self.last_check_time
            else None,
            "total_checks": len(self.checks),
            "healthy_checks": len(
                [c for c in self.checks if c.status == HealthStatus.HEALTHY]
            ),
            "degraded_checks": len(
                [c for c in self.checks if c.status == HealthStatus.DEGRADED]
            ),
            "unhealthy_checks": len(
                [c for c in self.checks if c.status == HealthStatus.UNHEALTHY]
            ),
        }


# Global health monitor instance
health_monitor = HealthMonitor()


def get_health_monitor() -> HealthMonitor:
    """Get health monitor instance"""
    return health_monitor


async def check_health() -> dict[str, Any]:
    """Check system health"""
    return await health_monitor.check_system_health()


async def get_health_summary() -> dict[str, Any]:
    """Get health summary"""
    return await health_monitor.get_health_summary()


# Export health monitoring functions
__all__ = [
    "HealthStatus",
    "HealthCheck",
    "HealthMonitor",
    "health_monitor",
    "get_health_monitor",
    "check_health",
    "get_health_summary",
]
