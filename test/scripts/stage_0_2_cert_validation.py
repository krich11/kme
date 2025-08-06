#!/usr/bin/env python3
"""
Stage 0.2: CA Setup Validation

This script validates that the CA is properly set up, KME certificate is generated,
and nginx is configured to use those specific files.
"""

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print(
        "Warning: python-dotenv not available, environment variables may not be loaded"
    )


class CAValidation:
    """Validate CA setup, KME certificate, and nginx configuration"""

    def __init__(self, test_result: dict[str, Any]):
        self.test_result = test_result
        self.project_root = Path(__file__).parent.parent.parent
        self.stage_name = "stage_0_2_cert_validation"
        self.stage_data = test_result["stages"][self.stage_name]

        print(f"Starting {self.stage_name}: CA Setup Validation")
        print(f"Project root: {self.project_root}")

    def update_test_status(
        self, test_name: str, status: str, details: str = "", error: str = None
    ):
        """Update test status in the result structure"""
        self.stage_data["tests"][test_name]["status"] = status
        self.stage_data["tests"][test_name]["details"] = details
        self.stage_data["tests"][test_name]["error_message"] = error

        if status == "PASSED":
            print(f"✅ {test_name}: {details}")
        elif status == "FAILED":
            print(f"❌ {test_name}: {error}")
        else:
            print(f"⏳ {test_name}: {details}")

    def run_command(self, command: list[str], description: str) -> bool:
        """Run a shell command and return success status"""
        try:
            print(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            if result.returncode == 0:
                print(f"✅ {description} - Success")
                if result.stdout:
                    print(f"Output: {result.stdout.strip()}")
                return True
            else:
                print(f"❌ {description} - Failed")
                print(f"Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"❌ {description} - Timeout")
            return False
        except Exception as e:
            print(f"❌ {description} - Exception: {e}")
            return False

    def validate_ca_setup(self) -> bool:
        """Validate that CA is properly set up"""
        try:
            ca_dir = self.project_root / "certs" / "ca"
            ca_cert = ca_dir / "ca.crt"
            ca_key = ca_dir / "ca.key"

            # Check CA files exist
            if not ca_cert.exists():
                error_msg = f"CA certificate not found: {ca_cert}"
                self.update_test_status("validate_ca_setup", "FAILED", error=error_msg)
                return False

            if not ca_key.exists():
                error_msg = f"CA private key not found: {ca_key}"
                self.update_test_status("validate_ca_setup", "FAILED", error=error_msg)
                return False

            # Validate CA certificate structure
            if self.run_command(
                ["openssl", "x509", "-in", str(ca_cert), "-text", "-noout"],
                "Validate CA certificate structure",
            ):
                details = f"CA setup validated successfully: {ca_cert}"
                self.update_test_status("validate_ca_setup", "PASSED", details)
                return True
            else:
                self.update_test_status(
                    "validate_ca_setup",
                    "FAILED",
                    error="CA certificate validation failed",
                )
                return False

        except Exception as e:
            error_msg = f"Failed to validate CA setup: {e}"
            self.update_test_status("validate_ca_setup", "FAILED", error=error_msg)
            return False

    def validate_kme_certificate(self) -> bool:
        """Validate that KME certificate is generated and matches KME ID"""
        try:
            # Read KME ID from environment
            kme_id = os.getenv("KME_ID")
            if not kme_id:
                error_msg = "KME_ID not found in environment variables"
                self.update_test_status(
                    "validate_kme_certificate", "FAILED", error=error_msg
                )
                return False

            kme_cert = self.project_root / "certs" / "kme_cert.pem"
            kme_key = self.project_root / "certs" / "kme_key.pem"

            # Check KME certificate files exist
            if not kme_cert.exists():
                error_msg = f"KME certificate not found: {kme_cert}"
                self.update_test_status(
                    "validate_kme_certificate", "FAILED", error=error_msg
                )
                return False

            if not kme_key.exists():
                error_msg = f"KME private key not found: {kme_key}"
                self.update_test_status(
                    "validate_kme_certificate", "FAILED", error=error_msg
                )
                return False

            # Validate KME certificate CN matches KME ID
            if self.run_command(
                ["openssl", "x509", "-in", str(kme_cert), "-subject", "-noout"],
                "Check KME certificate CN",
            ):
                # Check if CN matches KME ID
                result = subprocess.run(
                    ["openssl", "x509", "-in", str(kme_cert), "-subject", "-noout"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                )

                if f"CN = {kme_id}" in result.stdout:
                    details = f"KME certificate validated successfully: CN={kme_id}"
                    self.update_test_status(
                        "validate_kme_certificate", "PASSED", details
                    )
                    return True
                else:
                    error_msg = f"KME certificate CN does not match KME ID. Expected: {kme_id}, Found: {result.stdout}"
                    self.update_test_status(
                        "validate_kme_certificate", "FAILED", error=error_msg
                    )
                    return False
            else:
                self.update_test_status(
                    "validate_kme_certificate",
                    "FAILED",
                    error="KME certificate validation failed",
                )
                return False

        except Exception as e:
            error_msg = f"Failed to validate KME certificate: {e}"
            self.update_test_status(
                "validate_kme_certificate", "FAILED", error=error_msg
            )
            return False

    def validate_certificate_chain(self) -> bool:
        """Validate certificate chain integrity"""
        try:
            ca_cert = self.project_root / "certs" / "ca" / "ca.crt"
            kme_cert = self.project_root / "certs" / "kme_cert.pem"

            if not ca_cert.exists() or not kme_cert.exists():
                error_msg = "CA or KME certificate not found for chain validation"
                self.update_test_status(
                    "validate_certificate_chain", "FAILED", error=error_msg
                )
                return False

            # Validate certificate chain using OpenSSL
            command = ["openssl", "verify", "-CAfile", str(ca_cert), str(kme_cert)]

            if self.run_command(command, "Validate certificate chain"):
                details = "Certificate chain validated successfully"
                self.update_test_status("validate_certificate_chain", "PASSED", details)
                return True
            else:
                self.update_test_status(
                    "validate_certificate_chain",
                    "FAILED",
                    error="Certificate chain validation failed",
                )
                return False

        except Exception as e:
            error_msg = f"Failed to validate certificate chain: {e}"
            self.update_test_status(
                "validate_certificate_chain", "FAILED", error=error_msg
            )
            return False

    def validate_nginx_configuration(self) -> bool:
        """Validate that nginx is configured to use the KME certificate files"""
        try:
            kme_cert = self.project_root / "certs" / "kme_cert.pem"
            kme_key = self.project_root / "certs" / "kme_key.pem"

            if not kme_cert.exists() or not kme_key.exists():
                error_msg = "KME certificate or key not found for nginx validation"
                self.update_test_status(
                    "validate_nginx_configuration", "FAILED", error=error_msg
                )
                return False

            # Check if nginx configuration exists
            nginx_config = Path("/etc/nginx/sites-available/kme")
            if not nginx_config.exists():
                error_msg = (
                    "Nginx configuration not found: /etc/nginx/sites-available/kme"
                )
                self.update_test_status(
                    "validate_nginx_configuration", "FAILED", error=error_msg
                )
                return False

            # Check if nginx configuration is enabled
            nginx_enabled = Path("/etc/nginx/sites-enabled/kme")
            if not nginx_enabled.exists():
                error_msg = (
                    "Nginx configuration not enabled: /etc/nginx/sites-enabled/kme"
                )
                self.update_test_status(
                    "validate_nginx_configuration", "FAILED", error=error_msg
                )
                return False

            # Validate nginx configuration syntax
            if self.run_command(
                ["sudo", "nginx", "-t"], "Validate nginx configuration syntax"
            ):
                details = "Nginx configuration validated successfully"
                self.update_test_status(
                    "validate_nginx_configuration", "PASSED", details
                )
                return True
            else:
                self.update_test_status(
                    "validate_nginx_configuration",
                    "FAILED",
                    error="Nginx configuration syntax validation failed",
                )
                return False

        except Exception as e:
            error_msg = f"Failed to validate nginx configuration: {e}"
            self.update_test_status(
                "validate_nginx_configuration", "FAILED", error=error_msg
            )
            return False

    def run(self) -> bool:
        """Run the complete CA setup validation"""
        start_time = datetime.datetime.now()
        self.stage_data["start_time"] = start_time.isoformat()

        print(f"\n=== Starting {self.stage_name} ===")

        # Run all validation tests
        tests = [
            self.validate_ca_setup,
            self.validate_kme_certificate,
            self.validate_certificate_chain,
            self.validate_nginx_configuration,
        ]

        all_passed = True
        for test_func in tests:
            if not test_func():
                all_passed = False
                break

        # Update stage status
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.stage_data["end_time"] = end_time.isoformat()
        self.stage_data["duration_seconds"] = duration

        if all_passed:
            self.stage_data["status"] = "PASSED"
            print(
                f"\n✅ {self.stage_name} completed successfully in {duration:.2f} seconds"
            )
        else:
            self.stage_data["status"] = "FAILED"
            print(f"\n❌ {self.stage_name} failed after {duration:.2f} seconds")

        return all_passed


def main():
    """Main entry point"""
    # Load test result template
    template_path = Path(__file__).parent.parent / "test_result_template.json"

    with open(template_path) as f:
        test_result = json.load(f)

    # Update timestamp
    test_result["test_run"]["timestamp"] = datetime.datetime.now().isoformat()

    # Run the CA validation
    ca_validation = CAValidation(test_result)
    success = ca_validation.run()

    # Save result
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = (
        Path(__file__).parent.parent / "results" / f"test_result_{timestamp}.json"
    )

    with open(result_path, "w") as f:
        json.dump(test_result, f, indent=2)

    print(f"\nTest result saved to: {result_path}")

    if success:
        print("✅ CA setup validation completed successfully")
        sys.exit(0)
    else:
        print("❌ CA setup validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
