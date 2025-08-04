#!/usr/bin/env python3
# This script automatically activates the virtual environment
# -*- coding: utf-8 -*-
"""
SAE Client Example

This script demonstrates how to connect to the KME and perform key operations.
Automatically activates the virtual environment if available.
"""

import json
import os
import subprocess  # nosec B404 - Required for virtual environment activation
import sys
from pathlib import Path

import requests


def activate_venv():
    """Activate virtual environment if it exists"""
    venv_python = Path("venv/bin/python")
    if venv_python.exists():
        # Replace current process with venv python
        os.execv(
            str(venv_python), [str(venv_python)] + sys.argv
        )  # nosec B606 - Safe process replacement for venv activation
    else:
        print("Warning: Virtual environment not found. Using system Python.")
        print(
            "To create virtual environment: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        )


# Try to activate virtual environment
activate_venv()


def load_config():
    """Load SAE configuration"""
    # Try .config directory first (default)
    config_file = Path(".config/sae_package.json")
    if not config_file.exists():
        # Fallback to current directory
        config_file = Path("sae_package.json")
        if not config_file.exists():
            print("Error: sae_package.json not found in .config/ or current directory")
            sys.exit(1)

    with open(config_file) as f:
        return json.load(f)


def create_session(config):
    """Create requests session with certificate authentication"""
    session = requests.Session()

    # Set up certificate authentication
    cert_file = config["certificate_file"]
    key_file = config["private_key_file"]
    ca_file = config["ca_certificate_file"]

    session.cert = (cert_file, key_file)
    session.verify = ca_file

    # Set connection parameters
    session.timeout = config["connection_config"]["timeout"]

    return session


def test_connection(session, config):
    """Test connection to KME"""
    try:
        response = session.get(f"{config['kme_endpoint']}/health/ready")
        if response.status_code == 200:
            print("✅ Connection test successful")
            return True
        else:
            print(f"❌ Connection test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def get_status(session, config, slave_sae_id):
    """Get key status for slave SAE"""
    try:
        url = f"{config['kme_endpoint']}{config['api_endpoints']['status']}"
        url = url.replace("{slave_SAE_ID}", slave_sae_id)

        response = session.get(url)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Status retrieved successfully")
            print(f"   Stored keys: {status.get('stored_key_count', 0)}")
            print(f"   Max keys per request: {status.get('max_key_per_request', 0)}")
            return status
        else:
            print(f"❌ Status request failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Status request failed: {e}")
        return None


def request_keys(session, config, slave_sae_id, number=1, size=256):
    """Request keys from KME"""
    try:
        url = f"{config['kme_endpoint']}{config['api_endpoints']['enc_keys']}"
        url = url.replace("{slave_SAE_ID}", slave_sae_id)

        data = {"number": number, "size": size}

        response = session.post(url, json=data)
        if response.status_code == 200:
            keys = response.json()
            print(f"✅ Keys requested successfully")
            print(f"   Keys received: {len(keys.get('keys', []))}")
            return keys
        else:
            print(f"❌ Key request failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Key request failed: {e}")
        return None


def main():
    """Main function"""
    print("=== SAE Client Example ===")

    # Load configuration
    config = load_config()
    print(f"SAE: {config['sae_name']} ({config['sae_id']})")
    print(f"KME: {config['kme_endpoint']}")
    print()

    # Create session
    session = create_session(config)

    # Test connection
    if not test_connection(session, config):
        print("Cannot proceed without connection")
        sys.exit(1)

    # Example: Get status for another SAE
    slave_sae_id = input("Enter slave SAE ID to check status: ").strip()
    if slave_sae_id:
        status = get_status(session, config, slave_sae_id)
        if status:
            # Example: Request keys
            request_keys_input = input("Request keys? (y/n): ").strip().lower()
            if request_keys_input == "y":
                number = int(input("Number of keys (default 1): ") or "1")
                size = int(input("Key size in bits (default 256): ") or "256")
                request_keys(session, config, slave_sae_id, number, size)

    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()
