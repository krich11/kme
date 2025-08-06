#!/usr/bin/env python3
"""
Database Setup Tool

Sets up PostgreSQL database for KME testing.
"""

import os
import subprocess
import sys
from pathlib import Path

# Import secure credentials
from credentials import credentials

# Database configuration
DB_CONFIG = credentials.get_database_config()


def setup_database():
    """Set up the database"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_CONFIG["password"]

    # Create database if it doesn't exist
    create_cmd = [
        "createdb",
        "-h",
        DB_CONFIG["host"],
        "-p",
        DB_CONFIG["port"],
        "-U",
        DB_CONFIG["user"],
        DB_CONFIG["database"],
    ]

    result = subprocess.run(create_cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"Failed to create database: {result.stderr}")
        return False

    print("✅ Database setup completed")
    return True


def reset_database():
    """Reset the database to clean state"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_CONFIG["password"]

    # Drop and recreate schema
    reset_cmd = [
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
        "DROP SCHEMA public CASCADE; CREATE SCHEMA public;",
    ]

    result = subprocess.run(reset_cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to reset database: {result.stderr}")
        return False

    print("✅ Database reset completed")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python database_setup.py [setup|reset]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "setup":
        success = setup_database()
    elif command == "reset":
        success = reset_database()
    else:
        print("Unknown command. Use 'setup' or 'reset'")
        sys.exit(1)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
