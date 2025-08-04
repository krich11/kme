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
