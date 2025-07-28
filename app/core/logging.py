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
        details: dict[str, Any] = None,
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
        details: dict[str, Any] = None,
    ):
        """Log authorization event"""
        self.logger.info(
            "Authorization event",
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            granted=granted,
            details=details or {},
            category="security",
            severity="info",
        )

    def log_security_violation(
        self, violation_type: str, user_id: str = None, details: dict[str, Any] = None
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
        details: dict[str, Any] = None,
    ):
        """Log key access event"""
        self.logger.info(
            "Key access event",
            event_type=event_type,
            key_id=key_id,
            user_id=user_id,
            success=success,
            details=details or {},
            category="security",
            severity="info",
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

    def log_database_operation(
        self,
        operation: str,
        table: str,
        user_id: str,
        success: bool,
        details: dict[str, Any] = None,
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
        self, change_type: str, user_id: str, details: dict[str, Any] = None
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


class PerformanceLogger:
    """Performance metrics logging"""

    def __init__(self, logger: structlog.BoundLogger):
        """Initialize performance logger"""
        self.logger = logger

    def log_performance_metric(
        self, metric_name: str, value: float, unit: str, details: dict[str, Any] = None
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
        self, component: str, status: str, details: dict[str, Any] = None
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


def get_logger(name: str = None) -> structlog.BoundLogger:
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
