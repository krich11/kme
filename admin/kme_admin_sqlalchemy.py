#!/usr/bin/env python3
"""
KME Admin Tool - SQLAlchemy Version

Admin tool for KME management using SQLAlchemy ORM.
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add the project root to the Python path and set up environment
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ["ENV_FILE"] = str(project_root / ".env")

# Now import the modules that depend on the path setup
from admin.sqlalchemy_service import close_sqlalchemy_service  # noqa: E402
from admin.sqlalchemy_service import get_sqlalchemy_service  # noqa: E402
from app.core.config import settings  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_kme_id() -> str:
    """Detect KME ID from environment or certificate"""
    # Try to extract from server certificate first (most reliable)
    server_cert_path = "../certs/kme_cert.pem"
    if Path(server_cert_path).exists():
        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", server_cert_path, "-subject", "-noout"],
                capture_output=True,
                text=True,
                check=True,
            )
            # Extract CN from subject
            subject = result.stdout.strip()
            if "CN = " in subject:
                cn = subject.split("CN = ")[1].split(",")[0]
                if len(cn) == 16:  # Valid KME ID length
                    return cn
        except Exception as e:
            logger.warning(f"Failed to extract KME ID from certificate: {e}")

    # Try environment variable
    kme_id = os.getenv("KME_ID")
    if kme_id:
        return kme_id

    # Try settings (but this might be wrong due to .env loading issues)
    kme_id = settings.kme_id
    if kme_id and kme_id != "KME001":
        return kme_id

    # Fallback to default
    return "KME001"


class KMEAdminSQLAlchemy:
    """KME Admin tool using SQLAlchemy"""

    def __init__(self):
        """Initialize admin tool"""
        self.settings = settings
        self.kme_id = detect_kme_id()
        self.sqlalchemy_service = get_sqlalchemy_service()

    async def list_saes(self, args: argparse.Namespace) -> int:
        """List all SAEs"""
        try:
            saes = await self.sqlalchemy_service.load_saes()

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
                        print(f"KME ID: {sae['kme_id']}")
                        print(f"Status: {sae['status']}")
                        print(f"Registration Date: {sae['registration_date']}")
                        print("-" * 80)

            return 0
        except Exception as e:
            logger.error(f"Failed to list SAEs: {e}")
            return 1

    async def show_sae(self, args: argparse.Namespace) -> int:
        """Show SAE details"""
        try:
            sae = await self.sqlalchemy_service.get_sae_by_id(args.sae_id)

            if not sae:
                print(f"SAE {args.sae_id} not found")
                return 1

            if args.json:
                print(json.dumps(sae, indent=2))
            else:
                print(f"SAE Details for {args.sae_id}:")
                print("-" * 80)
                for key, value in sae.items():
                    if key == "certificate_info":
                        print(f"{key}:")
                        for cert_key, cert_value in value.items():
                            print(f"  {cert_key}: {cert_value}")
                    else:
                        print(f"{key}: {value}")

            return 0
        except Exception as e:
            logger.error(f"Failed to get SAE details: {e}")
            return 1

    async def register_sae(self, args: argparse.Namespace) -> int:
        """Register a new SAE"""
        try:
            logger.info(f"Registering SAE: {args.name}")

            # Validate certificate and extract SAE ID
            sae_id = self._extract_sae_id_from_certificate(args.certificate)
            if not sae_id:
                logger.error("Failed to extract SAE ID from certificate")
                return 1

            # Check if SAE is already registered
            if await self.sqlalchemy_service.is_sae_registered(sae_id):
                logger.warning(f"SAE {sae_id} is already registered")
                return 0

            # Prepare SAE data
            sae_data = {
                "sae_id": sae_id,
                "name": args.name,
                "kme_id": self.kme_id,
                "certificate_hash": self._get_certificate_hash(args.certificate),
                "certificate_subject": self._extract_certificate_subject(
                    args.certificate
                ),
                "certificate_issuer": self._extract_certificate_issuer(
                    args.certificate
                ),
                "registration_date": datetime.now().isoformat(),
                "status": "active",
            }

            # Add SAE to database
            success = await self.sqlalchemy_service.add_sae(sae_data)
            if success:
                logger.info(f"SAE {sae_id} registered successfully")
                return 0
            else:
                logger.error("SAE registration failed")
                return 1

        except Exception as e:
            logger.error(f"Failed to register SAE: {e}")
            return 1

    async def update_sae_status(self, args: argparse.Namespace) -> int:
        """Update SAE status"""
        try:
            success = await self.sqlalchemy_service.update_sae_status(
                args.sae_id, args.status
            )
            if success:
                logger.info(f"Updated SAE {args.sae_id} status to {args.status}")
                return 0
            else:
                logger.error(f"Failed to update SAE {args.sae_id} status")
                return 1
        except Exception as e:
            logger.error(f"Failed to update SAE status: {e}")
            return 1

    async def revoke_sae(self, args: argparse.Namespace) -> int:
        """Revoke SAE"""
        try:
            success = await self.sqlalchemy_service.revoke_sae(args.sae_id)
            if success:
                logger.info(f"Revoked SAE {args.sae_id}")
                return 0
            else:
                logger.error(f"Failed to revoke SAE {args.sae_id}")
                return 1
        except Exception as e:
            logger.error(f"Failed to revoke SAE: {e}")
            return 1

    def _extract_sae_id_from_certificate(self, certificate_path: str) -> str | None:
        """Extract SAE ID from certificate"""
        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", certificate_path, "-subject", "-noout"],
                capture_output=True,
                text=True,
                check=True,
            )
            subject = result.stdout.strip()
            if "CN = " in subject:
                cn = subject.split("CN = ")[1].split(",")[0]
                return cn
            return None
        except Exception as e:
            logger.error(f"Failed to extract SAE ID from certificate: {e}")
            return None

    def _get_certificate_hash(self, certificate_path: str) -> str:
        """Get certificate hash"""
        try:
            result = subprocess.run(
                [
                    "openssl",
                    "x509",
                    "-in",
                    certificate_path,
                    "-noout",
                    "-fingerprint",
                    "-sha256",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            fingerprint = result.stdout.strip()
            if "SHA256 Fingerprint=" in fingerprint:
                return (
                    fingerprint.split("SHA256 Fingerprint=")[1].replace(":", "").lower()
                )
            return "unknown"
        except Exception as e:
            logger.error(f"Failed to get certificate hash: {e}")
            return "unknown"

    def _extract_certificate_subject(self, certificate_path: str) -> str:
        """Extract certificate subject"""
        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", certificate_path, "-subject", "-noout"],
                capture_output=True,
                text=True,
                check=True,
            )
            subject = result.stdout.strip()
            if "subject=" in subject:
                return subject.replace("subject=", "")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract certificate subject: {e}")
            return ""

    def _extract_certificate_issuer(self, certificate_path: str) -> str:
        """Extract certificate issuer"""
        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", certificate_path, "-issuer", "-noout"],
                capture_output=True,
                text=True,
                check=True,
            )
            issuer = result.stdout.strip()
            if "issuer=" in issuer:
                return issuer.replace("issuer=", "")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract certificate issuer: {e}")
            return ""

    async def close(self):
        """Close database connections"""
        await close_sqlalchemy_service()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="KME Admin Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # SAE subcommands
    sae_parser = subparsers.add_parser("sae", help="SAE management")
    sae_subparsers = sae_parser.add_subparsers(dest="sae_command", help="SAE commands")

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

    # Register SAE
    register_parser = sae_subparsers.add_parser("register", help="Register SAE")
    register_parser.add_argument("--name", required=True, help="SAE name")
    register_parser.add_argument(
        "--certificate", required=True, help="Certificate file path"
    )

    # Update SAE status
    update_parser = sae_subparsers.add_parser("update-status", help="Update SAE status")
    update_parser.add_argument("sae_id", help="SAE ID")
    update_parser.add_argument(
        "status", choices=["active", "inactive", "suspended"], help="New status"
    )

    # Revoke SAE
    revoke_parser = sae_subparsers.add_parser("revoke", help="Revoke SAE")
    revoke_parser.add_argument("sae_id", help="SAE ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    admin = KMEAdminSQLAlchemy()

    try:
        if args.command == "sae":
            if args.sae_command == "list":
                return await admin.list_saes(args)
            elif args.sae_command == "show":
                return await admin.show_sae(args)
            elif args.sae_command == "register":
                return await admin.register_sae(args)
            elif args.sae_command == "update-status":
                return await admin.update_sae_status(args)
            elif args.sae_command == "revoke":
                return await admin.revoke_sae(args)
            else:
                sae_parser.print_help()
                return 1
        else:
            parser.print_help()
            return 1
    finally:
        await admin.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
