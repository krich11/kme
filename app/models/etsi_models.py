#!/usr/bin/env python3
"""
KME ETSI QKD 014 Data Models

Version: 1.0.0
Author: KME Development Team
Description: ETSI GS QKD 014 V1.1.1 compliant data models
License: [To be determined]

ToDo List:
- [x] Create ETSI compliant data models
- [x] Add Status data model
- [x] Add KeyRequest data model
- [x] Add KeyContainer data model
- [x] Add Key data model
- [x] Add KeyIDs data model
- [x] Add Error data model
- [x] Add validation rules
- [x] Add convenience fields
- [ ] Add model testing
- [ ] Add model documentation
- [ ] Add model serialization
- [ ] Add model deserialization
- [ ] Add model conversion utilities
- [ ] Add model versioning
- [ ] Add model migration support

Progress: 60% (9/15 tasks completed)
"""

import base64
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, root_validator, validator


class Status(BaseModel):
    """
    Status data format - ETSI GS QKD 014 V1.1.1 Section 6.1

    Used for response data model of API "Get status" method.
    """

    # Required fields from ETSI specification
    source_KME_ID: str = Field(..., description="KME ID of the KME")
    target_KME_ID: str = Field(..., description="KME ID of the target KME")
    master_SAE_ID: str = Field(..., description="SAE ID of the calling master SAE")
    slave_SAE_ID: str = Field(..., description="SAE ID of the specified slave SAE")
    key_size: int = Field(
        ..., description="Default size of key the KME can deliver to the SAE (in bit)"
    )
    stored_key_count: int = Field(
        ..., description="Number of stored keys KME can deliver to the SAE"
    )
    max_key_count: int = Field(..., description="Maximum number of stored_key_count")
    max_key_per_request: int = Field(
        ..., description="Maximum number of keys per request"
    )
    max_key_size: int = Field(
        ..., description="Maximum size of key the KME can deliver to the SAE (in bit)"
    )
    min_key_size: int = Field(
        ..., description="Minimum size of key the KME can deliver to the SAE (in bit)"
    )
    max_SAE_ID_count: int = Field(
        ...,
        description="Maximum number of additional_slave_SAE_IDs the KME allows. '0' when the KME does not support key multicast",
    )

    # Optional extension field from ETSI specification
    status_extension: dict[str, Any] | None = Field(
        None, description="(Option) for future use"
    )

    # Convenience fields (not in ETSI spec but useful for implementation)
    kme_status: str = Field(default="operational", description="KME operational status")
    qkd_network_status: str = Field(
        default="connected", description="QKD network connection status"
    )
    key_generation_rate: float | None = Field(
        None, description="Current key generation rate (keys/second)"
    )
    last_key_generation: datetime | None = Field(
        None, description="Timestamp of last key generation"
    )
    certificate_valid_until: datetime | None = Field(
        None, description="Certificate expiration date"
    )

    @validator("source_KME_ID", "target_KME_ID", "master_SAE_ID", "slave_SAE_ID")
    def validate_id_length(cls, v):
        """Validate ID length (ETSI spec doesn't specify exact length, but we use 16 chars)"""
        if len(v) != 16:
            raise ValueError("ID must be exactly 16 characters")
        return v

    @validator("key_size", "max_key_size", "min_key_size")
    def validate_key_sizes(cls, v):
        """Validate key sizes are positive and reasonable"""
        if v <= 0:
            raise ValueError("Key size must be positive")
        if v > 8192:
            raise ValueError("Key size cannot exceed 8192 bits")
        return v

    @validator("stored_key_count", "max_key_count", "max_key_per_request")
    def validate_counts(cls, v):
        """Validate counts are non-negative"""
        if v < 0:
            raise ValueError("Count must be non-negative")
        return v

    @root_validator(skip_on_failure=True)
    def validate_key_size_consistency(cls, values):
        """Validate key size consistency"""
        min_size = values.get("min_key_size")
        max_size = values.get("max_key_size")
        default_size = values.get("key_size")

        if min_size and max_size and min_size > max_size:
            raise ValueError("min_key_size cannot be greater than max_key_size")

        if default_size:
            if min_size and default_size < min_size:
                raise ValueError("key_size cannot be less than min_key_size")
            if max_size and default_size > max_size:
                raise ValueError("key_size cannot be greater than max_key_size")

        return values

    class Config:
        json_schema_extra = {
            "example": {
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
                "kme_status": "operational",
                "qkd_network_status": "connected",
                "key_generation_rate": 1000.0,
            }
        }


