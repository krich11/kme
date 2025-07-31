#!/usr/bin/env python3
"""
KME Security Infrastructure Module

Version: 1.0.0
Author: KME Development Team
Description: Security infrastructure including TLS, certificates, secure random generation, and key storage
License: [To be determined]

ToDo List:
- [x] Create TLS configuration module
- [x] Implement certificate validation
- [x] Add secure random generation
- [x] Create key storage security
- [ ] Add certificate renewal handling
- [ ] Implement revocation status verification
- [ ] Add hardware security module support
- [ ] Create security audit logging
- [ ] Add security metrics collection
- [ ] Implement security alerting

Progress: 40% (4/10 tasks completed)
"""

import asyncio
import base64
import datetime
import hashlib
import os
import re
import ssl
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import cryptography
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.x509.extensions import (
    ExtendedKeyUsage,
    KeyUsage,
    SubjectAlternativeName,
)
from cryptography.x509.oid import NameOID

from .config import settings
from .logging import logger, security_logger


class SecurityLevel(Enum):
    """Security level enumeration"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class CertificateType(Enum):
    """Certificate type enumeration"""

    KME = "kme"
    SAE = "sae"
    CA = "ca"


@dataclass
class CertificateInfo:
    """Certificate information"""

    subject: str
    issuer: str
    serial_number: str
    not_before: datetime.datetime
    not_after: datetime.datetime
    key_usage: list[str]
    extended_key_usage: list[str]
    subject_alt_names: list[str]
    certificate_type: CertificateType
    is_valid: bool
    validation_errors: list[str]


class TLSConfig:
    """TLS configuration for KME"""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.PRODUCTION):
        """Initialize TLS configuration"""
        self.security_level = security_level
        self.ssl_context: ssl.SSLContext | None = None
        self.certificate_path: Path | None = None
        self.private_key_path: Path | None = None
        self.ca_certificate_path: Path | None = None
        self.cipher_suites: list[str] = []
        self.min_tls_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2
        self.max_tls_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3

    def configure_tls_context(self) -> ssl.SSLContext:
        """Configure TLS context according to ETSI requirements"""
        logger.info("Configuring TLS context for ETSI QKD 014 compliance")

        # Create SSL context
        self.ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH,
            cafile=str(self.ca_certificate_path) if self.ca_certificate_path else None,
        )

        # Set TLS version requirements (ETSI requires TLS 1.2+)
        self.ssl_context.minimum_version = self.min_tls_version
        self.ssl_context.maximum_version = self.max_tls_version

        # Configure strong cipher suites
        self._configure_cipher_suites()

        # Set up certificate verification
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        self.ssl_context.check_hostname = True

        # Load KME certificate and private key
        if self.certificate_path and self.private_key_path:
            self.ssl_context.load_cert_chain(
                certfile=str(self.certificate_path),
                keyfile=str(self.private_key_path),
            )

        # Configure session resumption
        # self.ssl_context.session_tickets = True
        # Note: SSLSessionCacheMode not available in all Python versions
        # try:
        #     self.ssl_context.session_cache_mode = ssl.SSLSessionCacheMode.SERVER
        # except AttributeError:
        #     # Fallback for older Python versions
        #     pass

        security_logger.log_certificate_validation(
            certificate_type="tls_context",
            subject_id="kme_tls",
            success=True,
            validation_details={
                "tls_version_min": self.min_tls_version.name,
                "tls_version_max": self.max_tls_version.name,
                "cipher_suites_count": len(self.cipher_suites),
                "security_level": self.security_level.value,
            },
        )

        return self.ssl_context

    def _configure_cipher_suites(self):
        """Configure strong cipher suites"""
        if self.security_level == SecurityLevel.PRODUCTION:
            # Production: Only strong cipher suites
            self.cipher_suites = [
                "ECDHE-RSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-RSA-AES256-SHA384",
                "ECDHE-RSA-AES128-SHA256",
                "DHE-RSA-AES256-GCM-SHA384",
                "DHE-RSA-AES128-GCM-SHA256",
            ]
        elif self.security_level == SecurityLevel.TESTING:
            # Testing: Include some weaker but still secure ciphers
            self.cipher_suites = [
                "ECDHE-RSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-RSA-AES256-SHA384",
                "ECDHE-RSA-AES128-SHA256",
                "ECDHE-RSA-AES256-SHA",
                "ECDHE-RSA-AES128-SHA",
            ]
        else:
            # Development: More permissive for development
            self.cipher_suites = [
                "ECDHE-RSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-RSA-AES256-SHA384",
                "ECDHE-RSA-AES128-SHA256",
                "ECDHE-RSA-AES256-SHA",
                "ECDHE-RSA-AES128-SHA",
                "AES256-GCM-SHA384",
                "AES128-GCM-SHA256",
            ]

        # Set cipher suites
        self.ssl_context.set_ciphers(":".join(self.cipher_suites))


class CertificateManager:
    """Certificate management for KME"""

    def __init__(self):
        """Initialize certificate manager"""
        self.ca_certificates: list[x509.Certificate] = []
        self.trusted_certificates: dict[str, x509.Certificate] = {}
        self.certificate_cache: dict[str, CertificateInfo] = {}

    def load_ca_certificates(self, ca_path: Path) -> bool:
        """Load CA certificates from path"""
        try:
            if ca_path.is_file():
                # Single certificate file
                with open(ca_path, "rb") as f:
                    cert_data = f.read()
                    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                    self.ca_certificates.append(cert)
            elif ca_path.is_dir():
                # Directory of certificates
                for cert_file in ca_path.glob("*.pem"):
                    with open(cert_file, "rb") as f:
                        cert_data = f.read()
                        cert = x509.load_pem_x509_certificate(
                            cert_data, default_backend()
                        )
                        self.ca_certificates.append(cert)

            logger.info(f"Loaded {len(self.ca_certificates)} CA certificates")
            return True

        except Exception as e:
            logger.error(f"Failed to load CA certificates: {e}")
            return False

    def validate_certificate(
        self, cert_data: bytes, expected_id: str | None = None
    ) -> CertificateInfo:
        """Validate certificate and extract information"""
        try:
            # Parse certificate
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            # Extract basic information
            subject_raw = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[
                0
            ].value
            issuer_raw = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[
                0
            ].value

            # Convert to string if needed
            subject = (
                subject_raw.decode("utf-8")
                if isinstance(subject_raw, bytes)
                else subject_raw
            )
            issuer = (
                issuer_raw.decode("utf-8")
                if isinstance(issuer_raw, bytes)
                else issuer_raw
            )
            serial_number = str(cert.serial_number)

            # Check validity period
            now = datetime.datetime.utcnow()
            is_valid = cert.not_valid_before <= now <= cert.not_valid_after

            # Extract key usage
            key_usage = []
            try:
                ku = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.KEY_USAGE
                )
                key_usage_obj = cast(KeyUsage, ku.value)
                if key_usage_obj.digital_signature:
                    key_usage.append("digital_signature")
                if key_usage_obj.key_encipherment:
                    key_usage.append("key_encipherment")
                if key_usage_obj.key_agreement:
                    key_usage.append("key_agreement")
            except x509.extensions.ExtensionNotFound:
                pass

            # Extract extended key usage
            extended_key_usage = []
            try:
                eku = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.EXTENDED_KEY_USAGE
                )
                eku_obj = cast(ExtendedKeyUsage, eku.value)
                for usage in eku_obj:
                    extended_key_usage.append(str(usage))
            except x509.extensions.ExtensionNotFound:
                pass

            # Extract subject alternative names
            subject_alt_names = []
            try:
                san = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                san_obj = cast(SubjectAlternativeName, san.value)
                for name in san_obj:
                    subject_alt_names.append(str(name.value))
            except x509.extensions.ExtensionNotFound:
                pass

            # Determine certificate type
            certificate_type = self._determine_certificate_type(cert, subject)

            # Validate against expected ID if provided
            validation_errors = []
            if expected_id and not self._validate_certificate_id(cert, expected_id):
                validation_errors.append(
                    f"Certificate ID mismatch: expected {expected_id}"
                )
                is_valid = False

            # Create certificate info
            cert_info = CertificateInfo(
                subject=subject,
                issuer=issuer,
                serial_number=serial_number,
                not_before=cert.not_valid_before,
                not_after=cert.not_valid_after,
                key_usage=key_usage,
                extended_key_usage=extended_key_usage,
                subject_alt_names=subject_alt_names,
                certificate_type=certificate_type,
                is_valid=is_valid,
                validation_errors=validation_errors,
            )

            # Cache certificate info
            self.certificate_cache[serial_number] = cert_info

            # Log validation result
            security_logger.log_certificate_validation(
                certificate_type=certificate_type.value,
                subject_id=subject,
                success=is_valid,
                validation_details={
                    "issuer": issuer,
                    "serial_number": serial_number,
                    "validation_errors": validation_errors,
                },
            )

            return cert_info

        except Exception as e:
            logger.error(f"Certificate validation failed: {e}")
            return CertificateInfo(
                subject="unknown",
                issuer="unknown",
                serial_number="unknown",
                not_before=datetime.datetime.utcnow(),
                not_after=datetime.datetime.utcnow(),
                key_usage=[],
                extended_key_usage=[],
                subject_alt_names=[],
                certificate_type=CertificateType.SAE,
                is_valid=False,
                validation_errors=[str(e)],
            )

    def _determine_certificate_type(
        self, cert: x509.Certificate, subject: str
    ) -> CertificateType:
        """Determine certificate type based on subject and extensions"""
        # Check for KME-specific extensions or naming
        if "KME" in subject.upper() or "KEY_MANAGEMENT" in subject.upper():
            return CertificateType.KME

        # Check for CA certificate
        try:
            ku = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.KEY_USAGE)
            key_usage_obj = cast(KeyUsage, ku.value)
            if key_usage_obj.key_cert_sign:
                return CertificateType.CA

        except x509.extensions.ExtensionNotFound:
            pass

        # Default to SAE
        return CertificateType.SAE

    def _validate_certificate_id(
        self, cert: x509.Certificate, expected_id: str
    ) -> bool:
        """Validate that certificate contains expected ID"""
        # Check common name
        try:
            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            if expected_id in cn:
                return True
        except IndexError:
            pass

        # Check subject alternative names
        try:
            san = cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            )
            san_obj = cast(SubjectAlternativeName, san.value)
            for name in san_obj:
                if expected_id in str(name.value):
                    return True
        except x509.extensions.ExtensionNotFound:
            pass

        # Check custom extensions for KME/SAE ID
        try:
            for extension in cert.extensions:
                if extension.oid.dotted_string in ["2.5.29.17", "2.5.29.19"]:
                    if expected_id in str(extension.value):
                        return True
        except Exception:
            pass

        return False

    def extract_sae_id_from_certificate(self, cert_data: bytes) -> str | None:
        """Extract SAE ID from certificate"""
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            # Try to extract from common name
            try:
                cn_raw = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[
                    0
                ].value
                # Convert to string if needed
                cn = cn_raw.decode("utf-8") if isinstance(cn_raw, bytes) else cn_raw
                # Look for SAE ID pattern (16 characters)

                sae_match = re.search(r"[A-F0-9]{16}", cn)
                if sae_match:
                    return sae_match.group(0)
            except IndexError:
                pass

            # Try to extract from subject alternative names
            try:
                san = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                san_obj = cast(SubjectAlternativeName, san.value)
                for name in san_obj:
                    name_str = str(name.value)

                    sae_match = re.search(r"[A-F0-9]{16}", name_str)
                    if sae_match:
                        return sae_match.group(0)
            except x509.extensions.ExtensionNotFound:
                pass

            return None

        except Exception as e:
            logger.error(f"Failed to extract SAE ID from certificate: {e}")
            return None


class SecureRandomGenerator:
    """Secure random number generation for KME"""

    def __init__(self):
        """Initialize secure random generator"""
        self.entropy_sources = ["os.urandom", "secrets", "cryptography"]
        self.min_entropy_bits = 256

    def generate_uuid(self) -> str:
        """Generate cryptographically secure UUID"""
        return str(uuid.uuid4())

    def generate_random_bytes(self, length: int) -> bytes:
        """Generate cryptographically secure random bytes"""
        return os.urandom(length)

    def generate_random_key(self, key_size: int) -> bytes:
        """Generate random key of specified size"""
        if key_size % 8 != 0:
            raise ValueError("Key size must be a multiple of 8")

        key_bytes = key_size // 8
        return self.generate_random_bytes(key_bytes)

    def generate_base64_key(self, key_size: int) -> str:
        """Generate random key and encode as base64"""
        key_bytes = self.generate_random_key(key_size)
        return base64.b64encode(key_bytes).decode("utf-8")

    def validate_entropy_source(self) -> bool:
        """Validate entropy source quality"""
        try:
            # Test entropy source
            test_data = os.urandom(32)

            # Basic entropy check (not cryptographically sound, but good enough for validation)
            byte_counts = [0] * 256
            for byte in test_data:
                byte_counts[byte] += 1

            # Check for reasonable distribution
            min_count = min(byte_counts)
            max_count = max(byte_counts)

            # If distribution is too skewed, entropy might be poor
            if max_count - min_count > 8:
                logger.warning("Entropy source distribution appears skewed")
                return False

            return True

        except Exception as e:
            logger.error(f"Entropy source validation failed: {e}")
            return False

    def generate_secure_password(self, length: int = 32) -> str:
        """Generate secure password"""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + string.punctuation
        return "".join(secrets.choice(alphabet) for _ in range(length))


class KeyStorageSecurity:
    """Secure key storage for KME"""

    def __init__(self, encryption_key: bytes | None = None):
        """Initialize key storage security"""
        self.encryption_key = encryption_key or self._generate_encryption_key()
        self.algorithm = algorithms.AES256
        self.mode = modes.GCM

    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key for key storage"""
        return os.urandom(32)  # 256-bit key

    def encrypt_key_data(self, key_data: bytes, key_id: str) -> dict[str, Any]:
        """Encrypt key data for storage"""
        try:
            # Generate random IV
            iv = os.urandom(12)  # 96-bit IV for GCM

            # Create cipher
            cipher = Cipher(
                self.algorithm(self.encryption_key),
                self.mode(iv),
                backend=default_backend(),
            )
            encryptor = cipher.encryptor()

            # Add associated data (key ID for integrity)
            encryptor.authenticate_additional_data(key_id.encode("utf-8"))

            # Encrypt data
            ciphertext = encryptor.update(key_data) + encryptor.finalize()

            # Get authentication tag
            tag = encryptor.tag

            return {
                "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
                "iv": base64.b64encode(iv).decode("utf-8"),
                "tag": base64.b64encode(tag).decode("utf-8"),
                "algorithm": "AES256-GCM",
                "key_id": key_id,
                "encrypted_at": datetime.datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Key encryption failed: {e}")
            raise

    def decrypt_key_data(self, encrypted_data: dict[str, Any]) -> bytes:
        """Decrypt key data from storage"""
        try:
            # Extract components
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            iv = base64.b64decode(encrypted_data["iv"])
            tag = base64.b64decode(encrypted_data["tag"])
            key_id = encrypted_data["key_id"]

            # Create cipher
            cipher = Cipher(
                self.algorithm(self.encryption_key),
                self.mode(iv, tag),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()

            # Add associated data
            decryptor.authenticate_additional_data(key_id.encode("utf-8"))

            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            return plaintext

        except Exception as e:
            logger.error(f"Key decryption failed: {e}")
            raise

    def generate_key_metadata(
        self, key_data: bytes, key_id: str, sae_id: str
    ) -> dict[str, Any]:
        """Generate metadata for key storage"""
        return {
            "key_id": key_id,
            "sae_id": sae_id,
            "key_size": len(key_data) * 8,  # Convert bytes to bits
            "hash": hashlib.sha256(key_data).hexdigest(),
            "created_at": datetime.datetime.utcnow().isoformat(),
            "encryption_algorithm": "AES256-GCM",
            "integrity_protected": True,
        }

    def validate_key_integrity(self, key_data: bytes, expected_hash: str) -> bool:
        """Validate key integrity using hash"""
        actual_hash = hashlib.sha256(key_data).hexdigest()
        return actual_hash == expected_hash


# Global instances
tls_config = TLSConfig()
certificate_manager = CertificateManager()
secure_random = SecureRandomGenerator()
key_storage_security = KeyStorageSecurity()


def get_tls_config() -> TLSConfig:
    """Get TLS configuration instance"""
    return tls_config


def get_certificate_manager() -> CertificateManager:
    """Get certificate manager instance"""
    return certificate_manager


def get_secure_random() -> SecureRandomGenerator:
    """Get secure random generator instance"""
    return secure_random


def get_key_storage_security() -> KeyStorageSecurity:
    """Get key storage security instance"""
    return key_storage_security


def initialize_security_infrastructure() -> bool:
    """Initialize security infrastructure"""
    try:
        logger.info("Initializing KME security infrastructure")

        # Validate entropy source
        if not secure_random.validate_entropy_source():
            logger.error("Entropy source validation failed")
            return False

        # Configure TLS
        tls_config.configure_tls_context()

        # Load CA certificates if configured
        if hasattr(settings, "ca_certificate_path") and settings.ca_certificate_path:
            ca_path = Path(settings.ca_certificate_path)
            if not certificate_manager.load_ca_certificates(ca_path):
                logger.warning(
                    "Failed to load CA certificates, continuing without CA validation"
                )

        logger.info("Security infrastructure initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Security infrastructure initialization failed: {e}")
        return False
