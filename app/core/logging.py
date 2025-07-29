#!/usr/bin/env python3
"""
KME Logging Configuration Module

Version: 1.0.0
Author: KME Development Team
Description: Structured logging configuration for KME system
License: [To be determined]

ToDo List:
- [x] Create logging configuration
- [ ] Add log level filtering
- [ ] Implement security event logging
- [ ] Add performance metrics logging
- [ ] Create audit trail logging
- [ ] Add log rotation
- [ ] Implement log aggregation
- [ ] Add log monitoring
- [ ] Create log analysis tools
- [ ] Add log backup

Progress: 10% (1/10 tasks completed)
"""

import datetime
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.processors import (
    JSONRenderer,
    StackInfoRenderer,
    TimeStamper,
    UnicodeDecoder,
    format_exc_info,
)
from structlog.stdlib import LoggerFactory

from .security_events import (
    SecurityEvent,
    SecurityEventCategory,
    SecurityEventSeverity,
    SecurityEventType,
    create_security_event,
)


class LoggingConfig:
    """Logging configuration manager"""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize logging configuration"""
        self.config = config or {}
        self.logger = None
        self._setup_logging()

    def _setup_logging(self):
        """Setup structured logging configuration"""
        # Configure structlog processors
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            TimeStamper(fmt="iso"),
            StackInfoRenderer(),
            format_exc_info,
            UnicodeDecoder(),
            JSONRenderer(),
        ]

        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Create logger
        self.logger = structlog.get_logger(__name__)

    def set_log_level(self, level: str):
        """Set logging level for all loggers"""
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logging.getLogger().setLevel(numeric_level)

        # Update structlog configuration
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                TimeStamper(fmt="iso"),
                StackInfoRenderer(),
                format_exc_info,
                UnicodeDecoder(),
                JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        self.logger.info("Log level updated", level=level, numeric_level=numeric_level)

    def add_log_filter(self, filter_func):
        """Add custom log filter"""
        # Add filter to root logger
        logging.getLogger().addFilter(filter_func)
        self.logger.info("Custom log filter added")

    def get_logger(self, name: str = None) -> structlog.BoundLogger:
        """Get structured logger"""
        if name:
            return structlog.get_logger(name)
        return self.logger

    def setup_file_logging(self, log_file: str, log_level: str = "INFO"):
        """Setup file logging"""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))

        # Add file handler to root logger
        logging.getLogger().addHandler(file_handler)

        self.logger.info(
            f"File logging configured", log_file=log_file, log_level=log_level
        )

    def setup_console_logging(self, log_level: str = "INFO"):
        """Setup console logging"""
        # Configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))

        # Add console handler to root logger
        logging.getLogger().addHandler(console_handler)

        self.logger.info(f"Console logging configured", log_level=log_level)


class SecurityLogger:
    """Security event logging"""

    def __init__(self, logger: structlog.BoundLogger):
        """Initialize security logger"""
        self.logger = logger

    def log_authentication_event(
        self,
        event_type: str,
        user_id: str,
        success: bool,
        details: dict[str, Any] | None = None,
    ):
        """Log authentication event"""
        self.logger.info(
            "Authentication event",
            event_type=event_type,
            user_id=user_id,
            success=success,
            details=details or {},
            category="security",
            severity="info",
        )

    def log_authorization_event(
        self,
        event_type: str,
        user_id: str,
        resource: str,
        granted: bool,
        details: dict[str, Any] | None = None,
    ):
        """Log authorization event"""
        # Create security event
        security_event_type = (
            SecurityEventType.KEY_ACCESS_AUTHORIZED
            if granted and "key" in resource.lower()
            else SecurityEventType.KEY_ACCESS_DENIED
            if not granted and "key" in resource.lower()
            else SecurityEventType.API_ACCESS_AUTHORIZED
            if granted and "api" in resource.lower()
            else SecurityEventType.API_ACCESS_DENIED
            if not granted and "api" in resource.lower()
            else SecurityEventType.RESOURCE_ACCESS_AUTHORIZED
            if granted
            else SecurityEventType.RESOURCE_ACCESS_DENIED
        )

        security_event = create_security_event(
            event_type=security_event_type,
            user_id=user_id,
            resource=resource,
            details={
                "original_event_type": event_type,
                "authorization_result": "granted" if granted else "denied",
                **(details or {}),
            },
        )

        self.logger.info(
            "Authorization event",
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            granted=granted,
            details=details or {},
            category="security",
            severity="info",
            security_event=security_event,
        )

    def log_security_violation(
        self,
        violation_type: str,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Log security violation"""
        self.logger.warning(
            "Security violation",
            violation_type=violation_type,
            user_id=user_id,
            details=details or {},
            category="security",
            severity="warning",
        )

    def log_key_access_event(
        self,
        event_type: str,
        key_id: str,
        user_id: str,
        success: bool,
        details: dict[str, Any] | None = None,
    ):
        """Log key access event"""
        # Create security event
        security_event_type = (
            SecurityEventType.KEY_ACCESS_AUTHORIZED
            if success
            else SecurityEventType.KEY_ACCESS_DENIED
        )

        security_event = create_security_event(
            event_type=security_event_type,
            user_id=user_id,
            key_id=key_id,
            details={
                "original_event_type": event_type,
                "access_result": "success" if success else "failure",
                **(details or {}),
            },
        )

        self.logger.info(
            "Key access event",
            event_type=event_type,
            key_id=key_id,
            user_id=user_id,
            success=success,
            details=details or {},
            category="security",
            severity="info",
            security_event=security_event,
        )

    def log_sae_authentication(
        self,
        sae_id: str,
        kme_id: str,
        success: bool,
        certificate_info: dict[str, Any] | None = None,
    ):
        """Log SAE authentication event (ETSI QKD 014 specific)"""
        # Create security event
        event_type = (
            SecurityEventType.SAE_AUTHENTICATION_SUCCESS
            if success
            else SecurityEventType.SAE_AUTHENTICATION_FAILURE
        )

        security_event = create_security_event(
            event_type=event_type,
            sae_id=sae_id,
            kme_id=kme_id,
            details={
                "certificate_info": certificate_info or {},
                "authentication_method": "certificate_based",
                "etsi_compliance": True,
            },
        )

        # Log the event
        self.logger.info(
            "SAE authentication",
            sae_id=sae_id,
            kme_id=kme_id,
            success=success,
            certificate_info=certificate_info or {},
            category="security",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
            security_event=security_event,
        )

    def log_kme_authentication(
        self,
        kme_id: str,
        sae_id: str,
        success: bool,
        certificate_info: dict[str, Any] | None = None,
    ):
        """Log KME authentication event (ETSI QKD 014 specific)"""
        self.logger.info(
            "KME authentication",
            kme_id=kme_id,
            sae_id=sae_id,
            success=success,
            certificate_info=certificate_info or {},
            category="security",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
        )

    def log_certificate_validation(
        self,
        certificate_type: str,
        subject_id: str,
        success: bool,
        validation_details: dict[str, Any] | None = None,
    ):
        """Log certificate validation event"""
        # Create security event
        security_event_type = (
            SecurityEventType.CERTIFICATE_VALIDATION_SUCCESS
            if success
            else SecurityEventType.CERTIFICATE_VALIDATION_FAILURE
        )

        security_event = create_security_event(
            event_type=security_event_type,
            user_id=subject_id,
            details={
                "certificate_type": certificate_type,
                "validation_result": "success" if success else "failure",
                "validation_details": validation_details or {},
                "etsi_compliance": True,
            },
        )

        self.logger.info(
            "Certificate validation",
            certificate_type=certificate_type,
            subject_id=subject_id,
            success=success,
            validation_details=validation_details or {},
            category="security",
            severity="info",
            etsi_compliance=True,
            security_event=security_event,
        )