class KeyRequest(BaseModel):
    """
    Key request data format - ETSI GS QKD 014 V1.1.1 Section 6.2

    Used for request data model of API "Get key" method.
    """

    # Optional fields from ETSI specification
    number: int | None = Field(
        None, description="(Option) Number of keys requested, default value is 1"
    )
    size: int | None = Field(
        None,
        description="(Option) Size of each key in bits, default value is defined as key_size in Status data format",
    )
    additional_slave_SAE_IDs: list[str] | None = Field(
        None,
        description="(Option) Array of IDs of slave SAEs. It is used for specifying two or more slave SAEs to share identical keys. The maximum number of IDs is defined as max_SAE_ID_count in Status data format",
    )
    extension_mandatory: list[dict[str, Any]] | None = Field(
        None,
        description="(Option) Array of extension parameters specified as name/value pairs that KME shall handle or return an error. Parameter values may be of any type, including objects",
    )
    extension_optional: list[dict[str, Any]] | None = Field(
        None,
        description="(Option) Array of extension parameters specified as name/value pairs that KME may ignore. Parameter values may be of any type, including objects",
    )

    # Convenience fields
    request_id: str | None = Field(
        None, description="Unique request identifier for tracking"
    )
    priority: str | None = Field(
        default="normal", description="Request priority (low, normal, high, critical)"
    )
    timeout_seconds: int | None = Field(None, description="Request timeout in seconds")
    route_preference: str | None = Field(
        None, description="Route preference (direct, indirect, any)"
    )

    @validator("number")
    def validate_number(cls, v):
        """Validate number of keys requested"""
        if v is not None and v <= 0:
            raise ValueError("Number of keys must be positive")
        return v

    @validator("size")
    def validate_size(cls, v):
        """Validate key size"""
        if v is not None:
            if v <= 0:
                raise ValueError("Key size must be positive")
            if v % 8 != 0:
                raise ValueError("Key size must be a multiple of 8")
        return v

    @validator("additional_slave_SAE_IDs")
    def validate_additional_sae_ids(cls, v):
        """Validate additional SAE IDs"""
        if v is not None:
            for sae_id in v:
                if len(sae_id) != 16:
                    raise ValueError("SAE ID must be exactly 16 characters")
        return v

    @validator("priority")
    def validate_priority(cls, v):
        """Validate priority value"""
        valid_priorities = ["low", "normal", "high", "critical"]
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "number": 3,
                "size": 1024,
                "additional_slave_SAE_IDs": ["ABCDEFGHIJKLMNOP", "QRSTUVWXYZ123456"],
                "extension_mandatory": [
                    {"abc_route_type": "direct"},
                    {"abc_transfer_method": "qkd"},
                ],
                "extension_optional": [{"abc_max_age": 30000}],
                "priority": "high",
                "route_preference": "direct",
            }
        }


class Key(BaseModel):
    """
    Key data format - ETSI GS QKD 014 V1.1.1 Section 6.3

    Individual key within Key container.
    """

    # Required fields from ETSI specification
    key_ID: str = Field(..., description="ID of the key: UUID format")
    key: str = Field(..., description="Key data encoded by base64")

    # Optional extension fields from ETSI specification
    key_ID_extension: dict[str, Any] | None = Field(
        None, description="(Option) for future use"
    )
    key_extension: dict[str, Any] | None = Field(
        None, description="(Option) for future use"
    )

    # Convenience fields
    key_size: int | None = Field(None, description="Key size in bits")
    created_at: datetime | None = Field(None, description="Key creation timestamp")
    expires_at: datetime | None = Field(None, description="Key expiration timestamp")
    source_kme_id: str | None = Field(None, description="Source KME ID")
    target_kme_id: str | None = Field(None, description="Target KME ID")
    key_metadata: dict[str, Any] | None = Field(
        None, description="Additional key metadata"
    )

    @validator("key_ID")
    def validate_key_id(cls, v):
        """Validate key ID is a valid UUID"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("key_ID must be a valid UUID")
        return v

    @validator("key")
    def validate_key_data(cls, v):
        """Validate key data is valid base64"""
        try:
            base64.b64decode(v)
        except Exception:
            raise ValueError("key must be valid base64 encoded data")
        return v

    @validator("key_size")
    def validate_key_size(cls, v):
        """Validate key size"""
        if v is not None and v <= 0:
            raise ValueError("Key size must be positive")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "key_ID": "bc490419-7d60-487f-adc1-4ddcc177c139",
                "key": "wHHVxRwDJs3/bXd38GHP3oe4svTuRpZS0yCC7x4Ly+s=",
                "key_size": 256,
                "created_at": "2025-07-28T17:30:00Z",
                "expires_at": "2025-07-28T18:30:00Z",
            }
        }


class KeyContainer(BaseModel):
    """
    Key container data format - ETSI GS QKD 014 V1.1.1 Section 6.3

    Used for response data model of API "Get key" method and "Get key with key IDs" method.
    """

    # Required field from ETSI specification
    keys: list[Key] = Field(
        ...,
        description="Array of keys. The number of keys is specified by the 'number' parameter in 'Get key'. If not specified, the default number of keys is 1",
    )

    # Optional extension field from ETSI specification
    key_container_extension: dict[str, Any] | None = Field(
        None, description="(Option) for future use"
    )

    # Convenience fields
    container_id: str | None = Field(None, description="Unique container identifier")
    created_at: datetime | None = Field(
        None, description="Container creation timestamp"
    )
    master_sae_id: str | None = Field(None, description="Master SAE ID")
    slave_sae_id: str | None = Field(None, description="Slave SAE ID")
    total_key_size: int | None = Field(
        None, description="Total size of all keys in bits"
    )

    @validator("keys")
    def validate_keys(cls, v):
        """Validate keys array is not empty"""
        if not v:
            raise ValueError("Keys array cannot be empty")
        return v

    @root_validator(skip_on_failure=True)
    def validate_container_consistency(cls, values):
        """Validate container consistency"""
        keys = values.get("keys", [])
        if keys:
            # Check that all keys have consistent metadata
            key_sizes = [k.key_size for k in keys if k.key_size is not None]
            if len(set(key_sizes)) > 1:
                raise ValueError("All keys in container must have the same size")
        return values

    class Config:
        json_schema_extra = {
            "example": {
                "keys": [
                    {
                        "key_ID": "bc490419-7d60-487f-adc1-4ddcc177c139",
                        "key": "wHHVxRwDJs3/bXd38GHP3oe4svTuRpZS0yCC7x4Ly+s=",
                    },
                    {
                        "key_ID": "0a782fb5-3434-48fe-aa4d-14f41d46cf92",
                        "key": "OeGMPxh1+2RpJpNCYixWHFLYRubpOKCw94FcCI7VdJA=",
                    },
                ],
                "container_id": "container_123",
                "created_at": "2025-07-28T17:30:00Z",
            }
        }


class KeyID(BaseModel):
    """
    Key ID data format - ETSI GS QKD 014 V1.1.1 Section 6.4

    Individual key ID within Key IDs.
    """

    # Required field from ETSI specification
    key_ID: str = Field(..., description="ID of the key: UUID format")

    # Optional extension field from ETSI specification
    key_ID_extension: dict[str, Any] | None = Field(
        None, description="(Option) for future use"
    )

    # Convenience fields
    requested_at: datetime | None = Field(
        None, description="When this key ID was requested"
    )
    priority: str | None = Field(None, description="Request priority")

    @validator("key_ID")
    def validate_key_id(cls, v):
        """Validate key ID is a valid UUID"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("key_ID must be a valid UUID")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "key_ID": "bc490419-7d60-487f-adc1-4ddcc177c139",
                "requested_at": "2025-07-28T17:30:00Z",
                "priority": "high",
            }
        }


