#!/usr/bin/env python3
"""
KME Database Models

Version: 1.0.0
Author: KME Development Team
Description: Database models for KME internal operations
License: [To be determined]

ToDo List:
- [x] Create database models
- [x] Add KME entity model
- [x] Add SAE entity model
- [x] Add key record model
- [x] Add key request model
- [x] Add event models
- [x] Add performance models
- [x] Add validation rules
- [ ] Add model testing
- [ ] Add model documentation
- [ ] Add model serialization
- [ ] Add model deserialization
- [ ] Add model conversion utilities
- [ ] Add model versioning
- [ ] Add model migration support

Progress: 60% (8/15 tasks completed)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class KMEEntity(BaseModel):
    """KME entity database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    kme_id: str = Field(..., description="Unique KME identifier")
    hostname: str = Field(..., description="KME hostname")
    port: int = Field(default=443, description="KME port")
    certificate_info: dict[str, Any] | None = Field(
        None, description="Certificate information"
    )
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    @field_validator("kme_id")
    @classmethod
    def validate_kme_id(cls, v):
        """Validate KME ID length"""
        if len(v) != 16:
            raise ValueError("KME ID must be exactly 16 characters")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        """Validate port number"""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class SAEEntity(BaseModel):
    """SAE entity database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    sae_id: str = Field(..., description="Unique SAE identifier")
    kme_id: str = Field(..., description="Associated KME ID")
    certificate_info: dict[str, Any] | None = Field(
        None, description="Certificate information"
    )
    registration_date: datetime | None = Field(
        None, description="Registration timestamp"
    )
    last_seen: datetime | None = Field(None, description="Last activity timestamp")
    status: str = Field(default="active", description="SAE status")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    @field_validator("sae_id", "kme_id")
    @classmethod
    def validate_id_length(cls, v):
        """Validate ID length"""
        if len(v) != 16:
            raise ValueError("ID must be exactly 16 characters")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status value"""
        valid_statuses = ["active", "inactive", "suspended", "expired"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class KeyRecord(BaseModel):
    """Key record database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    key_id: str = Field(..., description="Unique key identifier (UUID)")
    key_data: bytes = Field(..., description="Key data as bytes")
    key_size: int = Field(..., description="Key size in bits")
    master_sae_id: str = Field(..., description="Master SAE ID")
    slave_sae_id: str = Field(..., description="Slave SAE ID")
    source_kme_id: str = Field(..., description="Source KME ID")
    target_kme_id: str = Field(..., description="Target KME ID")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    status: str = Field(default="active", description="Key status")
    additional_slave_sae_ids: list[str] | None = Field(
        None, description="Additional slave SAE IDs"
    )
    key_metadata: dict[str, Any] | None = Field(None, description="Key metadata")

    @field_validator("key_id")
    @classmethod
    def validate_key_id(cls, v):
        """Validate key ID is a valid UUID"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("key_id must be a valid UUID")
        return v

    @field_validator("key_size")
    @classmethod
    def validate_key_size(cls, v):
        """Validate key size"""
        if v <= 0:
            raise ValueError("Key size must be positive")
        if v > 8192:
            raise ValueError("Key size cannot exceed 8192 bits")
        return v

    @field_validator("master_sae_id", "slave_sae_id", "source_kme_id", "target_kme_id")
    @classmethod
    def validate_id_length(cls, v):
        """Validate ID length"""
        if len(v) != 16:
            raise ValueError("ID must be exactly 16 characters")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status value"""
        valid_statuses = ["active", "expired", "consumed", "revoked"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v

    @field_validator("additional_slave_sae_ids")
    @classmethod
    def validate_additional_sae_ids(cls, v):
        """Validate additional SAE IDs"""
        if v is not None:
            for sae_id in v:
                if len(sae_id) != 16:
                    raise ValueError("SAE ID must be exactly 16 characters")
        return v


class KeyRequestRecord(BaseModel):
    """Key request record database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    request_id: str = Field(..., description="Unique request identifier")
    master_sae_id: str = Field(..., description="Master SAE ID")
    slave_sae_id: str = Field(..., description="Slave SAE ID")
    number_of_keys: int = Field(default=1, description="Number of keys requested")
    key_size: int = Field(..., description="Key size in bits")
    additional_slave_sae_ids: list[str] | None = Field(
        None, description="Additional slave SAE IDs"
    )
    extension_mandatory: dict[str, Any] | None = Field(
        None, description="Mandatory extensions"
    )
    extension_optional: dict[str, Any] | None = Field(
        None, description="Optional extensions"
    )
    status: str = Field(default="pending", description="Request status")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error_message: str | None = Field(None, description="Error message if failed")

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, v):
        """Validate request ID is a valid UUID"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("request_id must be a valid UUID")
        return v

    @field_validator("master_sae_id", "slave_sae_id")
    @classmethod
    def validate_id_length(cls, v):
        """Validate ID length"""
        if len(v) != 16:
            raise ValueError("ID must be exactly 16 characters")
        return v

    @field_validator("number_of_keys")
    @classmethod
    def validate_number_of_keys(cls, v):
        """Validate number of keys"""
        if v <= 0:
            raise ValueError("Number of keys must be positive")
        return v

    @field_validator("key_size")
    @classmethod
    def validate_key_size(cls, v):
        """Validate key size"""
        if v <= 0:
            raise ValueError("Key size must be positive")
        if v % 8 != 0:
            raise ValueError("Key size must be a multiple of 8")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status value"""
        valid_statuses = ["pending", "processing", "completed", "failed", "cancelled"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class KeyDistributionEvent(BaseModel):
    """Key distribution event database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    event_type: str = Field(..., description="Event type")
    master_sae_id: str = Field(..., description="Master SAE ID")
    slave_sae_id: str = Field(..., description="Slave SAE ID")
    key_count: int = Field(..., description="Number of keys")
    key_size: int = Field(..., description="Key size in bits")
    success: bool = Field(..., description="Success status")
    error_message: str | None = Field(None, description="Error message if failed")
    event_details: dict[str, Any] | None = Field(None, description="Event details")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_validator("master_sae_id", "slave_sae_id")
    @classmethod
    def validate_id_length(cls, v):
        """Validate ID length"""
        if len(v) != 16:
            raise ValueError("ID must be exactly 16 characters")
        return v

    @field_validator("key_count")
    @classmethod
    def validate_key_count(cls, v):
        """Validate key count"""
        if v <= 0:
            raise ValueError("Key count must be positive")
        return v

    @field_validator("key_size")
    @classmethod
    def validate_key_size(cls, v):
        """Validate key size"""
        if v <= 0:
            raise ValueError("Key size must be positive")
        return v


class SecurityEventRecord(BaseModel):
    """Security event record database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    event_type: str = Field(..., description="Event type")
    severity: str = Field(..., description="Event severity")
    category: str = Field(..., description="Event category")
    user_id: str | None = Field(None, description="User ID")
    sae_id: str | None = Field(None, description="SAE ID")
    kme_id: str | None = Field(None, description="KME ID")
    key_id: str | None = Field(None, description="Key ID")
    resource: str | None = Field(None, description="Resource")
    details: dict[str, Any] | None = Field(None, description="Event details")
    etsi_compliance: bool = Field(default=True, description="ETSI compliance flag")
    specification: str = Field(
        default="ETSI GS QKD 014 V1.1.1", description="Specification version"
    )
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        """Validate severity value"""
        valid_severities = ["low", "medium", "high", "critical"]
        if v not in valid_severities:
            raise ValueError(f"Severity must be one of: {valid_severities}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        """Validate category value"""
        valid_categories = [
            "authentication",
            "authorization",
            "key_management",
            "network_security",
            "compliance",
        ]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {valid_categories}")
        return v

    @field_validator("sae_id", "kme_id")
    @classmethod
    def validate_id_length(cls, v):
        """Validate ID length"""
        if v is not None and len(v) != 16:
            raise ValueError("ID must be exactly 16 characters")
        return v

    @field_validator("key_id")
    @classmethod
    def validate_key_id(cls, v):
        """Validate key ID is a valid UUID"""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError("key_id must be a valid UUID")
        return v


class PerformanceMetric(BaseModel):
    """Performance metric database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    metric_name: str = Field(..., description="Metric name")
    metric_value: float = Field(..., description="Metric value")
    metric_unit: str = Field(..., description="Metric unit")
    metric_type: str = Field(..., description="Metric type")
    labels: dict[str, Any] | None = Field(None, description="Metric labels")
    timestamp: datetime | None = Field(None, description="Timestamp")

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, v):
        """Validate metric type"""
        valid_types = ["counter", "gauge", "histogram", "summary"]
        if v not in valid_types:
            raise ValueError(f"Metric type must be one of: {valid_types}")
        return v


class HealthCheck(BaseModel):
    """Health check database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    check_name: str = Field(..., description="Health check name")
    status: str = Field(..., description="Health status")
    message: str | None = Field(None, description="Status message")
    details: dict[str, Any] | None = Field(None, description="Check details")
    timestamp: datetime | None = Field(None, description="Timestamp")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status value"""
        valid_statuses = ["healthy", "degraded", "unhealthy", "unknown"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class AlertRecord(BaseModel):
    """Alert record database model"""

    id: uuid.UUID | None = Field(None, description="Primary key")
    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    source: str = Field(..., description="Alert source")
    details: dict[str, Any] | None = Field(None, description="Alert details")
    acknowledged: bool = Field(default=False, description="Acknowledgment status")
    resolved: bool = Field(default=False, description="Resolution status")
    acknowledged_by: str | None = Field(None, description="Acknowledged by")
    acknowledged_at: datetime | None = Field(
        None, description="Acknowledgment timestamp"
    )
    resolved_by: str | None = Field(None, description="Resolved by")
    resolved_at: datetime | None = Field(None, description="Resolution timestamp")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        """Validate severity value"""
        valid_severities = ["info", "warning", "error", "critical"]
        if v not in valid_severities:
            raise ValueError(f"Severity must be one of: {valid_severities}")
        return v

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v):
        """Validate alert type"""
        valid_types = [
            "performance",
            "security",
            "system",
            "database",
            "network",
            "compliance",
        ]
        if v not in valid_types:
            raise ValueError(f"Alert type must be one of: {valid_types}")
        return v
