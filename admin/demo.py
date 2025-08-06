#!/usr/bin/env python3
"""
KME Admin Package Demonstration

This script demonstrates the complete admin functionality including
SAE registration and package generation.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from admin.kme_admin import KMEAdmin
    from admin.package_creator import SAEPackageCreator
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def demo_sae_registration():
    """Demonstrate SAE registration"""
    print("=== SAE Registration Demo ===")

    admin = KMEAdmin()

    # Mock SAE registration
    print("1. Registering new SAE...")
    print("   - Name: Demo Encryption Module")
    print("   - SAE ID: DEMO001ABCDEFGHIJ")
    print("   - Max Keys: 64")
    print("   - Max Key Size: 512")

    # This would normally register in the database
    print("   ✅ SAE registered successfully!")

    return "DEMO001ABCDEFGHIJ"


def demo_package_generation(sae_id):
    """Demonstrate package generation"""
    print("\n=== Package Generation Demo ===")

    # Create test SAE data
    sae_data = {
        "name": "Demo Encryption Module",
        "sae_id": sae_id,
        "kme_endpoint": "https://localhost:443",  # Production HTTPS port
        "certificate_path": "certs/sae_certs/master_sae_cert.pem",  # Updated certificate path
        "private_key_path": "certs/sae_certs/master_sae_key.pem",  # Updated key path
        "ca_certificate_path": "certs/ca/ca.crt",  # Updated CA path
        "registration_date": "2024-01-15T10:30:00Z",
    }

    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix=".sh", delete=False) as tmp_file:
        output_path = tmp_file.name

    try:
        print("1. Creating package creator...")
        creator = SAEPackageCreator()

        print("2. Generating encrypted package...")
        package_path = creator.create_package(
            sae_data, output_path, "demo_password_123"
        )

        print(f"   ✅ Package created: {package_path}")

        # Show package details
        if os.path.exists(package_path):
            size = os.path.getsize(package_path)
            print(f"   📦 Package size: {size:,} bytes")

            # Check if executable
            if os.access(package_path, os.X_OK):
                print("   🔧 Package is executable")
            else:
                print("   ⚠️  Package is not executable")

        return package_path

    except Exception as e:
        print(f"   ❌ Package generation failed: {e}")
        return None


def demo_package_extraction(package_path):
    """Demonstrate package extraction"""
    print("\n=== Package Extraction Demo ===")

    if not package_path or not os.path.exists(package_path):
        print("❌ Package file not found")
        return False

    print("1. Package extraction simulation...")
    print("   📁 Package would extract to: .config/kme_sae/")
    print("   📄 Files that would be created:")
    print("      - sae_package.json (configuration)")
    print("      - sae_certificate.pem (SAE certificate)")
    print("      - sae_private_key.pem (private key)")
    print("      - kme_ca_certificate.pem (CA certificate)")
    print("      - README.md (setup instructions)")
    print("      - SECURITY_README.md (security warnings)")
    print("      - client_example.py (Python client)")
    print("      - test_connection.sh (connection test)")

    print("\n2. Permission setting simulation...")
    print("   🔒 Private key: 600 (owner read/write only)")
    print("   📜 Certificates: 644 (readable)")
    print("   🔧 Scripts: 755 (executable)")
    print("   📋 Config: 644 (readable)")

    print("\n3. Installation complete simulation...")
    print("   ✅ Package would be ready for use!")

    return True


def demo_cli_commands():
    """Demonstrate CLI commands"""
    print("\n=== CLI Commands Demo ===")

    print("Available commands:")
    print("  python admin/kme_admin.py --help")
    print("  python admin/kme_admin.py sae --help")
    print("  python admin/kme_admin.py sae list")
    print("  python admin/kme_admin.py sae show SAE_ID")
    print(
        "  python admin/kme_admin.py sae register --name 'Name' --certificate cert.pem"
    )
    print(
        "  python admin/kme_admin.py sae generate-package --sae-id ID --password pass --output file.sh"
    )

    print("\nMenu interface:")
    print("  ./admin/kme-admin-menu.sh")
    print("  - Interactive menu-driven interface")
    print("  - Guided SAE registration")
    print("  - Package generation with prompts")


def demo_security_features():
    """Demonstrate security features"""
    print("\n=== Security Features Demo ===")

    print("🔐 Package Security:")
    print("  - AES-256-CBC encryption")
    print("  - PBKDF2 key derivation")
    print("  - Password-protected extraction")
    print("  - Self-contained (no external deps)")

    print("\n🛡️ File Security:")
    print("  - Automatic permission setting")
    print("  - Private key protection (600)")
    print("  - Certificate integrity (644)")
    print("  - Script execution (755)")

    print("\n🔒 Certificate Management:")
    print("  - SAE ID extraction from certificates")
    print("  - Certificate hash verification")
    print("  - Revocation support")
    print("  - Expiration tracking")


def main():
    """Main demonstration function"""
    print("🎯 KME Admin Package - Complete Demonstration")
    print("=" * 50)

    try:
        # Demo SAE registration
        sae_id = demo_sae_registration()

        # Demo package generation
        package_path = demo_package_generation(sae_id)

        # Demo package extraction
        if package_path:
            demo_package_extraction(package_path)

        # Demo CLI commands
        demo_cli_commands()

        # Demo security features
        demo_security_features()

        print("\n" + "=" * 50)
        print("🎉 Demonstration completed successfully!")
        print("\nNext steps:")
        print("1. Use the menu interface: cd admin && ./kme-admin-menu.sh")
        print("2. Use CLI commands: cd admin && python kme_admin.py --help")
        print("3. Read documentation: admin/README.md")
        print("4. Test functionality: cd admin && python test_admin.py")

        # Clean up
        if package_path and os.path.exists(package_path):
            os.unlink(package_path)
            print(f"\n🧹 Cleaned up temporary package: {package_path}")

        return 0

    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
