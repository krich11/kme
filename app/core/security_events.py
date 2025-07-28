#!/usr/bin/env python3
"""
KME Security Event Types Module

Version: 1.0.0
Author: KME Development Team
Description: Security event types and definitions for ETSI QKD 014 compliance
License: [To be determined]

ToDo List:
- [x] Create security event types
- [ ] Add event validation
- [ ] Implement event categorization
- [ ] Add event severity levels
- [ ] Create event templates
- [ ] Add event documentation
- [ ] Implement event filtering
- [ ] Add event aggregation
- [ ] Create event reporting
- [ ] Add event monitoring

Progress: 10% (1/10 tasks completed)
"""

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SecurityEventType(Enum):
    """Security event types for ETSI QKD 014 compliance"""

    # Authentication Events
    SAE_AUTHENTICATION_SUCCESS = "sae_authentication_success"
    SAE_AUTHENTICATION_FAILURE = "sae_authentication_failure"
    KME_AUTHENTICATION_SUCCESS = "kme_authentication_success"
    KME_AUTHENTICATION_FAILURE = "kme_authentication_failure"
    MUTUAL_AUTHENTICATION_SUCCESS = "mutual_authentication_success"
    MUTUAL_AUTHENTICATION_FAILURE = "mutual_authentication_failure"

    # Certificate Events
    CERTIFICATE_VALIDATION_SUCCESS = "certificate_validation_success"
    CERTIFICATE_VALIDATION_FAILURE = "certificate_validation_failure"
    CERTIFICATE_EXPIRATION_WARNING = "certificate_expiration_warning"
    CERTIFICATE_REVOCATION_CHECK = "certificate_revocation_check"

    # Authorization Events
    KEY_ACCESS_AUTHORIZED = "key_access_authorized"
    KEY_ACCESS_DENIED = "key_access_denied"
    API_ACCESS_AUTHORIZED = "api_access_authorized"
    API_ACCESS_DENIED = "api_access_denied"
    RESOURCE_ACCESS_AUTHORIZED = "resource_access_authorized"
    RESOURCE_ACCESS_DENIED = "resource_access_denied"

    # Key Management Events
    KEY_GENERATION_SUCCESS = "key_generation_success"
    KEY_GENERATION_FAILURE = "key_generation_failure"
    KEY_DISTRIBUTION_SUCCESS = "key_distribution_success"
    KEY_DISTRIBUTION_FAILURE = "key_distribution_failure"
    KEY_RETRIEVAL_SUCCESS = "key_retrieval_success"
    KEY_RETRIEVAL_FAILURE = "key_retrieval_failure"
    KEY_CLEANUP_SUCCESS = "key_cleanup_success"
    KEY_CLEANUP_FAILURE = "key_cleanup_failure"

    # Network Security Events
    TLS_HANDSHAKE_SUCCESS = "tls_handshake_success"
    TLS_HANDSHAKE_FAILURE = "tls_handshake_failure"
    NETWORK_CONNECTION_ESTABLISHED = "network_connection_established"
    NETWORK_CONNECTION_TERMINATED = "network_connection_terminated"
    NETWORK_SECURITY_VIOLATION = "network_security_violation"

    # Compliance Events
    ETSI_COMPLIANCE_CHECK_SUCCESS = "etsi_compliance_check_success"
    ETSI_COMPLIANCE_CHECK_FAILURE = "etsi_compliance_check_failure"
    SECURITY_AUDIT_EVENT = "security_audit_event"
    COMPLIANCE_VIOLATION = "compliance_violation"


