#!/usr/bin/env python3
"""
Stage 0.3: Admin Tool SAE Management

This script validates SAE certificate generation and registration through the admin tools.
It tests the complete SAE lifecycle: generation, registration, management, and revocation.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pexpect

# Import secure credentials
from credentials import credentials

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class SAEManagementTest:
    """Test SAE certificate generation and registration through admin tools"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.absolute()
        self.scripts_dir = self.project_root / "test" / "scripts"
        self.results_dir = self.project_root / "test" / "results"
        self.logs_dir = self.project_root / "test" / "logs"

        # Ensure directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Test data
        self.test_sae_id = "TEST_SAE_001_XY"
        self.test_sae_name = "Test SAE 001"
        self.test_sae_cert_path = (
            self.project_root / "certs" / "sae_certs" / f"{self.test_sae_id}.crt"
        )
        self.test_sae_key_path = (
            self.project_root / "certs" / "sae_certs" / f"{self.test_sae_id}.key"
        )

        # Results tracking
        self.results = {
            "stage": "0.3",
            "name": "Admin Tool SAE Management",
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": []},
        }

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def run_command(self, command: list[str], description: str) -> bool:
        """Run a command and return success status"""
        try:
            self.log(f"Running: {' '.join(command)}")
            self.log(f"Description: {description}")

            # Check if this is a sudo command that might need password
            if command[0] == "sudo":
                # Use pexpect to handle sudo password prompt (or lack thereof)

                # Start the command
                child = pexpect.spawn(
                    " ".join(command), cwd=str(self.project_root), timeout=60
                )

                i = child.expect(["[Pp]assword.*:", pexpect.EOF, pexpect.TIMEOUT])
                if i == 0:
                    # Password prompt detected, send password
                    child.sendline(credentials.get_sudo_password())
                    child.expect(pexpect.EOF, timeout=60)
                elif i == 1:
                    # No password prompt, command completed
                    pass
                else:
                    # Timeout
                    self.log(
                        f"❌ Timeout waiting for command: {' '.join(command)}", "ERROR"
                    )
                    return False

                # Get the output
                output = child.before.decode("utf-8") + child.after.decode("utf-8")
                exit_code = child.exitstatus

            else:
                # Regular command
                result = subprocess.run(
                    command,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                output = result.stdout + result.stderr
                exit_code = result.returncode

            if exit_code == 0:
                self.log(f"✅ {description} - Success")
                if output.strip():
                    self.log(f"Output: {output.strip()}")
                return True
            else:
                self.log(f"❌ {description} - Failed (exit code: {exit_code})", "ERROR")
                if output.strip():
                    self.log(f"Error: {output.strip()}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ {description} - Exception: {e}", "ERROR")
            return False

    def test_sae_certificate_generation(self) -> bool:
        """Test SAE certificate generation using admin tools"""
        try:
            self.log("Testing SAE certificate generation...")

            # Generate SAE certificate using admin tool
            admin_tool = self.project_root / "admin" / "kme_admin.py"
            command = [
                "python",
                str(admin_tool),
                "sae",
                "generate-certificate",
                "--sae-id",
                self.test_sae_id,
                "--name",
                self.test_sae_name,
            ]

            if not self.run_command(command, "Generate SAE certificate"):
                return False

            # Verify certificate files were created
            if not self.test_sae_cert_path.exists():
                self.log(
                    f"❌ SAE certificate not found: {self.test_sae_cert_path}", "ERROR"
                )
                return False

            if not self.test_sae_key_path.exists():
                self.log(
                    f"❌ SAE private key not found: {self.test_sae_key_path}", "ERROR"
                )
                return False

            self.log(f"✅ SAE certificate generated: {self.test_sae_cert_path}")
            self.log(f"✅ SAE private key generated: {self.test_sae_key_path}")

            return True

        except Exception as e:
            self.log(f"❌ SAE certificate generation test failed: {e}", "ERROR")
            return False

    def test_sae_certificate_validation(self) -> bool:
        """Test SAE certificate structure and CA signing"""
        try:
            self.log("Testing SAE certificate validation...")

            # Verify certificate structure using OpenSSL
            command = [
                "openssl",
                "x509",
                "-in",
                str(self.test_sae_cert_path),
                "-text",
                "-noout",
            ]

            if not self.run_command(command, "Validate SAE certificate structure"):
                return False

            # Verify certificate is signed by CA
            ca_cert = self.project_root / "certs" / "ca" / "ca.crt"
            command = [
                "openssl",
                "verify",
                "-CAfile",
                str(ca_cert),
                str(self.test_sae_cert_path),
            ]

            if not self.run_command(command, "Verify SAE certificate CA signing"):
                return False

            # Extract and verify SAE ID from certificate
            command = [
                "openssl",
                "x509",
                "-in",
                str(self.test_sae_cert_path),
                "-subject",
                "-noout",
            ]

            if not self.run_command(command, "Extract SAE ID from certificate"):
                return False

            self.log("✅ SAE certificate validation passed")
            return True

        except Exception as e:
            self.log(f"❌ SAE certificate validation test failed: {e}", "ERROR")
            return False

    def test_sae_registration(self) -> bool:
        """Test SAE registration through admin interface"""
        try:
            self.log("Testing SAE registration...")

            # Register SAE using admin tool
            admin_tool = self.project_root / "admin" / "kme_admin.py"
            command = [
                "python",
                str(admin_tool),
                "sae",
                "register",
                "--name",
                self.test_sae_name,
                "--certificate",
                str(self.test_sae_cert_path),
            ]

            if not self.run_command(command, "Register SAE"):
                return False

            self.log("✅ SAE registration completed")
            return True

        except Exception as e:
            self.log(f"❌ SAE registration test failed: {e}", "ERROR")
            return False

    def test_sae_database_verification(self) -> bool:
        """Test SAE registration in database"""
        try:
            self.log("Testing SAE database verification...")

            # List SAEs to verify registration
            admin_tool = self.project_root / "admin" / "kme_admin.py"
            command = ["python", str(admin_tool), "sae", "list", "--json"]

            if not self.run_command(command, "List registered SAEs"):
                return False

            # Show specific SAE details
            command = [
                "python",
                str(admin_tool),
                "sae",
                "show",
                self.test_sae_id,
                "--json",
            ]

            if not self.run_command(command, "Show SAE details"):
                return False

            self.log("✅ SAE database verification completed")
            return True

        except Exception as e:
            self.log(f"❌ SAE database verification test failed: {e}", "ERROR")
            return False

    def test_sae_certificate_revocation(self) -> bool:
        """Test SAE certificate revocation"""
        try:
            self.log("Testing SAE certificate revocation...")

            # Revoke SAE certificate
            admin_tool = self.project_root / "admin" / "kme_admin.py"
            command = [
                "python",
                str(admin_tool),
                "sae",
                "revoke-certificate",
                self.test_sae_id,
            ]

            if not self.run_command(command, "Revoke SAE certificate"):
                return False

            # Verify revocation by listing certificates
            command = ["python", str(admin_tool), "sae", "list-certificates", "--json"]

            if not self.run_command(command, "List certificates after revocation"):
                return False

            self.log("✅ SAE certificate revocation completed")
            return True

        except Exception as e:
            self.log(f"❌ SAE certificate revocation test failed: {e}", "ERROR")
            return False

    def test_sae_management_operations(self) -> bool:
        """Test admin tool can list/manage all SAEs"""
        try:
            self.log("Testing SAE management operations...")

            admin_tool = self.project_root / "admin" / "kme_admin.py"

            # Test various management operations
            operations = [
                ("List all SAEs", ["sae", "list"]),
                ("List SAEs in JSON format", ["sae", "list", "--json"]),
                ("List all certificates", ["sae", "list-certificates"]),
                (
                    "List certificates in JSON format",
                    ["sae", "list-certificates", "--json"],
                ),
            ]

            for description, args in operations:
                command = ["python", str(admin_tool)] + args
                if not self.run_command(command, description):
                    return False

            self.log("✅ SAE management operations completed")
            return True

        except Exception as e:
            self.log(f"❌ SAE management operations test failed: {e}", "ERROR")
            return False

    def run_all_tests(self) -> bool:
        """Run all SAE management tests"""
        self.log("=" * 80)
        self.log("STAGE 0.3: ADMIN TOOL SAE MANAGEMENT")
        self.log("=" * 80)

        tests = [
            ("SAE Certificate Generation", self.test_sae_certificate_generation),
            ("SAE Certificate Validation", self.test_sae_certificate_validation),
            ("SAE Registration", self.test_sae_registration),
            ("SAE Database Verification", self.test_sae_database_verification),
            ("SAE Certificate Revocation", self.test_sae_certificate_revocation),
            ("SAE Management Operations", self.test_sae_management_operations),
        ]

        all_passed = True

        for test_name, test_func in tests:
            self.log(f"\n--- Running: {test_name} ---")
            self.results["summary"]["total"] += 1

            try:
                if test_func():
                    self.results["summary"]["passed"] += 1
                    self.results["tests"].append(
                        {
                            "name": test_name,
                            "status": "PASSED",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                else:
                    self.results["summary"]["failed"] += 1
                    self.results["tests"].append(
                        {
                            "name": test_name,
                            "status": "FAILED",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    all_passed = False

            except Exception as e:
                self.results["summary"]["failed"] += 1
                self.results["summary"]["errors"].append(str(e))
                self.results["tests"].append(
                    {
                        "name": test_name,
                        "status": "ERROR",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                all_passed = False

        return all_passed

    def save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"stage_0_3_results_{timestamp}.json"

        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        self.log(f"Results saved to: {results_file}")

        # Also save summary to logs
        log_file = self.logs_dir / f"stage_0_3_log_{timestamp}.txt"
        with open(log_file, "w") as f:
            f.write(f"Stage 0.3: Admin Tool SAE Management\n")
            f.write(f"Timestamp: {self.results['timestamp']}\n")
            f.write(f"Total Tests: {self.results['summary']['total']}\n")
            f.write(f"Passed: {self.results['summary']['passed']}\n")
            f.write(f"Failed: {self.results['summary']['failed']}\n")
            f.write(
                f"Success Rate: {self.results['summary']['passed']/self.results['summary']['total']*100:.1f}%\n"
            )

        self.log(f"Log saved to: {log_file}")

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 80)
        self.log("STAGE 0.3 TEST SUMMARY")
        self.log("=" * 80)

        total = self.results["summary"]["total"]
        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]

        self.log(f"Total Tests: {total}")
        self.log(f"Passed: {passed}")
        self.log(f"Failed: {failed}")

        if total > 0:
            success_rate = (passed / total) * 100
            self.log(f"Success Rate: {success_rate:.1f}%")

        if failed > 0:
            self.log("\nFailed Tests:")
            for test in self.results["tests"]:
                if test["status"] in ["FAILED", "ERROR"]:
                    self.log(f"  - {test['name']}: {test.get('error', 'Failed')}")

        if self.results["summary"]["errors"]:
            self.log("\nErrors:")
            for error in self.results["summary"]["errors"]:
                self.log(f"  - {error}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Stage 0.3: Admin Tool SAE Management")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Create test instance
    test = SAEManagementTest()

    try:
        # Run all tests
        success = test.run_all_tests()

        # Save results
        test.save_results()

        # Print summary
        test.print_summary()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        test.log("Test interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        test.log(f"Test failed with exception: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
