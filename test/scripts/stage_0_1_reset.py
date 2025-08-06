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
        """Remove configuration files and create new .env with defaults"""
        try:
            removed_count = 0

            for config_file in self.config_files:
                config_path = self.project_root / config_file
                if config_file == ".env" and config_path.exists():
                    # Backup original .env file if it exists
                    backup_path = config_path.with_suffix(
                        config_path.suffix + ".backup"
                    )
                    if not backup_path.exists():
                        shutil.copy2(config_path, backup_path)
                        print(f"Backed up: {config_path} -> {backup_path}")

                    # Remove old .env file
                    config_path.unlink()
                    removed_count += 1
                    print(f"Removed old config file: {config_path}")

                    # Create new .env file with sane defaults
                    self._create_default_env_file(config_path)
                    print(f"Created new .env file with defaults: {config_path}")

            details = (
                f"Removed {removed_count} configuration files and created new .env"
            )
            self.update_test_status("remove_config_files", "PASSED", details)
            return True

        except Exception as e:
            error_msg = f"Failed to remove config files: {e}"
            self.update_test_status("remove_config_files", "FAILED", error=error_msg)
            return False

    def _create_default_env_file(self, env_path: Path):
        """Create a new .env file with sane defaults"""
        try:
            # Generate a random KME ID
            import secrets
            import string

            hex_chars = string.hexdigits.upper()[:16]  # A-F, 0-9
            kme_id = "".join(secrets.choice(hex_chars) for _ in range(16))

            # Get database credentials
            db_config = credentials.get_database_config()

            # Create .env content with sane defaults
            env_content = f"""# KME Environment Configuration
# Generated by KME Test Environment Reset

# KME Identity
KME_ID={kme_id}
KME_HOSTNAME=localhost
KME_PORT=443

# Server Configuration
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
SERVER_RELOAD=true

# Database Configuration
DATABASE_URL=postgresql+asyncpg://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false
DATABASE_POOL_PRE_PING=true
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_TIMEOUT=30

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=10

# TLS Configuration
TLS_CERT_FILE=certs/kme_cert.pem
TLS_KEY_FILE=certs/kme_key.pem
TLS_CA_FILE=certs/ca/ca.crt
TLS_VERSION=1.2

# Security Configuration
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=
LOG_FORMAT=json

# Key Management Configuration
DEFAULT_KEY_SIZE=352
MAX_KEY_SIZE=1024
MIN_KEY_SIZE=64
MAX_KEYS_PER_REQUEST=128
MAX_KEY_COUNT=100000
MAX_SAE_ID_COUNT=10

# QKD Network Configuration
QKD_NETWORK_ENABLED=true
QKD_LINK_TIMEOUT=30
QKD_KEY_GENERATION_RATE=1000
QKD_LINKS=["link1", "link2"]

# Performance Configuration
WORKER_PROCESSES=4
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30

# Monitoring Configuration
METRICS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_ENABLED=true

# Development Configuration
DEBUG=false
RELOAD=false
TESTING=false

# CORS Configuration
ALLOWED_ORIGINS=["*"]
ALLOWED_HOSTS=["*"]

# Security Configuration
SECURITY_LEVEL=production
TLS_CERTIFICATE_PATH=certs/kme_cert.pem
TLS_PRIVATE_KEY_PATH=certs/kme_key.pem
CA_CERTIFICATE_PATH=certs/ca/ca.crt
KEY_ENCRYPTION_KEY=
ENABLE_MUTUAL_TLS=true
MIN_TLS_VERSION=TLSv1.2
MAX_TLS_VERSION=TLSv1.3

# Certificate Expiration Warning Configuration
CERTIFICATE_WARNING_DAYS=30
CERTIFICATE_CRITICAL_DAYS=7
CERTIFICATE_EXPIRATION_CHECK_ENABLED=true

# SSL Configuration (for main.py)
KME_ENABLE_SSL=0
"""

            # Write the new .env file
            with open(env_path, "w") as f:
                f.write(env_content)

            print(f"✅ Created new .env file with KME_ID: {kme_id}")

        except Exception as e:
            print(f"❌ Failed to create default .env file: {e}")
            raise

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

            # Check for configuration files (except .env which we create with defaults)
            for config_file in self.config_files:
                config_path = self.project_root / config_file
                if config_file == ".env":
                    # .env file should exist after we create it with defaults
                    if not config_path.exists():
                        issues.append(f"Configuration file missing: {config_path}")
                else:
                    # Other config files should not exist
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
