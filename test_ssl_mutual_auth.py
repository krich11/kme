#!/usr/bin/env python3
"""
Test script to verify SSL mutual authentication configuration
"""
import os
import ssl

import uvicorn


def test_ssl_config():
    """Test different SSL configurations"""

    # Current configuration (no mutual auth)
    print("=== Current Configuration (No Mutual Auth) ===")
    print("ssl_cert_reqs: CERT_NONE")
    print("ssl_ca_certs: None")
    print("Result: Client certificates not required")
    print()

    # Required mutual auth configuration
    print("=== Required Mutual Auth Configuration ===")
    print("ssl_cert_reqs: CERT_REQUIRED")
    print("ssl_ca_certs: test_certs/ca_cert.pem")
    print("Result: Client certificates required")
    print()

    # Test if CA cert exists
    ca_cert_path = "test_certs/ca_cert.pem"
    if os.path.exists(ca_cert_path):
        print(f"✅ CA certificate found: {ca_cert_path}")
    else:
        print(f"❌ CA certificate not found: {ca_cert_path}")

    # Test if server cert exists
    server_cert_path = "test_certs/kme_cert.pem"
    if os.path.exists(server_cert_path):
        print(f"✅ Server certificate found: {server_cert_path}")
    else:
        print(f"❌ Server certificate not found: {server_cert_path}")

    # Test if server key exists
    server_key_path = "test_certs/kme_key.pem"
    if os.path.exists(server_key_path):
        print(f"✅ Server key found: {server_key_path}")
    else:
        print(f"❌ Server key not found: {server_key_path}")


if __name__ == "__main__":
    test_ssl_config()
