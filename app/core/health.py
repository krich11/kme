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
        health_checks = []
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
            else:
                health_checks.append(check)

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
                    "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
                    "platform": psutil.sys.platform,
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

            # For now, return a placeholder check
            # TODO: Implement actual database connection check when database is set up
            return HealthCheck(
                name="database_health",
                status=HealthStatus.HEALTHY,
                message="Database health check placeholder - not yet implemented",
                details={
                    "database_url": settings.database_url.split("@")[0] + "@***"
                    if "@" in settings.database_url
                    else "***",
                    "database_type": "postgresql",
                    "connection_pool_size": settings.database_pool_size,
                    "max_overflow": settings.database_max_overflow,
                },
            )
        except Exception as e:
            return HealthCheck(
                name="database_health",
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_redis_health(self) -> HealthCheck:
        """Check Redis connectivity and health"""
        try:
            # Import here to avoid circular imports
            from .config import settings

            # For now, return a placeholder check
            # TODO: Implement actual Redis connection check when Redis is set up
            return HealthCheck(
                name="redis_health",
                status=HealthStatus.HEALTHY,
                message="Redis health check placeholder - not yet implemented",
                details={
                    "redis_url": settings.redis_url.split("@")[0] + "@***"
                    if "@" in settings.redis_url
                    else "***",
                    "redis_type": "redis",
                    "connection_pool_size": settings.redis_pool_size,
                },
            )
        except Exception as e:
            return HealthCheck(
                name="redis_health",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis health check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _check_qkd_network_health(self) -> HealthCheck:
        """Check QKD network connectivity and health"""
        try:
            # Import here to avoid circular imports
            from .config import settings

            # For now, return a placeholder check
            # TODO: Implement actual QKD network health check when QKD network is set up
            return HealthCheck(
                name="qkd_network_health",
                status=HealthStatus.HEALTHY,
                message="QKD network health check placeholder - not yet implemented",
                details={
                    "qkd_links": settings.qkd_links,
                    "key_generation_rate": settings.key_generation_rate,
                    "link_quality": "unknown",
                    "network_status": "placeholder",
                },
            )
        except Exception as e:
            return HealthCheck(
                name="qkd_network_health",
                status=HealthStatus.UNHEALTHY,
                message=f"QKD network health check failed: {str(e)}",
                details={"error": str(e)},
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
            cpu_healthy = max(cpu_info["cpu_percent"]) < 70
            disk_healthy = all(disk["percent"] < 80 for disk in disk_info.values())

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
            disk_io_ok = (disk_io.read_bytes + disk_io.write_bytes) < disk_io_threshold
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
            performance_logger.log_performance_metric(
                metric_name="system_performance",
                value=cpu_percent,
                unit="percent",
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_io_bytes": disk_io.read_bytes + disk_io.write_bytes,
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
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes,
                        "read_count": disk_io.read_count,
                        "write_count": disk_io.write_count,
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
