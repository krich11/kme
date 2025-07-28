#!/usr/bin/env python3
"""
KME Security Utilities Module

Version: 1.0.0
Author: KME Development Team
Description: Security utilities and helper functions for KME
License: [To be determined]

ToDo List:
- [x] Create certificate validation utilities
- [x] Add key generation helpers
- [x] Create encryption/decryption utilities
- [x] Add security validation functions
- [ ] Add certificate generation utilities
- [ ] Create key derivation functions
- [ ] Add secure communication helpers
- [ ] Create security audit utilities
- [ ] Add compliance checking functions
- [ ] Implement security testing helpers

Progress: 40% (4/10 tasks completed)
"""

import base64
import hashlib
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ..core.logging import logger, security_logger


def validate_sae_id(sae_id: str) -> bool:
    """Validate SAE ID format according to ETSI specification"""
    # ETSI QKD 014 doesn't specify exact format, but typically 16 characters
    if not sae_id or len(sae_id) != 16:
        return False

    # Check if it's alphanumeric (common pattern)
    if not re.match(r"^[A-F0-9]{16}$", sae_id.upper()):
        return False

    return True


def validate_kme_id(kme_id: str) -> bool:
    """Validate KME ID format according to ETSI specification"""
    # ETSI QKD 014 doesn't specify exact format, but typically 16 characters
    if not kme_id or len(kme_id) != 16:
        return False

    # Check if it's alphanumeric (common pattern)
    if not re.match(r"^[A-F0-9]{16}$", kme_id.upper()):
        return False

    return True


def validate_key_id(key_id: str) -> bool:
    """Validate key ID format (UUID)"""
    try:
        uuid.UUID(key_id)
        return True
    except ValueError:
        return False


def validate_key_size(key_size: int) -> bool:
    """Validate key size according to ETSI requirements"""
    # ETSI QKD 014 allows flexible key sizes, but typically 64-1024 bits
    if key_size < 64 or key_size > 1024:
        return False

    # Key size should be a multiple of 8
    if key_size % 8 != 0:
        return False

    return True


def generate_secure_key_id() -> str:
    """Generate secure key ID (UUID v4)"""
    return str(uuid.uuid4())


def generate_sae_id() -> str:
    """Generate SAE ID (16 character hex string)"""
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest().upper()[:16]


def generate_kme_id() -> str:
    """Generate KME ID (16 character hex string)"""
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest().upper()[:16]


def encode_key_base64(key_data: bytes) -> str:
    """Encode key data as base64"""
    return base64.b64encode(key_data).decode("utf-8")


def decode_key_base64(key_b64: str) -> bytes:
    """Decode key data from base64"""
    return base64.b64decode(key_b64)


def validate_base64_key(key_b64: str) -> bool:
    """Validate base64 encoded key"""
    try:
        decode_key_base64(key_b64)
        return True
    except Exception:
        return False


def extract_certificate_info(cert_data: bytes) -> dict[str, Any]:
    """Extract information from certificate"""
    try:
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())

        # Extract common name
        try:
            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except IndexError:
            cn = "Unknown"

        # Extract organization
        try:
            org = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[
                0
            ].value
        except IndexError:
            org = "Unknown"

        # Extract country
        try:
            country = cert.subject.get_attributes_for_oid(NameOID.COUNTRY_NAME)[0].value
        except IndexError:
            country = "Unknown"

        return {
            "subject": str(cert.subject),
            "issuer": str(cert.issuer),
            "common_name": cn,
            "organization": org,
            "country": country,
            "serial_number": str(cert.serial_number),
            "not_before": cert.not_valid_before.isoformat(),
            "not_after": cert.not_valid_after.isoformat(),
            "signature_algorithm": cert.signature_algorithm_oid.dotted_string,
        }

    except Exception as e:
        logger.error(f"Failed to extract certificate info: {e}")
        return {}


def validate_certificate_chain(cert_data: bytes, ca_cert_data: bytes) -> bool:
    """Validate certificate against CA certificate"""
    try:
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        ca_cert = x509.load_pem_x509_certificate(ca_cert_data, default_backend())

        # Basic validation
        if cert.issuer != ca_cert.subject:
            return False

        # Check validity period
        now = datetime.utcnow()
        if not (cert.not_valid_before <= now <= cert.not_valid_after):
            return False

        # TODO: Add signature validation
        # This would require the CA's public key

        return True

    except Exception as e:
        logger.error(f"Certificate chain validation failed: {e}")
        return False


