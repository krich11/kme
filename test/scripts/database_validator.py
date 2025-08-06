#!/usr/bin/env python3
"""
Database Validation Tool

Validates database connectivity and schema.
"""

import os
import subprocess
import sys

# Import secure credentials
from credentials import credentials

# Database configuration
DB_CONFIG = credentials.get_database_config()


def test_connection():
    """Test database connection"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_CONFIG["password"]

    cmd = [
        "psql",
        "-h",
        DB_CONFIG["host"],
        "-p",
        DB_CONFIG["port"],
        "-U",
        DB_CONFIG["user"],
        "-d",
        DB_CONFIG["database"],
        "-c",
        "SELECT version();",
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result.returncode == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python database_validator.py [test]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "test":
        if test_connection():
            print("✅ Database connection successful")
            sys.exit(0)
        else:
            print("❌ Database connection failed")
            sys.exit(1)
    else:
        print("Unknown command. Use 'test'")
        sys.exit(1)
