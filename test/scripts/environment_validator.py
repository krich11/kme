#!/usr/bin/env python3
"""
Environment Validator

Validates the test environment setup.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return (
            False,
            f"Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)",
        )


def check_openssl():
    """Check OpenSSL availability"""
    try:
        result = subprocess.run(["openssl", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, "OpenSSL not available"
    except Exception:
        return False, "OpenSSL not found"


def check_postgresql():
    """Check PostgreSQL availability"""
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, "PostgreSQL not available"
    except Exception:
        return False, "PostgreSQL not found"


def check_nginx():
    """Check nginx availability"""
    try:
        result = subprocess.run(["nginx", "-v"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, "nginx not available"
    except Exception:
        return False, "nginx not found"


def main():
    """Main validation function"""
    checks = [
        ("Python Version", check_python_version),
        ("OpenSSL", check_openssl),
        ("PostgreSQL", check_postgresql),
        ("Nginx", check_nginx),
    ]

    print("=== Environment Validation ===")

    all_passed = True
    for name, check_func in checks:
        passed, details = check_func()
        status = "✅" if passed else "❌"
        print(f"{status} {name}: {details}")

        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ Environment validation passed")
        sys.exit(0)
    else:
        print("\n❌ Environment validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
