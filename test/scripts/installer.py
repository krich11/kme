#!/usr/bin/env python3
"""
KME Test Environment Installer

This installer sets up all the infrastructure needed for comprehensive KME testing:
- CA and certificate generation tools
- Database setup and configuration
- Nginx configuration
- Test utilities and scripts
- Environment validation tools

Usage:
    python installer.py [component]

Components:
    all         - Install all components
    ca          - CA and certificate tools
    database    - Database setup and configuration
    nginx       - Nginx configuration
    utils       - Test utilities
    validate    - Environment validation
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class KMEInstaller:
    """KME Test Environment Installer"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.install_log = []

        # KME ID - will be determined early in installation
        self.kme_id = None

        # CA configuration - will be determined based on KME ID
        self.ca_name = None

        # Installation paths
        self.paths = {
            "ca_dir": self.project_root / "admin" / "ca",
            "sae_certs_dir": self.project_root / "admin" / "sae_certs",
            "test_certs_dir": self.project_root / "test_certs",
            "scripts_dir": self.project_root / "test" / "scripts",
            "data_dir": self.project_root / "test" / "data",
            "logs_dir": self.project_root / "test" / "logs",
            "results_dir": self.project_root / "test" / "results",
        }

        # Import secure credentials
        from credentials import credentials

        # Database configuration
        self.db_config = credentials.get_database_config()

        print("🔧 KME Test Environment Installer")
        print(f"Project root: {self.project_root}")

    def log(self, message: str, level: str = "INFO"):
        """Log installation message"""
        log_entry = f"[{level}] {message}"
        self.install_log.append(log_entry)
        print(log_entry)

    def run_command(
        self, command: list[str], description: str, cwd: Path | None = None
    ) -> bool:
        """Run a shell command and return success status"""
        try:
            self.log(f"Running: {' '.join(command)}")

            # Check if this is a sudo command that might need password
            if command[0] == "sudo":
                # Use pexpect to handle sudo password prompt (or lack thereof)
                import pexpect

                # Import secure credentials
                from credentials import credentials

                # Start the command
                child = pexpect.spawn(
                    " ".join(command), cwd=str(cwd or self.project_root), timeout=60
                )

                # Handle password prompt (or lack thereof)
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

                if exit_code == 0:
                    self.log(f"✅ {description} - Success")
                    if output.strip():
                        self.log(f"Output: {output.strip()}")
                    return True
                else:
                    self.log(f"❌ {description} - Failed: {output}", "ERROR")
                    return False
            else:
                # Non-sudo command, use regular subprocess
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=cwd or self.project_root,
                    timeout=60,
                )

                if result.returncode == 0:
                    self.log(f"✅ {description} - Success")
                    if result.stdout.strip():
                        self.log(f"Output: {result.stdout.strip()}")
                    return True
                else:
                    self.log(f"❌ {description} - Failed: {result.stderr}", "ERROR")
                    return False

        except subprocess.TimeoutExpired:
            self.log(f"❌ {description} - Timeout", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ {description} - Exception: {e}", "ERROR")
            return False

    def create_directories(self) -> bool:
        """Create all necessary directories"""
        try:
            for name, path in self.paths.items():
                path.mkdir(parents=True, exist_ok=True)
                self.log(f"Created directory: {path}")

            return True
        except Exception as e:
            self.log(f"Failed to create directories: {e}", "ERROR")
            return False

    def determine_kme_id(self, interactive: bool = False) -> bool:
        """Determine KME ID early in the installation process"""
        try:
            self.log("🆔 Determining KME ID...")

            if interactive:
                # Interactive mode - prompt user
                self.log("  📝 Interactive mode: Please enter KME ID")
                self.log(
                    "  💡 Format: 16-character hexadecimal (e.g., A1B2C3D4E5F67890)"
                )

                while True:
                    try:
                        kme_id = (
                            input("Enter KME ID (or press Enter for random): ")
                            .strip()
                            .upper()
                        )

                        if not kme_id:
                            # Generate random KME ID
                            self.kme_id = self._generate_random_kme_id()
                            self.log(f"  🎲 Generated random KME ID: {self.kme_id}")
                            break

                        # Validate KME ID format
                        if self._validate_kme_id_format(kme_id):
                            self.kme_id = kme_id
                            self.log(f"  ✅ Using provided KME ID: {self.kme_id}")
                            break
                        else:
                            self.log(
                                "  ❌ Invalid KME ID format. Must be 16-character hexadecimal.",
                                "ERROR",
                            )
                            self.log("  💡 Example: A1B2C3D4E5F67890")
                    except KeyboardInterrupt:
                        self.log("  ❌ KME ID input cancelled", "ERROR")
                        return False
            else:
                # Non-interactive mode - generate random KME ID
                self.kme_id = self._generate_random_kme_id()
                self.log(f"  🎲 Generated random KME ID: {self.kme_id}")

            self.log(f"  ✅ KME ID determined: {self.kme_id}")
            return True

        except Exception as e:
            self.log(f"❌ Failed to determine KME ID: {e}", "ERROR")
            return False

    def _generate_random_kme_id(self) -> str:
        """Generate a random KME ID"""
        import secrets
        import string

        # Generate 16-character hexadecimal string
        hex_chars = string.hexdigits.upper()[:16]  # A-F, 0-9
        return "".join(secrets.choice(hex_chars) for _ in range(16))

    def _validate_kme_id_format(self, kme_id: str) -> bool:
        """Validate KME ID format"""
        import re

        # Must be exactly 16 characters, hexadecimal (A-F, 0-9)
        pattern = r"^[A-F0-9]{16}$"
        return bool(re.match(pattern, kme_id.upper()))

    def _determine_ca_name(self) -> str:
        """Determine CA name based on KME ID"""
        if not self.kme_id:
            return "KME Root CA"

        # Create a meaningful CA name using the KME ID
        # Format: "KME Root CA - {first 8 chars of KME ID}"
        short_id = self.kme_id[:8]
        return f"KME Root CA - {short_id}"

    def install_ca_tools(self) -> bool:
        """Install CA and certificate generation tools"""
        try:
            self.log("🔐 Setting up Certificate Authority infrastructure...")

            # Create CA generation script
            ca_script = self.paths["scripts_dir"] / "generate_ca.py"
            if not ca_script.exists():
                self.log("  📝 Creating CA generation script...")
                # Copy the existing generate_ca.py
                source_ca_script = (
                    self.project_root / "test" / "scripts" / "generate_ca.py"
                )
                if source_ca_script.exists():
                    shutil.copy2(source_ca_script, ca_script)
                    self.log(f"    ✅ Created CA generation script: {ca_script}")
                else:
                    self.log("    ❌ CA generation script not found in source", "ERROR")
                    return False

            # Create certificate validation script
            cert_validator = self.paths["scripts_dir"] / "certificate_validator.py"
            if not cert_validator.exists():
                self.log("  📝 Creating certificate validation script...")
                self._create_certificate_validator(cert_validator)
                self.log("    ✅ Certificate validator created")

            # Determine CA name based on KME ID
            if not self.kme_id:
                self.log("❌ KME ID not determined for CA generation", "ERROR")
                return False

            self.ca_name = self._determine_ca_name()
            self.log(f"  🏷️ Using CA name: {self.ca_name}")

            # Test CA generation with determined CA name
            self.log("  🧪 Testing CA generation...")
            if self.run_command(
                ["python", str(ca_script), "ca", self.ca_name], "Test CA generation"
            ):
                self.log("    ✅ CA generation test successful")

                # Generate KME certificate with determined KME ID
                self.log("  🧪 Testing KME certificate generation...")
                if self.run_command(
                    ["python", str(ca_script), "kme", self.kme_id],
                    "Test KME certificate generation",
                ):
                    self.log("    ✅ KME certificate generation test successful")
                    return True
                else:
                    self.log("    ❌ KME certificate generation test failed", "ERROR")
                    return False
            else:
                self.log("    ❌ CA generation test failed", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Failed to install CA tools: {e}", "ERROR")
            return False

    def _create_certificate_validator(self, script_path: Path):
        """Create certificate validation script"""
        validator_content = '''#!/usr/bin/env python3
"""
Certificate Validation Tool

Validates certificate structure, chain, and compliance.
"""

import sys
import subprocess
from pathlib import Path

def validate_certificate(cert_path: str) -> bool:
    """Validate a certificate"""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-text", "-noout"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def validate_cert_chain(ca_path: str, cert_path: str) -> bool:
    """Validate certificate chain"""
    try:
        result = subprocess.run(
            ["openssl", "verify", "-CAfile", ca_path, cert_path],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python certificate_validator.py <cert_path> [ca_path]")
        sys.exit(1)

    cert_path = sys.argv[1]
    if not validate_certificate(cert_path):
        print(f"❌ Certificate validation failed: {cert_path}")
        sys.exit(1)

    if len(sys.argv) > 2:
        ca_path = sys.argv[2]
        if not validate_cert_chain(ca_path, cert_path):
            print(f"❌ Certificate chain validation failed")
            sys.exit(1)

    print(f"✅ Certificate validation successful: {cert_path}")
'''

        with open(script_path, "w") as f:
            f.write(validator_content)

        # Make executable
        script_path.chmod(0o755)

    def install_database_tools(self) -> bool:
        """Install database setup and configuration tools"""
        try:
            self.log("🗄️ Setting up Database infrastructure...")

            # Create database setup script
            db_setup = self.paths["scripts_dir"] / "database_setup.py"
            if not db_setup.exists():
                self.log("  📝 Creating database setup script...")
                self._create_database_setup(db_setup)
                self.log("    ✅ Database setup script created")

            # Create database validation script
            db_validator = self.paths["scripts_dir"] / "database_validator.py"
            if not db_validator.exists():
                self.log("  📝 Creating database validation script...")
                self._create_database_validator(db_validator)
                self.log("    ✅ Database validation script created")

            # Test database connection
            self.log("  🧪 Testing database connection...")
            if self.run_command(
                ["python", str(db_validator), "test"], "Test database connection"
            ):
                self.log("    ✅ Database connection test successful")
                return True
            else:
                self.log("    ❌ Database connection test failed", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Failed to install database tools: {e}", "ERROR")
            return False

    def _create_database_setup(self, script_path: Path):
        """Create database setup script"""
        setup_content = f'''#!/usr/bin/env python3
"""
Database Setup Tool

Sets up PostgreSQL database for KME testing.
"""

import os
import sys
import subprocess
from pathlib import Path

# Database configuration
DB_CONFIG = {{
    'host': '{self.db_config['host']}',
    'port': '{self.db_config['port']}',
    'user': '{self.db_config['user']}',
    'password': '{self.db_config['password']}',
    'database': '{self.db_config['database']}'
}}

def setup_database():
    """Set up the database"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_CONFIG['password']

    # Create database if it doesn't exist
    create_cmd = [
        "createdb", "-h", DB_CONFIG['host'], "-p", DB_CONFIG['port'],
        "-U", DB_CONFIG['user'], DB_CONFIG['database']
    ]

    result = subprocess.run(create_cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"Failed to create database: {{result.stderr}}")
        return False

    print("✅ Database setup completed")
    return True

def reset_database():
    """Reset the database to clean state"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_CONFIG['password']

    # Drop and recreate schema
    reset_cmd = [
        "psql", "-h", DB_CONFIG['host'], "-p", DB_CONFIG['port'],
        "-U", DB_CONFIG['user'], "-d", DB_CONFIG['database'],
        "-c", "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    ]

    result = subprocess.run(reset_cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to reset database: {{result.stderr}}")
        return False

    print("✅ Database reset completed")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python database_setup.py [setup|reset]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "setup":
        success = setup_database()
    elif command == "reset":
        success = reset_database()
    else:
        print("Unknown command. Use 'setup' or 'reset'")
        sys.exit(1)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
'''

        with open(script_path, "w") as f:
            f.write(setup_content)

        # Make executable
        script_path.chmod(0o755)

    def _create_database_validator(self, script_path: Path):
        """Create database validation script"""
        validator_content = f'''#!/usr/bin/env python3
"""
Database Validation Tool

Validates database connectivity and schema.
"""

import os
import sys
import subprocess

# Database configuration
DB_CONFIG = {{
    'host': '{self.db_config['host']}',
    'port': '{self.db_config['port']}',
    'user': '{self.db_config['user']}',
    'password': '{self.db_config['password']}',
    'database': '{self.db_config['database']}'
}}

def test_connection():
    """Test database connection"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_CONFIG['password']

    cmd = [
        "psql", "-h", DB_CONFIG['host'], "-p", DB_CONFIG['port'],
        "-U", DB_CONFIG['user'], "-d", DB_CONFIG['database'],
        "-c", "SELECT version();"
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result.returncode == 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python database_validator.py [test]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "test":
        if test_connection():
            print("✅ Database connection successful")
            sys.exit(0)
        else:
            print("❌ Database connection failed")
            sys.exit(1)
    else:
        print("Unknown command. Use 'test'")
        sys.exit(1)
'''

        with open(script_path, "w") as f:
            f.write(validator_content)

        # Make executable
        script_path.chmod(0o755)

    def install_nginx_tools(self) -> bool:
        """Install nginx tools and configure nginx"""
        try:
            self.log("🌐 Setting up Nginx infrastructure...")

            # Create nginx configuration generator
            nginx_gen = self.paths["scripts_dir"] / "nginx_config_generator.py"
            if not nginx_gen.exists():
                self.log("  📝 Creating nginx configuration generator...")
                self._create_nginx_generator(nginx_gen)
                self.log("    ✅ Nginx configuration generator created")

            # Create nginx validator
            nginx_validator = self.paths["scripts_dir"] / "nginx_validator.py"
            if not nginx_validator.exists():
                self.log("  📝 Creating nginx validator...")
                self._create_nginx_validator(nginx_validator)
                self.log("    ✅ Nginx validator created")

            # Create nginx installer
            nginx_installer = self.paths["scripts_dir"] / "nginx_installer.py"
            if not nginx_installer.exists():
                self.log("  📝 Creating nginx installer...")
                self._create_nginx_installer(nginx_installer)
                self.log("    ✅ Nginx installer created")

            # Configure nginx for KME
            self.log("  🔧 Configuring nginx for KME system...")
            if not self._configure_nginx_for_kme():
                self.log("    ❌ Nginx configuration failed", "ERROR")
                return False

            self.log("    ✅ Nginx configuration completed")
            return True

        except Exception as e:
            self.log(f"❌ Failed to install nginx tools: {e}", "ERROR")
            return False

    def _create_nginx_generator(self, script_path: Path):
        """Create nginx configuration generator"""
        generator_content = '''#!/usr/bin/env python3
"""
Nginx Configuration Generator

Generates nginx configuration for KME testing.
"""

import sys
from pathlib import Path

def generate_nginx_config(kme_cert: str, kme_key: str, output_path: str = "nginx.conf"):
    """Generate nginx configuration"""

    config_content = f"""
server {{
    listen 443 ssl;
    server_name localhost;

    ssl_certificate {kme_cert};
    ssl_certificate_key {kme_key};

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    with open(output_path, 'w') as f:
        f.write(config_content)

    print(f"✅ Nginx configuration generated: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python nginx_config_generator.py <kme_cert> <kme_key> [output_path]")
        sys.exit(1)

    kme_cert = sys.argv[1]
    kme_key = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else "nginx.conf"

    generate_nginx_config(kme_cert, kme_key, output_path)
'''

        with open(script_path, "w") as f:
            f.write(generator_content)

        # Make executable
        script_path.chmod(0o755)

    def _create_nginx_validator(self, script_path: Path):
        """Create nginx validator"""
        validator_content = '''#!/usr/bin/env python3
"""
Nginx Configuration Validator

Validates nginx configuration.
"""

import sys
import subprocess
from pathlib import Path

def validate_nginx_config(config_path: str) -> bool:
    """Validate nginx configuration"""
    try:
        result = subprocess.run(
            ["nginx", "-t", "-c", config_path],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python nginx_validator.py <config_path>")
        sys.exit(1)

    config_path = sys.argv[1]

    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)

    if validate_nginx_config(config_path):
        print(f"✅ Nginx configuration valid: {config_path}")
        sys.exit(0)
    else:
        print(f"❌ Nginx configuration invalid: {config_path}")
        sys.exit(1)
'''

        with open(script_path, "w") as f:
            f.write(validator_content)

        # Make executable
        script_path.chmod(0o755)

    def _create_nginx_installer(self, script_path: Path):
        """Create nginx installer"""
        installer_content = '''#!/usr/bin/env python3
"""
Nginx Installer

Installs and configures nginx for KME system.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_nginx_installed() -> bool:
    """Check if nginx is installed"""
    try:
        result = subprocess.run(["nginx", "-v"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_nginx() -> bool:
    """Install nginx if not present"""
    if check_nginx_installed():
        print("✅ Nginx is already installed")
        return True

    print("📦 Installing nginx...")

    try:
        # Try to install nginx using package manager
        if shutil.which("apt"):
            result = subprocess.run(["sudo", "apt", "update"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to update package list: {result.stderr}")
                return False

            result = subprocess.run(["sudo", "apt", "install", "-y", "nginx"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to install nginx: {result.stderr}")
                return False

        elif shutil.which("yum"):
            result = subprocess.run(["sudo", "yum", "install", "-y", "nginx"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to install nginx: {result.stderr}")
                return False

        elif shutil.which("dnf"):
            result = subprocess.run(["sudo", "dnf", "install", "-y", "nginx"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to install nginx: {result.stderr}")
                return False

        else:
            print("❌ No supported package manager found")
            return False

        print("✅ Nginx installed successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to install nginx: {e}")
        return False

def backup_nginx_config() -> bool:
    """Backup existing nginx configuration"""
    nginx_conf = Path("/etc/nginx/nginx.conf")
    if nginx_conf.exists():
        backup_path = Path("/etc/nginx/nginx.conf.backup")
        try:
            shutil.copy2(nginx_conf, backup_path)
            print(f"✅ Nginx configuration backed up to: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to backup nginx configuration: {e}")
            return False
    return True

def install_kme_nginx_config(kme_cert: str, kme_key: str) -> bool:
    """Install KME nginx configuration"""
    try:
        # Create KME nginx configuration
        kme_config = f"""
# KME Nginx Configuration
# Generated by KME Test Environment Installer

server {{
    listen 443 ssl;
    server_name localhost;

    ssl_certificate {kme_cert};
    ssl_certificate_key {kme_key};

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}

    # Health check endpoint
    location /health {{
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }}
}}

# HTTP to HTTPS redirect
server {{
    listen 80;
    server_name localhost;
    return 301 https://$server_name$request_uri;
}}
"""

        # Write to sites-available
        sites_available = Path("/etc/nginx/sites-available")
        sites_enabled = Path("/etc/nginx/sites-enabled")

        if not sites_available.exists():
            sites_available.mkdir(parents=True, exist_ok=True)

        if not sites_enabled.exists():
            sites_enabled.mkdir(parents=True, exist_ok=True)

        kme_site_config = sites_available / "kme"
        with open(kme_site_config, 'w') as f:
            f.write(kme_config)

        # Enable the site
        kme_site_enabled = sites_enabled / "kme"
        if kme_site_enabled.exists():
            kme_site_enabled.unlink()

        kme_site_enabled.symlink_to(kme_site_config)

        print(f"✅ KME nginx configuration installed: {kme_site_config}")
        return True

    except Exception as e:
        print(f"❌ Failed to install KME nginx configuration: {e}")
        return False

def test_nginx_config() -> bool:
    """Test nginx configuration"""
    try:
        result = subprocess.run(["sudo", "nginx", "-t"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Nginx configuration test passed")
            return True
        else:
            print(f"❌ Nginx configuration test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Failed to test nginx configuration: {e}")
        return False

def restart_nginx() -> bool:
    """Restart nginx service"""
    try:
        # Try systemctl first
        if shutil.which("systemctl"):
            result = subprocess.run(["sudo", "systemctl", "restart", "nginx"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Nginx restarted successfully")
                return True

        # Fallback to service command
        if shutil.which("service"):
            result = subprocess.run(["sudo", "service", "nginx", "restart"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Nginx restarted successfully")
                return True

        print("❌ Failed to restart nginx")
        return False

    except Exception as e:
        print(f"❌ Failed to restart nginx: {e}")
        return False

def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python nginx_installer.py <kme_cert> <kme_key>")
        sys.exit(1)

    kme_cert = sys.argv[1]
    kme_key = sys.argv[2]

    # Check if certificate files exist
    if not Path(kme_cert).exists():
        print(f"❌ KME certificate not found: {kme_cert}")
        sys.exit(1)

    if not Path(kme_key).exists():
        print(f"❌ KME key not found: {kme_key}")
        sys.exit(1)

    print("🔧 Installing and configuring nginx for KME...")

    # Install nginx if needed
    if not install_nginx():
        sys.exit(1)

    # Backup existing configuration
    if not backup_nginx_config():
        sys.exit(1)

    # Install KME configuration
    if not install_kme_nginx_config(kme_cert, kme_key):
        sys.exit(1)

    # Test configuration
    if not test_nginx_config():
        sys.exit(1)

    # Restart nginx
    if not restart_nginx():
        sys.exit(1)

    print("✅ Nginx installation and configuration completed successfully")

if __name__ == "__main__":
    main()
'''

        with open(script_path, "w") as f:
            f.write(installer_content)

        # Make executable
        script_path.chmod(0o755)

    def install_test_utils(self) -> bool:
        """Install test utilities"""
        try:
            self.log("🧪 Setting up Test infrastructure...")

            # Create test runner
            test_runner = self.paths["scripts_dir"] / "test_runner.py"
            if not test_runner.exists():
                self.log("  📝 Creating test runner...")
                self._create_test_runner(test_runner)
                self.log("    ✅ Test runner created")

            # Create environment validator
            env_validator = self.paths["scripts_dir"] / "environment_validator.py"
            if not env_validator.exists():
                self.log("  📝 Creating environment validator...")
                self._create_environment_validator(env_validator)
                self.log("    ✅ Environment validator created")

            # Create test report generator
            report_gen = self.paths["scripts_dir"] / "report_generator.py"
            if not report_gen.exists():
                self.log("  📝 Creating test report generator...")
                self._create_report_generator(report_gen)
                self.log("    ✅ Test report generator created")

            self.log("    ✅ Test infrastructure setup completed")
            return True

        except Exception as e:
            self.log(f"❌ Failed to install test utilities: {e}", "ERROR")
            return False

    def install_env_config(self) -> bool:
        """Install environment configuration"""
        try:
            self.log("⚙️ Setting up Environment configuration...")

            # Create environment configuration tool
            env_config_tool = self.paths["scripts_dir"] / "env_config.py"
            if not env_config_tool.exists():
                self.log("  📝 Creating environment configuration tool...")
                self._create_env_config_tool(env_config_tool)
                self.log("    ✅ Environment configuration tool created")

            # Run environment configuration with default values
            self.log("  🔧 Configuring environment with default values...")
            if not self._configure_environment_defaults():
                self.log("    ❌ Environment configuration failed", "ERROR")
                return False

            self.log("    ✅ Environment configuration completed")
            return True

        except Exception as e:
            self.log(f"❌ Failed to install environment configuration: {e}", "ERROR")
            return False

    def _create_test_runner(self, script_path: Path):
        """Create test runner"""
        runner_content = '''#!/usr/bin/env python3
"""
Test Runner

Runs KME test stages in sequence.
"""

import sys
import json
import datetime
from pathlib import Path

def run_test_stage(stage_name: str, stage_script: str) -> bool:
    """Run a test stage"""
    print(f"Running {stage_name}...")

    try:
        result = subprocess.run(
            ["python", stage_script],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to run {stage_name}: {e}")
        return False

def main():
    """Main test runner"""
    stages = [
        ("Stage 0.1: Environment Reset", "stage_0_1_reset.py"),
        ("Stage 0.2: CA Setup", "stage_0_2_ca_setup.py"),
        ("Stage 0.3: SAE Management", "stage_0_3_sae_management.py"),
        ("Stage 0.4: Database Operations", "stage_0_4_database_ops.py"),
    ]

    results = {}

    for stage_name, stage_script in stages:
        script_path = Path(__file__).parent / stage_script
        if script_path.exists():
            success = run_test_stage(stage_name, str(script_path))
            results[stage_name] = "PASSED" if success else "FAILED"
        else:
            print(f"Stage script not found: {script_path}")
            results[stage_name] = "SKIPPED"

    # Generate summary
    print("\\n=== Test Results Summary ===")
    for stage_name, result in results.items():
        print(f"{stage_name}: {result}")

    # Save results
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = Path(__file__).parent.parent / "results" / f"test_summary_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\\nResults saved to: {results_file}")

if __name__ == "__main__":
    main()
'''

        with open(script_path, "w") as f:
            f.write(runner_content)

        # Make executable
        script_path.chmod(0o755)

    def _create_environment_validator(self, script_path: Path):
        """Create environment validator"""
        validator_content = '''#!/usr/bin/env python3
"""
Environment Validator

Validates the test environment setup.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)"

def check_openssl():
    """Check OpenSSL availability"""
    try:
        result = subprocess.run(["openssl", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, "OpenSSL not available"
    except Exception:
        return False, "OpenSSL not found"

def check_postgresql():
    """Check PostgreSQL availability"""
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, "PostgreSQL not available"
    except Exception:
        return False, "PostgreSQL not found"

def check_nginx():
    """Check nginx availability"""
    try:
        result = subprocess.run(["nginx", "-v"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, "nginx not available"
    except Exception:
        return False, "nginx not found"

def main():
    """Main validation function"""
    checks = [
        ("Python Version", check_python_version),
        ("OpenSSL", check_openssl),
        ("PostgreSQL", check_postgresql),
        ("Nginx", check_nginx),
    ]

    print("=== Environment Validation ===")

    all_passed = True
    for name, check_func in checks:
        passed, details = check_func()
        status = "✅" if passed else "❌"
        print(f"{status} {name}: {details}")

        if not passed:
            all_passed = False

    if all_passed:
        print("\\n✅ Environment validation passed")
        sys.exit(0)
    else:
        print("\\n❌ Environment validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

        with open(script_path, "w") as f:
            f.write(validator_content)

        # Make executable
        script_path.chmod(0o755)

    def _create_report_generator(self, script_path: Path):
        """Create test report generator"""
        generator_content = '''#!/usr/bin/env python3
"""
Test Report Generator

Generates HTML and JSON reports from test results.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def generate_html_report(test_results: dict, output_path: str):
    """Generate HTML report"""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>KME Test Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
        .stage {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ background-color: #d4edda; border-color: #c3e6cb; }}
        .failed {{ background-color: #f8d7da; border-color: #f5c6cb; }}
        .test {{ margin: 5px 0; padding: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>KME Test Results</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""

    for stage_name, stage_data in test_results.get('stages', {}).items():
        status = stage_data.get('status', 'UNKNOWN')
        css_class = 'passed' if status == 'PASSED' else 'failed'

        html_content += f"""
    <div class="stage {css_class}">
        <h3>{stage_data.get('name', stage_name)}</h3>
        <p>Status: {status}</p>
        <p>Duration: {stage_data.get('duration_seconds', 0):.2f} seconds</p>
"""

        for test_name, test_data in stage_data.get('tests', {}).items():
            test_status = test_data.get('status', 'UNKNOWN')
            test_css_class = 'passed' if test_status == 'PASSED' else 'failed'

            html_content += f"""
        <div class="test {test_css_class}">
            <strong>{test_data.get('name', test_name)}</strong>: {test_status}
            <br><small>{test_data.get('details', '')}</small>
        </div>
"""

        html_content += """
    </div>
"""

    html_content += """
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html_content)

def main():
    """Main report generator"""
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <test_results.json>")
        sys.exit(1)

    results_file = sys.argv[1]

    if not Path(results_file).exists():
        print(f"Results file not found: {results_file}")
        sys.exit(1)

    with open(results_file, 'r') as f:
        test_results = json.load(f)

    # Generate HTML report
    html_path = results_file.replace('.json', '.html')
    generate_html_report(test_results, html_path)

    print(f"✅ HTML report generated: {html_path}")

if __name__ == "__main__":
    main()
'''

        with open(script_path, "w") as f:
            f.write(generator_content)

        # Make executable
        script_path.chmod(0o755)

    def _create_env_config_tool(self, script_path: Path):
        """Create environment configuration tool"""
        config_content = f'''#!/usr/bin/env python3
"""
Environment Configuration Tool

Configures the .env file for KME system operation.
"""

import os
import sys
import secrets
import string
from pathlib import Path
from cryptography.fernet import Fernet

def generate_secure_key() -> str:
    """Generate a secure Fernet key"""
    return Fernet.generate_key().decode()

def generate_kme_id() -> str:
    """Generate a KME ID"""
    # Generate 16-character alphanumeric ID
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(16))

def get_user_input(prompt: str, default: str = None, required: bool = True) -> str:
    """Get user input with default value support"""
    if default:
        prompt = f"{{prompt}} (default: {{default}}): "
    else:
        prompt = f"{{prompt}}: "

    while True:
        value = input(prompt).strip()
        if value:
            return value
        elif default and not required:
            return default
        elif not required:
            return ""
        else:
            print("This field is required. Please enter a value.")

def configure_environment():
    """Configure the environment file"""
    env_file = Path(".env")

    print("🔧 KME Environment Configuration")
    print("=" * 40)

    # Check if .env already exists
    if env_file.exists():
        print("⚠️  .env file already exists.")
        overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Configuration cancelled.")
            return False

    # Database configuration
    print("\\n📊 Database Configuration:")
    db_host = get_user_input("Database host", "localhost")
    db_port = get_user_input("Database port", "5432")
    db_name = get_user_input("Database name", "kme_db")
    db_user = get_user_input("Database user", "krich")
                db_password = get_user_input("Database password", credentials.get_postgres_password())

    # KME configuration
    print("\\n🔑 KME Configuration:")
    kme_id = get_user_input("KME ID", generate_kme_id())

    # Generate secure master key
    master_key = generate_secure_key()
    print(f"Generated secure master key: {{master_key[:20]}}...")

    # Server configuration
    print("\\n🌐 Server Configuration:")
    server_host = get_user_input("Server host", "0.0.0.0")
    server_port = get_user_input("Server port", "8000")

    # Logging configuration
    print("\\n📝 Logging Configuration:")
    log_level = get_user_input("Log level", "INFO", required=False)

    # Security configuration
    print("\\n🔒 Security Configuration:")
    enable_debug = get_user_input("Enable debug mode", "false", required=False).lower() == 'true'

    # Build environment content
    env_content = f"""# KME Environment Configuration
# Generated by KME Test Environment Installer

# Database Configuration
DATABASE_URL=postgresql+asyncpg://{{db_user}}:{{db_password}}@{{db_host}}:{{db_port}}/{{db_name}}
POSTGRES_HOST={{db_host}}
POSTGRES_PORT={{db_port}}
POSTGRES_DB={{db_name}}
POSTGRES_USER={{db_user}}
POSTGRES_PASSWORD={{db_password}}

# KME Configuration
KME_ID={{kme_id}}
KME_MASTER_KEY={{master_key}}

# Server Configuration
HOST={{server_host}}
PORT={{server_port}}

# Logging Configuration
LOG_LEVEL={{log_level or 'INFO'}}

# Security Configuration
DEBUG={{str(enable_debug).lower()}}

# Test Configuration
TESTING=false
"""

    # Write .env file
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)

        print(f"\\n✅ Environment configuration saved to: {{env_file}}")
        print("\\n📋 Configuration Summary:")
        print(f"  Database: {{db_user}}@{{db_host}}:{{db_port}}/{{db_name}}")
        print(f"  KME ID: {{kme_id}}")
        print(f"  Server: {{server_host}}:{{server_port}}")
        print(f"  Log Level: {{log_level or 'INFO'}}")
        print(f"  Debug Mode: {{enable_debug}}")

        return True

    except Exception as e:
        print(f"❌ Failed to write .env file: {{e}}")
        return False

