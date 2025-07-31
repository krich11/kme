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

    model_config = ConfigDict(
        schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"key_count": 3},
                "timestamp": "2025-07-28T17:30:00Z",
                "request_id": "req_123",
                "version": "1.0.0",
            }
        }
    )


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

    model_config = ConfigDict(
        schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-07-28T17:30:00Z",
                "version": "1.0.0",
                "uptime_seconds": 3600.5,
                "checks": [
                    {
                        "name": "database_health",
                        "status": "healthy",
                        "message": "Database connection is operational",
                    }
                ],
                "summary": {
                    "total_checks": 5,
                    "healthy_checks": 5,
                    "degraded_checks": 0,
                    "unhealthy_checks": 0,
                },
            }
        }
    )


class MetricsResponse(BaseModel):
    """Metrics response model"""

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics timestamp"
    )
    metrics: dict[str, Any] = Field(..., description="Metrics data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metrics metadata"
    )

    model_config = ConfigDict(
        schema_extra={
            "example": {
                "timestamp": "2025-07-28T17:30:00Z",
                "metrics": {
                    "api_response_time": {
                        "avg": 150.5,
                        "min": 50.2,
                        "max": 500.0,
                        "p95": 300.0,
                    }
                },
                "metadata": {"collection_interval": 60, "retention_period": 86400},
            }
        }
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

    model_config = ConfigDict(
        schema_extra={
            "example": {
                "success": False,
                "error": {
                    "message": "Invalid request parameters",
                    "error_code": "INVALID_PARAMETERS",
                    "severity": "error",
                },
                "timestamp": "2025-07-28T17:30:00Z",
                "request_id": "req_123",
                "trace_id": "trace_456",
            }
        }
    )


class StatusResponse(BaseModel):
    """Status response model (ETSI QKD 014 compliant)"""

    status: Status = Field(..., description="ETSI QKD 014 Status data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: str | None = Field(None, description="Request identifier")

    model_config = ConfigDict(
        schema_extra={
            "example": {
                "status": {
                    "source_KME_ID": "AAAABBBBCCCCDDDD",
                    "target_KME_ID": "EEEEFFFFGGGGHHHH",
                    "master_SAE_ID": "IIIIJJJJKKKKLLLL",
                    "slave_SAE_ID": "MMMMNNNNOOOOPPPP",
                    "key_size": 352,
                    "stored_key_count": 25000,
                    "max_key_count": 100000,
                    "max_key_per_request": 128,
                    "max_key_size": 1024,
                    "min_key_size": 64,
                    "max_SAE_ID_count": 0,
                },
                "timestamp": "2025-07-28T17:30:00Z",
                "request_id": "req_123",
            }
        }
    )


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

    model_config = ConfigDict(
        schema_extra={
            "example": {
                "keys": {
                    "keys": [
                        {
                            "key_ID": "bc490419-7d60-487f-adc1-4ddcc177c139",
                            "key": "wHHVxRwDJs3/bXd38GHP3oe4svTuRpZS0yCC7x4Ly+s=",
                        }
                    ]
                },
                "timestamp": "2025-07-28T17:30:00Z",
                "request_id": "req_123",
                "processing_time_ms": 150.5,
            }
        }
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

    model_config = ConfigDict(
        schema_extra={
            "example": {
                "kme_id": "AAAABBBBCCCCDDDD",
                "version": "1.0.0",
                "build_date": "2025-07-28",
                "uptime_seconds": 3600.5,
                "system_info": {
                    "platform": "Linux",
                    "python_version": "3.10.0",
                    "cpu_count": 4,
                    "memory_total_gb": 16.0,
                },
                "qkd_network_info": {
                    "connected_links": 2,
                    "key_generation_rate": 1000.0,
                    "network_status": "operational",
                },
                "certificate_info": {
                    "subject": "CN=KME001",
                    "issuer": "CN=CA",
                    "valid_until": "2025-12-31T23:59:59Z",
                },
                "timestamp": "2025-07-28T17:30:00Z",
            }
        }
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

    model_config = ConfigDict(
        schema_extra={
            "example": {
                "kme_configuration": {
                    "kme_id": "AAAABBBBCCCCDDDD",
                    "hostname": "kme1.example.com",
                    "port": 8443,
                    "default_key_size": 352,
                },
                "database_configuration": {
                    "database_url": "postgresql://user@localhost:5432/kme",
                    "pool_size": 10,
                    "max_overflow": 20,
                },
                "security_configuration": {
                    "tls_version": "1.2",
                    "certificate_file": "/path/to/cert.pem",
                    "key_file": "/path/to/key.pem",
                },
                "network_configuration": {
                    "allowed_origins": ["*"],
                    "allowed_hosts": ["*"],
                    "cors_enabled": True,
                },
                "timestamp": "2025-07-28T17:30:00Z",
            }
        }
    )
