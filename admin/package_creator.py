#!/usr/bin/env python3
"""
SAE Package Creator

Creates self-extracting encrypted packages for SAE distribution.
"""

import base64
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Set up logger
logger = logging.getLogger(__name__)


class SAEPackageCreator:
    """Creates self-extracting encrypted SAE packages"""

    def __init__(self, admin_dir: str = "admin"):
        self.admin_dir = Path(admin_dir)
        self.temp_dir: str | None = None

    def create_package(
        self, sae_data: dict[str, Any], output_path: str, password: str
    ) -> str:
        """Create self-extracting encrypted package"""

        logger.info(f"Creating SAE package for {sae_data.get('name', 'Unknown')}")

        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()

        try:
            # 1. Create package contents
            package_dir = self._create_package_contents(sae_data)

            # 2. Create tar.gz archive
            archive_path = self._create_archive(package_dir)

            # 3. Encrypt archive
            encrypted_data = self._encrypt_archive(archive_path, password)

            # 4. Create self-extracting script
            self._create_self_extractor(encrypted_data, sae_data, output_path)

            # 5. Clean up
            self._cleanup()

            logger.info(f"Package created successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Package creation failed: {e}")
            self._cleanup()
            raise e

    def _create_package_contents(self, sae_data: dict[str, Any]) -> Path:
        """Create package directory with all files"""
        if self.temp_dir is None:
            raise RuntimeError("temp_dir not initialized")
        package_dir = Path(self.temp_dir) / "sae_package"
        package_dir.mkdir()

        # Create .config directory for sensitive files
        config_dir = package_dir / ".config"
        config_dir.mkdir()

        # Create configuration JSON for .config directory
        config = {
            "sae_name": sae_data["name"],
            "sae_id": sae_data["sae_id"],
            "kme_endpoint": sae_data["kme_endpoint"],
            "certificate_file": ".config/sae_certificate.pem",
            "private_key_file": ".config/sae_private_key.pem",
            "ca_certificate_file": ".config/kme_ca_certificate.pem",
            "connection_config": {
                "verify_ssl": True,
                "timeout": 30,
                "retry_attempts": 3,
            },
            "api_endpoints": {
                "status": "/api/v1/keys/{slave_SAE_ID}/status",
                "enc_keys": "/api/v1/keys/{slave_SAE_ID}/enc_keys",
                "dec_keys": "/api/v1/keys/{master_SAE_ID}/dec_keys",
            },
            "registration_date": sae_data.get(
                "registration_date", datetime.utcnow().isoformat()
            ),
            "package_version": "1.0.0",
        }

        with open(config_dir / "sae_package.json", "w") as f:
            json.dump(config, f, indent=2)

        # Copy certificate files to .config directory
        shutil.copy2(sae_data["certificate_path"], config_dir / "sae_certificate.pem")
        shutil.copy2(sae_data["private_key_path"], config_dir / "sae_private_key.pem")
        shutil.copy2(
            sae_data["ca_certificate_path"], config_dir / "kme_ca_certificate.pem"
        )

        # Create README and scripts
        self._create_readme(package_dir, sae_data)
        self._create_client_example(package_dir, config)
        self._create_test_script(package_dir, config)
        self._create_security_readme(package_dir)

        return package_dir

    def _create_archive(self, package_dir: Path) -> Path:
        """Create tar.gz archive of package contents"""
        if self.temp_dir is None:
            raise RuntimeError("temp_dir not initialized")
        archive_path = Path(self.temp_dir) / "package.tar.gz"

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(package_dir, arcname=".")

        return archive_path

    def _encrypt_archive(self, archive_path: Path, password: str) -> str:
        """Encrypt the archive with password"""
        # Read archive data
        with open(archive_path, "rb") as f:
            data = f.read()

        # Encrypt using OpenSSL
        result = subprocess.run(
            [
                "openssl",
                "enc",
                "-aes-256-cbc",
                "-salt",
                "-pbkdf2",
                "-pass",
                f"pass:{password}",
                "-base64",
            ],
            input=data,
            capture_output=True,
        )

        if result.returncode != 0:
            stderr_msg = (
                result.stderr.decode("utf-8") if result.stderr else "Unknown error"
            )
            raise Exception(f"Encryption failed: {stderr_msg}")

        return result.stdout.decode("utf-8").strip()

    def _create_self_extractor(
        self, encrypted_data: str, sae_data: dict[str, Any], output_path: str
    ):
        """Create self-extracting script with embedded encrypted data"""

        # Read template
        template_path = Path("templates") / "package_template.sh"
        with open(template_path) as f:
            template = f.read()

        # Replace placeholders
        script_content = (
            template.replace("{{ENCRYPTED_DATA}}", encrypted_data)
            .replace("{{PACKAGE_NAME}}", sae_data["name"])
            .replace("{{SAE_ID}}", sae_data["sae_id"])
            .replace("{{PACKAGE_VERSION}}", "1.0.0")
        )

        # Write self-extracting script
        with open(output_path, "w") as f:
            f.write(script_content)

        # Make executable
        os.chmod(output_path, 0o755)

    def _create_readme(self, package_dir: Path, sae_data: dict[str, Any]):
        """Create README file"""
        readme_content = f"""# SAE Connection Package: {sae_data['name']}

## Overview
This package contains everything needed to connect this SAE to the KME.

## File Structure
```
./
├── client_example.py          # Python client example
├── test_connection.sh         # Connection test script
├── README.md                  # This file
└── SECURITY_README.md         # Security warnings and instructions

.config/
├── sae_package.json           # Configuration and metadata
├── sae_certificate.pem        # SAE certificate for authentication
├── sae_private_key.pem        # SAE private key (keep secure!)
└── kme_ca_certificate.pem     # KME CA certificate for verification
```

## Quick Start
1. Install dependencies: `pip install requests cryptography`
2. Test connection: `./test_connection.sh`
3. Use client example: `python client_example.py`

## Configuration
The `.config/sae_package.json` file contains all connection parameters:
- KME endpoint URL
- SAE ID and name
- API endpoint paths
- Connection settings

## Security Notes
- Sensitive files are stored in `.config/` directory with proper permissions
- Keep private key secure and restrict access
- Verify KME CA certificate before connecting
- Use HTTPS for all communications
- Review SECURITY_README.md for detailed security information

## Support
For issues or questions, contact your KME administrator.
"""

        with open(package_dir / "README.md", "w") as f:
            f.write(readme_content)

    def _create_security_readme(self, package_dir: Path):
        """Create security README"""
        security_content = """# ⚠️ SECURITY WARNINGS ⚠️

## Critical Security Items

### 1. sae_private_key.pem - CRITICAL SECURITY
- This is your SAE's private key
- Keep it secure and restrict access
- File permissions should be 600 (owner read/write only)
- Never share this file
- Never transmit over insecure channels
- Store in secure location with limited access

### 2. sae_certificate.pem - HIGH SECURITY
- Your SAE's public certificate
- Protect from tampering
- File permissions should be 644
- Verify certificate integrity regularly
- Monitor for unauthorized changes

## Operational Security Items

### 3. SAE ID - MEDIUM SECURITY
- Your unique SAE identifier
- Treat as operational security
- Don't share unnecessarily
- Monitor for unauthorized usage
- Report suspicious activity

### 4. KME Endpoint - MEDIUM SECURITY
- KME server address
- May be internal-only
- Don't expose unnecessarily
- Use secure network connections
- Monitor for unauthorized access

## Installation Security

### File Permissions
The installation script automatically sets proper permissions:
- Private key: 600 (owner read/write only)
- Certificate: 644 (owner read/write, others read)
- Scripts: 755 (executable)
- Config: 644 (readable)

### Network Security
- Use HTTPS for all communications
- Verify SSL certificates
- Use secure network connections
- Monitor for unauthorized access

### Access Control
- Limit access to SAE files
- Use principle of least privilege
- Monitor file access
- Log security events

## Emergency Procedures
If you suspect compromise:
1. Immediately revoke SAE access
2. Generate new certificates
3. Update KME registration
4. Monitor for unauthorized activity
5. Report incident to administrator

## Contact Information
For security incidents or questions:
- KME Administrator: [Contact Information]
- Security Team: [Contact Information]
- Emergency: [Emergency Contact]
"""

        with open(package_dir / "SECURITY_README.md", "w") as f:
            f.write(security_content)

    def _create_client_example(self, package_dir: Path, config: dict[str, Any]):
        """Create Python client example"""
        client_content = f"""#!/usr/bin/env python3
\"\"\"
SAE Client Example

This script demonstrates how to connect to the KME and perform key operations.
\"\"\"

import json
import requests
import sys
from pathlib import Path

def load_config():
    \"\"\"Load SAE configuration\"\"\"
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
    \"\"\"Create requests session with certificate authentication\"\"\"
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
    \"\"\"Test connection to KME\"\"\"
    try:
        response = session.get(f"{{config['kme_endpoint']}}/health/ready")
        if response.status_code == 200:
            print("✅ Connection test successful")
            return True
        else:
            print(f"❌ Connection test failed: {{response.status_code}}")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {{e}}")
        return False

def get_status(session, config, slave_sae_id):
    \"\"\"Get key status for slave SAE\"\"\"
    try:
        url = f"{{config['kme_endpoint']}}{{config['api_endpoints']['status']}}"
        url = url.replace("{{slave_SAE_ID}}", slave_sae_id)

        response = session.get(url)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Status retrieved successfully")
            print(f"   Stored keys: {{status.get('stored_key_count', 0)}}")
            print(f"   Max keys per request: {{status.get('max_key_per_request', 0)}}")
            return status
        else:
            print(f"❌ Status request failed: {{response.status_code}}")
            return None
    except Exception as e:
        print(f"❌ Status request failed: {{e}}")
        return None

def request_keys(session, config, slave_sae_id, number=1, size=256):
    \"\"\"Request keys from KME\"\"\"
    try:
        url = f"{{config['kme_endpoint']}}{{config['api_endpoints']['enc_keys']}}"
        url = url.replace("{{slave_SAE_ID}}", slave_sae_id)

        data = {{
            "number": number,
            "size": size
        }}

        response = session.post(url, json=data)
        if response.status_code == 200:
            keys = response.json()
            print(f"✅ Keys requested successfully")
            print(f"   Keys received: {{len(keys.get('keys', []))}}")
            return keys
        else:
            print(f"❌ Key request failed: {{response.status_code}}")
            return None
    except Exception as e:
        print(f"❌ Key request failed: {{e}}")
        return None

def main():
    \"\"\"Main function\"\"\"
    print("=== SAE Client Example ===")

    # Load configuration
    config = load_config()
    print(f"SAE: {{config['sae_name']}} ({{config['sae_id']}})")
    print(f"KME: {{config['kme_endpoint']}}")
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
            if request_keys_input == 'y':
                number = int(input("Number of keys (default 1): ") or "1")
                size = int(input("Key size in bits (default 256): ") or "256")
                request_keys(session, config, slave_sae_id, number, size)

    print("\\nExample completed successfully!")

if __name__ == "__main__":
    main()
"""

        with open(package_dir / "client_example.py", "w") as f:
            f.write(client_content)

        # Make executable
        os.chmod(package_dir / "client_example.py", 0o755)

    def _create_test_script(self, package_dir: Path, config: dict[str, Any]):
        """Create connection test script"""
        test_content = f"""#!/bin/bash
# SAE Connection Test Script

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

# Function to print colored output
print_status() {{
    echo -e "${{GREEN}}[INFO]${{NC}} $1"
}}

print_error() {{
    echo -e "${{RED}}[ERROR]${{NC}} $1"
}}

print_header() {{
    echo -e "${{BLUE}}================================${{NC}}"
    echo -e "${{BLUE}}  SAE Connection Test${{NC}}"
    echo -e "${{BLUE}}================================${{NC}}"
}}

# Load configuration
if [[ -f ".config/sae_package.json" ]]; then
    CONFIG_FILE=".config/sae_package.json"
elif [[ -f "sae_package.json" ]]; then
    CONFIG_FILE="sae_package.json"
else
    print_error "sae_package.json not found in .config/ or current directory"
    exit 1
fi

# Extract values from JSON (requires jq)
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed"
    exit 1
fi

KME_ENDPOINT=$(jq -r '.kme_endpoint' "$CONFIG_FILE")
CERT_FILE=$(jq -r '.certificate_file' "$CONFIG_FILE")
KEY_FILE=$(jq -r '.private_key_file' "$CONFIG_FILE")
CA_FILE=$(jq -r '.ca_certificate_file' "$CONFIG_FILE")
SAE_NAME=$(jq -r '.sae_name' "$CONFIG_FILE")
SAE_ID=$(jq -r '.sae_id' "$CONFIG_FILE")

print_header
echo "SAE: $SAE_NAME ($SAE_ID)"
echo "KME: $KME_ENDPOINT"
echo ""

# Check if files exist
if [[ ! -f "$CERT_FILE" ]]; then
    print_error "Certificate file not found: $CERT_FILE"
    exit 1
fi

if [[ ! -f "$KEY_FILE" ]]; then
    print_error "Private key file not found: $KEY_FILE"
    exit 1
fi

if [[ ! -f "$CA_FILE" ]]; then
    print_error "CA certificate file not found: $CA_FILE"
    exit 1
fi

# Test 1: Health check
print_status "Testing KME health..."
HEALTH_RESPONSE=$(curl -s -w "\\nHTTP_STATUS:%{{http_code}}" \\
    -X GET "$KME_ENDPOINT/health/ready" \\
    --cert "$CERT_FILE" \\
    --key "$KEY_FILE" \\
    --cacert "$CA_FILE" \\
    --connect-timeout 10)

HTTP_STATUS=$(echo "$HEALTH_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | grep -v "HTTP_STATUS:")

if [[ "$HTTP_STATUS" == "200" ]]; then
    print_status "✅ Health check successful"
else
    print_error "❌ Health check failed: HTTP $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

# Test 2: Detailed health check
print_status "Testing detailed health..."
DETAILED_RESPONSE=$(curl -s -w "\\nHTTP_STATUS:%{{http_code}}" \\
    -X GET "$KME_ENDPOINT/health/detailed" \\
    --cert "$CERT_FILE" \\
    --key "$KEY_FILE" \\
    --cacert "$CA_FILE" \\
    --connect-timeout 10)

HTTP_STATUS=$(echo "$DETAILED_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$DETAILED_RESPONSE" | grep -v "HTTP_STATUS:")

if [[ "$HTTP_STATUS" == "200" ]]; then
    print_status "✅ Detailed health check successful"
    # Extract status from response
    STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status' 2>/dev/null)
    echo "   KME Status: $STATUS"
else
    print_error "❌ Detailed health check failed: HTTP $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
fi

# Test 3: SAE status endpoint
print_status "Testing SAE status endpoint..."
STATUS_RESPONSE=$(curl -s -w "\\nHTTP_STATUS:%{{http_code}}" \\
    -X GET "$KME_ENDPOINT/api/v1/keys/$SAE_ID/status" \\
    --cert "$CERT_FILE" \\
    --key "$KEY_FILE" \\
    --cacert "$CA_FILE" \\
    --connect-timeout 10)

HTTP_STATUS=$(echo "$STATUS_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$STATUS_RESPONSE" | grep -v "HTTP_STATUS:")

if [[ "$HTTP_STATUS" == "200" ]]; then
    print_status "✅ SAE status check successful"
    # Extract key information
    STORED_KEYS=$(echo "$RESPONSE_BODY" | jq -r '.stored_key_count' 2>/dev/null)
    MAX_KEYS=$(echo "$RESPONSE_BODY" | jq -r '.max_key_per_request' 2>/dev/null)
    echo "   Stored keys: $STORED_KEYS"
    echo "   Max keys per request: $MAX_KEYS"
else
    print_error "❌ SAE status check failed: HTTP $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
fi

echo ""
print_status "Connection test completed!"
print_status "All tests passed successfully!"
"""

        with open(package_dir / "test_connection.sh", "w") as f:
            f.write(test_content)

        # Make executable
        os.chmod(package_dir / "test_connection.sh", 0o755)

    def _cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
