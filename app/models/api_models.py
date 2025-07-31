#!/usr/bin/env python3
"""
KME API Models

Version: 1.0.0
Author: KME Development Team
Description: API response models for KME internal endpoints
License: [To be determined]

ToDo List:
- [x] Create API response models
- [x] Add generic API response model
- [x] Add health response model
- [x] Add metrics response model
- [x] Add error response model
- [x] Add validation rules
- [ ] Add model testing
- [ ] Add model documentation
- [ ] Add model serialization
- [ ] Add model deserialization
- [ ] Add model conversion utilities
- [ ] Add model versioning
- [ ] Add model migration support

Progress: 60% (6/12 tasks completed)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .etsi_models import Error, KeyContainer, Status


class APIResponse(BaseModel):
    """Generic API response model"""

    success: bool = Field(..., description="Request success status")
    message: str = Field(..., description="Response message")
    data: dict[str, Any] | None = Field(None, description="Response data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: str | None = Field(None, description="Request identifier")
    version: str = Field(default="1.0.0", description="API version")


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )
    version: str = Field(default="1.0.0", description="KME version")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    checks: list[dict[str, Any]] = Field(
        ..., description="Individual health check results"
    )
    summary: dict[str, int] = Field(..., description="Health check summary")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status value"""
        valid_statuses = ["healthy", "degraded", "unhealthy", "unknown"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v):
        """Validate summary contains required fields"""
        required_fields = [
            "total_checks",
            "healthy_checks",
            "degraded_checks",
            "unhealthy_checks",
        ]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Summary must contain '{field}' field")
        return v


class MetricsResponse(BaseModel):
    """Metrics response model"""

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics timestamp"
    )
    metrics: dict[str, Any] = Field(..., description="Metrics data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metrics metadata"
    )


class ErrorResponse(BaseModel):
    """Error response model"""

    success: bool = Field(
        default=False, description="Request success status (always false for errors)"
    )
    error: Error = Field(..., description="Error details")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )
    request_id: str | None = Field(None, description="Request identifier")
    trace_id: str | None = Field(None, description="Error trace identifier")


class StatusResponse(BaseModel):
    """Status response model (ETSI QKD 014 compliant)"""

    status: Status = Field(..., description="ETSI QKD 014 Status data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: str | None = Field(None, description="Request identifier")


class KeyResponse(BaseModel):
    """Key response model (ETSI QKD 014 compliant)"""

    keys: KeyContainer = Field(..., description="ETSI QKD 014 Key container data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: str | None = Field(None, description="Request identifier")
    processing_time_ms: float | None = Field(
        None, description="Request processing time in milliseconds"
    )


class SystemInfoResponse(BaseModel):
    """System information response model"""

    kme_id: str = Field(..., description="KME identifier")
    version: str = Field(..., description="KME version")
    build_date: str = Field(..., description="Build date")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    system_info: dict[str, Any] = Field(..., description="System information")
    qkd_network_info: dict[str, Any] = Field(..., description="QKD network information")
    certificate_info: dict[str, Any] | None = Field(
        None, description="Certificate information"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class ConfigurationResponse(BaseModel):
    """Configuration response model"""

    kme_configuration: dict[str, Any] = Field(..., description="KME configuration")
    database_configuration: dict[str, Any] = Field(
        ..., description="Database configuration"
    )
    security_configuration: dict[str, Any] = Field(
        ..., description="Security configuration"
    )
    network_configuration: dict[str, Any] = Field(
        ..., description="Network configuration"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