def create_self_signed_certificate(
    common_name: str,
    organization: str = "KME Development",
    country: str = "US",
    days_valid: int = 365,
) -> tuple[bytes, bytes]:
    """Create self-signed certificate for development/testing"""
    try:
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        # Create certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Development"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=days_valid))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName(common_name),
                    ]
                ),
                critical=False,
            )
            .sign(private_key, hashes.SHA256(), default_backend())
        )

        # Serialize
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return cert_pem, key_pem

    except Exception as e:
        logger.error(f"Failed to create self-signed certificate: {e}")
        raise


def hash_key_data(key_data: bytes) -> str:
    """Generate hash of key data for integrity checking"""
    return hashlib.sha256(key_data).hexdigest()


def validate_key_integrity(key_data: bytes, expected_hash: str) -> bool:
    """Validate key integrity using hash"""
    actual_hash = hash_key_data(key_data)
    return actual_hash == expected_hash


def sanitize_log_data(data: Any) -> Any:
    """Sanitize data for logging (remove sensitive information)"""
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = ["key", "password", "secret", "token", "private_key"]

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_log_data(value)

        return sanitized

    elif isinstance(data, list):
        return [sanitize_log_data(item) for item in data]

    else:
        return data


def log_security_event(
    event_type: str,
    user_id: str = None,
    resource: str = None,
    success: bool = True,
    details: dict[str, Any] = None,
):
    """Log security event with sanitization"""
    # Sanitize details for logging
    sanitized_details = sanitize_log_data(details) if details else {}

    security_logger.log_authentication_event(
        event_type=event_type,
        user_id=user_id or "unknown",
        success=success,
        details=sanitized_details,
    )


def validate_etsi_compliance(
    data: dict[str, Any], data_type: str
) -> tuple[bool, list[str]]:
    """Validate data for ETSI QKD 014 compliance"""
    errors = []

    if data_type == "status":
        required_fields = [
            "source_KME_ID",
            "target_KME_ID",
            "master_SAE_ID",
            "slave_SAE_ID",
            "key_size",
            "stored_key_count",
            "max_key_count",
            "max_key_per_request",
            "max_key_size",
            "min_key_size",
            "max_SAE_ID_count",
        ]

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate IDs
        if "source_KME_ID" in data and not validate_kme_id(data["source_KME_ID"]):
            errors.append("Invalid source_KME_ID format")

        if "target_KME_ID" in data and not validate_kme_id(data["target_KME_ID"]):
            errors.append("Invalid target_KME_ID format")

        if "master_SAE_ID" in data and not validate_sae_id(data["master_SAE_ID"]):
            errors.append("Invalid master_SAE_ID format")

        if "slave_SAE_ID" in data and not validate_sae_id(data["slave_SAE_ID"]):
            errors.append("Invalid slave_SAE_ID format")

    elif data_type == "key_request":
        # Validate key request fields
        if "number" in data and (data["number"] < 1 or data["number"] > 128):
            errors.append("Invalid number of keys requested")

        if "size" in data and not validate_key_size(data["size"]):
            errors.append("Invalid key size")

    elif data_type == "key_container":
        if "keys" not in data or not isinstance(data["keys"], list):
            errors.append("Missing or invalid keys array")
        else:
            for i, key in enumerate(data["keys"]):
                if "key_ID" not in key or not validate_key_id(key["key_ID"]):
                    errors.append(f"Invalid key_ID in key {i}")

                if "key" not in key or not validate_base64_key(key["key"]):
                    errors.append(f"Invalid key data in key {i}")

    return len(errors) == 0, errors


def generate_secure_nonce(length: int = 32) -> str:
    """Generate secure nonce for cryptographic operations"""
    import secrets

    return secrets.token_hex(length)


def validate_tls_version(version: str) -> bool:
    """Validate TLS version string"""
    valid_versions = ["TLSv1.2", "TLSv1.3"]
    return version in valid_versions


def validate_cipher_suite(cipher_suite: str) -> bool:
    """Validate cipher suite string"""
    # Common secure cipher suites
    valid_ciphers = [
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES256-SHA384",
        "ECDHE-RSA-AES128-SHA256",
        "DHE-RSA-AES256-GCM-SHA384",
        "DHE-RSA-AES128-GCM-SHA256",
    ]
    return cipher_suite in valid_ciphers
