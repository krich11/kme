#!/usr/bin/env python3
"""
Certificate Validation Tool

Validates certificate structure, chain, and compliance.
"""

import subprocess
import sys
from pathlib import Path


def validate_certificate(cert_path: str) -> bool:
    """Validate a certificate"""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-text", "-noout"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def validate_cert_chain(ca_path: str, cert_path: str) -> bool:
    """Validate certificate chain"""
    try:
        result = subprocess.run(
            ["openssl", "verify", "-CAfile", ca_path, cert_path],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python certificate_validator.py <cert_path> [ca_path]")
        sys.exit(1)

    cert_path = sys.argv[1]
    if not validate_certificate(cert_path):
        print(f"❌ Certificate validation failed: {cert_path}")
        sys.exit(1)

    if len(sys.argv) > 2:
        ca_path = sys.argv[2]
        if not validate_cert_chain(ca_path, cert_path):
            print(f"❌ Certificate chain validation failed")
            sys.exit(1)

    print(f"✅ Certificate validation successful: {cert_path}")
