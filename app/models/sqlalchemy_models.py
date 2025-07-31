#!/usr/bin/env python3
"""
KME SQLAlchemy Database Models

Version: 1.0.0
Author: KME Development Team
Description: SQLAlchemy models for KME database operations
License: [To be determined]

Implements ETSI GS QKD 014 V1.1.1 requirements for:
- Key storage with encryption at rest
- Key indexing by key_ID and SAE_ID
- Key metadata storage
- Key expiration handling
- Audit logging

ToDo List:
- [x] Create SQLAlchemy models
- [x] Add Key model with encryption support
- [x] Add SAE model
- [x] Add audit logging models
- [x] Add key pool management models
- [ ] Add model relationships
- [ ] Add database indexes
- [ ] Add model validation
- [ ] Add model serialization
- [ ] Add model testing

Progress: 50% (5/10 tasks completed)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Key(Base):  # type: ignore[misc,valid-type]
    """
    Key storage model for ETSI QKD 014 V1.1.1 compliance

    Stores encrypted key data with metadata and access controls
    """

    __tablename__ = "keys"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Key identifier (UUID format as per ETSI specification)
    key_id = Column(String(36), unique=True, nullable=False, index=True)

    # Encrypted key data (encrypted at rest)
    encrypted_key_data = Column(LargeBinary, nullable=False)

    # Key hash for integrity verification
    key_hash = Column(String(64), nullable=False)

    # Salt for key derivation
    salt = Column(LargeBinary(16), nullable=False)

    # SAE identifiers (16 characters as per ETSI specification)
    master_sae_id = Column(String(16), nullable=False, index=True)
    slave_sae_id = Column(String(16), nullable=False, index=True)

    # Key metadata
    key_size = Column(Integer, nullable=False)  # Size in bits
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    key_metadata = Column(JSONB, nullable=True)  # Additional key metadata

    # Status and access control
    is_active = Column(Boolean, default=True, nullable=False)
    is_consumed = Column(Boolean, default=False, nullable=False)

    # Additional slave SAE IDs for multicast (ETSI extension)
    additional_slave_sae_ids = Column(JSONB, nullable=True)

    # Audit fields
    created_by = Column(String(16), nullable=True)  # SAE ID that created the key
    last_accessed_at = Column(DateTime, nullable=True)
    last_accessed_by = Column(String(16), nullable=True)  # SAE ID that last accessed

    # Database constraints
    __table_args__ = (
        # Ensure key_id is unique
        UniqueConstraint("key_id", name="uq_key_id"),
        # Index for efficient key lookups
        Index("idx_key_master_slave", "master_sae_id", "slave_sae_id"),
        Index("idx_key_expires", "expires_at"),
        Index("idx_key_active", "is_active"),
        Index("idx_key_consumed", "is_consumed"),
    )


class SAE(Base):  # type: ignore[misc,valid-type]
    """
    SAE (Secure Application Entity) model

    Stores SAE registration and authentication information
    """

    __tablename__ = "saes"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # SAE identifier (16 characters as per ETSI specification)
    sae_id = Column(String(16), unique=True, nullable=False, index=True)

    # Associated KME
    kme_id = Column(String(16), nullable=False, index=True)

    # Certificate information
    certificate_hash = Column(String(64), nullable=False)
    certificate_subject = Column(Text, nullable=True)
    certificate_issuer = Column(Text, nullable=True)
    certificate_valid_until = Column(DateTime, nullable=True)

    # Registration and status
    registration_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)
    status = Column(
        String(20), default="active", nullable=False
    )  # active, inactive, revoked

    # Capabilities and limits
    max_keys_per_request = Column(Integer, default=128, nullable=False)
    max_key_size = Column(Integer, default=1024, nullable=False)
    min_key_size = Column(Integer, default=64, nullable=False)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Database constraints
    __table_args__ = (
        # Ensure sae_id is unique
        UniqueConstraint("sae_id", name="uq_sae_id"),
        # Index for efficient lookups
        Index("idx_sae_kme", "kme_id"),
        Index("idx_sae_status", "status"),
        Index("idx_sae_last_seen", "last_seen"),
    )


class KeyAccessLog(Base):  # type: ignore[misc,valid-type]
    """
    Key access audit log

    Records all key access attempts for security auditing
    """

    __tablename__ = "key_access_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Key reference
    key_id = Column(String(36), nullable=False, index=True)

    # Access details
    requesting_sae_id = Column(String(16), nullable=False, index=True)
    access_type = Column(String(20), nullable=False)  # retrieve, store, delete
    success = Column(Boolean, nullable=False)

    # Request details
    request_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    response_timestamp = Column(DateTime, nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)
    error_code = Column(String(10), nullable=True)

    # Request context
    client_ip = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(36), nullable=True)  # For request tracing

    # Database constraints
    __table_args__ = (
        # Index for efficient querying
        Index("idx_access_key_id", "key_id"),
        Index("idx_access_sae_id", "requesting_sae_id"),
        Index("idx_access_timestamp", "request_timestamp"),
        Index("idx_access_success", "success"),
    )


class KeyPoolStatus(Base):  # type: ignore[misc,valid-type]
    """
    Key pool status tracking

    Maintains current status of key pool for monitoring and management
    """

    __tablename__ = "key_pool_status"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Pool metrics
    total_keys = Column(Integer, nullable=False, default=0)
    active_keys = Column(Integer, nullable=False, default=0)
    expired_keys = Column(Integer, nullable=False, default=0)
    consumed_keys = Column(Integer, nullable=False, default=0)

    # Capacity limits
    max_key_count = Column(Integer, nullable=False, default=100000)
    min_key_threshold = Column(Integer, nullable=False, default=1000)

    # Generation metrics
    key_generation_rate = Column(Integer, nullable=True)  # keys per hour
    last_key_generation = Column(DateTime, nullable=True)

    # Status timestamp
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Database constraints
    __table_args__ = (
        # Ensure only one status record
        UniqueConstraint("id", name="uq_pool_status"),
    )


class SecurityEvent(Base):  # type: ignore[misc,valid-type]
    """
    Security event logging

    Records security-related events for monitoring and alerting
    """

    __tablename__ = "security_events"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(
        String(20), nullable=False, index=True
    )  # low, medium, high, critical
    category = Column(
        String(30), nullable=False, index=True
    )  # authentication, authorization, key_access, etc.

    # Affected entities
    sae_id = Column(String(16), nullable=True, index=True)
    kme_id = Column(String(16), nullable=True, index=True)
    key_id = Column(String(36), nullable=True, index=True)

    # Event details
    description = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ETSI compliance tracking
    etsi_compliance = Column(Boolean, default=True, nullable=False)
    specification = Column(String(30), default="ETSI GS QKD 014 V1.1.1", nullable=False)

    # Database constraints
    __table_args__ = (
        # Index for efficient querying
        Index("idx_security_event_type", "event_type"),
        Index("idx_security_severity", "severity"),
        Index("idx_security_category", "category"),
        Index("idx_security_timestamp", "timestamp"),
        Index("idx_security_sae_id", "sae_id"),
        Index("idx_security_kme_id", "kme_id"),
    )


class KeyDistributionEvent(Base):  # type: ignore[misc,valid-type]
    """
    Key distribution event tracking

    Records key distribution events for audit and monitoring
    """

    __tablename__ = "key_distribution_events"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event details
    event_type = Column(
        String(30), nullable=False, index=True
    )  # get_key, get_key_with_ids, etc.
    master_sae_id = Column(String(16), nullable=False, index=True)
    slave_sae_id = Column(String(16), nullable=False, index=True)

    # Key details
    key_count = Column(Integer, nullable=False)
    key_size = Column(Integer, nullable=False)
    key_ids = Column(JSONB, nullable=True)  # Array of key IDs

    # Success/failure
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    # Performance metrics
    request_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    response_timestamp = Column(DateTime, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # Request context
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(36), nullable=True)

    # Database constraints
    __table_args__ = (
        # Index for efficient querying
        Index("idx_distribution_event_type", "event_type"),
        Index("idx_distribution_master_sae", "master_sae_id"),
        Index("idx_distribution_slave_sae", "slave_sae_id"),
        Index("idx_distribution_timestamp", "request_timestamp"),
        Index("idx_distribution_success", "success"),
    )


# Model relationships (if needed for complex queries)
# These can be added later as the application grows


def create_tables(engine):
    """
    Create all database tables

    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(bind=engine)


def drop_tables(engine):
    """
    Drop all database tables (use with caution!)

    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.drop_all(bind=engine)
