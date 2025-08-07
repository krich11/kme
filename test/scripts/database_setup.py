#!/usr/bin/env python3
"""
Database Setup Tool

Sets up PostgreSQL database for KME testing.
"""

import os
import subprocess
import sys
from pathlib import Path

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "user": "krich",
    "password": "mustang",
    "database": "kme_db",
}


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

    # Create tables using SQLAlchemy
    create_tables_cmd = ["python", "test/scripts/create_tables.py"]

    result = subprocess.run(create_tables_cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to create tables: {result.stderr}")
        return False

    # Insert KME entity
    kme_id = os.environ.get("KME_ID", "DEFAULT_KME_ID")
    certificate_info = '{"issuer": "CN=CA", "subject": "CN=' + kme_id + '"}'
    insert_kme_cmd = [
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
        f"INSERT INTO kme_entities (id, kme_id, hostname, port, certificate_info, created_at, updated_at) VALUES (gen_random_uuid(), '{kme_id}', 'localhost', 443, '{certificate_info}', NOW(), NOW());",
    ]

    result = subprocess.run(insert_kme_cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0 and "duplicate key" not in result.stderr:
        print(f"Failed to insert KME entity: {result.stderr}")
        return False

    print("✅ Database setup and tables created with KME entity")
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

    # Create tables using SQLAlchemy
    create_tables_cmd = ["python", "test/scripts/create_tables.py"]

    result = subprocess.run(create_tables_cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to create tables: {result.stderr}")
        return False

    print("✅ Database reset and tables created")
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
