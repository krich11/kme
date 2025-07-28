#!/usr/bin/env python3
"""
KME Data Models Package

Version: 1.0.0
Author: KME Development Team
Description: ETSI QKD 014 V1.1.1 compliant data models
License: [To be determined]

ToDo List:
- [x] Create models package
- [x] Import all data models
- [ ] Add model validation
- [ ] Add model documentation
- [ ] Add model testing
- [ ] Add model serialization
- [ ] Add model deserialization
- [ ] Add model conversion utilities
- [ ] Add model versioning
- [ ] Add model migration support

Progress: 20% (2/10 tasks completed)
"""

from .api_models import APIResponse, ErrorResponse, HealthResponse, MetricsResponse
from .database_models import (
    AlertRecord,
    HealthCheck,
    KeyDistributionEvent,
    KeyRecord,
    KeyRequestRecord,
    KMEEntity,
    PerformanceMetric,
    SAEEntity,
    SecurityEventRecord,
)
from .etsi_models import (
    Error,
    ErrorDetail,
    Key,
    KeyContainer,
    KeyID,
    KeyIDs,
    KeyRequest,
    Status,
)

__all__ = [
    # ETSI QKD 014 Models
    "Status",
    "KeyRequest",
    "KeyContainer",
    "Key",
    "KeyIDs",
    "KeyID",
    "Error",
    "ErrorDetail",
    # Database Models
    "KMEEntity",
    "SAEEntity",
    "KeyRecord",
    "KeyRequestRecord",
    "KeyDistributionEvent",
    "SecurityEventRecord",
    "PerformanceMetric",
    "HealthCheck",
    "AlertRecord",
    # API Models
    "APIResponse",
    "HealthResponse",
    "MetricsResponse",
    "ErrorResponse",
]
