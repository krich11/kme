#!/usr/bin/env python3
"""
KME Admin Configuration

Configuration settings for the KME admin tool when running from the admin/ directory.
All paths are relative to the admin/ directory.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Base paths (relative to admin/ directory)
ADMIN_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = ADMIN_DIR.parent  # Go up one level to get to project root

# Load environment variables from .env file
load_dotenv(ADMIN_DIR / ".env")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://krich:password@localhost/kme_db")

# KME configuration
KME_ID = os.getenv("KME_ID", "KME001")
KME_HOST = os.getenv("KME_HOST", "localhost")
KME_PORT = int(os.getenv("KME_PORT", "8000"))

# Certificate paths (relative to admin/ directory)
CERT_DIR = ADMIN_DIR / "sae_certs"
CA_CERT_PATH = ADMIN_DIR / os.getenv("CA_CERT_PATH", "ca/ca_cert.pem")
CA_KEY_PATH = ADMIN_DIR / os.getenv("CA_KEY_PATH", "ca/ca_key.pem")

# Package paths (relative to admin/ directory)
PACKAGE_DIR = ADMIN_DIR / "packages"
TEMPLATE_DIR = ADMIN_DIR / "templates"

# Test certificate paths (relative to admin/ directory)
TEST_CERT_DIR = PROJECT_ROOT / "test_certs"
KME_CERT_PATH = ADMIN_DIR / os.getenv("KME_CERT_PATH", "../test_certs/kme_cert.pem")
KME_KEY_PATH = ADMIN_DIR / os.getenv("KME_KEY_PATH", "../test_certs/kme_key.pem")

# Environment file paths (relative to admin/ directory)
ENV_FILE = PROJECT_ROOT / ".env"
ENV_TEMPLATE = PROJECT_ROOT / "env.template"

# App paths (relative to admin/ directory)
APP_DIR = PROJECT_ROOT / "app"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

# Certificate generation defaults
DEFAULT_CERT_VALIDITY_DAYS = int(os.getenv("DEFAULT_CERT_VALIDITY_DAYS", "365"))
DEFAULT_KEY_SIZE = int(os.getenv("DEFAULT_KEY_SIZE", "2048"))

# SAE configuration defaults
DEFAULT_MAX_KEYS_PER_REQUEST = int(os.getenv("DEFAULT_MAX_KEYS_PER_REQUEST", "128"))
DEFAULT_MAX_KEY_SIZE = int(os.getenv("DEFAULT_MAX_KEY_SIZE", "1024"))
DEFAULT_MIN_KEY_SIZE = int(os.getenv("DEFAULT_MIN_KEY_SIZE", "64"))

# Security settings
DEFAULT_CA_SUBJECT = os.getenv(
    "DEFAULT_CA_SUBJECT",
    "/C=US/ST=State/L=City/O=KME Organization/OU=KME Unit/CN=KME Development CA",
)
DEFAULT_SAE_SUBJECT_TEMPLATE = os.getenv(
    "DEFAULT_SAE_SUBJECT_TEMPLATE",
    "/C=US/ST=State/L=City/O=KME Organization/OU=KME Unit/CN={sae_id}",
)

# File permissions
CERT_FILE_PERMISSIONS = 0o644  # rw-r--r--
KEY_FILE_PERMISSIONS = 0o600  # rw-------

# Validation settings
SAE_ID_MIN_LENGTH = int(os.getenv("SAE_ID_MIN_LENGTH", "1"))
SAE_ID_MAX_LENGTH = int(os.getenv("SAE_ID_MAX_LENGTH", "255"))

# Database table names
SAE_ENTITIES_TABLE = "sae_entities"
KME_ENTITIES_TABLE = "kme_entities"
KEYS_TABLE = "keys"
KEY_REQUESTS_TABLE = "key_requests"

# Status values
VALID_SAE_STATUSES = ["active", "inactive", "suspended", "expired", "revoked"]
VALID_KEY_STATUSES = ["active", "expired", "consumed", "revoked"]

# Network settings
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Package settings
PACKAGE_ENCRYPTION_ALGORITHM = "AES-256-GCM"
PACKAGE_COMPRESSION = True

# Development settings
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
SKIP_CERT_VALIDATION = os.getenv("SKIP_CERT_VALIDATION", "false").lower() == "true"

# Path validation and creation


def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        CERT_DIR,
        PACKAGE_DIR,
        TEMPLATE_DIR,
        TEST_CERT_DIR,
        CA_CERT_PATH.parent,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_relative_path(path: Path) -> str:
    """Get path relative to admin directory for display"""
    try:
        return str(path.relative_to(ADMIN_DIR))
    except ValueError:
        return str(path)


def get_absolute_path(relative_path: str) -> Path:
    """Convert relative path to absolute path from admin directory"""
    return ADMIN_DIR / relative_path


# Configuration validation


def validate_config():
    """Validate configuration settings"""
    errors = []

    # Check required directories
    if not ADMIN_DIR.exists():
        errors.append(f"Admin directory does not exist: {ADMIN_DIR}")

    if not PROJECT_ROOT.exists():
        errors.append(f"Project root does not exist: {PROJECT_ROOT}")

    # Check database URL format
    if not DATABASE_URL.startswith(("postgresql://", "postgresql+asyncpg://")):
        errors.append(f"Invalid database URL format: {DATABASE_URL}")

    # Check KME ID
    if not KME_ID or len(KME_ID) < SAE_ID_MIN_LENGTH:
        errors.append(f"Invalid KME ID: {KME_ID}")

    # Check port range
    if not (1 <= KME_PORT <= 65535):
        errors.append(f"Invalid KME port: {KME_PORT}")

    if errors:
        raise ValueError(
            f"Configuration validation failed:\n"
            + "\n".join(f"  - {error}" for error in errors)
        )

    return True


# Initialize configuration


if __name__ == "__main__":
    try:
        ensure_directories()
        validate_config()
        print("✅ Configuration validated successfully")
        print(f"Admin directory: {ADMIN_DIR}")
        print(f"Project root: {PROJECT_ROOT}")
        print(f"Database URL: {DATABASE_URL}")
        print(f"KME ID: {KME_ID}")
        print(f"Certificate directory: {get_relative_path(CERT_DIR)}")
        print(f"Package directory: {get_relative_path(PACKAGE_DIR)}")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        exit(1)
