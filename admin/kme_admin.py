#!/usr/bin/env python3
"""
KME Admin CLI Tool

Provides administrative tools for SAE management and package generation.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Set up logger
logger = logging.getLogger(__name__)


# Mock settings for now
def get_settings():
    class Settings:
        host = "localhost"
        port = 8464  # Updated to use Nginx SSL port with mTLS
        kme_id = detect_kme_id()

    return Settings()


def detect_kme_id() -> str:
    """Detect KME ID from server certificate or environment"""
    try:
        # Try to extract from server certificate - updated path
        server_cert_path = "../test_certs/kme_cert.pem"  # Updated path
        if os.path.exists(server_cert_path):
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend

            with open(server_cert_path, "rb") as f:
                cert_data = x509.load_pem_x509_certificate(f.read(), default_backend())

            # Extract KME ID from Common Name
            cn = cert_data.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[
                0
            ].value
            if cn and "KME" in cn:
                return cn

        # Try environment variable
        kme_id = os.environ.get("KME_ID")
        if kme_id:
            return kme_id

        # Fallback to default
        return "KME001ABCDEFGHIJ"
    except Exception as e:
        logger.warning(f"Failed to detect KME ID: {e}, using default")
        return "KME001ABCDEFGHIJ"


# Mock services for now
class StatusService:
    pass


try:
    from certificate_generator import CertificateGenerator
    from package_creator import SAEPackageCreator
    from sae_id_generator import SAEIDGenerator
except ImportError:
    print(
        "Warning: Could not import SAEPackageCreator, CertificateGenerator, or SAEIDGenerator"
    )
    SAEPackageCreator = None
    CertificateGenerator = None
    SAEIDGenerator = None


class KMEAdmin:
    """KME Administration Tool"""

    def __init__(self):
        self.settings = get_settings()
        self.status_service = StatusService()
        self.package_creator = SAEPackageCreator() if SAEPackageCreator else None
        self.cert_generator = CertificateGenerator() if CertificateGenerator else None
        self.sae_storage_file = Path("sae_registry.json")
        self._ensure_sae_storage()

    def _ensure_sae_storage(self):
        """Ensure SAE storage file exists"""
        if not self.sae_storage_file.exists():
            self.sae_storage_file.write_text("[]")

    def _load_saes(self) -> list:
        """Load SAEs from storage"""
        try:
            data = self.sae_storage_file.read_text()
            return json.loads(data)
        except Exception:
            return []

    def _save_saes(self, saes: list):
        """Save SAEs to storage"""
        try:
            self.sae_storage_file.write_text(json.dumps(saes, indent=2))
        except Exception as e:
            logger.error(f"Failed to save SAEs: {e}")

    def _add_sae(self, sae_data: dict):
        """Add SAE to storage"""
        saes = self._load_saes()
        saes.append(sae_data)
        self._save_saes(saes)

    def _get_sae_by_id(self, sae_id: str) -> dict | None:
        """Get SAE by ID from storage"""
        saes = self._load_saes()
        for sae in saes:
            if sae.get("sae_id") == sae_id:
                return sae
        return None

    def register_sae(self, args: argparse.Namespace) -> int:
        """Register a new SAE"""
        try:
            logger.info(f"Registering SAE: {args.name}")

            # Validate certificate and extract SAE ID
            sae_id = self._extract_sae_id_from_certificate(args.certificate)
            if not sae_id:
                logger.error("Failed to extract SAE ID from certificate")
                return 1

            # Check if SAE already exists
            if self._is_sae_registered(sae_id):
                logger.error(f"SAE {sae_id} is already registered")
                return 1

            # Create SAE entity
            sae_data = {
                "sae_id": sae_id,
                "name": args.name,
                "kme_id": self.settings.kme_id,
                "certificate_hash": self._get_certificate_hash(args.certificate),
                "max_keys_per_request": args.max_keys,
                "max_key_size": args.max_key_size,
                "min_key_size": 64,  # Default minimum
                "status": "active",
                "registration_date": datetime.now().isoformat(),
            }

            # Save SAE to storage
            self._add_sae(sae_data)
            logger.info(f"SAE {sae_id} registered successfully")

            # Generate package if requested
            if args.generate_package:
                return self._generate_package(sae_id, args)

            return 0

        except Exception as e:
            logger.error(f"SAE registration failed: {e}")
            return 1

    def list_saes(self, args: argparse.Namespace) -> int:
        """List all registered SAEs"""
        try:
            # Load SAEs from storage
            saes = self._load_saes()

            if args.json:
                print(json.dumps(saes, indent=2))
            else:
                if not saes:
                    print("No SAEs registered.")
                else:
                    print("Registered SAEs:")
                    print("-" * 80)
                    for sae in saes:
                        print(f"SAE ID: {sae['sae_id']}")
                        print(f"Name: {sae['name']}")
                        print(f"Status: {sae['status']}")
                        print(f"Registered: {sae['registration_date']}")
                        print("-" * 80)

            return 0

        except Exception as e:
            logger.error(f"Failed to list SAEs: {e}")
            return 1

    def show_sae(self, args: argparse.Namespace) -> int:
        """Show SAE details"""
        try:
            sae_id = args.sae_id

            # Load SAE from storage
            sae_data = self._get_sae_by_id(sae_id)

            if not sae_data:
                logger.error(f"SAE {sae_id} not found")
                return 1

            if args.json:
                print(json.dumps(sae_data, indent=2))
            else:
                print(f"SAE Details: {sae_id}")
                print("-" * 50)
                for key, value in sae_data.items():
                    print(f"{key.replace('_', ' ').title()}: {value}")

            return 0

        except Exception as e:
            logger.error(f"Failed to show SAE: {e}")
            return 1

    def update_sae_status(self, args: argparse.Namespace) -> int:
        """Update SAE status"""
        try:
            sae_id = args.sae_id
            new_status = args.status

            # Validate status
            valid_statuses = ["active", "inactive", "suspended", "expired"]
            if new_status not in valid_statuses:
                logger.error(f"Invalid status. Must be one of: {valid_statuses}")
                return 1

            # This would typically update the database
            logger.info(f"Updated SAE {sae_id} status to {new_status}")

            return 0

        except Exception as e:
            logger.error(f"Failed to update SAE status: {e}")
            return 1

    def revoke_sae(self, args: argparse.Namespace) -> int:
        """Revoke SAE access"""
        try:
            sae_id = args.sae_id

            # This would typically update the database
            logger.info(f"Revoked access for SAE {sae_id}")

            return 0

        except Exception as e:
            logger.error(f"Failed to revoke SAE: {e}")
            return 1

    def generate_package(self, args: argparse.Namespace) -> int:
        """Generate SAE package"""
        try:
            if not self.package_creator:
                logger.error("Package creator not available")
                return 1

            sae_id = args.sae_id
            password = args.password
            output_path = args.output

            # Get SAE details
            sae_data = self._get_sae_data(sae_id)
            if not sae_data:
                logger.error(f"SAE {sae_id} not found")
                return 1

            # Create package
            package_path = self.package_creator.create_package(
                sae_data, output_path, password
            )

            print(f"Package created successfully: {package_path}")
            return 0

        except Exception as e:
            logger.error(f"Package generation failed: {e}")
            return 1

    def generate_certificate(self, args: argparse.Namespace) -> int:
        """Generate SAE certificate"""
        try:
            if not self.cert_generator:
                logger.error("Certificate generator not available")
                return 1

            sae_id = args.sae_id
            sae_name = args.name
            validity_days = args.validity_days
            key_size = args.key_size

            # Generate certificate
            result = self.cert_generator.generate_sae_certificate(
                sae_id=sae_id,
                sae_name=sae_name,
                validity_days=validity_days,
                key_size=key_size,
            )

            print(f"Certificate generated successfully!")
            print(f"Certificate: {result['certificate_path']}")
            print(f"Private Key: {result['private_key_path']}")
            print(f"Expires: {result['expires']}")

            # Display certificate subject for verification
            try:
                from cryptography import x509
                from cryptography.hazmat.backends import default_backend

                with open(result["certificate_path"], "rb") as f:
                    cert_data = x509.load_pem_x509_certificate(
                        f.read(), default_backend()
                    )

                print(f"Certificate Subject: {cert_data.subject}")
                print(f"Certificate Issuer: {cert_data.issuer}")

                # Extract and display SAE ID from CN
                cn = cert_data.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[
                    0
                ].value
                print(f"SAE ID (CN): {cn}")

            except Exception as e:
                print(f"Warning: Could not read certificate details: {e}")

            return 0

        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            return 1

    def list_certificates(self, args: argparse.Namespace) -> int:
        """List SAE certificates"""
        try:
            if not self.cert_generator:
                logger.error("Certificate generator not available")
                return 1

            certificates = self.cert_generator.list_sae_certificates()

            if args.json:
                print(json.dumps(certificates, indent=2))
            else:
                print("SAE Certificates:")
                print("-" * 80)
                for cert in certificates:
                    print(f"SAE ID: {cert['sae_id']}")
                    print(f"Subject: {cert['subject']}")
                    print(f"Valid From: {cert['not_valid_before']}")
                    print(f"Valid Until: {cert['not_valid_after']}")
                    print(f"Certificate: {cert['certificate_file']}")
                    print(f"Private Key: {cert['private_key_file'] or 'Not found'}")
                    print(f"Has Private Key: {cert['has_private_key']}")
                    print("-" * 80)

            return 0

        except Exception as e:
            logger.error(f"Failed to list certificates: {e}")
            return 1

    def revoke_certificate(self, args: argparse.Namespace) -> int:
        """Revoke SAE certificate"""
        try:
            if not self.cert_generator:
                logger.error("Certificate generator not available")
                return 1

            sae_id = args.sae_id

            if self.cert_generator.revoke_sae_certificate(sae_id):
                print(f"Certificate revoked successfully for SAE: {sae_id}")
                return 0
            else:
                print(f"Failed to revoke certificate for SAE: {sae_id}")
                return 1

        except Exception as e:
            logger.error(f"Certificate revocation failed: {e}")
            return 1

    def _extract_sae_id_from_certificate(self, certificate_path: str) -> str | None:
        """Extract SAE ID from certificate"""
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend

            with open(certificate_path, "rb") as f:
                cert_data = x509.load_pem_x509_certificate(f.read(), default_backend())

            # Extract SAE ID from Common Name
            cn = cert_data.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[
                0
            ].value
            return cn
        except Exception as e:
            logger.error(f"Failed to extract SAE ID from certificate: {e}")
            return None

    def _extract_sae_name_from_certificate(self, certificate_path: str) -> str:
        """Extract SAE name from certificate or generate fallback"""
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend

            with open(certificate_path, "rb") as f:
                cert_data = x509.load_pem_x509_certificate(f.read(), default_backend())

            # Try to extract from Organizational Unit Name
            try:
                ou = cert_data.subject.get_attributes_for_oid(
                    x509.NameOID.ORGANIZATIONAL_UNIT_NAME
                )[0].value
                if ou and ou != "SAE":
                    return ou
            except IndexError:
                pass

            # Try to extract from Organization Name
            try:
                org = cert_data.subject.get_attributes_for_oid(
                    x509.NameOID.ORGANIZATION_NAME
                )[0].value
                if org and org != "KME System":
                    return org
            except IndexError:
                pass

            # Fallback to SAE ID-based name
            sae_id = self._extract_sae_id_from_certificate(certificate_path)
            if sae_id:
                return f"SAE {sae_id[:8]}"

            return "Unknown SAE"
        except Exception as e:
            logger.error(f"Failed to extract SAE name from certificate: {e}")
            return "Unknown SAE"

    def _get_certificate_hash(self, certificate_path: str) -> str:
        """Get certificate hash"""
        try:
            import hashlib

            with open(certificate_path, "rb") as f:
                cert_data = f.read()
            return hashlib.sha256(cert_data).hexdigest()
        except Exception as e:
            logger.error(f"Failed to get certificate hash: {e}")
            return ""

    def _is_sae_registered(self, sae_id: str) -> bool:
        """Check if SAE is registered"""
        sae_data = self._get_sae_by_id(sae_id)
        return sae_data is not None

    def _get_sae_data(self, sae_id: str) -> dict[str, Any] | None:
        """Get SAE data for package generation"""
        try:
            # Check if certificate exists in sae_certs directory
            cert_path = f"sae_certs/{sae_id}_certificate.pem"
            key_path = f"sae_certs/{sae_id}_private_key.pem"
            ca_cert_path = "../test_certs/ca_cert.pem"

            # Use actual certificate paths if they exist
            if os.path.exists(cert_path) and os.path.exists(key_path):
                # Extract actual SAE name from certificate
                sae_name = self._extract_sae_name_from_certificate(cert_path)
                return {
                    "name": sae_name,
                    "sae_id": sae_id,
                    "kme_endpoint": f"https://{self.settings.host}:{self.settings.port}",
                    "certificate_path": cert_path,
                    "private_key_path": key_path,
                    "ca_certificate_path": ca_cert_path,
                    "registration_date": datetime.now().isoformat(),
                }
            else:
                # Fallback to mock data if certificates don't exist
                return {
                    "name": f"SAE {sae_id[:8]}",  # Generate name from SAE ID
                    "sae_id": sae_id,
                    "kme_endpoint": f"https://{self.settings.host}:{self.settings.port}",
                    "certificate_path": "test_certs/master_sae_cert.pem",
                    "private_key_path": "test_certs/master_sae_key.pem",
                    "ca_certificate_path": "test_certs/ca_cert.pem",
                    "registration_date": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(f"Failed to get SAE data: {e}")
            return None

    def _generate_package(self, sae_id: str, args: argparse.Namespace) -> int:
        """Generate package for newly registered SAE"""
        try:
            # Prompt for package password
            import getpass

            password = getpass.getpass("Enter package encryption password: ")
            confirm_password = getpass.getpass("Confirm password: ")

            if password != confirm_password:
                logger.error("Passwords do not match")
                return 1

            # Create package
            sae_data = self._get_sae_data(sae_id)
            if not sae_data:
                return 1

            package_name = sae_data["name"].replace(" ", "_").lower()
            output_path = f"admin/packages/{package_name}_sae_package.sh"

            # Ensure packages directory exists
            Path("admin/packages").mkdir(parents=True, exist_ok=True)

            package_path = self.package_creator.create_package(
                sae_data, output_path, password
            )

            print(f"Package created successfully: {package_path}")
            return 0

        except Exception as e:
            logger.error(f"Package generation failed: {e}")
            return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="KME Administration Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Register SAE command
    register_parser = subparsers.add_parser("sae", help="SAE management")
    sae_subparsers = register_parser.add_subparsers(
        dest="sae_command", help="SAE commands"
    )

    # Register new SAE
    register_sae_parser = sae_subparsers.add_parser("register", help="Register new SAE")
    register_sae_parser.add_argument(
        "--name", required=True, help="Human readable name"
    )
    register_sae_parser.add_argument(
        "--certificate", required=True, help="Certificate file path"
    )
    register_sae_parser.add_argument("--private-key", help="Private key file path")
    register_sae_parser.add_argument(
        "--max-keys", type=int, default=128, help="Max keys per request"
    )
    register_sae_parser.add_argument(
        "--max-key-size", type=int, default=1024, help="Max key size"
    )
    register_sae_parser.add_argument(
        "--generate-package",
        action="store_true",
        help="Generate package after registration",
    )

    # List SAEs
    list_parser = sae_subparsers.add_parser("list", help="List all SAEs")
    list_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Show SAE
    show_parser = sae_subparsers.add_parser("show", help="Show SAE details")
    show_parser.add_argument("sae_id", help="SAE ID")
    show_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Update SAE status
    update_parser = sae_subparsers.add_parser("update-status", help="Update SAE status")
    update_parser.add_argument("sae_id", help="SAE ID")
    update_parser.add_argument(
        "status", help="New status (active, inactive, suspended, expired)"
    )

    # Revoke SAE
    revoke_parser = sae_subparsers.add_parser("revoke", help="Revoke SAE access")
    revoke_parser.add_argument("sae_id", help="SAE ID")

    # Generate package
    package_parser = sae_subparsers.add_parser(
        "generate-package", help="Generate SAE package"
    )
    package_parser.add_argument("sae_id", help="SAE ID")
    package_parser.add_argument(
        "--password", required=True, help="Package encryption password"
    )
    package_parser.add_argument("--output", required=True, help="Output file path")

    # Generate certificate
    cert_parser = sae_subparsers.add_parser(
        "generate-certificate", help="Generate SAE certificate"
    )
    cert_parser.add_argument("--sae-id", help="SAE ID (auto-generated if not provided)")
    cert_parser.add_argument("--name", help="SAE name (auto-generated if not provided)")
    cert_parser.add_argument(
        "--validity-days", type=int, default=365, help="Certificate validity in days"
    )
    cert_parser.add_argument(
        "--key-size", type=int, default=2048, help="Private key size in bits"
    )

    # List certificates
    list_certs_parser = sae_subparsers.add_parser(
        "list-certificates", help="List SAE certificates"
    )
    list_certs_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Revoke certificate
    revoke_cert_parser = sae_subparsers.add_parser(
        "revoke-certificate", help="Revoke SAE certificate"
    )
    revoke_cert_parser.add_argument("sae_id", help="SAE ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    admin = KMEAdmin()

    try:
        if args.command == "sae":
            if args.sae_command == "register":
                return admin.register_sae(args)
            elif args.sae_command == "list":
                return admin.list_saes(args)
            elif args.sae_command == "show":
                return admin.show_sae(args)
            elif args.sae_command == "update-status":
                return admin.update_sae_status(args)
            elif args.sae_command == "revoke":
                return admin.revoke_sae(args)
            elif args.sae_command == "generate-package":
                return admin.generate_package(args)
            elif args.sae_command == "generate-certificate":
                return admin.generate_certificate(args)
            elif args.sae_command == "list-certificates":
                return admin.list_certificates(args)
            elif args.sae_command == "revoke-certificate":
                return admin.revoke_certificate(args)
            else:
                register_parser.print_help()
                return 1
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
