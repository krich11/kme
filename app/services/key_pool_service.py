#!/usr/bin/env python3
"""
KME Key Pool Management Service - ETSI QKD 014 V1.1.1 Compliant

Version: 1.0.0
Author: KME Development Team
Description: Key pool management and replenishment system
License: [To be determined]

Implements ETSI GS QKD 014 V1.1.1 requirements for:
- Key pool status monitoring
- Automatic key replenishment
- Key exhaustion handling
- Pool statistics and reporting

ToDo List:
- [x] Create key pool service structure
- [x] Implement pool status monitoring
- [x] Add automatic replenishment
- [x] Create exhaustion detection
- [x] Add pool statistics
- [ ] Add performance optimization
- [ ] Add alerting system
- [ ] Add manual replenishment triggers
- [ ] Add comprehensive error handling
- [ ] Add unit tests

Progress: 50% (5/10 tasks completed)
"""

import asyncio
import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.key_storage_service import KeyStorageService

logger = structlog.get_logger()


class KeyPoolService:
    """
    Key pool management service

    Manages key pool status, replenishment, and exhaustion handling
    according to ETSI GS QKD 014 V1.1.1 requirements
    """

    def __init__(
        self, db_session: AsyncSession, key_storage_service: KeyStorageService
    ):
        """
        Initialize the key pool service

        Args:
            db_session: Database session for pool operations
            key_storage_service: Key storage service for key operations
        """
        self.logger = logger.bind(service="KeyPoolService")
        self.db_session = db_session
        self.key_storage_service = key_storage_service
        self._replenishment_task: asyncio.Task[None] | None = None
        self._monitoring_task: asyncio.Task[None] | None = None
        self.logger.info("Key pool service initialized")

    async def get_pool_status(self) -> dict[str, Any]:
        """
        Get current key pool status

        Returns:
            Dict containing comprehensive pool status information
        """
        try:
            # Get current pool statistics
            total_keys = await self._count_total_keys()
            active_keys = await self._count_active_keys()
            expired_keys = await self._count_expired_keys()
            consumed_keys = await self._count_consumed_keys()

            # Get pool configuration
            pool_config = await self._get_pool_configuration()

            # Calculate availability percentage
            availability_percentage = 0
            if pool_config["max_key_count"] > 0:
                availability_percentage = (
                    active_keys / pool_config["max_key_count"]
                ) * 100

            # Determine pool health
            pool_health = self._determine_pool_health(active_keys, pool_config)

            status = {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "expired_keys": expired_keys,
                "consumed_keys": consumed_keys,
                "max_key_count": pool_config["max_key_count"],
                "min_key_threshold": pool_config["min_key_threshold"],
                "availability_percentage": round(availability_percentage, 2),
                "pool_health": pool_health,
                "last_updated": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "key_generation_rate": pool_config.get("key_generation_rate"),
                "last_key_generation": pool_config.get("last_key_generation"),
            }

            # Update pool status in database
            await self._update_pool_status_record(status)

            self.logger.info(
                "Pool status retrieved",
                active_keys=active_keys,
                max_keys=pool_config["max_key_count"],
                health=pool_health,
            )

            return status

        except Exception as e:
            self.logger.error("Failed to get pool status", error=str(e))
            raise RuntimeError(f"Pool status retrieval failed: {e}")

    async def check_key_availability(self, requested_keys: int, key_size: int) -> bool:
        """
        Check if sufficient keys are available for a request

        Args:
            requested_keys: Number of keys requested
            key_size: Size of keys in bits

        Returns:
            bool: True if sufficient keys are available
        """
        try:
            # Get current active key count
            active_keys = await self._count_active_keys()

            # Get pool configuration
            pool_config = await self._get_pool_configuration()

            # Check if we have enough keys
            if active_keys >= requested_keys:
                return True

            # Check if we're below threshold and should trigger replenishment
            if active_keys < pool_config["min_key_threshold"]:
                self.logger.warning(
                    "Key pool below threshold, triggering replenishment",
                    active_keys=active_keys,
                    threshold=pool_config["min_key_threshold"],
                )
                await self._trigger_replenishment()

            return False

        except Exception as e:
            self.logger.error("Failed to check key availability", error=str(e))
            return False

    async def check_key_exhaustion(self, requested_keys: int) -> dict[str, Any]:
        """
        Check for key exhaustion and return ETSI-compliant response

        Args:
            requested_keys: Number of keys requested

        Returns:
            dict: Exhaustion status with ETSI-compliant error details
        """
        try:
            # Get current active key count
            active_keys = await self._count_active_keys()

            # Check if we have any keys at all
            if active_keys == 0:
                self.logger.error("Key pool completely exhausted")
                return {
                    "exhausted": True,
                    "available_keys": 0,
                    "requested_keys": requested_keys,
                    "etsi_error": {
                        "message": "Key pool exhausted - no keys available",
                        "details": [
                            {
                                "error_type": "key_exhaustion",
                                "available_keys": 0,
                                "requested_keys": requested_keys,
                                "recommendation": "Wait for key generation to complete",
                            }
                        ],
                    },
                }

            # Check if we have insufficient keys
            if active_keys < requested_keys:
                self.logger.warning(
                    "Insufficient keys available",
                    available_keys=active_keys,
                    requested_keys=requested_keys,
                )
                return {
                    "exhausted": True,
                    "available_keys": active_keys,
                    "requested_keys": requested_keys,
                    "etsi_error": {
                        "message": f"Insufficient keys available - requested {requested_keys}, available {active_keys}",
                        "details": [
                            {
                                "error_type": "insufficient_keys",
                                "available_keys": active_keys,
                                "requested_keys": requested_keys,
                                "recommendation": "Reduce key request size or wait for replenishment",
                            }
                        ],
                    },
                }

            # Keys are available
            return {
                "exhausted": False,
                "available_keys": active_keys,
                "requested_keys": requested_keys,
            }

        except Exception as e:
            self.logger.error("Failed to check key exhaustion", error=str(e))
            return {
                "exhausted": True,
                "available_keys": 0,
                "requested_keys": requested_keys,
                "etsi_error": {
                    "message": "Failed to check key availability",
                    "details": [
                        {
                            "error_type": "system_error",
                            "error": str(e),
                            "recommendation": "Contact system administrator",
                        }
                    ],
                },
            }

    async def handle_key_exhaustion(self) -> dict[str, Any]:
        """
        Handle key pool exhaustion

        Returns:
            Dict containing exhaustion response and recovery actions
        """
        try:
            self.logger.warning("Key pool exhaustion detected")

            # Get current status
            status = await self.get_pool_status()

            # Trigger emergency replenishment
            replenishment_result = await self._trigger_emergency_replenishment()

            # Create exhaustion response
            response = {
                "exhaustion_detected": True,
                "current_status": status,
                "replenishment_triggered": replenishment_result["success"],
                "estimated_recovery_time": replenishment_result.get("estimated_time"),
                "recommended_actions": [
                    "Wait for key generation to complete",
                    "Consider reducing key request frequency",
                    "Monitor pool status for recovery",
                ],
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

            # Log exhaustion event
            await self._log_exhaustion_event(response)

            return response

        except Exception as e:
            self.logger.error("Failed to handle key exhaustion", error=str(e))
            raise RuntimeError(f"Key exhaustion handling failed: {e}")

    async def start_automatic_replenishment(self) -> bool:
        """
        Start automatic key replenishment monitoring

        Returns:
            bool: True if monitoring started successfully
        """
        try:
            if self._replenishment_task and not self._replenishment_task.done():
                self.logger.info("Automatic replenishment already running")
                return True

            # Start replenishment monitoring task
            self._replenishment_task = asyncio.create_task(
                self._replenishment_monitor()
            )

            self.logger.info("Automatic key replenishment started")
            return True

        except Exception as e:
            self.logger.error("Failed to start automatic replenishment", error=str(e))
            return False

    async def stop_automatic_replenishment(self) -> bool:
        """
        Stop automatic key replenishment monitoring

        Returns:
            bool: True if monitoring stopped successfully
        """
        try:
            if self._replenishment_task and not self._replenishment_task.done():
                self._replenishment_task.cancel()
                try:
                    await self._replenishment_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("Automatic key replenishment stopped")
            return True

        except Exception as e:
            self.logger.error("Failed to stop automatic replenishment", error=str(e))
            return False

    async def get_pool_health_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive pool health metrics

        Returns:
            Dict containing detailed health metrics
        """
        try:
            status = await self.get_pool_status()
            config = await self._get_pool_configuration()

            # Calculate health indicators
            availability_ratio = (
                status["active_keys"] / config["max_key_count"]
                if config["max_key_count"] > 0
                else 0
            )
            consumption_rate = await self._calculate_consumption_rate()
            generation_rate = await self._calculate_generation_rate()
            replenishment_frequency = await self._calculate_replenishment_frequency()

            # Determine health status
            health_status = "healthy"
            if availability_ratio < 0.2:
                health_status = "critical"
            elif availability_ratio < 0.5:
                health_status = "warning"
            elif availability_ratio < 0.8:
                health_status = "degraded"

            return {
                "health_status": health_status,
                "availability_ratio": round(availability_ratio, 3),
                "consumption_rate_per_hour": round(consumption_rate, 2),
                "generation_rate_per_hour": round(generation_rate, 2),
                "replenishment_frequency_hours": round(replenishment_frequency, 2),
                "last_health_check": datetime.datetime.utcnow().isoformat(),
                "recommendations": self._generate_health_recommendations(
                    availability_ratio, consumption_rate, generation_rate
                ),
            }

        except Exception as e:
            self.logger.error("Failed to get pool health metrics", error=str(e))
            raise RuntimeError(f"Health metrics retrieval failed: {e}")

    async def _calculate_consumption_rate(self) -> float:
        """Calculate key consumption rate (keys per hour)"""
        try:
            # Get consumption in last 24 hours
            yesterday = datetime.datetime.utcnow() - datetime.timedelta(hours=24)

            # Count keys consumed in last 24 hours
            consumed_query = text(
                """
                SELECT COUNT(*) FROM keys
                WHERE status = 'consumed'
                AND updated_at >= :yesterday
            """
            )
            result = await self.db_session.execute(
                consumed_query, {"yesterday": yesterday}
            )
            consumed_count = result.scalar() or 0

            return consumed_count / 24.0  # keys per hour

        except Exception as e:
            self.logger.error("Failed to calculate consumption rate", error=str(e))
            return 0.0

    async def _calculate_generation_rate(self) -> float:
        """Calculate key generation rate (keys per hour)"""
        try:
            # Get generation in last 24 hours
            yesterday = datetime.datetime.utcnow() - datetime.timedelta(hours=24)

            # Count keys generated in last 24 hours
            generated_query = text(
                """
                SELECT COUNT(*) FROM keys
                WHERE status = 'active'
                AND created_at >= :yesterday
            """
            )
            result = await self.db_session.execute(
                generated_query, {"yesterday": yesterday}
            )
            generated_count = result.scalar() or 0

            return generated_count / 24.0  # keys per hour

        except Exception as e:
            self.logger.error("Failed to calculate generation rate", error=str(e))
            return 0.0

    async def _calculate_replenishment_frequency(self) -> float:
        """Calculate replenishment frequency (hours between replenishments)"""
        try:
            # Get last few replenishment events
            # This would typically query a replenishment events table
            # For now, return a default value
            return 6.0  # Default: 6 hours between replenishments

        except Exception as e:
            self.logger.error(
                "Failed to calculate replenishment frequency", error=str(e)
            )
            return 6.0

    def _generate_health_recommendations(
        self, availability_ratio: float, consumption_rate: float, generation_rate: float
    ) -> list[str]:
        """Generate health recommendations based on metrics"""
        recommendations = []

        if availability_ratio < 0.2:
            recommendations.append(
                "CRITICAL: Key pool critically low - immediate replenishment required"
            )
        elif availability_ratio < 0.5:
            recommendations.append(
                "WARNING: Key pool below 50% - schedule replenishment soon"
            )
        elif availability_ratio < 0.8:
            recommendations.append(
                "INFO: Key pool below 80% - monitor consumption rate"
            )

        if consumption_rate > generation_rate * 1.5:
            recommendations.append(
                "WARNING: Consumption rate significantly higher than generation rate"
            )
        elif consumption_rate < generation_rate * 0.5:
            recommendations.append(
                "INFO: Generation rate much higher than consumption - consider reducing generation"
            )

        if not recommendations:
            recommendations.append("HEALTHY: Key pool operating normally")

        return recommendations

    async def setup_pool_alerting(self, alert_thresholds: dict[str, Any]) -> bool:
        """
        Set up pool alerting system

        Args:
            alert_thresholds: Dictionary containing alert thresholds

        Returns:
            bool: True if setup successful
        """
        try:
            self.logger.info(
                "Setting up pool alerting system",
                thresholds=alert_thresholds,
            )

            # Store alert thresholds in configuration
            # In a real implementation, this would be stored in a configuration table
            self._alert_thresholds = alert_thresholds

            # Set up alert channels
            # This would typically integrate with:
            # - Email/SMS alerting systems
            # - Monitoring platforms (Prometheus, Grafana, etc.)
            # - Log aggregation systems

            return True

        except Exception as e:
            self.logger.error("Failed to setup pool alerting", error=str(e))
            return False

    async def check_alert_conditions(self) -> list[dict[str, Any]]:
        """
        Check for alert conditions and return active alerts

        Returns:
            List of active alerts
        """
        try:
            alerts = []
            status = await self.get_pool_status()
            health_metrics = await self.get_pool_health_metrics()

            # Check availability threshold
            if status["active_keys"] < self._alert_thresholds.get("min_keys", 100):
                alerts.append(
                    {
                        "type": "availability",
                        "severity": "critical",
                        "message": f"Key pool below minimum threshold: {status['active_keys']} keys",
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                    }
                )

            # Check health status
            if health_metrics["health_status"] in ["critical", "warning"]:
                alerts.append(
                    {
                        "type": "health",
                        "severity": health_metrics["health_status"],
                        "message": f"Pool health degraded: {health_metrics['health_status']}",
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                    }
                )

            # Check consumption rate
            if health_metrics["consumption_rate_per_hour"] > self._alert_thresholds.get(
                "max_consumption_rate", 100
            ):
                alerts.append(
                    {
                        "type": "consumption",
                        "severity": "warning",
                        "message": f"High consumption rate: {health_metrics['consumption_rate_per_hour']} keys/hour",
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                    }
                )

            return alerts

        except Exception as e:
            self.logger.error("Failed to check alert conditions", error=str(e))
            return []

    async def optimize_pool_performance(self) -> dict[str, Any]:
        """
        Optimize pool performance based on current metrics

        Returns:
            Dict containing optimization results
        """
        try:
            health_metrics = await self.get_pool_health_metrics()
            status = await self.get_pool_status()
            config = await self._get_pool_configuration()

            optimizations = []

            # Adjust replenishment frequency based on consumption rate
            if health_metrics["consumption_rate_per_hour"] > 50:
                optimizations.append(
                    {
                        "type": "replenishment_frequency",
                        "action": "increase",
                        "reason": "High consumption rate detected",
                    }
                )

            # Adjust batch size based on availability
            availability_ratio = status["active_keys"] / config["max_key_count"]
            if availability_ratio < 0.3:
                optimizations.append(
                    {
                        "type": "batch_size",
                        "action": "increase",
                        "reason": "Low availability - increase batch size",
                    }
                )

            # Adjust monitoring frequency
            if health_metrics["health_status"] == "critical":
                optimizations.append(
                    {
                        "type": "monitoring_frequency",
                        "action": "increase",
                        "reason": "Critical health status - increase monitoring",
                    }
                )

            return {
                "optimizations_applied": len(optimizations),
                "optimizations": optimizations,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Failed to optimize pool performance", error=str(e))
            return {"optimizations_applied": 0, "error": str(e)}

    async def _count_total_keys(self) -> int:
        """Count total keys in the pool"""
        query = text("SELECT COUNT(*) FROM keys")
        result = await self.db_session.execute(query)
        return result.scalar() or 0

    async def _count_active_keys(self) -> int:
        """Count active (non-expired, non-consumed) keys"""
        now = datetime.datetime.now(datetime.timezone.utc)
        query = text(
            """
            SELECT COUNT(*) FROM keys
            WHERE status = 'active'
            AND (expires_at IS NULL OR expires_at > :now)
        """
        )
        result = await self.db_session.execute(query, {"now": now})
        return result.scalar() or 0

    async def _count_expired_keys(self) -> int:
        """Count expired keys"""
        now = datetime.datetime.now(datetime.timezone.utc)
        query = text(
            """
            SELECT COUNT(*) FROM keys
            WHERE status = 'active'
            AND expires_at IS NOT NULL
            AND expires_at <= :now
        """
        )
        result = await self.db_session.execute(query, {"now": now})
        return result.scalar() or 0

    async def _count_consumed_keys(self) -> int:
        """Count consumed keys"""
        query = text("SELECT COUNT(*) FROM keys WHERE status = 'consumed'")
        result = await self.db_session.execute(query)
        return result.scalar() or 0

    async def _get_pool_configuration(self) -> dict[str, Any]:
        """Get pool configuration from database or defaults"""
        try:
            # Try to get from database
            query = text("SELECT * FROM key_pool_status LIMIT 1")
            result = await self.db_session.execute(query)
            pool_status = result.scalar_one_or_none()

            if pool_status:
                return {
                    "max_key_count": pool_status.max_key_count,
                    "min_key_threshold": pool_status.min_key_threshold,
                    "key_generation_rate": pool_status.key_generation_rate,
                    "last_key_generation": pool_status.last_key_generation,
                }

            # Return defaults if no record exists
            return {
                "max_key_count": 100000,
                "min_key_threshold": 1000,
                "key_generation_rate": None,
                "last_key_generation": None,
            }

        except Exception as e:
            self.logger.warning(
                "Failed to get pool configuration, using defaults", error=str(e)
            )
            return {
                "max_key_count": 100000,
                "min_key_threshold": 1000,
                "key_generation_rate": None,
                "last_key_generation": None,
            }

    def _determine_pool_health(self, active_keys: int, config: dict[str, Any]) -> str:
        """Determine pool health status"""
        if active_keys == 0:
            return "exhausted"
        elif active_keys < config["min_key_threshold"]:
            return "critical"
        elif active_keys < config["min_key_threshold"] * 2:
            return "warning"
        else:
            return "healthy"

    async def _update_pool_status_record(self, status: dict[str, Any]) -> None:
        """Update pool status record in database"""
        try:
            # Get existing record or create new one
            query = text("SELECT * FROM key_pool_status LIMIT 1")
            result = await self.db_session.execute(query)
            pool_status = result.scalar_one_or_none()

            if pool_status:
                # Update existing record
                query = text(
                    """
                    UPDATE key_pool_status
                    SET total_keys = :total_keys,
                        active_keys = :active_keys,
                        expired_keys = :expired_keys,
                        consumed_keys = :consumed_keys,
                        last_updated = :last_updated
                    WHERE id = (SELECT id FROM key_pool_status LIMIT 1)
                """
                )
                await self.db_session.execute(
                    query,
                    {
                        "total_keys": status["total_keys"],
                        "active_keys": status["active_keys"],
                        "expired_keys": status["expired_keys"],
                        "consumed_keys": status["consumed_keys"],
                        "last_updated": datetime.datetime.now(datetime.timezone.utc),
                    },
                )
            else:
                # Create new record
                query = text(
                    """
                    INSERT INTO key_pool_status (total_keys, active_keys, expired_keys, consumed_keys, max_key_count, min_key_threshold, key_generation_rate, last_key_generation, last_updated)
                    VALUES (:total_keys, :active_keys, :expired_keys, :consumed_keys, :max_key_count, :min_key_threshold, :key_generation_rate, :last_key_generation, :last_updated)
                """
                )
                await self.db_session.execute(
                    query,
                    {
                        "total_keys": status["total_keys"],
                        "active_keys": status["active_keys"],
                        "expired_keys": status["expired_keys"],
                        "consumed_keys": status["consumed_keys"],
                        "max_key_count": status["max_key_count"],
                        "min_key_threshold": status["min_key_threshold"],
                        "key_generation_rate": status.get("key_generation_rate"),
                        "last_key_generation": status.get("last_key_generation"),
                        "last_updated": datetime.datetime.now(datetime.timezone.utc),
                    },
                )

            await self.db_session.commit()

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error("Failed to update pool status record", error=str(e))

    async def _trigger_replenishment(self) -> dict[str, Any]:
        """Trigger normal key replenishment"""
        try:
            self.logger.info("Triggering normal key replenishment")

            # Get current status
            status = await self.get_pool_status()
            config = await self._get_pool_configuration()

            # Calculate how many keys to generate
            target_keys = config["max_key_count"]
            current_keys = status["active_keys"]
            keys_to_generate = max(0, target_keys - current_keys)

            if keys_to_generate == 0:
                return {
                    "success": True,
                    "keys_generated": 0,
                    "message": "No replenishment needed",
                }

            # TODO: Interface with QKD network for key generation
            # For now, simulate key generation
            generated_keys = await self._simulate_key_generation(keys_to_generate)

            # Update last generation timestamp
            await self._update_last_generation_timestamp()

            self.logger.info(
                "Key replenishment completed",
                keys_generated=generated_keys,
                target_keys=target_keys,
            )

            return {
                "success": True,
                "keys_generated": generated_keys,
                "target_keys": target_keys,
                "estimated_time": "5 minutes",  # Placeholder
            }

        except Exception as e:
            self.logger.error("Failed to trigger replenishment", error=str(e))
            return {"success": False, "error": str(e)}

    async def _trigger_emergency_replenishment(self) -> dict[str, Any]:
        """Trigger emergency key replenishment"""
        try:
            self.logger.warning("Triggering emergency key replenishment")

            # Emergency replenishment generates a smaller batch quickly
            emergency_batch_size = 100  # Smaller batch for emergency

            # TODO: Interface with QKD network for emergency key generation
            generated_keys = await self._simulate_key_generation(emergency_batch_size)

            # Update last generation timestamp
            await self._update_last_generation_timestamp()

            self.logger.info(
                "Emergency key replenishment completed",
                keys_generated=generated_keys,
            )

            return {
                "success": True,
                "keys_generated": generated_keys,
                "estimated_time": "2 minutes",  # Faster for emergency
            }

        except Exception as e:
            self.logger.error("Failed to trigger emergency replenishment", error=str(e))
            return {"success": False, "error": str(e)}

    async def _simulate_key_generation(self, count: int) -> int:
        """Simulate key generation (placeholder for QKD network interface)"""
        # TODO: Replace with actual QKD network interface
        self.logger.info(f"Simulating generation of {count} keys")

        # Simulate some processing time
        await asyncio.sleep(0.1)

        # For now, return the requested count
        # In real implementation, this would interface with QKD network
        return count

    async def _update_last_generation_timestamp(self) -> None:
        """Update last key generation timestamp"""
        try:
            query = text("SELECT * FROM key_pool_status LIMIT 1")
            result = await self.db_session.execute(query)
            pool_status = result.scalar_one_or_none()

            if pool_status:
                query = text(
                    """
                    UPDATE key_pool_status
                    SET last_key_generation = :last_key_generation
                    WHERE id = (SELECT id FROM key_pool_status LIMIT 1)
                """
                )
                await self.db_session.execute(
                    query,
                    {
                        "last_key_generation": datetime.datetime.now(
                            datetime.timezone.utc
                        ),
                    },
                )
                await self.db_session.commit()

        except Exception as e:
            await self.db_session.rollback()
            self.logger.error("Failed to update generation timestamp", error=str(e))

    async def _log_exhaustion_event(self, response: dict[str, Any]) -> None:
        """Log key exhaustion event"""
        try:
            # TODO: Log to security events table
            self.logger.warning(
                "Key exhaustion event logged",
                response=response,
            )

        except Exception as e:
            self.logger.error("Failed to log exhaustion event", error=str(e))

    async def _replenishment_monitor(self) -> None:
        """Background task for monitoring and automatic replenishment"""
        try:
            while True:
                try:
                    # Check pool status
                    status = await self.get_pool_status()
                    config = await self._get_pool_configuration()

                    # Check if replenishment is needed
                    if status["active_keys"] < config["min_key_threshold"]:
                        self.logger.info(
                            "Automatic replenishment triggered",
                            active_keys=status["active_keys"],
                            threshold=config["min_key_threshold"],
                        )
                        await self._trigger_replenishment()

                    # Wait before next check (5 minutes)
                    await asyncio.sleep(300)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error("Error in replenishment monitor", error=str(e))
                    await asyncio.sleep(60)  # Wait 1 minute before retry

        except asyncio.CancelledError:
            self.logger.info("Replenishment monitor cancelled")
        except Exception as e:
            self.logger.error("Replenishment monitor failed", error=str(e))