class AuditLogger:
    """Audit trail logging"""

    def __init__(self, logger: structlog.BoundLogger):
        """Initialize audit logger"""
        self.logger = logger

    def log_api_request(
        self, method: str, path: str, user_id: str, status_code: int, duration_ms: float
    ):
        """Log API request"""
        self.logger.info(
            "API request",
            method=method,
            path=path,
            user_id=user_id,
            status_code=status_code,
            duration_ms=duration_ms,
            category="audit",
            severity="info",
        )

    def log_etsi_api_request(
        self,
        endpoint: str,
        method: str,
        sae_id: str,
        kme_id: str,
        status_code: int,
        duration_ms: float,
        request_details: dict[str, Any] | None = None,
    ):
        """Log ETSI QKD 014 API request"""
        self.logger.info(
            "ETSI API request",
            endpoint=endpoint,
            method=method,
            sae_id=sae_id,
            kme_id=kme_id,
            status_code=status_code,
            duration_ms=duration_ms,
            request_details=request_details or {},
            category="audit",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
        )

    def log_key_distribution_event(
        self,
        event_type: str,
        master_sae_id: str,
        slave_sae_id: str,
        key_count: int,
        key_size: int,
        success: bool,
        details: dict[str, Any] | None = None,
    ):
        """Log key distribution event (ETSI QKD 014 specific)"""
        self.logger.info(
            "Key distribution event",
            event_type=event_type,
            master_sae_id=master_sae_id,
            slave_sae_id=slave_sae_id,
            key_count=key_count,
            key_size=key_size,
            success=success,
            details=details or {},
            category="audit",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
        )

    def log_database_operation(
        self,
        operation: str,
        table: str,
        user_id: str,
        success: bool,
        details: dict[str, Any] | None = None,
    ):
        """Log database operation"""
        self.logger.info(
            "Database operation",
            operation=operation,
            table=table,
            user_id=user_id,
            success=success,
            details=details or {},
            category="audit",
            severity="info",
        )

    def log_configuration_change(
        self, change_type: str, user_id: str, details: dict[str, Any] | None = None
    ):
        """Log configuration change"""
        self.logger.info(
            "Configuration change",
            change_type=change_type,
            user_id=user_id,
            details=details or {},
            category="audit",
            severity="info",
        )

    def log_etsi_compliance_event(
        self,
        compliance_type: str,
        event_description: str,
        success: bool,
        details: dict[str, Any] | None = None,
    ):
        """Log ETSI QKD 014 compliance event"""
        self.logger.info(
            "ETSI compliance event",
            compliance_type=compliance_type,
            event_description=event_description,
            success=success,
            details=details or {},
            category="audit",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
        )

    def log_security_audit_trail(
        self,
        audit_event: str,
        user_id: str,
        resource: str,
        action: str,
        result: str,
        details: dict[str, Any] | None = None,
    ):
        """Log security audit trail event"""
        self.logger.info(
            "Security audit trail",
            audit_event=audit_event,
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            category="audit",
            severity="info",
            etsi_compliance=True,
            timestamp=datetime.datetime.utcnow().isoformat(),
        )


