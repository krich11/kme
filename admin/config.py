#!/usr/bin/env python3
"""
KME Admin Configuration

Configuration settings for the KME admin tool.
Uses centralized configuration from app/core/config.py with admin-specific overrides.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file in project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
load_dotenv(PROJECT_ROOT / ".env")

# Import main app configuration
try:
    from app.core.config import settings
except ImportError:
    # Fallback if main app config is not available
    class FallbackSettings:
        # Database
        DATABASE_URL = os.getenv(
            "DATABASE_URL", "postgresql://krich:password@localhost/kme_db"
        )

        # KME Identity
        KME_ID = os.getenv("KME_ID", "KME001")
        KME_HOST = os.getenv("KME_HOST", "localhost")
        KME_PORT = int(os.getenv("KME_PORT", "443"))

        # Certificate defaults
        DEFAULT_CERT_VALIDITY_DAYS = int(os.getenv("DEFAULT_CERT_VALIDITY_DAYS", "365"))
        DEFAULT_KEY_SIZE = int(os.getenv("DEFAULT_KEY_SIZE", "2048"))

        # SAE defaults
        DEFAULT_MAX_KEYS_PER_REQUEST = int(
            os.getenv("DEFAULT_MAX_KEYS_PER_REQUEST", "128")
        )
        DEFAULT_MAX_KEY_SIZE = int(os.getenv("DEFAULT_MAX_KEY_SIZE", "1024"))
        DEFAULT_MIN_KEY_SIZE = int(os.getenv("DEFAULT_MIN_KEY_SIZE", "64"))

        # Timeouts
        DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))

        # Security
        SECURITY_LEVEL = os.getenv("SECURITY_LEVEL", "production")

    # Create fallback settings instance
    fallback_settings = FallbackSettings()
    settings = fallback_settings  # type: ignore

# Admin-specific paths (relative to project root)
ADMIN_DIR = PROJECT_ROOT / "admin"
CERT_DIR = PROJECT_ROOT / "certs"
SAE_CERTS_DIR = CERT_DIR / "sae_certs"
CA_DIR = CERT_DIR / "ca"
PACKAGE_DIR = ADMIN_DIR / "packages"
TEMPLATE_DIR = ADMIN_DIR / "templates"

# Certificate file paths
CA_CERT_PATH = CA_DIR / "ca.crt"
CA_KEY_PATH = CA_DIR / "ca.key"
KME_CERT_PATH = CERT_DIR / "kme_cert.pem"
KME_KEY_PATH = CERT_DIR / "kme_key.pem"

# File permissions
CERT_FILE_PERMISSIONS = 0o644  # rw-r--r--
KEY_FILE_PERMISSIONS = 0o600  # rw-------

# Database table names
SAE_ENTITIES_TABLE = "sae_entities"
KME_ENTITIES_TABLE = "kme_entities"
KEYS_TABLE = "keys"
KEY_REQUESTS_TABLE = "key_requests"

# Status values
VALID_SAE_STATUSES = ["active", "inactive", "suspended", "expired", "revoked"]
VALID_KEY_STATUSES = ["active", "expired", "consumed", "revoked"]

# Package settings
PACKAGE_ENCRYPTION_ALGORITHM = "AES-256-GCM"
PACKAGE_COMPRESSION = True

# Development settings
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
SKIP_CERT_VALIDATION = os.getenv("SKIP_CERT_VALIDATION", "false").lower() == "true"

# Validation settings
SAE_ID_MIN_LENGTH = int(os.getenv("SAE_ID_MIN_LENGTH", "1"))
SAE_ID_MAX_LENGTH = int(os.getenv("SAE_ID_MAX_LENGTH", "255"))


def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        CERT_DIR,
        SAE_CERTS_DIR,
        CA_DIR,
        PACKAGE_DIR,
        TEMPLATE_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_relative_path(path: Path) -> str:
    """Get path relative to project root for display"""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def validate_config():
    """Validate configuration settings"""
    errors = []

    # Check required directories
    if not PROJECT_ROOT.exists():
        errors.append(f"Project root does not exist: {PROJECT_ROOT}")

    if not ADMIN_DIR.exists():
        errors.append(f"Admin directory does not exist: {ADMIN_DIR}")

    # Check database URL format
    if not settings.DATABASE_URL.startswith(("postgresql://", "postgresql+asyncpg://")):
        errors.append(f"Invalid database URL format: {settings.DATABASE_URL}")

    # Check KME ID
    if not settings.KME_ID or len(settings.KME_ID) < SAE_ID_MIN_LENGTH:
        errors.append(f"Invalid KME ID: {settings.KME_ID}")

    # Check port range
    if not (1 <= settings.KME_PORT <= 65535):
        errors.append(f"Invalid KME port: {settings.KME_PORT}")

    if errors:
        raise ValueError(
            f"Configuration validation failed:\n"
            + "\n".join(f"  - {error}" for error in errors)
        )

    return True


if __name__ == "__main__":
    try:
        ensure_directories()
        validate_config()
        print("✅ Configuration validated successfully")
        print(f"Project root: {PROJECT_ROOT}")
        print(f"Admin directory: {get_relative_path(ADMIN_DIR)}")
        print(f"Database URL: {settings.DATABASE_URL}")
        print(f"KME ID: {settings.KME_ID}")
        print(f"Certificate directory: {get_relative_path(CERT_DIR)}")
        print(f"SAE certificates: {get_relative_path(SAE_CERTS_DIR)}")
        print(f"Package directory: {get_relative_path(PACKAGE_DIR)}")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        exit(1)