class SecurityEventSeverity(Enum):
    """Security event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventCategory(Enum):
    """Security event categories"""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    KEY_MANAGEMENT = "key_management"
    NETWORK_SECURITY = "network_security"
    COMPLIANCE = "compliance"


@dataclass
class SecurityEvent:
    """Security event data structure"""

    event_type: SecurityEventType
    severity: SecurityEventSeverity
    category: SecurityEventCategory
    timestamp: datetime.datetime
    user_id: str | None = None
    sae_id: str | None = None
    kme_id: str | None = None
    key_id: str | None = None
    resource: str | None = None
    details: dict[str, Any] | None = None
    etsi_compliance: bool = True
    specification: str = "ETSI GS QKD 014 V1.1.1"


class SecurityEventManager:
    """Security event manager for ETSI QKD 014 compliance"""

    def __init__(self):
        """Initialize security event manager"""
        self.event_definitions = self._create_event_definitions()

    def _create_event_definitions(self) -> dict[SecurityEventType, dict[str, Any]]:
        """Create event definitions with metadata"""
        return {
            SecurityEventType.SAE_AUTHENTICATION_SUCCESS: {
                "description": "SAE successfully authenticated with KME",
                "severity": SecurityEventSeverity.LOW,
                "category": SecurityEventCategory.AUTHENTICATION,
                "etsi_required": True,
            },
            SecurityEventType.SAE_AUTHENTICATION_FAILURE: {
                "description": "SAE authentication failed",
                "severity": SecurityEventSeverity.HIGH,
                "category": SecurityEventCategory.AUTHENTICATION,
                "etsi_required": True,
            },
            SecurityEventType.KME_AUTHENTICATION_SUCCESS: {
                "description": "KME successfully authenticated with SAE",
                "severity": SecurityEventSeverity.LOW,
                "category": SecurityEventCategory.AUTHENTICATION,
                "etsi_required": True,
            },
            SecurityEventType.KME_AUTHENTICATION_FAILURE: {
                "description": "KME authentication failed",
                "severity": SecurityEventSeverity.HIGH,
                "category": SecurityEventCategory.AUTHENTICATION,
                "etsi_required": True,
            },
            SecurityEventType.KEY_ACCESS_AUTHORIZED: {
                "description": "Key access authorized",
                "severity": SecurityEventSeverity.LOW,
                "category": SecurityEventCategory.AUTHORIZATION,
                "etsi_required": True,
            },
            SecurityEventType.KEY_ACCESS_DENIED: {
                "description": "Key access denied",
                "severity": SecurityEventSeverity.MEDIUM,
                "category": SecurityEventCategory.AUTHORIZATION,
                "etsi_required": True,
            },
            SecurityEventType.KEY_DISTRIBUTION_SUCCESS: {
                "description": "Key distribution successful",
                "severity": SecurityEventSeverity.LOW,
                "category": SecurityEventCategory.KEY_MANAGEMENT,
                "etsi_required": True,
            },
            SecurityEventType.KEY_DISTRIBUTION_FAILURE: {
                "description": "Key distribution failed",
                "severity": SecurityEventSeverity.HIGH,
                "category": SecurityEventCategory.KEY_MANAGEMENT,
                "etsi_required": True,
            },
            SecurityEventType.TLS_HANDSHAKE_SUCCESS: {
                "description": "TLS handshake successful",
                "severity": SecurityEventSeverity.LOW,
                "category": SecurityEventCategory.NETWORK_SECURITY,
                "etsi_required": True,
            },
            SecurityEventType.TLS_HANDSHAKE_FAILURE: {
                "description": "TLS handshake failed",
                "severity": SecurityEventSeverity.HIGH,
                "category": SecurityEventCategory.NETWORK_SECURITY,
                "etsi_required": True,
            },
            SecurityEventType.ETSI_COMPLIANCE_CHECK_SUCCESS: {
                "description": "ETSI compliance check passed",
                "severity": SecurityEventSeverity.LOW,
                "category": SecurityEventCategory.COMPLIANCE,
                "etsi_required": True,
            },
            SecurityEventType.ETSI_COMPLIANCE_CHECK_FAILURE: {
                "description": "ETSI compliance check failed",
                "severity": SecurityEventSeverity.CRITICAL,
                "category": SecurityEventCategory.COMPLIANCE,
                "etsi_required": True,
            },
        }

    def get_event_definition(self, event_type: SecurityEventType) -> dict[str, Any]:
        """Get event definition"""
        return self.event_definitions.get(event_type, {})

    def create_security_event(
        self,
        event_type: SecurityEventType,
        user_id: str | None = None,
        sae_id: str | None = None,
        kme_id: str | None = None,
        key_id: str | None = None,
        resource: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Create a security event"""
        definition = self.get_event_definition(event_type)

        return SecurityEvent(
            event_type=event_type,
            severity=definition.get("severity", SecurityEventSeverity.MEDIUM),
            category=definition.get("category", SecurityEventCategory.COMPLIANCE),
            timestamp=datetime.datetime.utcnow(),
            user_id=user_id,
            sae_id=sae_id,
            kme_id=kme_id,
            key_id=key_id,
            resource=resource,
            details=details or {},
            etsi_compliance=definition.get("etsi_required", True),
            specification="ETSI GS QKD 014 V1.1.1",
        )

    def validate_event(self, event: SecurityEvent) -> bool:
        """Validate security event"""
        definition = self.get_event_definition(event.event_type)
        if not definition:
            return False

        # Check required fields based on event type
        if event.event_type in [
            SecurityEventType.SAE_AUTHENTICATION_SUCCESS,
            SecurityEventType.SAE_AUTHENTICATION_FAILURE,
        ]:
            if not event.sae_id or not event.kme_id:
                return False

        if event.event_type in [
            SecurityEventType.KEY_ACCESS_AUTHORIZED,
            SecurityEventType.KEY_ACCESS_DENIED,
        ]:
            if not event.key_id or not event.user_id:
                return False

        return True


# Global security event manager
security_event_manager = SecurityEventManager()


def get_security_event_manager() -> SecurityEventManager:
    """Get security event manager instance"""
    return security_event_manager


def create_security_event(
    event_type: SecurityEventType,
    user_id: str | None = None,
    sae_id: str | None = None,
    kme_id: str | None = None,
    key_id: str | None = None,
    resource: str | None = None,
    details: dict[str, Any] | None = None,
) -> SecurityEvent:
    """Create a security event"""
    return security_event_manager.create_security_event(
        event_type=event_type,
        user_id=user_id,
        sae_id=sae_id,
        kme_id=kme_id,
        key_id=key_id,
        resource=resource,
        details=details,
    )


# Export security event types
__all__ = [
    "SecurityEventType",
    "SecurityEventSeverity",
    "SecurityEventCategory",
    "SecurityEvent",
    "SecurityEventManager",
    "security_event_manager",
    "get_security_event_manager",
    "create_security_event",
]