class PerformanceLogger:
    """Performance metrics logging"""

    def __init__(self, logger: structlog.BoundLogger):
        """Initialize performance logger"""
        self.logger = logger

    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        details: dict[str, Any] | None = None,
    ):
        """Log performance metric"""
        self.logger.info(
            "Performance metric",
            metric_name=metric_name,
            value=value,
            unit=unit,
            details=details or {},
            category="performance",
            severity="info",
        )

    def log_system_health(
        self, component: str, status: str, details: dict[str, Any] | None = None
    ):
        """Log system health"""
        self.logger.info(
            "System health",
            component=component,
            status=status,
            details=details or {},
            category="performance",
            severity="info",
        )

    def log_key_pool_status(
        self,
        stored_key_count: int,
        max_key_count: int,
        available_keys: int,
        key_size: int,
        details: dict[str, Any] | None = None,
    ):
        """Log key pool status (ETSI QKD 014 specific)"""
        self.logger.info(
            "Key pool status",
            stored_key_count=stored_key_count,
            max_key_count=max_key_count,
            available_keys=available_keys,
            key_size=key_size,
            utilization_percent=(stored_key_count / max_key_count * 100)
            if max_key_count > 0
            else 0,
            details=details or {},
            category="performance",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
        )

    def log_qkd_network_status(
        self,
        link_status: str,
        key_generation_rate: float,
        link_quality: str,
        details: dict[str, Any] | None = None,
    ):
        """Log QKD network status"""
        self.logger.info(
            "QKD network status",
            link_status=link_status,
            key_generation_rate=key_generation_rate,
            link_quality=link_quality,
            details=details or {},
            category="performance",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
        )

    def log_api_performance_metrics(
        self,
        endpoint: str,
        response_time_ms: float,
        throughput_requests_per_sec: float,
        error_rate_percent: float,
        details: dict[str, Any] | None = None,
    ):
        """Log API performance metrics"""
        self.logger.info(
            "API performance metrics",
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            throughput_requests_per_sec=throughput_requests_per_sec,
            error_rate_percent=error_rate_percent,
            details=details or {},
            category="performance",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
        )

    def log_key_management_metrics(
        self,
        key_generation_rate: float,
        key_distribution_rate: float,
        key_retrieval_rate: float,
        key_cleanup_rate: float,
        details: dict[str, Any] | None = None,
    ):
        """Log key management performance metrics"""
        self.logger.info(
            "Key management metrics",
            key_generation_rate=key_generation_rate,
            key_distribution_rate=key_distribution_rate,
            key_retrieval_rate=key_retrieval_rate,
            key_cleanup_rate=key_cleanup_rate,
            details=details or {},
            category="performance",
            severity="info",
            etsi_compliance=True,
            specification="ETSI GS QKD 014 V1.1.1",
        )


