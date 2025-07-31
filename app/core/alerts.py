#!/usr/bin/env python3
"""
KME Performance Alerting Module

Version: 1.0.0
Author: KME Development Team
Description: Performance alerting and notification system for KME
License: [To be determined]

ToDo List:
- [x] Create performance alerting
- [ ] Add alert thresholds
- [ ] Implement alert notifications
- [ ] Add alert escalation
- [ ] Create alert history
- [ ] Add alert suppression
- [ ] Implement alert routing
- [ ] Add alert templates
- [ ] Create alert dashboard
- [ ] Add alert analytics

Progress: 10% (1/10 tasks completed)
"""

import asyncio
import datetime
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .logging import logger, performance_logger


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Alert types"""

    PERFORMANCE = "performance"
    SECURITY = "security"
    SYSTEM = "system"
    DATABASE = "database"
    NETWORK = "network"
    COMPLIANCE = "compliance"


@dataclass
class Alert:
    """Alert data structure"""

    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime.datetime
    source: str
    details: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime.datetime | None = None
    resolved_by: str | None = None
    resolved_at: datetime.datetime | None = None


class AlertThreshold:
    """Alert threshold configuration"""

    def __init__(
        self,
        metric_name: str,
        threshold_value: float,
        severity: AlertSeverity,
        comparison: str = ">",
        duration_minutes: int = 5,
    ):
        self.metric_name = metric_name
        self.threshold_value = threshold_value
        self.severity = severity
        self.comparison = comparison  # >, <, >=, <=, ==
        self.duration_minutes = duration_minutes
        self.triggered = False
        self.last_check: datetime.datetime | None = None


class AlertManager:
    """Alert management system for KME"""

    def __init__(self):
        """Initialize alert manager"""
        self.alerts: list[Alert] = []
        self.thresholds: dict[str, AlertThreshold] = {}
        self.notification_handlers: list[Callable] = []
        self.alert_id_counter = 0

        # Set up default thresholds
        self._setup_default_thresholds()

    def _setup_default_thresholds(self):
        """Setup default alert thresholds"""
        self.add_threshold(
            AlertThreshold("cpu_percent", 80.0, AlertSeverity.WARNING, ">", 5)
        )
        self.add_threshold(
            AlertThreshold("cpu_percent", 90.0, AlertSeverity.ERROR, ">", 2)
        )
        self.add_threshold(
            AlertThreshold("memory_percent", 85.0, AlertSeverity.WARNING, ">", 5)
        )
        self.add_threshold(
            AlertThreshold("memory_percent", 95.0, AlertSeverity.ERROR, ">", 2)
        )
        self.add_threshold(
            AlertThreshold("disk_percent", 90.0, AlertSeverity.WARNING, ">", 5)
        )
        self.add_threshold(
            AlertThreshold("api_response_time", 1000.0, AlertSeverity.WARNING, ">", 5)
        )
        self.add_threshold(
            AlertThreshold("api_response_time", 5000.0, AlertSeverity.ERROR, ">", 2)
        )
        self.add_threshold(
            AlertThreshold("database_query_time", 1000.0, AlertSeverity.WARNING, ">", 5)
        )
        self.add_threshold(
            AlertThreshold("database_query_time", 5000.0, AlertSeverity.ERROR, ">", 2)
        )

    def add_threshold(self, threshold: AlertThreshold):
        """Add an alert threshold"""
        self.thresholds[threshold.metric_name] = threshold
        logger.info(
            f"Added alert threshold: {threshold.metric_name} {threshold.comparison} {threshold.threshold_value}"
        )

    def remove_threshold(self, metric_name: str):
        """Remove an alert threshold"""
        if metric_name in self.thresholds:
            del self.thresholds[metric_name]
            logger.info(f"Removed alert threshold: {metric_name}")

    def check_threshold(self, metric_name: str, value: float) -> Alert | None:
        """Check if a metric value triggers an alert threshold"""
        if metric_name not in self.thresholds:
            return None

        threshold = self.thresholds[metric_name]
        triggered = False

        # Check threshold condition
        if threshold.comparison == ">":
            triggered = value > threshold.threshold_value
        elif threshold.comparison == "<":
            triggered = value < threshold.threshold_value
        elif threshold.comparison == ">=":
            triggered = value >= threshold.threshold_value
        elif threshold.comparison == "<=":
            triggered = value <= threshold.threshold_value
        elif threshold.comparison == "==":
            triggered = value == threshold.threshold_value

        if triggered and not threshold.triggered:
            # Create alert
            alert = self.create_alert(
                type=AlertType.PERFORMANCE,
                severity=threshold.severity,
                title=f"Performance threshold exceeded: {metric_name}",
                message=f"Metric {metric_name} value {value} exceeded threshold {threshold.threshold_value}",
                source=metric_name,
                details={
                    "metric_name": metric_name,
                    "current_value": value,
                    "threshold_value": threshold.threshold_value,
                    "comparison": threshold.comparison,
                    "duration_minutes": threshold.duration_minutes,
                },
            )

            threshold.triggered = True
            threshold.last_check = datetime.datetime.now(datetime.timezone.utc)

            # Send notifications
            asyncio.create_task(self._send_notifications(alert))

            return alert

        elif not triggered and threshold.triggered:
            # Reset threshold
            threshold.triggered = False
            threshold.last_check = datetime.datetime.now(datetime.timezone.utc)

        return None

    def create_alert(
        self,
        type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str,
        details: dict[str, Any] | None = None,
    ) -> Alert:
        """Create a new alert"""
        self.alert_id_counter += 1
        alert_id = f"alert_{self.alert_id_counter}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        alert = Alert(
            id=alert_id,
            type=type,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.datetime.utcnow(),
            source=source,
            details=details or {},
        )

        self.alerts.append(alert)

        # Log the alert
        logger.warning(
            f"Alert created: {alert.title}",
            alert_id=alert.id,
            alert_type=alert.type.value,
            alert_severity=alert.severity.value,
            alert_source=alert.source,
            alert_details=alert.details,
        )

        return alert

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.acknowledged:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.datetime.utcnow()

                logger.info(
                    f"Alert acknowledged: {alert.title}",
                    alert_id=alert.id,
                    acknowledged_by=acknowledged_by,
                )
                return True

        return False

    def resolve_alert(self, alert_id: str, resolved_by: str):
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_by = resolved_by
                alert.resolved_at = datetime.datetime.utcnow()

                logger.info(
                    f"Alert resolved: {alert.title}",
                    alert_id=alert.id,
                    resolved_by=resolved_by,
                )
                return True

        return False

    def get_active_alerts(self) -> list[Alert]:
        """Get all active (unresolved) alerts"""
        return [alert for alert in self.alerts if not alert.resolved]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> list[Alert]:
        """Get alerts by severity"""
        return [alert for alert in self.alerts if alert.severity == severity]

    def get_alerts_by_type(self, alert_type: AlertType) -> list[Alert]:
        """Get alerts by type"""
        return [alert for alert in self.alerts if alert.type == alert_type]

    def clear_old_alerts(self, max_age_hours: int = 24):
        """Clear alerts older than specified age"""
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(
            hours=max_age_hours
        )
        old_count = len(self.alerts)

        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]

        cleared_count = old_count - len(self.alerts)
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} old alerts")

    def add_notification_handler(self, handler: Callable):
        """Add a notification handler"""
        self.notification_handlers.append(handler)
        logger.info("Added notification handler")

    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")


# Global alert manager instance
alert_manager = AlertManager()


def get_alert_manager() -> AlertManager:
    """Get alert manager instance"""
    return alert_manager


def create_alert(
    type: AlertType,
    severity: AlertSeverity,
    title: str,
    message: str,
    source: str,
    details: dict[str, Any] | None = None,
) -> Alert:
    """Create a new alert"""
    return alert_manager.create_alert(type, severity, title, message, source, details)


def check_performance_threshold(metric_name: str, value: float) -> Alert | None:
    """Check if a performance metric triggers an alert"""
    return alert_manager.check_threshold(metric_name, value)


# Export alerting functions
__all__ = [
    "AlertSeverity",
    "AlertType",
    "Alert",
    "AlertThreshold",
    "AlertManager",
    "alert_manager",
    "get_alert_manager",
    "create_alert",
    "check_performance_threshold",
]
