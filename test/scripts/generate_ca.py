#!/usr/bin/env python3
"""
Simple CA Generation Script

This script generates a CA certificate and private key using OpenSSL.
"""

import os
import subprocess
import sys
from pathlib import Path


def generate_ca(ca_dir: str = "certs/ca", ca_name: str = "Test KME CA"):
    """Generate CA certificate and private key"""

    ca_path = Path(ca_dir)
    ca_path.mkdir(parents=True, exist_ok=True)

    ca_key = ca_path / "ca.key"
    ca_cert = ca_path / "ca.crt"

    print(f"Generating CA in: {ca_path}")

    # Generate CA private key
    print("Generating CA private key...")
    key_cmd = ["openssl", "genrsa", "-out", str(ca_key), "2048"]

    result = subprocess.run(key_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to generate CA key: {result.stderr}")
        return False

    # Generate CA certificate
    print("Generating CA certificate...")
    cert_cmd = [
        "openssl",
        "req",
        "-new",
        "-x509",
        "-days",
        "3650",
        "-key",
        str(ca_key),
        "-out",
        str(ca_cert),
        "-subj",
        f"/C=US/ST=CA/L=San Francisco/O=Test KME Organization/CN={ca_name}",
    ]

    result = subprocess.run(cert_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to generate CA certificate: {result.stderr}")
        return False

    print(f"✅ CA generated successfully:")
    print(f"   Key: {ca_key}")
    print(f"   Certificate: {ca_cert}")

    return True


def generate_kme_cert(ca_dir: str = "certs/ca", kme_id: str = None):
    """Generate KME certificate using the CA"""

    # KME ID must be provided - this is an error condition if it's not
    if kme_id is None:
        print("❌ ERROR: KME ID must be provided for certificate generation")
        print(
            "   This indicates an installation error - KME ID should be determined earlier"
        )
        return False

    ca_path = Path(ca_dir)
    ca_key = ca_path / "ca.key"
    ca_cert = ca_path / "ca.crt"

    if not ca_key.exists() or not ca_cert.exists():
        print("CA files not found. Generate CA first.")
        return False

    kme_key = Path("certs/kme_key.pem")
    kme_cert = Path("certs/kme_cert.pem")

    print(f"Generating KME certificate for ID: {kme_id}")

    # Generate KME private key
    print("Generating KME private key...")
    key_cmd = ["openssl", "genrsa", "-out", str(kme_key), "2048"]

    result = subprocess.run(key_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to generate KME key: {result.stderr}")
        return False

    # Generate KME certificate signing request
    print("Generating KME certificate signing request...")
    csr_cmd = [
        "openssl",
        "req",
        "-new",
        "-key",
        str(kme_key),
        "-out",
        "kme.csr",
        "-subj",
        f"/C=US/ST=CA/L=San Francisco/O=Test KME Organization/CN={kme_id}",
    ]

    result = subprocess.run(csr_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to generate KME CSR: {result.stderr}")
        return False

    # Sign KME certificate with CA
    print("Signing KME certificate with CA...")
    sign_cmd = [
        "openssl",
        "x509",
        "-req",
        "-days",
        "365",
        "-in",
        "kme.csr",
        "-CA",
        str(ca_cert),
        "-CAkey",
        str(ca_key),
        "-CAcreateserial",
        "-out",
        str(kme_cert),
    ]

    result = subprocess.run(sign_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to sign KME certificate: {result.stderr}")
        return False

    # Clean up CSR
    os.remove("kme.csr")

    print(f"✅ KME certificate generated successfully:")
    print(f"   Key: {kme_key}")
    print(f"   Certificate: {kme_cert}")

    return True


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python generate_ca.py [ca|kme] [ca_name|kme_id]")
        print("Commands:")
        print("  ca [ca_name]    Generate CA certificate and key (CA name optional)")
        print("  kme [kme_id]    Generate KME certificate (KME ID optional)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "ca":
        # Use provided CA name or default
        ca_name = sys.argv[2] if len(sys.argv) > 2 else "KME Root CA"
        success = generate_ca(ca_name=ca_name)
    elif command == "kme":
        # Use provided KME ID or error out
        if len(sys.argv) > 2:
            kme_id = sys.argv[2]
            success = generate_kme_cert(kme_id=kme_id)
        else:
            print("❌ ERROR: KME ID must be provided")
            print("Usage: python generate_ca.py kme <KME_ID>")
            print("Example: python generate_ca.py kme 63BF19E5AD497358")
            sys.exit(1)
    else:
        print("Unknown command. Use 'ca' or 'kme'")
        sys.exit(1)

    if success:
        print("✅ Operation completed successfully")
        sys.exit(0)
    else:
        print("❌ Operation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