class KeyIDs(BaseModel):
    """
    Key IDs data format - ETSI GS QKD 014 V1.1.1 Section 6.4

    Used for request data model of API "Get key with key IDs" method.
    """

    # Required field from ETSI specification
    key_IDs: list[KeyID] = Field(..., description="Array of key IDs")

    # Optional extension field from ETSI specification
    key_IDs_extension: dict[str, Any] | None = Field(
        None, description="(Option) for future use"
    )

    # Convenience fields
    request_id: str | None = Field(None, description="Unique request identifier")
    master_sae_id: str | None = Field(None, description="Master SAE ID")
    requested_at: datetime | None = Field(None, description="Request timestamp")
    timeout_seconds: int | None = Field(None, description="Request timeout")

    @validator("key_IDs")
    def validate_key_ids(cls, v):
        """Validate key IDs array is not empty"""
        if not v:
            raise ValueError("Key IDs array cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "key_IDs": [
                    {"key_ID": "bc490419-7d60-487f-adc1-4ddcc177c139"},
                    {"key_ID": "0a782fb5-3434-48fe-aa4d-14f41d46cf92"},
                ],
                "request_id": "req_123",
                "master_sae_id": "IIIIJJJJKKKKLLLL",
            }
        }


class ErrorDetail(BaseModel):
    """
    Error detail data format - ETSI GS QKD 014 V1.1.1 Section 6.5

    Individual error detail within Error response.
    """

    # Error detail can be any name/value pair
    detail: dict[str, Any] = Field(..., description="Error detail as name/value pair")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": {
                    "extension_mandatory_unsupported": "abc_route_type is not supported"
                }
            }
        }


class Error(BaseModel):
    """
    Error data format - ETSI GS QKD 014 V1.1.1 Section 6.5

    Used for error response data model of API methods.
    """

    # Required field from ETSI specification
    message: str = Field(..., description="Error message")

    # Optional field from ETSI specification
    details: list[ErrorDetail] | None = Field(
        None,
        description="(Option) Array to supply additional detailed error information specified as name/value pairs. Values may be of any type, including objects",
    )

    # Convenience fields
    error_code: str | None = Field(
        None, description="Error code for programmatic handling"
    )
    timestamp: datetime | None = Field(None, description="Error timestamp")
    request_id: str | None = Field(None, description="Request ID that caused the error")
    severity: str | None = Field(
        default="error", description="Error severity (info, warning, error, critical)"
    )

    @validator("severity")
    def validate_severity(cls, v):
        """Validate severity value"""
        valid_severities = ["info", "warning", "error", "critical"]
        if v not in valid_severities:
            raise ValueError(f"Severity must be one of: {valid_severities}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "message": "not all extension_mandatory parameters are supported",
                "details": [
                    {
                        "extension_mandatory_unsupported": "abc_route_type is not supported"
                    }
                ],
                "error_code": "EXTENSION_NOT_SUPPORTED",
                "severity": "error",
            }
        }
