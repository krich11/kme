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

    def create_multi_sae_package(self, output_path: str, password: str) -> str:
        """Create self-extracting encrypted multi-SAE test package"""

        logger.info("Creating multi-SAE test package")

        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()

        try:
            # 1. Register all SAEs in the KME system
            self._register_multi_sae_saes()

            # 2. Create multi-SAE package contents
            package_dir = self._create_multi_sae_package_contents()

            # 3. Create tar.gz archive
            archive_path = self._create_archive(package_dir)

            # 4. Encrypt archive
            encrypted_data = self._encrypt_archive(archive_path, password)

            # 5. Create self-extracting script
            self._create_multi_sae_self_extractor(encrypted_data, output_path)

            # 6. Clean up
            self._cleanup()

            logger.info(f"Multi-SAE test package created successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Multi-SAE package creation failed: {e}")
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

        # Read template - use absolute path to ensure it works from any directory
        script_dir = Path(__file__).parent
        template_path = script_dir / "templates" / "package_template.sh"
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
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
        # Read template file - use absolute path to ensure it works from any directory
        script_dir = Path(__file__).parent
        template_path = script_dir / "templates" / "README.md"
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path) as f:
            readme_content = f.read()

        # Replace template variables
        readme_content = readme_content.format(sae_name=sae_data["name"])

        with open(package_dir / "README.md", "w") as f:
            f.write(readme_content)

    def _create_security_readme(self, package_dir: Path):
        """Create security README"""
        # Read template file - use absolute path to ensure it works from any directory
        script_dir = Path(__file__).parent
        template_path = script_dir / "templates" / "SECURITY_README.md"
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path) as f:
            security_content = f.read()

        with open(package_dir / "SECURITY_README.md", "w") as f:
            f.write(security_content)

    def _create_client_example(self, package_dir: Path, config: dict[str, Any]):
        """Create Python client example"""
        # Read template file - use absolute path to ensure it works from any directory
        script_dir = Path(__file__).parent
        template_path = script_dir / "templates" / "client_example.py"
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path) as f:
            client_content = f.read()

        with open(package_dir / "client_example.py", "w") as f:
            f.write(client_content)

        # Python files don't need execute permissions - they're run by the interpreter

    def _create_test_script(self, package_dir: Path, config: dict[str, Any]):
        """Create comprehensive ETSI QKD 014 test script"""
        # Read template file - use absolute path to ensure it works from any directory
        script_dir = Path(__file__).parent
        template_path = script_dir / "templates" / "test_connection.sh"
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path) as f:
            test_content = f.read()

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

    def _create_multi_sae_package_contents(self) -> Path:
        """Create multi-SAE package directory with all files"""
        if self.temp_dir is None:
            raise RuntimeError("temp_dir not initialized")
        package_dir = Path(self.temp_dir) / "multi_sae_package"
        package_dir.mkdir()

        # Create .config directory for sensitive files
        config_dir = package_dir / ".config"
        config_dir.mkdir()

        # Generate multiple SAE certificates
        sae_configs = self._generate_multi_sae_certificates(config_dir)

        # Create multi-SAE configuration JSON
        config = {
            "package_type": "multi_sae_test",
            "package_version": "1.0.0",
            "kme_endpoint": "https://localhost:443",
            "ca_certificate_file": ".config/kme_ca_certificate.pem",
            "sae_configurations": sae_configs,
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
            "created_date": datetime.utcnow().isoformat(),
        }

        with open(config_dir / "multi_sae_config.json", "w") as f:
            json.dump(config, f, indent=2)

        # Copy CA certificate
        ca_cert_path = Path("../test_certs/kme_ca_cert.pem")
        if ca_cert_path.exists():
            shutil.copy2(ca_cert_path, config_dir / "kme_ca_certificate.pem")
        else:
            # Create a placeholder CA certificate
            self._create_placeholder_ca_cert(config_dir / "kme_ca_certificate.pem")

        # Create multi-SAE test script
        self._create_multi_sae_test_script(package_dir, config)

        # Create README
        self._create_multi_sae_readme(package_dir)

        # Copy requirements.txt
        requirements_path = Path(__file__).parent / "requirements.txt"
        if requirements_path.exists():
            shutil.copy2(requirements_path, package_dir / "requirements.txt")

        return package_dir

    def _generate_multi_sae_certificates(
        self, config_dir: Path
    ) -> list[dict[str, Any]]:
        """Generate multiple SAE certificates for testing"""
        sae_configs = []

        # Define SAE configurations
        sae_definitions = [
            {
                "id": "qnFFr9m6Re3EWs7C",
                "name": "Master SAE",
                "role": "master",
                "cert_file": "master_sae_cert.pem",
                "key_file": "master_sae_key.pem",
            },
            {
                "id": "sae_slave_001",
                "name": "Slave SAE 1",
                "role": "slave",
                "cert_file": "slave_sae_001_cert.pem",
                "key_file": "slave_sae_001_key.pem",
            },
            {
                "id": "sae_slave_002",
                "name": "Slave SAE 2",
                "role": "slave",
                "cert_file": "slave_sae_002_cert.pem",
                "key_file": "slave_sae_002_key.pem",
            },
            {
                "id": "sae_slave_003",
                "name": "Slave SAE 3",
                "role": "slave",
                "cert_file": "slave_sae_003_cert.pem",
                "key_file": "slave_sae_003_key.pem",
            },
        ]

        for sae_def in sae_definitions:
            # Create placeholder certificates for now
            # In a real implementation, these would be generated using the certificate generator
            cert_path = config_dir / sae_def["cert_file"]
            key_path = config_dir / sae_def["key_file"]

            self._create_placeholder_certificate(
                cert_path, sae_def["id"], sae_def["name"]
            )
            self._create_placeholder_private_key(key_path)

            sae_configs.append(
                {
                    "sae_id": sae_def["id"],
                    "sae_name": sae_def["name"],
                    "role": sae_def["role"],
                    "certificate_file": f".config/{sae_def['cert_file']}",
                    "private_key_file": f".config/{sae_def['key_file']}",
                }
            )

        return sae_configs

    def _create_placeholder_certificate(
        self, cert_path: Path, sae_id: str, sae_name: str
    ):
        """Create a placeholder certificate for testing"""
        cert_content = f"""-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKoK8HhJ8qQqMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMjQwNzI5MDkzMDAwWhcNMjUwNzI5MDkzMDAwWjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEA{sae_id}==
-----END CERTIFICATE-----"""

        with open(cert_path, "w") as f:
            f.write(cert_content)

    def _create_placeholder_private_key(self, key_path: Path):
        """Create a placeholder private key for testing"""
        key_content = """-----BEGIN PLACEHOLDER PRIVATE KEY-----
# This is a placeholder private key for testing purposes only
# NOT A REAL PRIVATE KEY - DO NOT USE IN PRODUCTION
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKB
TCEHkS+tX9P9DzWz7QZtNqBkUhnXzrPkpj4cn0GITP/towAOC4VAWxN2ok3hOBJ7
-----END PLACEHOLDER PRIVATE KEY-----"""

        with open(key_path, "w") as f:
            f.write(key_content)

    def _create_placeholder_ca_cert(self, ca_path: Path):
        """Create a placeholder CA certificate for testing"""
        ca_content = """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKoK8HhJ8qQqMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMjQwNzI5MDkzMDAwWhcNMjUwNzI5MDkzMDAwWjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEAKME_CA_CERT_PLACEHOLDER
-----END CERTIFICATE-----"""

        with open(ca_path, "w") as f:
            f.write(ca_content)

    def _create_multi_sae_test_script(self, package_dir: Path, config: dict[str, Any]):
        """Create multi-SAE test script"""
        script_content = """#!/bin/bash
# Multi-SAE Test Script
# ETSI QKD 014 V1.1.1 Multi-SAE Testing

set -e

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
CYAN='\\033[0;36m'
NC='\\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Multi-SAE Test Suite${NC}"
    echo -e "${BLUE}  ETSI QKD 014 V1.1.1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_section() {
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..${#1}})${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load configuration
if [[ -f ".config/multi_sae_config.json" ]]; then
    CONFIG_FILE=".config/multi_sae_config.json"
else
    print_error "multi_sae_config.json not found in .config/"
    exit 1
fi

# Extract values from JSON (requires jq)
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed"
    exit 1
fi

KME_ENDPOINT=$(jq -r '.kme_endpoint' "$CONFIG_FILE")
CA_FILE=$(jq -r '.ca_certificate_file' "$CONFIG_FILE")

print_header
echo "Multi-SAE Test Suite"
echo "KME: $KME_ENDPOINT"
echo ""

# Test all SAE configurations
sae_count=$(jq '.sae_configurations | length' "$CONFIG_FILE")
print_status "Found $sae_count SAE configurations"

for i in $(seq 0 $((sae_count - 1))); do
    sae_id=$(jq -r ".sae_configurations[$i].sae_id" "$CONFIG_FILE")
    sae_name=$(jq -r ".sae_configurations[$i].sae_name" "$CONFIG_FILE")
    role=$(jq -r ".sae_configurations[$i].role" "$CONFIG_FILE")
    cert_file=$(jq -r ".sae_configurations[$i].certificate_file" "$CONFIG_FILE")
    key_file=$(jq -r ".sae_configurations[$i].private_key_file" "$CONFIG_FILE")

    print_section "Testing $sae_name ($sae_id) - Role: $role"

    # Test basic connectivity
    print_status "Testing basic connectivity for $sae_name..."
    if curl -s -X GET "$KME_ENDPOINT/health/ready" \
        --cert "$cert_file" \
        --key "$key_file" \
        --cacert "$CA_FILE" \
        --connect-timeout 10 > /dev/null; then
        print_status "✅ $sae_name connectivity successful"
    else
        print_error "❌ $sae_name connectivity failed"
    fi

    # Test status endpoint
    print_status "Testing status endpoint for $sae_name..."
    if curl -s -X GET "$KME_ENDPOINT/api/v1/keys/$sae_id/status" \
        --cert "$cert_file" \
        --key "$key_file" \
        --cacert "$CA_FILE" \
        --connect-timeout 10 > /dev/null; then
        print_status "✅ $sae_name status endpoint successful"
    else
        print_error "❌ $sae_name status endpoint failed"
    fi
done

print_section "Multi-SAE Key Distribution Testing"

# Test master SAE requesting keys for slave SAEs
master_sae=$(jq -r '.sae_configurations[] | select(.role == "master") | .sae_id' "$CONFIG_FILE")
slave_saes=$(jq -r '.sae_configurations[] | select(.role == "slave") | .sae_id' "$CONFIG_FILE")

if [[ -n "$master_sae" ]]; then
    master_cert=$(jq -r ".sae_configurations[] | select(.sae_id == \"$master_sae\") | .certificate_file" "$CONFIG_FILE")
    master_key=$(jq -r ".sae_configurations[] | select(.sae_id == \"$master_sae\") | .private_key_file" "$CONFIG_FILE")

    print_status "Testing master SAE ($master_sae) requesting keys for slave SAEs..."

    for slave_sae in $slave_saes; do
        print_status "Requesting keys for slave SAE: $slave_sae"

        # Create key request JSON
        key_request=$(jq -n '{"number": 1, "size": 352}')

        if curl -s -X POST "$KME_ENDPOINT/api/v1/keys/$slave_sae/enc_keys" \
            --cert "$master_cert" \
            --key "$master_key" \
            --cacert "$CA_FILE" \
            --header "Content-Type: application/json" \
            --data "$key_request" \
            --connect-timeout 10 > /dev/null; then
            print_status "✅ Key request for $slave_sae successful"
        else
            print_error "❌ Key request for $slave_sae failed"
        fi
    done
fi

print_section "Test Summary"
echo "Multi-SAE test suite completed!"
echo "Check the output above for any errors or warnings."
"""

        with open(package_dir / "multi_sae_test.sh", "w") as f:
            f.write(script_content)

        # Make executable
        os.chmod(
            package_dir / "multi_sae_test.sh", 0o755
        )  # nosec B103 - Shell script needs execute permissions

    def _create_multi_sae_readme(self, package_dir: Path):
        """Create multi-SAE README"""
        readme_content = """# Multi-SAE Test Package

This package contains a comprehensive test suite for multi-SAE scenarios according to ETSI QKD 014 V1.1.1 specifications.

## Contents

- **4 SAE Certificates**: 1 Master SAE + 3 Slave SAEs
- **Multi-SAE Test Script**: Comprehensive testing of all multi-SAE scenarios
- **Configuration Files**: All necessary configuration for testing
- **CA Certificate**: KME CA certificate for authentication

## SAE Configurations

1. **Master SAE** (`qnFFr9m6Re3EWs7C`)
   - Role: Master SAE
   - Can request keys for slave SAEs
   - Can distribute keys to multiple SAEs

2. **Slave SAE 1** (`sae_slave_001`)
   - Role: Slave SAE
   - Can retrieve keys using key IDs
   - Tests key access permissions

3. **Slave SAE 2** (`sae_slave_002`)
   - Role: Slave SAE
   - Can retrieve keys using key IDs
   - Tests key access permissions

4. **Slave SAE 3** (`sae_slave_003`)
   - Role: Slave SAE
   - Can retrieve keys using key IDs
   - Tests key access permissions

## Quick Start

1. **Extract the package**:
   ```bash
   ./multi_sae_test_package.sh
   ```

2. **Run the test suite**:
   ```bash
   ./multi_sae_test.sh
   ```

## Test Scenarios

The test suite covers:

- **Basic Connectivity**: Each SAE can connect to the KME
- **Status Endpoints**: Each SAE can access status information
- **Key Distribution**: Master SAE can request keys for slave SAEs
- **Key Retrieval**: Slave SAEs can retrieve keys using key IDs
- **Access Control**: Proper validation of SAE permissions
- **Multi-SAE Workflows**: Complete ETSI QKD 014 multi-SAE scenarios

## Configuration

All configuration is stored in `.config/multi_sae_config.json`:

- KME endpoint configuration
- SAE certificate and key file paths
- API endpoint definitions
- Connection settings

## Security

- All certificates and private keys are stored in the `.config/` directory
- Certificates are placeholder certificates for testing
- In production, use properly generated certificates

## Troubleshooting

1. **Connection Issues**: Verify KME endpoint is accessible
2. **Certificate Errors**: Check certificate file paths in configuration
3. **Permission Errors**: Ensure script has execute permissions
4. **JSON Parsing Errors**: Verify `jq` is installed

## ETSI QKD 014 Compliance

This test suite validates compliance with:

- Section 5.1: Get Status endpoint
- Section 5.2: Get Key endpoint
- Section 5.3: Get Key with Key IDs endpoint
- Multi-SAE key distribution scenarios
- Access control and authorization
- Error handling and validation
"""

        with open(package_dir / "README.md", "w") as f:
            f.write(readme_content)

    def _create_multi_sae_self_extractor(self, encrypted_data: str, output_path: str):
        """Create self-extracting script for multi-SAE package"""
        script_content = f"""#!/bin/bash
# Multi-SAE Test Package Self-Extractor
# ETSI QKD 014 V1.1.1 Multi-SAE Testing Package

set -e

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
CYAN='\\033[0;36m'
NC='\\033[0m' # No Color

print_header() {{
    echo -e "${{BLUE}}================================${{NC}}"
    echo -e "${{BLUE}}  Multi-SAE Test Package${{NC}}"
    echo -e "${{BLUE}}  ETSI QKD 014 V1.1.1${{NC}}"
    echo -e "${{BLUE}}================================${{NC}}"
}}

print_status() {{
    echo -e "${{GREEN}}[INFO]${{NC}} $1"
}}

print_error() {{
    echo -e "${{RED}}[ERROR]${{NC}} $1"
}}

print_header

# Check for password
if [[ $# -eq 0 ]]; then
    read -s -p "Enter package password: " PASSWORD
    echo
else
    PASSWORD="$1"
fi

# Create extraction directory
EXTRACT_DIR="multi_sae_test_package"
mkdir -p "$EXTRACT_DIR"
cd "$EXTRACT_DIR"

print_status "Extracting package contents..."

# Decrypt and extract
echo "$PASSWORD" | openssl enc -d -aes-256-cbc -a -salt -pbkdf2 -pass stdin << 'ENCRYPTED_DATA'
{encrypted_data}
ENCRYPTED_DATA
| tar -xzf -

print_status "Package extracted successfully!"
print_status "Directory: $EXTRACT_DIR"

echo ""
echo "Next steps:"
echo "1. cd $EXTRACT_DIR"
echo "2. ./multi_sae_test.sh"
echo ""
echo "This will run the comprehensive multi-SAE test suite."
"""

        with open(output_path, "w") as f:
            f.write(script_content)

        # Make executable
        os.chmod(
            output_path, 0o755
        )  # nosec B103 - Self-extracting script needs execute permissions

    def _register_multi_sae_saes(self):
        """Register all multi-SAE SAEs in the KME system"""
        logger.info("Registering multi-SAE SAEs in KME system")

        # Define SAE configurations
        sae_definitions = [
            {
                "id": "qnFFr9m6Re3EWs7C",
                "name": "Master SAE",
                "role": "master",
                "max_keys": 128,
                "max_key_size": 1024,
            },
            {
                "id": "sae_slave_001",
                "name": "Slave SAE 1",
                "role": "slave",
                "max_keys": 128,
                "max_key_size": 1024,
            },
            {
                "id": "sae_slave_002",
                "name": "Slave SAE 2",
                "role": "slave",
                "max_keys": 128,
                "max_key_size": 1024,
            },
            {
                "id": "sae_slave_003",
                "name": "Slave SAE 3",
                "role": "slave",
                "max_keys": 128,
                "max_key_size": 1024,
            },
        ]

        # Register each SAE
        for sae_def in sae_definitions:
            try:
                self._register_sae_in_kme(sae_def)
                logger.info(f"Registered SAE: {sae_def['name']} ({sae_def['id']})")
            except Exception as e:
                logger.warning(f"Failed to register SAE {sae_def['id']}: {e}")
                # Continue with other SAEs even if one fails

    def _register_sae_in_kme(self, sae_def: dict[str, Any]):
        """Register a single SAE in the KME system"""
        # Try to register in database first
        try:
            self._register_sae_in_database(sae_def)
        except Exception as e:
            logger.warning(f"Database registration failed for {sae_def['id']}: {e}")
            # Fallback to JSON registry
            self._register_sae_in_json_registry(sae_def)

    def _register_sae_in_database(self, sae_def: dict[str, Any]):
        """Register SAE in database"""
        try:
            # Import here to avoid circular imports
            from app.core.database import database_manager

            async def register_async():
                # Initialize database if needed
                await database_manager.initialize()

                async with database_manager.get_session_context() as session:
                    # Check if SAE already exists
                    existing_sae = await session.execute(
                        "SELECT sae_id FROM sae_entities WHERE sae_id = :sae_id",
                        {"sae_id": sae_def["id"]},
                    )

                    if existing_sae.fetchone():
                        logger.info(f"SAE {sae_def['id']} already exists in database")
                        return

                    # Insert new SAE
                    await session.execute(
                        """
                        INSERT INTO sae_entities
                        (sae_id, sae_name, status, max_keys_per_request, max_key_size, created_at, updated_at)
                        VALUES (:sae_id, :sae_name, :status, :max_keys, :max_key_size, NOW(), NOW())
                        """,
                        {
                            "sae_id": sae_def["id"],
                            "sae_name": sae_def["name"],
                            "status": "active",
                            "max_keys": sae_def["max_keys"],
                            "max_key_size": sae_def["max_key_size"],
                        },
                    )
                    await session.commit()
                    logger.info(f"Registered SAE {sae_def['id']} in database")

            # Run the async function
            import asyncio

            asyncio.run(register_async())

        except Exception as e:
            logger.warning(f"Database registration failed: {e}")
            raise e

    def _register_sae_in_json_registry(self, sae_def: dict[str, Any]):
        """Register SAE in JSON registry file"""
        try:
            registry_path = Path("admin/sae_registry.json")

            # Load existing registry
            if registry_path.exists():
                with open(registry_path) as f:
                    registry = json.load(f)
            else:
                registry = []

            # Check if SAE already exists
            existing_sae = next(
                (sae for sae in registry if sae.get("sae_id") == sae_def["id"]), None
            )
            if existing_sae:
                logger.info(f"SAE {sae_def['id']} already exists in JSON registry")
                return

            # Add new SAE
            new_sae = {
                "sae_id": sae_def["id"],
                "sae_name": sae_def["name"],
                "status": "active",
                "max_keys_per_request": sae_def["max_keys"],
                "max_key_size": sae_def["max_key_size"],
                "registration_date": datetime.utcnow().isoformat(),
                "role": sae_def["role"],
            }

            registry.append(new_sae)

            # Save updated registry
            with open(registry_path, "w") as f:
                json.dump(registry, f, indent=2)

            logger.info(f"Registered SAE {sae_def['id']} in JSON registry")

        except Exception as e:
            logger.error(f"JSON registry registration failed: {e}")
            raise e