# Security event categories for ETSI QKD 014 compliance
SECURITY_EVENT_CATEGORIES = {
    "authentication": {
        "sae_auth": "SAE authentication events",
        "kme_auth": "KME authentication events",
        "cert_validation": "Certificate validation events",
        "mutual_auth": "Mutual authentication events",
    },
    "authorization": {
        "key_access": "Key access authorization",
        "api_access": "API endpoint authorization",
        "resource_access": "Resource access control",
    },
    "key_management": {
        "key_generation": "Key generation events",
        "key_distribution": "Key distribution events",
        "key_retrieval": "Key retrieval events",
        "key_cleanup": "Key cleanup events",
    },
    "network_security": {
        "tls_handshake": "TLS handshake events",
        "certificate_management": "Certificate management events",
        "network_monitoring": "Network security monitoring",
    },
    "compliance": {
        "etsi_audit": "ETSI QKD 014 compliance events",
        "security_violations": "Security violation events",
        "audit_trail": "Audit trail events",
    },
}

# Global logging configuration
logging_config = LoggingConfig()

# Get main logger
logger = logging_config.get_logger()

# Create specialized loggers
security_logger = SecurityLogger(logger)
audit_logger = AuditLogger(logger)
performance_logger = PerformanceLogger(logger)


def setup_logging(log_level: str = "INFO", log_file: str | None = None):
    """Setup logging configuration"""
    # Setup console logging
    logging_config.setup_console_logging(log_level)

    # Setup file logging if specified
    if log_file:
        logging_config.setup_file_logging(log_file, log_level)

    logger.info("Logging system initialized", log_level=log_level, log_file=log_file)


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get logger instance"""
    return logging_config.get_logger(name)


# Export specialized loggers
__all__ = [
    "logger",
    "security_logger",
    "audit_logger",
    "performance_logger",
    "setup_logging",
    "get_logger",
]
