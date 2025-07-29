#!/usr/bin/env python3
"""
KME Performance Monitoring Module

Version: 1.0.0
Author: KME Development Team
Description: Performance monitoring and metrics collection for KME system
License: [To be determined]

ToDo List:
- [x] Create performance metrics collection
- [ ] Add API performance monitoring
- [ ] Implement key management metrics
- [ ] Add database performance metrics
- [ ] Create performance alerting
- [ ] Add performance reporting
- [ ] Implement performance optimization
- [ ] Add performance benchmarking
- [ ] Create performance dashboards
- [ ] Add performance trend analysis

Progress: 10% (1/10 tasks completed)
"""

import asyncio
import datetime
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional

import psutil

from .logging import logger, performance_logger


class MetricType(Enum):
    """Performance metric types"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class PerformanceMetric:
    """Performance metric data structure"""

    name: str
    value: float
    unit: str
    metric_type: MetricType
    timestamp: datetime.datetime
    labels: dict[str, str] = field(default_factory=dict)
    description: str | None = None


class PerformanceMonitor:
    """Performance monitoring system for KME"""

    def __init__(self):
        """Initialize performance monitor"""
        self.metrics: list[PerformanceMetric] = []
        self.start_time = datetime.datetime.utcnow()
        self.api_metrics: dict[str, list[float]] = {}
        self.key_metrics: dict[str, list[float]] = {}
        self.database_metrics: dict[str, list[float]] = {}

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        metric_type: MetricType = MetricType.GAUGE,
        labels: dict[str, str] | None = None,
        description: str | None = None,
    ):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            metric_type=metric_type,
            timestamp=datetime.datetime.utcnow(),
            labels=labels or {},
            description=description,
        )

        self.metrics.append(metric)

        # Log the metric
        performance_logger.log_performance_metric(
            metric_name=name,
            value=value,
            unit=unit,
            details={
                "metric_type": metric_type.value,
                "labels": labels or {},
                "description": description,
            },
        )

    def record_api_metric(
        self, endpoint: str, response_time_ms: float, status_code: int
    ):
        """Record API performance metric"""
        if endpoint not in self.api_metrics:
            self.api_metrics[endpoint] = []

        self.api_metrics[endpoint].append(response_time_ms)

        # Keep only last 1000 metrics per endpoint
        if len(self.api_metrics[endpoint]) > 1000:
            self.api_metrics[endpoint] = self.api_metrics[endpoint][-1000:]

        self.record_metric(
            name="api_response_time",
            value=response_time_ms,
            unit="milliseconds",
            metric_type=MetricType.HISTOGRAM,
            labels={
                "endpoint": endpoint,
                "status_code": str(status_code),
            },
            description=f"API response time for {endpoint}",
        )

    def record_key_metric(
        self,
        operation: str,
        duration_ms: float,
        key_count: int = 1,
        key_size: int = 0,
    ):
        """Record key management performance metric"""
        if operation not in self.key_metrics:
            self.key_metrics[operation] = []

        self.key_metrics[operation].append(duration_ms)

        # Keep only last 1000 metrics per operation
        if len(self.key_metrics[operation]) > 1000:
            self.key_metrics[operation] = self.key_metrics[operation][-1000:]

        self.record_metric(
            name="key_operation_duration",
            value=duration_ms,
            unit="milliseconds",
            metric_type=MetricType.HISTOGRAM,
            labels={
                "operation": operation,
                "key_count": str(key_count),
                "key_size": str(key_size),
            },
            description=f"Key operation duration for {operation}",
        )

    def record_database_metric(
        self,
        operation: str,
        duration_ms: float,
        table: str = "",
        rows_affected: int = 0,
    ):
        """Record database performance metric"""
        if operation not in self.database_metrics:
            self.database_metrics[operation] = []

        self.database_metrics[operation].append(duration_ms)

        # Keep only last 1000 metrics per operation
        if len(self.database_metrics[operation]) > 1000:
            self.database_metrics[operation] = self.database_metrics[operation][-1000:]

        self.record_metric(
            name="database_operation_duration",
            value=duration_ms,
            unit="milliseconds",
            metric_type=MetricType.HISTOGRAM,
            labels={
                "operation": operation,
                "table": table,
                "rows_affected": str(rows_affected),
            },
            description=f"Database operation duration for {operation}",
        )

    def get_api_performance_summary(self) -> dict[str, Any]:
        """Get API performance summary"""
        summary = {}

        for endpoint, metrics in self.api_metrics.items():
            if metrics:
                summary[endpoint] = {
                    "count": len(metrics),
                    "avg_response_time": sum(metrics) / len(metrics),
                    "min_response_time": min(metrics),
                    "max_response_time": max(metrics),
                    "p95_response_time": sorted(metrics)[int(len(metrics) * 0.95)],
                    "p99_response_time": sorted(metrics)[int(len(metrics) * 0.99)],
                }

        return summary

    def get_key_performance_summary(self) -> dict[str, Any]:
        """Get key management performance summary"""
        summary = {}

        for operation, metrics in self.key_metrics.items():
            if metrics:
                summary[operation] = {
                    "count": len(metrics),
                    "avg_duration": sum(metrics) / len(metrics),
                    "min_duration": min(metrics),
                    "max_duration": max(metrics),
                    "p95_duration": sorted(metrics)[int(len(metrics) * 0.95)],
                    "p99_duration": sorted(metrics)[int(len(metrics) * 0.99)],
                }

        return summary

    def get_database_performance_summary(self) -> dict[str, Any]:
        """Get database performance summary"""
        summary = {}

        for operation, metrics in self.database_metrics.items():
            if metrics:
                summary[operation] = {
                    "count": len(metrics),
                    "avg_duration": sum(metrics) / len(metrics),
                    "min_duration": min(metrics),
                    "max_duration": max(metrics),
                    "p95_duration": sorted(metrics)[int(len(metrics) * 0.95)],
                    "p99_duration": sorted(metrics)[int(len(metrics) * 0.99)],
                }

        return summary

    def get_system_performance_metrics(self) -> dict[str, Any]:
        """Get current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_io_read_mb": round(disk_io.read_bytes / (1024**2), 2),
                "disk_io_write_mb": round(disk_io.write_bytes / (1024**2), 2),
                "network_io_sent_mb": round(network_io.bytes_sent / (1024**2), 2),
                "network_io_recv_mb": round(network_io.bytes_recv / (1024**2), 2),
                "uptime_seconds": (
                    datetime.datetime.utcnow() - self.start_time
                ).total_seconds(),
            }
        except Exception as e:
            logger.error(f"Failed to get system performance metrics: {e}")
            return {"error": str(e)}

    def clear_old_metrics(self, max_age_hours: int = 24):
        """Clear metrics older than specified age"""
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(
            hours=max_age_hours
        )

        # Clear old metrics
        self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]

        # Clear old API metrics (keep only last 100 per endpoint)
        for endpoint in self.api_metrics:
            if len(self.api_metrics[endpoint]) > 100:
                self.api_metrics[endpoint] = self.api_metrics[endpoint][-100:]

        # Clear old key metrics (keep only last 100 per operation)
        for operation in self.key_metrics:
            if len(self.key_metrics[operation]) > 100:
                self.key_metrics[operation] = self.key_metrics[operation][-100:]

        logger.info(f"Cleared metrics older than {max_age_hours} hours")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get performance monitor instance"""
    return performance_monitor


def monitor_api_performance(endpoint: str):
    """Decorator to monitor API performance"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                response_time = (
                    time.time() - start_time
                ) * 1000  # Convert to milliseconds
                status_code = getattr(result, "status_code", 200)

                performance_monitor.record_api_metric(
                    endpoint, response_time, status_code
                )
                return result
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                performance_monitor.record_api_metric(endpoint, response_time, 500)
                raise

        return wrapper

    return decorator


def monitor_key_operation(operation: str):
    """Decorator to monitor key management operations"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds

                # Extract key count and size from result if available
                key_count = getattr(result, "key_count", 1)
                key_size = getattr(result, "key_size", 0)

                performance_monitor.record_key_metric(
                    operation, duration, key_count, key_size
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                performance_monitor.record_key_metric(operation, duration, 0, 0)
                raise

        return wrapper

    return decorator


def monitor_database_operation(operation: str, table: str = ""):
    """Decorator to monitor database operations"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds

                # Extract rows affected from result if available
                rows_affected = getattr(result, "rowcount", 0)

                performance_monitor.record_database_metric(
                    operation, duration, table, rows_affected
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                performance_monitor.record_database_metric(
                    operation, duration, table, 0
                )
                raise

        return wrapper

    return decorator


# Export performance monitoring functions
__all__ = [
    "MetricType",
    "PerformanceMetric",
    "PerformanceMonitor",
    "performance_monitor",
    "get_performance_monitor",
    "monitor_api_performance",
    "monitor_key_operation",
    "monitor_database_operation",
]
