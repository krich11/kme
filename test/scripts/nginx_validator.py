#!/usr/bin/env python3
"""
Nginx Configuration Validator

Validates nginx configuration.
"""

import subprocess
import sys
from pathlib import Path


def validate_nginx_config(config_path: str) -> bool:
    """Validate nginx configuration"""
    try:
        # Convert to absolute path
        abs_config_path = Path(config_path).resolve()

        result = subprocess.run(
            ["nginx", "-t", "-c", str(abs_config_path)], capture_output=True, text=True
        )

        # Check if syntax is ok (ignore permission errors for logs/pid)
        if "syntax is ok" in result.stdout or "syntax is ok" in result.stderr:
            return True
        else:
            return False
    except Exception:
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python nginx_validator.py <config_path>")
        sys.exit(1)

    config_path = sys.argv[1]

    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)

    if validate_nginx_config(config_path):
        print(f"✅ Nginx configuration valid: {config_path}")
        sys.exit(0)
    else:
        print(f"❌ Nginx configuration invalid: {config_path}")
        sys.exit(1)
