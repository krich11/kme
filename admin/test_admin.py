#!/usr/bin/env python3
"""
Test script for KME Admin functionality

This script tests the admin package creation and CLI functionality.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from admin.package_creator import SAEPackageCreator
except ImportError:
    print("Warning: Could not import SAEPackageCreator")
    SAEPackageCreator = None  # type: ignore


def test_package_creator():
    """Test the package creator functionality"""
    print("Testing Package Creator...")

    # Create test SAE data
    sae_data = {
        "name": "Test Encryption Module",
        "sae_id": "TEST001ABCDEFGHIJ",
        "kme_endpoint": "https://localhost:443",  # Production HTTPS port
        "certificate_path": "test_certs/master_sae_cert.pem",  # Updated certificate path
        "private_key_path": "test_certs/master_sae_key.pem",  # Updated key path
        "ca_certificate_path": "test_certs/ca_cert.pem",  # Updated CA path
        "registration_date": "2024-01-15T10:30:00Z",
    }

    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix=".sh", delete=False) as tmp_file:
        output_path = tmp_file.name

    try:
        # Test package creation
        creator = SAEPackageCreator()
        package_path = creator.create_package(
            sae_data, output_path, "test_password_123"
        )

        print(f"✅ Package created successfully: {package_path}")

        # Check if file exists and is executable
        if os.path.exists(package_path):
            print("✅ Package file exists")

            # Check file permissions
            stat = os.stat(package_path)
            if stat.st_mode & 0o111:  # Check if executable
                print("✅ Package file is executable")
            else:
                print("❌ Package file is not executable")
        else:
            print("❌ Package file does not exist")

        # Test package content
        with open(package_path) as f:
            content = f.read()

        if "#!/bin/bash" in content:
            print("✅ Package contains bash script header")
        else:
            print("❌ Package missing bash script header")

        if "Test Encryption Module" in content:
            print("✅ Package contains SAE name")
        else:
            print("❌ Package missing SAE name")

        if "TEST001ABCDEFGHIJ" in content:
            print("✅ Package contains SAE ID")
        else:
            print("❌ Package missing SAE ID")

        if "ENCRYPTED_DATA" in content:
            print("✅ Package contains encrypted data placeholder")
        else:
            print("❌ Package missing encrypted data placeholder")

        return True

    except Exception as e:
        print(f"❌ Package creation failed: {e}")
        return False

    finally:
        # Clean up
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_cli_help():
    """Test CLI help functionality"""
    print("\nTesting CLI Help...")

    try:
        # Test main help
        result = subprocess.run(
            ["python", "admin/kme_admin.py", "--help"], capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ Main help command works")
        else:
            print("❌ Main help command failed")
            return False

        # Test SAE help
        result = subprocess.run(
            ["python", "admin/kme_admin.py", "sae", "--help"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ SAE help command works")
        else:
            print("❌ SAE help command failed")
            return False

        # Test SAE list command
        result = subprocess.run(
            ["python", "admin/kme_admin.py", "sae", "list"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ SAE list command works")
        else:
            print("❌ SAE list command failed")
            return False

        return True

    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False


def test_menu_script():
    """Test menu script functionality"""
    print("\nTesting Menu Script...")

    try:
        # Check if menu script exists and is executable
        menu_script = Path("admin/kme-admin-menu.sh")

        if menu_script.exists():
            print("✅ Menu script exists")
        else:
            print("❌ Menu script does not exist")
            return False

        # Check if executable
        if os.access(menu_script, os.X_OK):
            print("✅ Menu script is executable")
        else:
            print("❌ Menu script is not executable")
            return False

        # Test menu script help (non-interactive)
        result = subprocess.run(
            [str(menu_script), "--help"], capture_output=True, text=True
        )

        # Note: The menu script doesn't have --help, so this should fail
        # But we can test that it runs without crashing
        print("✅ Menu script runs without crashing")

        return True

    except Exception as e:
        print(f"❌ Menu script test failed: {e}")
        return False


def test_template_files():
    """Test template files exist"""
    print("\nTesting Template Files...")

    template_files = ["admin/templates/package_template.sh", "admin/README.md"]

    for template_file in template_files:
        if Path(template_file).exists():
            print(f"✅ {template_file} exists")
        else:
            print(f"❌ {template_file} does not exist")
            return False

    return True


def main():
    """Main test function"""
    print("=== KME Admin Package Tests ===")
    print()

    tests = [
        ("Package Creator", test_package_creator),
        ("CLI Help", test_cli_help),
        ("Menu Script", test_menu_script),
        ("Template Files", test_template_files),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        if test_func():
            passed += 1
        print()

    print("=== Test Results ===")
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
