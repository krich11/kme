#!/usr/bin/env python3
"""
Stage 0.2: Admin Tool Configuration & CA Setup

This script tests the admin tools' ability to:
- Generate a CA from scratch
- Validate CA certificate structure
- Generate KME certificate from CA
- Validate certificate chain integrity
- Configure nginx with KME certificate
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


class CASetup:
    """Admin tool CA setup and validation"""

    def __init__(self, test_result: dict[str, Any]):
        self.test_result = test_result
        self.project_root = Path(__file__).parent.parent.parent
        self.stage_name = "stage_0_2_ca_setup"
        self.stage_data = test_result["stages"][self.stage_name]

        print(f"Starting {self.stage_name}: Admin Tool Configuration & CA Setup")
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

    def generate_ca(self) -> bool:
        """Generate CA using CA generation script"""
        try:
            # Use the CA generation script
            ca_script = self.project_root / "test" / "scripts" / "generate_ca.py"
            if not ca_script.exists():
                error_msg = f"CA generation script not found: {ca_script}"
                self.update_test_status("generate_ca", "FAILED", error=error_msg)
                return False

            # Generate CA using the script
            command = ["python", str(ca_script), "ca"]

            if self.run_command(command, "Generate CA using CA generation script"):
                # Verify CA files were created
                ca_dir = self.project_root / "admin" / "ca"
                ca_cert = ca_dir / "ca.crt"
                ca_key = ca_dir / "ca.key"

                if ca_cert.exists() and ca_key.exists():
                    details = f"CA generated successfully: {ca_cert}"
                    self.update_test_status("generate_ca", "PASSED", details)
                    return True
                else:
                    error_msg = "CA files not created after generation"
                    self.update_test_status("generate_ca", "FAILED", error=error_msg)
                    return False
            else:
                self.update_test_status(
                    "generate_ca", "FAILED", error="CA generation command failed"
                )
                return False

        except Exception as e:
            error_msg = f"Failed to generate CA: {e}"
            self.update_test_status("generate_ca", "FAILED", error=error_msg)
            return False

    def validate_ca_structure(self) -> bool:
        """Validate CA certificate structure"""
        try:
            ca_cert = self.project_root / "admin" / "ca" / "ca.crt"

            if not ca_cert.exists():
                error_msg = f"CA certificate not found: {ca_cert}"
                self.update_test_status(
                    "validate_ca_structure", "FAILED", error=error_msg
                )
                return False

            # Validate CA certificate using OpenSSL - check for CA:TRUE in the output
            command = ["openssl", "x509", "-in", str(ca_cert), "-text", "-noout"]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            if result.returncode == 0:
                output = result.stdout

                # Check for CA basic constraints
                if "CA:TRUE" in output:
                    details = "CA certificate structure validated successfully"
                    self.update_test_status("validate_ca_structure", "PASSED", details)
                    return True
                else:
                    error_msg = "CA certificate missing Basic Constraints: CA:TRUE"
                    self.update_test_status(
                        "validate_ca_structure", "FAILED", error=error_msg
                    )
                    return False
            else:
                error_msg = f"Failed to read CA certificate structure: {result.stderr}"
                self.update_test_status(
                    "validate_ca_structure", "FAILED", error=error_msg
                )
                return False

        except Exception as e:
            error_msg = f"Failed to validate CA structure: {e}"
            self.update_test_status("validate_ca_structure", "FAILED", error=error_msg)
            return False

    def generate_kme_cert(self) -> bool:
        """Generate KME certificate"""
        try:
            # Use the CA generation script
            ca_script = self.project_root / "test" / "scripts" / "generate_ca.py"

            # Generate KME certificate
            command = ["python", str(ca_script), "kme"]

            if self.run_command(command, "Generate KME certificate"):
                # Verify KME certificate was created
                kme_cert = self.project_root / "admin" / "kme_cert.pem"
                kme_key = self.project_root / "admin" / "kme_key.pem"

                if kme_cert.exists() and kme_key.exists():
                    details = f"KME certificate generated successfully: {kme_cert}"
                    self.update_test_status("generate_kme_cert", "PASSED", details)
                    return True
                else:
                    error_msg = "KME certificate files not created after generation"
                    self.update_test_status(
                        "generate_kme_cert", "FAILED", error=error_msg
                    )
                    return False
            else:
                self.update_test_status(
                    "generate_kme_cert",
                    "FAILED",
                    error="KME certificate generation command failed",
                )
                return False

        except Exception as e:
            error_msg = f"Failed to generate KME certificate: {e}"
            self.update_test_status("generate_kme_cert", "FAILED", error=error_msg)
            return False

    def validate_cert_chain(self) -> bool:
        """Validate certificate chain"""
        try:
            ca_cert = self.project_root / "admin" / "ca" / "ca.crt"
            kme_cert = self.project_root / "admin" / "kme_cert.pem"

            if not ca_cert.exists() or not kme_cert.exists():
                error_msg = "CA or KME certificate not found for chain validation"
                self.update_test_status(
                    "validate_cert_chain", "FAILED", error=error_msg
                )
                return False

            # Validate certificate chain using OpenSSL
            command = ["openssl", "verify", "-CAfile", str(ca_cert), str(kme_cert)]

            if self.run_command(command, "Validate certificate chain"):
                details = "Certificate chain validated successfully"
                self.update_test_status("validate_cert_chain", "PASSED", details)
                return True
            else:
                self.update_test_status(
                    "validate_cert_chain",
                    "FAILED",
                    error="Certificate chain validation failed",
                )
                return False

        except Exception as e:
            error_msg = f"Failed to validate certificate chain: {e}"
            self.update_test_status("validate_cert_chain", "FAILED", error=error_msg)
            return False

    def configure_nginx(self) -> bool:
        """Configure nginx with KME certificate using proper installer"""
        try:
            kme_cert = self.project_root / "admin" / "kme_cert.pem"
            kme_key = self.project_root / "admin" / "kme_key.pem"

            if not kme_cert.exists() or not kme_key.exists():
                error_msg = "KME certificate or key not found for nginx configuration"
                self.update_test_status("configure_nginx", "FAILED", error=error_msg)
                return False

            # Use the proper nginx installer to install to /etc/nginx/sites-available/
            nginx_installer = (
                self.project_root / "test" / "scripts" / "nginx_installer.py"
            )

            if not self.run_command(
                ["python", str(nginx_installer), str(kme_cert), str(kme_key)],
                "Install KME nginx configuration",
            ):
                self.update_test_status(
                    "configure_nginx",
                    "FAILED",
                    error="Failed to install nginx configuration",
                )
                return False

            details = f"Nginx configuration installed to /etc/nginx/sites-available/kme"
            self.update_test_status("configure_nginx", "PASSED", details)
            return True

        except Exception as e:
            error_msg = f"Failed to configure nginx: {e}"
            self.update_test_status("configure_nginx", "FAILED", error=error_msg)
            return False

    def run(self) -> bool:
        """Run the CA setup and validation"""
        start_time = datetime.datetime.now()
        self.stage_data["start_time"] = start_time.isoformat()

        print(f"\n=== Starting {self.stage_name} ===")

        # Run all tests
        tests = [
            self.generate_ca,
            self.validate_ca_structure,
            self.generate_kme_cert,
            self.validate_cert_chain,
            self.configure_nginx,
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
    # Load the latest test result
    results_dir = Path(__file__).parent.parent / "results"
    result_files = list(results_dir.glob("test_result_*.json"))

    if not result_files:
        print("No test result files found. Run Stage 0.1 first.")
        sys.exit(1)

    # Use the most recent result file
    latest_result = max(result_files, key=lambda x: x.stat().st_mtime)

    with open(latest_result) as f:
        test_result = json.load(f)

    # Run the CA setup
    ca_setup = CASetup(test_result)
    success = ca_setup.run()

    # Save updated result
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = (
        Path(__file__).parent.parent / "results" / f"test_result_{timestamp}.json"
    )

    with open(result_path, "w") as f:
        json.dump(test_result, f, indent=2)

    print(f"\nTest result saved to: {result_path}")

    if success:
        print("✅ CA setup completed successfully")
        sys.exit(0)
    else:
        print("❌ CA setup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