def validate_environment():
    """Validate the current environment configuration"""
    env_file = Path(".env")

    if not env_file.exists():
        print("❌ .env file not found")
        return False

    print("🔍 Validating environment configuration...")

    # Load environment variables
    with open(env_file, 'r') as f:
        env_content = f.read()

    # Check for required variables
    required_vars = [
        'DATABASE_URL',
        'KME_ID',
        'KME_MASTER_KEY',
        'HOST',
        'PORT'
    ]

    missing_vars = []
    for var in required_vars:
        if f"{{var}}=" not in env_content:
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {{', '.join(missing_vars)}}")
        return False

    print("✅ Environment configuration is valid")
    return True

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python env_config.py [configure|validate]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "configure":
        success = configure_environment()
    elif command == "validate":
        success = validate_environment()
    else:
        print("Unknown command. Use 'configure' or 'validate'")
        sys.exit(1)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

        with open(script_path, "w") as f:
            f.write(config_content)

        # Make executable
        script_path.chmod(0o755)

    def _configure_nginx_for_kme(self) -> bool:
        """Configure nginx for KME system"""
        try:
            # Check if KME certificates exist
            kme_cert = self.project_root / "admin" / "kme_cert.pem"
            kme_key = self.project_root / "admin" / "kme_key.pem"

            if not kme_cert.exists() or not kme_key.exists():
                self.log("KME certificates not found - generating them first...")

                # Generate CA and KME certificates
                ca_script = self.paths["scripts_dir"] / "generate_ca.py"
                if not self.run_command(
                    ["python", str(ca_script), "ca"], "Generate CA"
                ):
                    return False

                # Use the determined KME ID for certificate generation
                if not self.kme_id:
                    self.log(
                        "❌ KME ID not determined. Run determine_kme_id() first.",
                        "ERROR",
                    )
                    return False

                if not self.run_command(
                    ["python", str(ca_script), "kme", self.kme_id],
                    "Generate KME certificate",
                ):
                    return False

            # Use the proper nginx installer to install to /etc/nginx/sites-available/
            self.log(
                "Installing KME nginx configuration to /etc/nginx/sites-available/..."
            )
            nginx_installer = self.paths["scripts_dir"] / "nginx_installer.py"

            if not self.run_command(
                ["python", str(nginx_installer), str(kme_cert), str(kme_key)],
                "Install KME nginx configuration",
            ):
                return False

            self.log(
                "✅ KME nginx configuration installed to /etc/nginx/sites-available/kme"
            )
            self.log("  Configuration: /etc/nginx/sites-available/kme")
            self.log("  Enabled: /etc/nginx/sites-enabled/kme")

            return True

        except Exception as e:
            self.log(f"Failed to configure nginx for KME: {e}", "ERROR")
            return False

    def _configure_environment_defaults(self) -> bool:
        """Configure environment with default values"""
        try:
            from credentials import credentials
            from cryptography.fernet import Fernet

            env_file = self.project_root / ".env"

            # Generate secure master key
            master_key = Fernet.generate_key().decode()

            # Use the determined KME ID
            if not self.kme_id:
                self.log(
                    "❌ KME ID not determined. Run determine_kme_id() first.", "ERROR"
                )
                return False

            # Build environment content with defaults
            env_content = f"""# KME Environment Configuration
# Generated by KME Test Environment Installer

# Database Configuration
DATABASE_URL={credentials.get_database_url()}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=kme_db
POSTGRES_USER={credentials.get_postgres_user()}
POSTGRES_PASSWORD={credentials.get_postgres_password()}

# KME Configuration
KME_ID={self.kme_id}
KME_MASTER_KEY={master_key}

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Logging Configuration
LOG_LEVEL=INFO

# Security Configuration
DEBUG=false

# Test Configuration
TESTING=false
"""

            # Write .env file
            with open(env_file, "w") as f:
                f.write(env_content)

            self.log(f"✅ Environment configuration created: {env_file}")
            self.log(f"  KME ID: {self.kme_id}")
            self.log(f"  Master Key: {master_key[:20]}...")

            return True

        except Exception as e:
            self.log(f"Failed to configure environment: {e}", "ERROR")
            return False

    def validate_environment(self) -> bool:
        """Validate the installed environment for KME system use or further testing"""
        try:
            self.log("")
            self.log("🔍 VALIDATING COMPLETE ENVIRONMENT")
            self.log("=" * 60)
            self.log("")

            # Phase 1: Check if all installer-created tools are available
            self.log("📋 PHASE 1: Validating installer-created tools...")
            self.log("-" * 40)
            tools = [
                ("CA Generation", self.paths["scripts_dir"] / "generate_ca.py"),
                (
                    "Certificate Validator",
                    self.paths["scripts_dir"] / "certificate_validator.py",
                ),
                ("Database Setup", self.paths["scripts_dir"] / "database_setup.py"),
                (
                    "Database Validator",
                    self.paths["scripts_dir"] / "database_validator.py",
                ),
                (
                    "Nginx Generator",
                    self.paths["scripts_dir"] / "nginx_config_generator.py",
                ),
                ("Nginx Validator", self.paths["scripts_dir"] / "nginx_validator.py"),
                ("Nginx Installer", self.paths["scripts_dir"] / "nginx_installer.py"),
                ("Test Runner", self.paths["scripts_dir"] / "test_runner.py"),
                (
                    "Environment Validator",
                    self.paths["scripts_dir"] / "environment_validator.py",
                ),
                ("Report Generator", self.paths["scripts_dir"] / "report_generator.py"),
                ("Environment Config", self.paths["scripts_dir"] / "env_config.py"),
            ]

            all_tools_available = True
            for tool_name, tool_path in tools:
                if tool_path.exists():
                    self.log(f"✅ {tool_name}: {tool_path}")
                else:
                    self.log(f"❌ {tool_name}: {tool_path} (missing)", "ERROR")
                    all_tools_available = False

            if not all_tools_available:
                self.log("Some installer tools are missing", "ERROR")
                return False

            # Phase 2: Validate basic system requirements
            self.log("")
            self.log("🔧 PHASE 2: Validating system requirements...")
            self.log("-" * 40)
            env_validator = self.paths["scripts_dir"] / "environment_validator.py"
            if not self.run_command(
                ["python", str(env_validator)], "Test system requirements"
            ):
                self.log("System requirements validation failed", "ERROR")
                return False

            # Phase 3: Test CA and certificate functionality
            self.log("")
            self.log("🔐 PHASE 3: Validating CA and certificate functionality...")
            self.log("-" * 40)
            if not self._validate_ca_functionality():
                return False

            # Phase 4: Test database functionality
            self.log("")
            self.log("🗄️ PHASE 4: Validating database functionality...")
            self.log("-" * 40)
            if not self._validate_database_functionality():
                return False

            # Phase 5: Test nginx functionality
            self.log("")
            self.log("🌐 PHASE 5: Validating nginx functionality...")
            self.log("-" * 40)
            if not self._validate_nginx_functionality():
                return False

            # Phase 6: Test test infrastructure functionality
            self.log("")
            self.log("🧪 PHASE 6: Validating test infrastructure...")
            self.log("-" * 40)
            if not self._validate_test_infrastructure():
                return False

            # Phase 7: Validate KME system readiness
            self.log("")
            self.log("🎯 PHASE 7: Validating KME system readiness...")
            self.log("-" * 40)
            if not self._validate_kme_readiness():
                return False

            self.log("")
            self.log("=" * 60)
            self.log("✅ ENVIRONMENT VALIDATION COMPLETED SUCCESSFULLY")
            self.log(
                "🎯 Environment is ready for KME system use and comprehensive testing"
            )
            self.log("=" * 60)
            return True

        except Exception as e:
            self.log(f"Failed to validate environment: {e}", "ERROR")
            return False

    def _validate_ca_functionality(self) -> bool:
        """Validate CA and certificate functionality"""
        try:
            # Determine CA name if not already set
            if not self.ca_name and self.kme_id:
                self.ca_name = self._determine_ca_name()

            # Test CA generation
            ca_script = self.paths["scripts_dir"] / "generate_ca.py"
            if not self.run_command(
                ["python", str(ca_script), "ca", self.ca_name or "KME Root CA"],
                "Test CA generation",
            ):
                self.log("CA generation test failed", "ERROR")
                return False

            # Verify CA files were created
            ca_cert = self.paths["ca_dir"] / "ca.crt"
            ca_key = self.paths["ca_dir"] / "ca.key"

            if not ca_cert.exists() or not ca_key.exists():
                self.log("CA files not created after generation", "ERROR")
                return False

            # Test certificate validation
            cert_validator = self.paths["scripts_dir"] / "certificate_validator.py"
            if not self.run_command(
                ["python", str(cert_validator), str(ca_cert)],
                "Test certificate validation",
            ):
                self.log("Certificate validation test failed", "ERROR")
                return False

            # Test KME certificate generation with determined KME ID
            if not self.kme_id:
                self.log("❌ KME ID not determined for certificate validation", "ERROR")
                return False

            if not self.run_command(
                ["python", str(ca_script), "kme", self.kme_id],
                "Test KME certificate generation",
            ):
                self.log("KME certificate generation test failed", "ERROR")
                return False

            # Verify KME certificate files
            kme_cert = self.project_root / "admin" / "kme_cert.pem"
            kme_key = self.project_root / "admin" / "kme_key.pem"

            if not kme_cert.exists() or not kme_key.exists():
                self.log("KME certificate files not created", "ERROR")
                return False

            # Test certificate chain validation
            if not self.run_command(
                ["python", str(cert_validator), str(kme_cert), str(ca_cert)],
                "Test certificate chain validation",
            ):
                self.log("Certificate chain validation test failed", "ERROR")
                return False

            self.log("✅ CA and certificate functionality validated")
            return True

        except Exception as e:
            self.log(f"Failed to validate CA functionality: {e}", "ERROR")
            return False

    def _validate_database_functionality(self) -> bool:
        """Validate database functionality"""
        try:
            # Test database connection
            db_validator = self.paths["scripts_dir"] / "database_validator.py"
            if not self.run_command(
                ["python", str(db_validator), "test"], "Test database connection"
            ):
                self.log("Database connection test failed", "ERROR")
                return False

            # Test database setup
            db_setup = self.paths["scripts_dir"] / "database_setup.py"
            if not self.run_command(
                ["python", str(db_setup), "setup"], "Test database setup"
            ):
                self.log("Database setup test failed", "ERROR")
                return False

            self.log("✅ Database functionality validated")
            return True

        except Exception as e:
            self.log(f"Failed to validate database functionality: {e}", "ERROR")
            return False

    def _validate_nginx_functionality(self) -> bool:
        """Validate nginx functionality"""
        try:
            # Test nginx configuration generation
            nginx_gen = self.paths["scripts_dir"] / "nginx_config_generator.py"
            kme_cert = self.project_root / "admin" / "kme_cert.pem"
            kme_key = self.project_root / "admin" / "kme_key.pem"

            if not kme_cert.exists() or not kme_key.exists():
                self.log("KME certificates not found for nginx test", "ERROR")
                return False

            if not self.run_command(
                [
                    "python",
                    str(nginx_gen),
                    str(kme_cert),
                    str(kme_key),
                    "test_nginx.conf",
                ],
                "Test nginx configuration generation",
            ):
                self.log("Nginx configuration generation test failed", "ERROR")
                return False

            # Test nginx configuration validation (skip if nginx not available)
            nginx_validator = self.paths["scripts_dir"] / "nginx_validator.py"
            test_config = self.project_root / "test_nginx.conf"

            if test_config.exists():
                # Check if nginx is available
                try:
                    result = subprocess.run(
                        ["nginx", "-v"], capture_output=True, text=True, timeout=5
                    )
                    nginx_available = result.returncode == 0
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    nginx_available = False

                if nginx_available:
                    if not self.run_command(
                        ["python", str(nginx_validator), str(test_config)],
                        "Test nginx configuration validation",
                    ):
                        self.log("Nginx configuration validation test failed", "ERROR")
                        return False
                else:
                    self.log(
                        "⚠️ Nginx not available - skipping configuration validation",
                        "WARNING",
                    )

                # Clean up test file
                test_config.unlink()

            # Test nginx service status (if nginx is installed)
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", "nginx"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    nginx_status = result.stdout.strip()
                    if nginx_status == "active":
                        self.log("✅ Nginx service is running")
                    else:
                        self.log(f"⚠️ Nginx service status: {nginx_status}", "WARNING")
                else:
                    self.log("⚠️ Nginx service not found or not running", "WARNING")
            except Exception:
                self.log("⚠️ Could not check nginx service status", "WARNING")

            self.log("✅ Nginx functionality validated")
            return True

        except Exception as e:
            self.log(f"Failed to validate nginx functionality: {e}", "ERROR")
            return False

    def _validate_test_infrastructure(self) -> bool:
        """Validate test infrastructure functionality"""
        try:
            # Test report generator
            report_gen = self.paths["scripts_dir"] / "report_generator.py"

            # Create a simple test result for validation
            test_result = {
                "test_run": {
                    "timestamp": "2025-08-06T19:00:00Z",
                    "overall_status": "PASSED",
                },
                "stages": {
                    "test_stage": {
                        "name": "Test Stage",
                        "status": "PASSED",
                        "tests": {
                            "test1": {
                                "name": "Test 1",
                                "status": "PASSED",
                                "details": "Test passed successfully",
                            }
                        },
                    }
                },
            }

            test_result_file = self.paths["results_dir"] / "test_validation.json"
            with open(test_result_file, "w") as f:
                json.dump(test_result, f, indent=2)

            if not self.run_command(
                ["python", str(report_gen), str(test_result_file)],
                "Test report generation",
            ):
                self.log("Report generation test failed", "ERROR")
                return False

            # Clean up test file
            test_result_file.unlink()

            self.log("✅ Test infrastructure validated")
            return True

        except Exception as e:
            self.log(f"Failed to validate test infrastructure: {e}", "ERROR")
            return False

    def _validate_kme_readiness(self) -> bool:
        """Validate KME system readiness"""
        try:
            # Check for required KME system components
            kme_components = [
                ("KME Application", self.project_root / "main.py"),
                ("KME API Routes", self.project_root / "app" / "api" / "routes.py"),
                ("KME Core Config", self.project_root / "app" / "core" / "config.py"),
                (
                    "KME Key Service",
                    self.project_root / "app" / "services" / "key_service.py",
                ),
                (
                    "KME Database Models",
                    self.project_root / "app" / "models" / "database_models.py",
                ),
            ]

            all_components_present = True
            for component_name, component_path in kme_components:
                if component_path.exists():
                    self.log(f"✅ {component_name}: {component_path}")
                else:
                    self.log(f"❌ {component_name}: {component_path} (missing)", "ERROR")
                    all_components_present = False

            if not all_components_present:
                self.log("Some KME system components are missing", "ERROR")
                return False

            # Check for required directories
            required_dirs = [
                ("Admin Directory", self.project_root / "admin"),
                ("App Directory", self.project_root / "app"),
                ("Test Directory", self.project_root / "test"),
            ]

            for dir_name, dir_path in required_dirs:
                if dir_path.exists() and dir_path.is_dir():
                    self.log(f"✅ {dir_name}: {dir_path}")
                else:
                    self.log(f"❌ {dir_name}: {dir_path} (missing)", "ERROR")
                    all_components_present = False

            # Check for environment configuration
            env_file = self.project_root / ".env"
            if env_file.exists():
                self.log(f"✅ Environment file: {env_file}")

                # Validate environment configuration
                env_config_tool = self.paths["scripts_dir"] / "env_config.py"
                if env_config_tool.exists():
                    if self.run_command(
                        ["python", str(env_config_tool), "validate"],
                        "Validate environment configuration",
                    ):
                        self.log("Environment configuration is valid")
                    else:
                        self.log("Environment configuration validation failed", "ERROR")
                        all_components_present = False
            else:
                self.log(
                    f"⚠️ Environment file: {env_file} (not found - will be created during configuration)",
                    "WARNING",
                )

            # Check for requirements
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                self.log(f"✅ Requirements file: {requirements_file}")
            else:
                self.log(f"❌ Requirements file: {requirements_file} (missing)", "ERROR")
                all_components_present = False

            if not all_components_present:
                self.log("KME system is not ready for use", "ERROR")
                return False

            self.log("✅ KME system readiness validated")
            return True

        except Exception as e:
            self.log(f"Failed to validate KME readiness: {e}", "ERROR")
            return False

    def _generate_installation_summary(self):
        """Generate comprehensive installation summary"""
        try:
            self.log("")
            self.log("=" * 80)
            self.log("🎯 KME TEST ENVIRONMENT INSTALLATION SUMMARY")
            self.log("=" * 80)

            # Project structure
            self.log("")
            self.log("📁 PROJECT STRUCTURE:")
            self.log(f"  Project Root: {self.project_root}")
            self.log(f"  Test Directory: {self.project_root / 'test'}")
            self.log(f"  Scripts Directory: {self.paths['scripts_dir']}")
            self.log(f"  Data Directory: {self.paths['data_dir']}")
            self.log(f"  Logs Directory: {self.paths['logs_dir']}")
            self.log(f"  Results Directory: {self.paths['results_dir']}")

            # Installed tools
            self.log("")
            self.log("🔧 INSTALLED TOOLS:")
            tools = [
                ("CA Generation", "generate_ca.py"),
                ("Certificate Validator", "certificate_validator.py"),
                ("Database Setup", "database_setup.py"),
                ("Database Validator", "database_validator.py"),
                ("Nginx Generator", "nginx_config_generator.py"),
                ("Nginx Validator", "nginx_validator.py"),
                ("Nginx Installer", "nginx_installer.py"),
                ("Test Runner", "test_runner.py"),
                ("Environment Validator", "environment_validator.py"),
                ("Report Generator", "report_generator.py"),
                ("Environment Config", "env_config.py"),
            ]

            for tool_name, tool_file in tools:
                tool_path = self.paths["scripts_dir"] / tool_file
                if tool_path.exists():
                    self.log(f"  ✅ {tool_name}: {tool_path}")
                else:
                    self.log(f"  ❌ {tool_name}: {tool_path} (missing)")

            # Generated files
            self.log("")
            self.log("📄 GENERATED FILES:")

            # Environment configuration
            env_file = self.project_root / ".env"
            if env_file.exists():
                self.log(f"  ✅ Environment Configuration: {env_file}")
                # Read and display key values
                try:
                    with open(env_file) as f:
                        env_content = f.read()
                        for line in env_content.split("\n"):
                            if line.startswith("KME_ID="):
                                kme_id = line.split("=")[1]
                                self.log(f"    KME ID: {kme_id}")
                            elif line.startswith("KME_MASTER_KEY="):
                                master_key = line.split("=")[1][:20] + "..."
                                self.log(f"    Master Key: {master_key}")
                            elif line.startswith("DATABASE_URL="):
                                db_url = line.split("=")[1]
                                self.log(f"    Database: {db_url}")
                except Exception:
                    pass

            # CA and certificates
            ca_dir = self.project_root / "admin" / "ca"
            if ca_dir.exists():
                ca_cert = ca_dir / "ca.crt"
                ca_key = ca_dir / "ca.key"
                if ca_cert.exists() and ca_key.exists():
                    self.log(f"  ✅ CA Certificate: {ca_cert}")
                    self.log(f"  ✅ CA Private Key: {ca_key}")

            kme_cert = self.project_root / "admin" / "kme_cert.pem"
            kme_key = self.project_root / "admin" / "kme_key.pem"
            if kme_cert.exists() and kme_key.exists():
                self.log(f"  ✅ KME Certificate: {kme_cert}")
                self.log(f"  ✅ KME Private Key: {kme_key}")

            # Nginx configuration
            nginx_conf = self.project_root / "kme_nginx.conf"
            if nginx_conf.exists():
                self.log(f"  ✅ Nginx Configuration: {nginx_conf}")

            # Log files
            log_files = list(self.paths["logs_dir"].glob("*.txt"))
            if log_files:
                self.log(f"  ✅ Installation Logs: {len(log_files)} files")
                for log_file in log_files[-3:]:  # Show last 3 logs
                    self.log(f"    - {log_file.name}")

            # System requirements
            self.log("")
            self.log("🔍 SYSTEM REQUIREMENTS:")
            try:
                # Python version
                import sys

                self.log(f"  ✅ Python: {sys.version.split()[0]}")

                # Check other tools
                import subprocess

                tools_to_check = [
                    ("OpenSSL", ["openssl", "version"]),
                    ("PostgreSQL", ["psql", "--version"]),
                    ("Nginx", ["nginx", "-v"]),
                ]

                for tool_name, cmd in tools_to_check:
                    try:
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            version = result.stdout.strip().split("\n")[0]
                            self.log(f"  ✅ {tool_name}: {version}")
                        else:
                            self.log(f"  ❌ {tool_name}: Not available")
                    except Exception:
                        self.log(f"  ❌ {tool_name}: Not available")

            except Exception as e:
                self.log(f"  ⚠️ Could not verify all system requirements: {e}")

            # Usage instructions
            self.log("")
            self.log("🚀 USAGE INSTRUCTIONS:")
            self.log("")
            self.log("1. Start KME Service:")
            self.log(f"   cd {self.project_root}")
            self.log("   source venv/bin/activate")
            self.log("   python main.py")
            self.log("")
            self.log("2. Test with Nginx (Local):")
            self.log(f"   nginx -c {self.project_root}/kme_nginx.conf")
            self.log("   # Access KME at https://localhost")
            self.log("")
            self.log("3. Run Tests:")
            self.log(f"   python {self.paths['scripts_dir']}/test_runner.py")
            self.log("")
            self.log("4. Validate Environment:")
            self.log(f"   python {self.paths['scripts_dir']}/installer.py validate")
            self.log("")
            self.log("5. System Nginx Installation (requires sudo):")
            self.log(
                f"   sudo python {self.paths['scripts_dir']}/nginx_installer.py certs/kme_cert.pem certs/kme_key.pem"
            )

            # Security notes
            self.log("")
            self.log("🔒 SECURITY NOTES:")
            self.log("  - KME certificates and keys are stored in certs/ directory")
            self.log("  - Master key is stored in .env file")
            self.log("  - Database credentials are in .env file")
            self.log("  - Keep these files secure and do not commit to version control")
            self.log("  - Consider using environment variables for production")

            # Next steps
            self.log("")
            self.log("📋 NEXT STEPS:")
            self.log("  1. Review the generated configuration files")
            self.log("  2. Start the KME service for testing")
            self.log("  3. Run the comprehensive test suite")
            self.log("  4. Configure nginx for production use if needed")
            self.log("  5. Set up monitoring and logging")

            self.log("")
            self.log("=" * 80)
            self.log("✅ KME Test Environment Installation Complete!")
            self.log("=" * 80)
            self.log("")

        except Exception as e:
            self.log(f"Failed to generate installation summary: {e}", "ERROR")

    def _generate_component_summary(self, component: str):
        """Generate component-specific installation summary"""
        try:
            self.log("")
            self.log("=" * 60)
            self.log(f"🎯 {component.upper()} INSTALLATION SUMMARY")
            self.log("=" * 60)

            if component == "ca":
                self.log("")
                self.log("📄 GENERATED FILES:")
                ca_dir = self.project_root / "admin" / "ca"
                if ca_dir.exists():
                    ca_cert = ca_dir / "ca.crt"
                    ca_key = ca_dir / "ca.key"
                    if ca_cert.exists() and ca_key.exists():
                        self.log(f"  ✅ CA Certificate: {ca_cert}")
                        self.log(f"  ✅ CA Private Key: {ca_key}")

                kme_cert = self.project_root / "admin" / "kme_cert.pem"
                kme_key = self.project_root / "admin" / "kme_key.pem"
                if kme_cert.exists() and kme_key.exists():
                    self.log(f"  ✅ KME Certificate: {kme_cert}")
                    self.log(f"  ✅ KME Private Key: {kme_key}")

                self.log("")
                self.log("🔧 INSTALLED TOOLS:")
                self.log(
                    f"  ✅ CA Generation: {self.paths['scripts_dir']}/generate_ca.py"
                )
                self.log(
                    f"  ✅ Certificate Validator: {self.paths['scripts_dir']}/certificate_validator.py"
                )

            elif component == "database":
                self.log("")
                self.log("🔧 INSTALLED TOOLS:")
                self.log(
                    f"  ✅ Database Setup: {self.paths['scripts_dir']}/database_setup.py"
                )
                self.log(
                    f"  ✅ Database Validator: {self.paths['scripts_dir']}/database_validator.py"
                )

                self.log("")
                self.log("📊 DATABASE CONFIGURATION:")
                env_file = self.project_root / ".env"
                if env_file.exists():
                    try:
                        with open(env_file) as f:
                            env_content = f.read()
                            for line in env_content.split("\n"):
                                if line.startswith("DATABASE_URL="):
                                    db_url = line.split("=")[1]
                                    self.log(f"  ✅ Database URL: {db_url}")
                                    break
                    except Exception:
                        pass

            elif component == "nginx":
                self.log("")
                self.log("🔧 INSTALLED TOOLS:")
                self.log(
                    f"  ✅ Nginx Generator: {self.paths['scripts_dir']}/nginx_config_generator.py"
                )
                self.log(
                    f"  ✅ Nginx Validator: {self.paths['scripts_dir']}/nginx_validator.py"
                )
                self.log(
                    f"  ✅ Nginx Installer: {self.paths['scripts_dir']}/nginx_installer.py"
                )

                self.log("")
                self.log("📄 GENERATED FILES:")
                nginx_conf = self.project_root / "kme_nginx.conf"
                if nginx_conf.exists():
                    self.log(f"  ✅ Nginx Configuration: {nginx_conf}")

                self.log("")
                self.log("🚀 USAGE:")
                self.log("  Local testing: nginx -c kme_nginx.conf")
                self.log(
                    "  System install: sudo python test/scripts/nginx_installer.py certs/kme_cert.pem certs/kme_key.pem"
                )

            elif component == "utils":
                self.log("")
                self.log("🔧 INSTALLED TOOLS:")
                self.log(f"  ✅ Test Runner: {self.paths['scripts_dir']}/test_runner.py")
                self.log(
                    f"  ✅ Environment Validator: {self.paths['scripts_dir']}/environment_validator.py"
                )
                self.log(
                    f"  ✅ Report Generator: {self.paths['scripts_dir']}/report_generator.py"
                )

                self.log("")
                self.log("📁 CREATED DIRECTORIES:")
                self.log(f"  ✅ Test Data: {self.paths['data_dir']}")
                self.log(f"  ✅ Test Logs: {self.paths['logs_dir']}")
                self.log(f"  ✅ Test Results: {self.paths['results_dir']}")

            elif component == "env":
                self.log("")
                self.log("📄 GENERATED FILES:")
                env_file = self.project_root / ".env"
                if env_file.exists():
                    self.log(f"  ✅ Environment Configuration: {env_file}")

                    # Read and display key values
                    try:
                        with open(env_file) as f:
                            env_content = f.read()
                            for line in env_content.split("\n"):
                                if line.startswith("KME_ID="):
                                    kme_id = line.split("=")[1]
                                    self.log(f"    KME ID: {kme_id}")
                                elif line.startswith("KME_MASTER_KEY="):
                                    master_key = line.split("=")[1][:20] + "..."
                                    self.log(f"    Master Key: {master_key}")
                                elif line.startswith("DATABASE_URL="):
                                    db_url = line.split("=")[1]
                                    self.log(f"    Database: {db_url}")
                    except Exception:
                        pass

                self.log("")
                self.log("🔧 INSTALLED TOOLS:")
                self.log(
                    f"  ✅ Environment Config: {self.paths['scripts_dir']}/env_config.py"
                )

            self.log("")
            self.log("=" * 60)
            self.log(f"✅ {component.upper()} INSTALLATION COMPLETE!")
            self.log("=" * 60)
            self.log("")

        except Exception as e:
            self.log(f"Failed to generate component summary: {e}", "ERROR")

    def install_all(self) -> bool:
        """Install all components"""
        try:
            self.log("")
            self.log("=" * 80)
            self.log("🚀 STARTING KME TEST ENVIRONMENT INSTALLATION")
            self.log("=" * 80)
            self.log("")

            # Create directories
            self.log("📁 STEP 1: Creating Directory Structure")
            self.log("-" * 50)
            if not self.create_directories():
                return False
            self.log("✅ Directory structure created successfully")
            self.log("")

            # Determine KME ID early (if not already determined)
            if not self.kme_id:
                self.log("🆔 STEP 2: Determining KME ID")
                self.log("-" * 50)
                if not self.determine_kme_id(interactive=False):
                    return False
                self.log("✅ KME ID determined successfully")
            else:
                self.log("🆔 STEP 2: KME ID Already Determined")
                self.log("-" * 50)
                self.log(f"✅ Using existing KME ID: {self.kme_id}")
            self.log("")

            # Install components
            components = [
                ("CA Tools", self.install_ca_tools),
                ("Database Tools", self.install_database_tools),
                ("Nginx Tools", self.install_nginx_tools),
                ("Test Utils", self.install_test_utils),
                ("Environment Configuration", self.install_env_config),
            ]

            for i, (component_name, install_func) in enumerate(components, 3):
                self.log("")
                self.log(f"🔧 STEP {i}: Installing {component_name}")
                self.log("-" * 50)
                if not install_func():
                    self.log(f"❌ Failed to install {component_name}", "ERROR")
                    return False
                self.log(f"✅ {component_name} installed successfully")

            # Validate installation
            self.log("")
            self.log("🔍 STEP 8: Validating Complete Installation")
            self.log("-" * 50)
            if not self.validate_environment():
                return False

            self.log("")
            self.log("=" * 80)
            self.log("✅ ALL COMPONENTS INSTALLED SUCCESSFULLY")
            self.log("=" * 80)
            self.log("")

            # Generate installation summary
            self._generate_installation_summary()

            return True

        except Exception as e:
            self.log(f"Failed to install all components: {e}", "ERROR")
            return False

    def save_install_log(self):
        """Save installation log"""
        log_file = (
            self.paths["logs_dir"]
            / f"install_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        with open(log_file, "w") as f:
            for entry in self.install_log:
                f.write(entry + "\n")

        self.log(f"Installation log saved to: {log_file}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python installer.py [component] [--interactive]")
        print("Components: all, ca, database, nginx, utils, env, validate")
        print("Options:")
        print("  --interactive    Enable interactive mode for KME ID input")
        sys.exit(1)

    component = sys.argv[1]
    interactive = "--interactive" in sys.argv

    installer = KMEInstaller()

    try:
        if component == "all":
            # For all installation, determine KME ID first
            if interactive:
                if not installer.determine_kme_id(interactive=True):
                    sys.exit(1)
            # Note: install_all() will determine KME ID again if not already set
            success = installer.install_all()
        elif component == "ca":
            success = installer.install_ca_tools()
            if success:
                installer._generate_component_summary("ca")
        elif component == "database":
            success = installer.install_database_tools()
            if success:
                installer._generate_component_summary("database")
        elif component == "nginx":
            success = installer.install_nginx_tools()
            if success:
                installer._generate_component_summary("nginx")
        elif component == "utils":
            success = installer.install_test_utils()
            if success:
                installer._generate_component_summary("utils")
        elif component == "env":
            success = installer.install_env_config()
            if success:
                installer._generate_component_summary("env")
        elif component == "validate":
            success = installer.validate_environment()
        else:
            print(f"Unknown component: {component}")
            sys.exit(1)

        installer.save_install_log()

        if success:
            print("✅ Installation completed successfully")
            sys.exit(0)
        else:
            print("❌ Installation failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInstallation interrupted by user")
        installer.save_install_log()
        sys.exit(1)
    except Exception as e:
        print(f"Installation failed with exception: {e}")
        installer.save_install_log()
        sys.exit(1)


if __name__ == "__main__":
    main()
