#!/usr/bin/env python3
"""
Stage 0.1: Complete Environment Reset

This script performs a complete reset of the KME environment:
- Removes all existing certificates
- Clears configuration files
- Resets database to clean state
- Restores nginx configuration
- Verifies clean slate state
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pexpect

# Import secure credentials
from credentials import credentials

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class EnvironmentReset:
    """Complete environment reset for KME testing"""

    def __init__(self, test_result: dict[str, Any]):
        self.test_result = test_result
        self.project_root = Path(__file__).parent.parent.parent
        self.stage_name = "stage_0_1_reset"
        self.stage_data = test_result["stages"][self.stage_name]

        # Directories to clean
        self.cert_directories = [
            "sae_certs",
            "admin/sae_certs",
            "test_certs",
            "certs",
        ]

        # Files to remove
        self.cert_files = ["*.pem", "*.key", "*.crt", "*.p12", "*.pfx"]

        # Configuration files to reset
        self.config_files = [".env"]

        print(f"Starting {self.stage_name}: Complete Environment Reset")
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

            # Check if this is a sudo command that might need password
            if command[0] == "sudo":
                # Use pexpect to handle sudo password prompt (or lack thereof)

                # Start the command
                child = pexpect.spawn(
                    " ".join(command), cwd=str(self.project_root), timeout=30
                )

                # Handle password prompt (or lack thereof)
                i = child.expect(["[Pp]assword.*:", pexpect.EOF, pexpect.TIMEOUT])
                if i == 0:
                    # Password prompt detected, send password
                    child.sendline(credentials.get_sudo_password())
                    child.expect(pexpect.EOF, timeout=30)
                elif i == 1:
                    # No password prompt, command completed
                    pass
                else:
                    # Timeout
                    print(f"❌ Timeout waiting for command: {' '.join(command)}")
                    return False

                # Get the output
                output = child.before.decode("utf-8") + child.after.decode("utf-8")
                exit_code = child.exitstatus

                if exit_code == 0:
                    print(f"✅ {description} - Success")
                    return True
                else:
                    print(f"❌ {description} - Failed")
                    print(f"Error: {output}")
                    return False
            else:
                # Non-sudo command, use regular subprocess
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=30,
                )

                if result.returncode == 0:
                    print(f"✅ {description} - Success")
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

    def run_command_with_env(
        self, command: list[str], description: str, env: dict[str, str]
    ) -> bool:
        """Run a shell command with specific environment variables and return success status"""
        try:
            print(f"Running: {' '.join(command)}")

            # Check if this is a sudo command that might need password
            if command[0] == "sudo":
                # Use pexpect to handle sudo password prompt (or lack thereof)

                # Start the command with environment variables
                child = pexpect.spawn(
                    " ".join(command), cwd=str(self.project_root), timeout=30, env=env
                )

                # Handle password prompt (or lack thereof)
                i = child.expect(["[Pp]assword.*:", pexpect.EOF, pexpect.TIMEOUT])
                if i == 0:
                    # Password prompt detected, send password
                    child.sendline(credentials.get_sudo_password())
                    child.expect(pexpect.EOF, timeout=30)
                elif i == 1:
                    # No password prompt, command completed
                    pass
                else:
                    # Timeout
                    print(f"❌ Timeout waiting for command: {' '.join(command)}")
                    return False

                # Get the output
                output = child.before.decode("utf-8") + child.after.decode("utf-8")
                exit_code = child.exitstatus

                if exit_code == 0:
                    print(f"✅ {description} - Success")
                    return True
                else:
                    print(f"❌ {description} - Failed")
                    print(f"Error: {output}")
                    return False
            else:
                # Non-sudo command, use regular subprocess
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=30,
                    env=env,
                )

                if result.returncode == 0:
                    print(f"✅ {description} - Success")
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

    def remove_existing_certificates(self) -> bool:
        """Remove all existing certificates"""
        try:
            removed_count = 0

            # Remove certificate directories
            for cert_dir in self.cert_directories:
                cert_path = self.project_root / cert_dir
                if cert_path.exists():
                    shutil.rmtree(cert_path)
                    removed_count += 1
                    print(f"Removed directory: {cert_path}")

            # Remove certificate files
            for pattern in self.cert_files:
                for cert_file in self.project_root.glob(pattern):
                    if cert_file.is_file():
                        cert_file.unlink()
                        removed_count += 1
                        print(f"Removed file: {cert_file}")

            details = f"Removed {removed_count} certificate files/directories"
            self.update_test_status("remove_existing_certificates", "PASSED", details)
            return True

        except Exception as e:
            error_msg = f"Failed to remove certificates: {e}"
            self.update_test_status(
                "remove_existing_certificates", "FAILED", error=error_msg
            )
            return False

    def remove_config_files(self) -> bool:
        """Remove configuration files"""
        try:
            removed_count = 0

            for config_file in self.config_files:
                config_path = self.project_root / config_file
                if config_path.exists():
                    # Backup original file if it exists
                    backup_path = config_path.with_suffix(
                        config_path.suffix + ".backup"
                    )
                    if not backup_path.exists():
                        shutil.copy2(config_path, backup_path)
                        print(f"Backed up: {config_path} -> {backup_path}")

                    config_path.unlink()
                    removed_count += 1
                    print(f"Removed config file: {config_path}")

            details = f"Removed {removed_count} configuration files"
            self.update_test_status("remove_config_files", "PASSED", details)
            return True

        except Exception as e:
            error_msg = f"Failed to remove config files: {e}"
            self.update_test_status("remove_config_files", "FAILED", error=error_msg)
            return False

    def clear_database(self) -> bool:
        """Clear all database entries"""
        try:
            # Check if PostgreSQL is running
            if not self.run_command(["pg_isready"], "Check PostgreSQL status"):
                print("PostgreSQL not running, skipping database cleanup")
                self.update_test_status(
                    "clear_database", "SKIPPED", "PostgreSQL not running"
                )
                return True

            # Use secure database credentials
            db_config = credentials.get_database_config()
            db_name = db_config["database"]
            db_user = db_config["user"]
            db_host = db_config["host"]
            db_port = db_config["port"]
            db_password = db_config["password"]

            # Set PGPASSWORD environment variable to avoid password prompt
            env = os.environ.copy()
            env["PGPASSWORD"] = db_password

            # Drop and recreate schema
            drop_command = [
                "psql",
                "-h",
                db_host,
                "-p",
                db_port,
                "-U",
                db_user,
                "-d",
                db_name,
                "-c",
                "DROP SCHEMA public CASCADE; CREATE SCHEMA public;",
            ]

            if self.run_command_with_env(drop_command, "Clear database schema", env):
                self.update_test_status(
                    "clear_database", "PASSED", "Database schema cleared"
                )
                return True
            else:
                self.update_test_status(
                    "clear_database", "FAILED", error="Failed to clear database"
                )
                return False

        except Exception as e:
            error_msg = f"Failed to clear database: {e}"
            self.update_test_status("clear_database", "FAILED", error=error_msg)
            return False

    def reset_nginx(self) -> bool:
        """Reset nginx configuration"""
        try:
            # Remove KME-specific nginx configuration files
            nginx_files_to_remove = [
                "nginx.conf",
                "kme_nginx.conf",
                "nginx.conf.backup",
            ]

            removed_files = []
            for nginx_file in nginx_files_to_remove:
                nginx_path = self.project_root / nginx_file
                if nginx_path.exists():
                    nginx_path.unlink()
                    removed_files.append(nginx_file)
                    print(f"Removed nginx config: {nginx_file}")

            if removed_files:
                print(f"Removed {len(removed_files)} nginx configuration files")
                self.update_test_status(
                    "reset_nginx",
                    "PASSED",
                    f"Removed {len(removed_files)} nginx config files",
                )
            else:
                print("No KME nginx configuration files found")
                self.update_test_status(
                    "reset_nginx", "PASSED", "No KME nginx config files to remove"
                )

            return True

        except Exception as e:
            error_msg = f"Failed to reset nginx: {e}"
            self.update_test_status("reset_nginx", "FAILED", error=error_msg)
            return False

    def verify_clean_state(self) -> bool:
        """Verify clean slate state"""
        try:
            issues = []

            # Check for remaining certificate files
            for cert_dir in self.cert_directories:
                cert_path = self.project_root / cert_dir
                if cert_path.exists():
                    issues.append(f"Certificate directory still exists: {cert_path}")

            # Check for remaining certificate files
            for pattern in self.cert_files:
                for cert_file in self.project_root.glob(pattern):
                    if cert_file.is_file():
                        issues.append(f"Certificate file still exists: {cert_file}")

            # Check for configuration files
            for config_file in self.config_files:
                config_path = self.project_root / config_file
                if config_path.exists():
                    issues.append(f"Configuration file still exists: {config_path}")

            # Check environment variables - only check if they're set in current process
            # Note: We can't clear environment variables from parent process
            env_vars = ["KME_MASTER_KEY", "KME_ID", "DATABASE_URL"]
            for env_var in env_vars:
                if os.getenv(env_var):
                    # Don't fail on environment variables - they may be set in parent shell
                    print(f"Warning: Environment variable still set: {env_var}")

            if issues:
                error_msg = f"Clean state verification failed: {'; '.join(issues)}"
                self.update_test_status("verify_clean_state", "FAILED", error=error_msg)
                return False
            else:
                self.update_test_status(
                    "verify_clean_state", "PASSED", "Clean state verified"
                )
                return True

        except Exception as e:
            error_msg = f"Failed to verify clean state: {e}"
            self.update_test_status("verify_clean_state", "FAILED", error=error_msg)
            return False

    def run(self) -> bool:
        """Run the complete environment reset"""
        start_time = datetime.datetime.now()
        self.stage_data["start_time"] = start_time.isoformat()

        print(f"\n=== Starting {self.stage_name} ===")

        # Run all tests
        tests = [
            self.remove_existing_certificates,
            self.remove_config_files,
            self.clear_database,
            self.reset_nginx,
            self.verify_clean_state,
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

    # Run the reset
    reset = EnvironmentReset(test_result)
    success = reset.run()

    # Save result
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = (
        Path(__file__).parent.parent / "results" / f"test_result_{timestamp}.json"
    )

    with open(result_path, "w") as f:
        json.dump(test_result, f, indent=2)

    print(f"\nTest result saved to: {result_path}")

    if success:
        print("✅ Environment reset completed successfully")
        sys.exit(0)
    else:
        print("❌ Environment reset failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
