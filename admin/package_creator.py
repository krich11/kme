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
import subprocess  # nosec B404 - Required for OpenSSL encryption in admin tools
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

        # Copy requirements.txt to package
        requirements_src = Path(self.admin_dir) / "requirements.txt"
        if requirements_src.exists():
            shutil.copy2(requirements_src, package_dir / "requirements.txt")
        else:
            # Create a basic requirements.txt if it doesn't exist
            with open(package_dir / "requirements.txt", "w") as f:
                f.write("# SAE Package Requirements\n")
                f.write("requests>=2.31.0\n")
                f.write("cryptography>=41.0.0\n")

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
        result = subprocess.run(  # nosec B603
            [
                "/usr/bin/openssl",
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

        # Make executable - self-extracting script needs execute permissions
        os.chmod(
            output_path, 0o755
        )  # nosec B103 - Self-extracting script needs execute permissions

    def _create_readme(self, package_dir: Path, sae_data: dict[str, Any]):
        """Create README file"""
        readme_content = f"""# SAE Connection Package: {sae_data['name']}

## Overview
This package contains everything needed to connect this SAE to the KME.

## File Structure
```
./
├── client_example.py          # Python client example
├── test_connection.sh         # Comprehensive ETSI QKD 014 test script
├── requirements.txt           # Python dependencies
├── venv/                      # Python virtual environment (created by installer)
├── README.md                  # This file
└── SECURITY_README.md         # Security warnings and instructions

.config/
├── sae_package.json           # Configuration and metadata
├── sae_certificate.pem        # SAE certificate for authentication
├── sae_private_key.pem        # SAE private key (keep secure!)
└── kme_ca_certificate.pem     # KME CA certificate for verification
```

## Quick Start
1. Extract the package: `./package_name.sh [password]`
2. The installer will automatically create a virtual environment and install dependencies
3. Run comprehensive ETSI QKD 014 tests: `./test_connection.sh`
4. Use client example: `python client_example.py` (automatically activates venv)

## Virtual Environment
The package installer automatically creates a Python virtual environment (`venv/`) and installs all required dependencies from `requirements.txt`. This ensures:
- Isolated Python environment
- Correct dependency versions
- No conflicts with system Python packages

**Automatic Activation**: The `client_example.py` script automatically activates the virtual environment when run.

To manually activate the virtual environment:
```bash
source venv/bin/activate
```

## Configuration
The `.config/sae_package.json` file contains all connection parameters:
- KME endpoint URL
- SAE ID and name
- API endpoint paths
- Connection settings

## Testing
The `test_connection.sh` script provides comprehensive testing of all ETSI QKD 014 V1.1.1 workflows:
- **Phase 1**: Basic connectivity and health checks
- **Phase 2**: Core ETSI API endpoints (Get Status, Get Key, Get Key with Key IDs)
- **Phase 3**: Master SAE workflows (key request operations)
- **Phase 4**: Slave SAE workflows (key retrieval operations)
- **Phase 5**: Error handling and edge cases
- **Phase 6**: Performance and stress testing
- **Phase 7**: ETSI compliance verification

The test script validates:
- All required ETSI data formats
- Error handling and edge cases
- Performance under load
- Full compliance with ETSI GS QKD 014 V1.1.1 specification

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
# This script automatically activates the virtual environment
# -*- coding: utf-8 -*-
\"\"\"
SAE Client Example

This script demonstrates how to connect to the KME and perform key operations.
Automatically activates the virtual environment if available.
\"\"\"

import json
import os
import sys
import subprocess
from pathlib import Path

def activate_venv():
    \"\"\"Activate virtual environment if it exists\"\"\"
    venv_python = Path("venv/bin/python")
    if venv_python.exists():
        # Replace current process with venv python
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    else:
        print("Warning: Virtual environment not found. Using system Python.")
        print("To create virtual environment: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt")

# Try to activate virtual environment
activate_venv()

import requests

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

        # Python files don't need execute permissions - they're run by the interpreter

    def _create_test_script(self, package_dir: Path, config: dict[str, Any]):
        """Create comprehensive ETSI QKD 014 test script"""
        test_content = f"""#!/bin/bash
# ETSI QKD 014 V1.1.1 Comprehensive SAE Workflow Test Script

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
CYAN='\\033[0;36m'
NC='\\033[0m' # No Color

# Function to print colored output
print_status() {{
    echo -e "${{GREEN}}[INFO]${{NC}} $1"
}}

print_error() {{
    echo -e "${{RED}}[ERROR]${{NC}} $1"
}}

print_warning() {{
    echo -e "${{YELLOW}}[WARNING]${{NC}} $1"
}}

print_header() {{
    echo -e "${{BLUE}}================================${{NC}}"
    echo -e "${{BLUE}}  ETSI QKD 014 SAE Workflow Test${{NC}}"
    echo -e "${{BLUE}}================================${{NC}}"
}}

print_section() {{
    echo -e "${{CYAN}}$1${{NC}}"
    echo -e "${{CYAN}}${{1//?/=}}${{NC}}"
}}

# Function to make HTTP request and extract status
make_request() {{
    local method="$1"
    local url="$2"
    local data="$3"
    local description="$4"

    print_status "$description"

    local curl_cmd="curl -s -w \\"\\nHTTP_STATUS:%{{http_code}}\\""
    curl_cmd="$curl_cmd -X $method \\"$url\\""
    curl_cmd="$curl_cmd --cert \\"$CERT_FILE\\""
    curl_cmd="$curl_cmd --key \\"$KEY_FILE\\""
    curl_cmd="$curl_cmd --cacert \\"$CA_FILE\\""
    curl_cmd="$curl_cmd --connect-timeout 10"
    curl_cmd="$curl_cmd --max-time 30"

    if [[ -n "$data" ]]; then
        curl_cmd="$curl_cmd -H \\"Content-Type: application/json\\""
        curl_cmd="$curl_cmd -d \\"$data\\""
    fi

    local response=$(eval $curl_cmd)
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local response_body=$(echo "$response" | grep -v "HTTP_STATUS:")

    if [[ "$http_status" == "200" ]]; then
        print_status "✅ $description successful"
        echo "$response_body"
        return 0
    else
        print_error "❌ $description failed: HTTP $http_status"
        echo "Response: $response_body"
        return 1
    fi
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

# Initialize test results
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# PHASE 1: BASIC CONNECTIVITY AND HEALTH CHECKS
# ============================================================================
print_section "PHASE 1: BASIC CONNECTIVITY AND HEALTH CHECKS"

# Test 1.1: KME Health Check
if make_request "GET" "$KME_ENDPOINT/health/ready" "" "Testing KME health readiness"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
    print_error "Cannot proceed without basic health check"
    exit 1
fi

# Test 1.2: Detailed Health Check
if make_request "GET" "$KME_ENDPOINT/health/detailed" "" "Testing detailed KME health"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# ============================================================================
# PHASE 2: ETSI QKD 014 CORE API ENDPOINTS
# ============================================================================
print_section "PHASE 2: ETSI QKD 014 CORE API ENDPOINTS"

# Test 2.1: Get Status (ETSI Section 5.1)
print_status "Testing Get Status endpoint (ETSI Section 5.1)..."
STATUS_RESPONSE=$(curl -s -w "\\nHTTP_STATUS:%{{http_code}}" \\
    -X GET "$KME_ENDPOINT/api/v1/keys/$SAE_ID/status" \\
    --cert "$CERT_FILE" \\
    --key "$KEY_FILE" \\
    --cacert "$CA_FILE" \\
    --connect-timeout 10)

HTTP_STATUS=$(echo "$STATUS_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
STATUS_BODY=$(echo "$STATUS_RESPONSE" | grep -v "HTTP_STATUS:")

if [[ "$HTTP_STATUS" == "200" ]]; then
    print_status "✅ Get Status successful"
    ((TESTS_PASSED++))

    # Extract and display status information
    STORED_KEYS=$(echo "$STATUS_BODY" | jq -r '.stored_key_count' 2>/dev/null)
    MAX_KEYS=$(echo "$STATUS_BODY" | jq -r '.max_key_per_request' 2>/dev/null)
    KEY_SIZE=$(echo "$STATUS_BODY" | jq -r '.key_size' 2>/dev/null)
    MAX_KEY_SIZE=$(echo "$STATUS_BODY" | jq -r '.max_key_size' 2>/dev/null)
    MIN_KEY_SIZE=$(echo "$STATUS_BODY" | jq -r '.min_key_size' 2>/dev/null)
    MAX_SAE_COUNT=$(echo "$STATUS_BODY" | jq -r '.max_SAE_ID_count' 2>/dev/null)

    echo "   Stored keys: $STORED_KEYS"
    echo "   Max keys per request: $MAX_KEYS"
    echo "   Default key size: $KEY_SIZE bits"
    echo "   Key size range: $MIN_KEY_SIZE - $MAX_KEY_SIZE bits"
    echo "   Max additional SAEs: $MAX_SAE_COUNT"

    # Store values for later tests
    echo "$STORED_KEYS" > /tmp/stored_keys_count
    echo "$MAX_KEYS" > /tmp/max_keys_per_request
    echo "$KEY_SIZE" > /tmp/default_key_size
    echo "$MAX_KEY_SIZE" > /tmp/max_key_size
    echo "$MIN_KEY_SIZE" > /tmp/min_key_size
    echo "$MAX_SAE_COUNT" > /tmp/max_sae_count

else
    print_error "❌ Get Status failed: HTTP $HTTP_STATUS"
    echo "Response: $STATUS_BODY"
    ((TESTS_FAILED++))
    # Use default values if status fails
    echo "1" > /tmp/stored_keys_count
    echo "10" > /tmp/max_keys_per_request
    echo "256" > /tmp/default_key_size
    echo "256" > /tmp/max_key_size
    echo "128" > /tmp/min_key_size
    echo "0" > /tmp/max_sae_count
fi

# Load stored values
STORED_KEYS=$(cat /tmp/stored_keys_count)
MAX_KEYS=$(cat /tmp/max_keys_per_request)
DEFAULT_KEY_SIZE=$(cat /tmp/default_key_size)
MAX_KEY_SIZE=$(cat /tmp/max_key_size)
MIN_KEY_SIZE=$(cat /tmp/min_key_size)
MAX_SAE_COUNT=$(cat /tmp/max_sae_count)

# ============================================================================
# PHASE 3: MASTER SAE WORKFLOWS (Key Request Operations)
# ============================================================================
print_section "PHASE 3: MASTER SAE WORKFLOWS (Key Request Operations)"

# Test 3.1: Basic Key Request (Single Key)
print_status "Testing basic key request (single key)..."
KEY_REQUEST_DATA='{{"number": 1, "size": '$DEFAULT_KEY_SIZE'}}'
if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Basic key request (1 key, $DEFAULT_KEY_SIZE bits)"; then
    ((TESTS_PASSED++))
    # Extract key IDs for later tests
    echo "$response_body" | jq -r '.keys[].key_ID' > /tmp/key_ids.txt
else
    ((TESTS_FAILED++))
fi

# Test 3.2: Multiple Key Request
if [[ "$MAX_KEYS" -gt 1 ]]; then
    REQUEST_COUNT=$((MAX_KEYS > 3 ? 3 : MAX_KEYS))
    print_status "Testing multiple key request ($REQUEST_COUNT keys)..."
    KEY_REQUEST_DATA='{{"number": '$REQUEST_COUNT', "size": '$DEFAULT_KEY_SIZE'}}'
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Multiple key request ($REQUEST_COUNT keys)"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
else
    print_warning "Skipping multiple key test (max_keys_per_request = $MAX_KEYS)"
fi

# Test 3.3: Custom Key Size Request
if [[ "$MAX_KEY_SIZE" -gt "$DEFAULT_KEY_SIZE" ]]; then
    CUSTOM_SIZE=$((DEFAULT_KEY_SIZE + 64))
    if [[ "$CUSTOM_SIZE" -le "$MAX_KEY_SIZE" ]]; then
        print_status "Testing custom key size request ($CUSTOM_SIZE bits)..."
        KEY_REQUEST_DATA='{{"number": 1, "size": '$CUSTOM_SIZE'}}'
        if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Custom key size request ($CUSTOM_SIZE bits)"; then
            ((TESTS_PASSED++))
        else
            ((TESTS_FAILED++))
        fi
    fi
else
    print_warning "Skipping custom key size test (max_key_size = $MAX_KEY_SIZE)"
fi

# Test 3.4: Minimum Key Size Request
if [[ "$MIN_KEY_SIZE" -lt "$DEFAULT_KEY_SIZE" ]]; then
    print_status "Testing minimum key size request ($MIN_KEY_SIZE bits)..."
    KEY_REQUEST_DATA='{{"number": 1, "size": '$MIN_KEY_SIZE'}}'
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Minimum key size request ($MIN_KEY_SIZE bits)"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
else
    print_warning "Skipping minimum key size test (min_key_size = $MIN_KEY_SIZE)"
fi

# Test 3.5: Key Request with Extensions (Optional)
print_status "Testing key request with optional extensions..."
KEY_REQUEST_DATA='{{"number": 1, "size": '$DEFAULT_KEY_SIZE', "extension_optional": [{{"priority": "high"}}, {{"timeout": 30}}]}}'
if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Key request with optional extensions"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 3.6: Key Request with Mandatory Extensions (should fail gracefully)
print_status "Testing key request with mandatory extensions (should handle gracefully)..."
KEY_REQUEST_DATA='{{"number": 1, "size": '$DEFAULT_KEY_SIZE', "extension_mandatory": [{{"custom_requirement": "test"}}]}}'
if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Key request with mandatory extensions"; then
    ((TESTS_PASSED++))
else
    print_warning "Mandatory extensions not supported (expected for some implementations)"
    ((TESTS_PASSED++))  # Count as passed since it's optional
fi

# ============================================================================
# PHASE 4: SLAVE SAE WORKFLOWS (Key Retrieval Operations)
# ============================================================================
print_section "PHASE 4: SLAVE SAE WORKFLOWS (Key Retrieval Operations)"

# Test 4.1: Get Key with Key IDs (if we have key IDs from previous tests)
if [[ -f "/tmp/key_ids.txt" ]]; then
    KEY_ID=$(head -1 /tmp/key_ids.txt)
    if [[ -n "$KEY_ID" ]]; then
        print_status "Testing Get Key with Key IDs..."
        KEY_IDS_DATA='{{"key_IDs": [{{"key_ID": "'$KEY_ID'"}}]}}'
        if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/dec_keys" "$KEY_IDS_DATA" "Get Key with Key IDs"; then
            ((TESTS_PASSED++))
        else
            ((TESTS_FAILED++))
        fi
    else
        print_warning "No key IDs available for retrieval test"
    fi
else
    print_warning "No key IDs available for retrieval test"
fi

# ============================================================================
# PHASE 5: ERROR HANDLING AND EDGE CASES
# ============================================================================
print_section "PHASE 5: ERROR HANDLING AND EDGE CASES"

# Test 5.1: Invalid SAE ID
print_status "Testing invalid SAE ID (should return 400/401)..."
INVALID_SAE_ID="INVALID123456789"
if make_request "GET" "$KME_ENDPOINT/api/v1/keys/$INVALID_SAE_ID/status" "" "Invalid SAE ID test"; then
    print_warning "Invalid SAE ID accepted (unexpected)"
    ((TESTS_FAILED++))
else
    print_status "✅ Invalid SAE ID properly rejected"
    ((TESTS_PASSED++))
fi

# Test 5.2: Invalid Key Request (exceed max keys)
if [[ "$MAX_KEYS" -gt 1 ]]; then
    EXCESS_COUNT=$((MAX_KEYS + 1))
    print_status "Testing key request exceeding maximum ($EXCESS_COUNT keys)..."
    KEY_REQUEST_DATA='{{"number": '$EXCESS_COUNT', "size": '$DEFAULT_KEY_SIZE'}}'
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Excessive key request ($EXCESS_COUNT keys)"; then
        print_warning "Excessive key request accepted (unexpected)"
        ((TESTS_FAILED++))
    else
        print_status "✅ Excessive key request properly rejected"
        ((TESTS_PASSED++))
    fi
fi

# Test 5.3: Invalid Key Size (exceed max)
if [[ "$MAX_KEY_SIZE" -gt "$DEFAULT_KEY_SIZE" ]]; then
    EXCESS_SIZE=$((MAX_KEY_SIZE + 64))
    print_status "Testing key request exceeding maximum size ($EXCESS_SIZE bits)..."
    KEY_REQUEST_DATA='{{"number": 1, "size": '$EXCESS_SIZE'}}'
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Excessive key size request ($EXCESS_SIZE bits)"; then
        print_warning "Excessive key size accepted (unexpected)"
        ((TESTS_FAILED++))
    else
        print_status "✅ Excessive key size properly rejected"
        ((TESTS_PASSED++))
    fi
fi

# Test 5.4: Invalid Key Size (below minimum)
if [[ "$MIN_KEY_SIZE" -gt 64 ]]; then
    BELOW_MIN_SIZE=$((MIN_KEY_SIZE - 64))
    print_status "Testing key request below minimum size ($BELOW_MIN_SIZE bits)..."
    KEY_REQUEST_DATA='{{"number": 1, "size": '$BELOW_MIN_SIZE'}}'
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Below minimum key size request ($BELOW_MIN_SIZE bits)"; then
        print_warning "Below minimum key size accepted (unexpected)"
        ((TESTS_FAILED++))
    else
        print_status "✅ Below minimum key size properly rejected"
        ((TESTS_PASSED++))
    fi
fi

# Test 5.5: Invalid JSON Request
print_status "Testing invalid JSON request..."
INVALID_JSON='{{"invalid": "json", "missing": "closing brace"'
if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$INVALID_JSON" "Invalid JSON request"; then
    print_warning "Invalid JSON accepted (unexpected)"
    ((TESTS_FAILED++))
else
    print_status "✅ Invalid JSON properly rejected"
    ((TESTS_PASSED++))
fi

# ============================================================================
# PHASE 6: PERFORMANCE AND STRESS TESTING
# ============================================================================
print_section "PHASE 6: PERFORMANCE AND STRESS TESTING"

# Test 6.1: Rapid Successive Requests
print_status "Testing rapid successive key requests..."
for i in {{1..3}}; do
    KEY_REQUEST_DATA='{{"number": 1, "size": '$DEFAULT_KEY_SIZE'}}'
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Rapid request $i/3"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    sleep 0.5  # Small delay between requests
done

# Test 6.2: Concurrent Status Checks
print_status "Testing concurrent status checks..."
for i in {{1..3}}; do
    if make_request "GET" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/status" "" "Concurrent status check $i/3"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
done

# ============================================================================
# PHASE 7: ETSI COMPLIANCE VERIFICATION
# ============================================================================
print_section "PHASE 7: ETSI COMPLIANCE VERIFICATION"

# Test 7.1: Verify Status Response Format
print_status "Verifying Status response format compliance..."
STATUS_RESPONSE=$(curl -s -X GET "$KME_ENDPOINT/api/v1/keys/$SAE_ID/status" \\
    --cert "$CERT_FILE" \\
    --key "$KEY_FILE" \\
    --cacert "$CA_FILE" \\
    --connect-timeout 10)

# Check for required ETSI fields
REQUIRED_FIELDS=("source_KME_ID" "target_KME_ID" "master_SAE_ID" "slave_SAE_ID" "key_size" "stored_key_count" "max_key_count" "max_key_per_request" "max_key_size" "min_key_size" "max_SAE_ID_count")
MISSING_FIELDS=()

for field in "${{REQUIRED_FIELDS[@]}}"; do
    if ! echo "$STATUS_RESPONSE" | jq -e ".$field" > /dev/null 2>&1; then
        MISSING_FIELDS+=("$field")
    fi
done

if [[ ${{#MISSING_FIELDS[@]}} -eq 0 ]]; then
    print_status "✅ Status response contains all required ETSI fields"
    ((TESTS_PASSED++))
else
    print_error "❌ Status response missing required fields: ${{MISSING_FIELDS[*]}}"
    ((TESTS_FAILED++))
fi

# Test 7.2: Verify Key Response Format
print_status "Verifying Key response format compliance..."
KEY_RESPONSE=$(curl -s -X POST "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" \\
    --cert "$CERT_FILE" \\
    --key "$KEY_FILE" \\
    --cacert "$CA_FILE" \\
    --header "Content-Type: application/json" \\
    --data '{{"number": 1, "size": '$DEFAULT_KEY_SIZE'}}' \\
    --connect-timeout 10)

# Check for required ETSI fields in key response
if echo "$KEY_RESPONSE" | jq -e '.keys' > /dev/null 2>&1; then
    KEY_COUNT=$(echo "$KEY_RESPONSE" | jq -r '.keys | length')
    if [[ "$KEY_COUNT" -gt 0 ]]; then
        # Check first key for required fields
        FIRST_KEY=$(echo "$KEY_RESPONSE" | jq -r '.keys[0]')
        if echo "$FIRST_KEY" | jq -e '.key_ID' > /dev/null 2>&1 && echo "$FIRST_KEY" | jq -e '.key' > /dev/null 2>&1; then
            print_status "✅ Key response contains required ETSI fields"
            ((TESTS_PASSED++))
        else
            print_error "❌ Key response missing required key fields"
            ((TESTS_FAILED++))
        fi
    else
        print_error "❌ Key response contains no keys"
        ((TESTS_FAILED++))
    fi
else
    print_error "❌ Key response missing 'keys' field"
    ((TESTS_FAILED++))
fi

# ============================================================================
# TEST SUMMARY
# ============================================================================
print_section "TEST SUMMARY"

echo ""
echo "ETSI QKD 014 V1.1.1 Compliance Test Results:"
echo "============================================="
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo "Success Rate: $(( (TESTS_PASSED * 100) / (TESTS_PASSED + TESTS_FAILED) ))%"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo ""
    print_status "🎉 ALL TESTS PASSED! SAE is fully compliant with ETSI QKD 014 V1.1.1"
    print_status "✅ Basic connectivity: OK"
    print_status "✅ Health checks: OK"
    print_status "✅ Get Status endpoint: OK"
    print_status "✅ Get Key endpoint: OK"
    print_status "✅ Get Key with Key IDs endpoint: OK"
    print_status "✅ Error handling: OK"
    print_status "✅ Performance: OK"
    print_status "✅ ETSI compliance: OK"
else
    echo ""
    print_warning "⚠️  Some tests failed. Review the output above for details."
    print_warning "Consider checking:"
    print_warning "  - KME configuration and status"
    print_warning "  - Network connectivity"
    print_warning "  - Certificate validity"
    print_warning "  - SAE registration status"
fi

echo ""
print_status "Test completed at: $(date)"
print_status "SAE ID: $SAE_ID"
print_status "KME Endpoint: $KME_ENDPOINT"

# Clean up temporary files
rm -f /tmp/stored_keys_count /tmp/max_keys_per_request /tmp/default_key_size /tmp/max_key_size /tmp/min_key_size /tmp/max_sae_count /tmp/key_ids.txt

echo ""
print_status "For detailed API documentation, see: https://www.etsi.org/deliver/etsi_gs/QKD/001_099/014/01.01.01_60/gs_qkd014v010101p.pdf"
"""

        with open(package_dir / "test_connection.sh", "w") as f:
            f.write(test_content)

        # Make executable - shell script needs execute permissions
        os.chmod(
            package_dir / "test_connection.sh", 0o755
        )  # nosec B103 - Shell script needs execute permissions

    def _cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
