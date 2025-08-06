#!/usr/bin/env python3
"""
Certificate Generator for SAE Registration

Generates X.509 certificates for SAEs using the KME CA.
"""

import ipaddress
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from sae_id_generator import SAEIDGenerator
except ImportError:
    print("Warning: Could not import SAEIDGenerator")
    SAEIDGenerator = None

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class CertificateGenerator:
    """Generates X.509 certificates for SAEs"""

    def __init__(self, ca_dir: str = None, sae_certs_dir: str = None):
        """Initialize certificate generator with configurable paths"""
        from .config import CA_DIR, SAE_CERTS_DIR

        self.ca_dir = Path(ca_dir) if ca_dir else CA_DIR
        self.sae_certs_dir = Path(sae_certs_dir) if sae_certs_dir else SAE_CERTS_DIR

        # Ensure directories exist
        self.ca_dir.mkdir(parents=True, exist_ok=True)
        self.sae_certs_dir.mkdir(parents=True, exist_ok=True)

    def generate_sae_certificate(
        self,
        sae_id: str | None = None,
        sae_name: str | None = None,
        validity_days: int = 365,
        key_size: int = 2048,
    ) -> dict[str, str]:
        """Generate a new SAE certificate and private key"""

        # Generate SAE ID if not provided
        if sae_id is None:
            if SAEIDGenerator:
                sae_id = SAEIDGenerator.generate_sae_id()
                print(f"Generated SAE ID: {sae_id}")
            else:
                raise ValueError(
                    "SAE ID is required when SAEIDGenerator is not available"
                )

        # Generate SAE name if not provided
        if sae_name is None:
            sae_name = f"SAE {sae_id[:8]}"

        print(f"Generating certificate for SAE: {sae_name} ({sae_id})")

        # Load CA certificate and private key
        ca_cert, ca_key = self._load_ca_credentials()

        # Generate SAE private key
        print("  Generating SAE private key...")
        sae_private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size, backend=default_backend()
        )

        # Create certificate subject
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, sae_id),  # Use SAE ID for CN
                x509.NameAttribute(
                    NameOID.ORGANIZATIONAL_UNIT_NAME, sae_name
                ),  # Store SAE name in OU
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "KME System"),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            ]
        )

        # Create certificate
        print("  Creating SAE certificate...")
        sae_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(sae_private_key.public_key())
            .serial_number(self._get_next_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                        x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .sign(ca_key, hashes.SHA256(), default_backend())
        )

        # Save certificate and private key
        cert_path, key_path = self._save_sae_credentials(
            sae_id, sae_cert, sae_private_key
        )

        print(f"  Certificate generated successfully!")
        print(f"  Certificate: {cert_path}")
        print(f"  Private Key: {key_path}")

        return {
            "certificate_path": str(cert_path),
            "private_key_path": str(key_path),
            "sae_id": sae_id,
            "sae_name": sae_name,
            "validity_days": str(validity_days),
            "expires": sae_cert.not_valid_after.isoformat(),
        }

    def _load_ca_credentials(self) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Load CA certificate and private key"""

        if not self.ca_dir.exists():
            raise FileNotFoundError(f"CA directory not found: {self.ca_dir}")

        if not self.ca_dir.joinpath("ca_cert.pem").exists():
            raise FileNotFoundError(
                f"CA certificate not found: {self.ca_dir / 'ca_cert.pem'}"
            )

        if not self.ca_dir.joinpath("ca_key.pem").exists():
            raise FileNotFoundError(
                f"CA private key not found: {self.ca_dir / 'ca_key.pem'}"
            )

        # Load CA certificate
        with open(self.ca_dir / "ca_cert.pem", "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        # Load CA private key
        with open(self.ca_dir / "ca_key.pem", "rb") as f:
            ca_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        # Ensure it's an RSA key
        if not isinstance(ca_key, rsa.RSAPrivateKey):
            raise ValueError("CA private key must be an RSA key")

        return ca_cert, ca_key

    def _get_next_serial_number(self) -> int:
        """Get next certificate serial number"""
        serial_file = self.sae_certs_dir / "serial"

        if serial_file.exists():
            with open(serial_file) as f:
                current_serial = int(f.read().strip())
        else:
            current_serial = 1000  # Start with 1000

        # Increment serial number
        next_serial = current_serial + 1

        # Save new serial number
        with open(serial_file, "w") as f:
            f.write(str(next_serial))

        return next_serial

    def _save_sae_credentials(
        self, sae_id: str, certificate: x509.Certificate, private_key: rsa.RSAPrivateKey
    ) -> tuple[Path, Path]:
        """Save SAE certificate and private key"""

        # Create filenames
        cert_filename = f"{sae_id}_certificate.pem"
        key_filename = f"{sae_id}_private_key.pem"

        cert_path = self.sae_certs_dir / cert_filename
        key_path = self.sae_certs_dir / key_filename

        # Save certificate
        with open(cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))

        # Save private key
        with open(key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # Set proper permissions
        os.chmod(cert_path, 0o644)  # Readable by all
        os.chmod(key_path, 0o600)  # Owner read/write only

        return cert_path, key_path

    def list_sae_certificates(self) -> list[dict[str, Any]]:
        """List all generated SAE certificates"""
        certificates = []

        for cert_file in self.sae_certs_dir.glob("*_certificate.pem"):
            sae_id = cert_file.stem.replace("_certificate", "")

            # Load certificate to get details
            with open(cert_file, "rb") as f:
                cert_data = x509.load_pem_x509_certificate(f.read(), default_backend())

            # Check if private key exists
            key_file = self.sae_certs_dir / f"{sae_id}_private_key.pem"
            has_private_key = key_file.exists()

            certificates.append(
                {
                    "sae_id": sae_id,
                    "certificate_file": str(cert_file),
                    "private_key_file": str(key_file) if has_private_key else None,
                    "has_private_key": has_private_key,
                    "subject": str(cert_data.subject),
                    "issuer": str(cert_data.issuer),
                    "not_valid_before": cert_data.not_valid_before.isoformat(),
                    "not_valid_after": cert_data.not_valid_after.isoformat(),
                    "serial_number": cert_data.serial_number,
                }
            )

        return certificates

    def revoke_sae_certificate(self, sae_id: str) -> bool:
        """Revoke a SAE certificate (mark as revoked)"""
        cert_file = self.sae_certs_dir / f"{sae_id}_certificate.pem"
        key_file = self.sae_certs_dir / f"{sae_id}_private_key.pem"

        if not cert_file.exists():
            print(f"Certificate not found for SAE: {sae_id}")
            return False

        # Create revoked directory
        revoked_dir = self.sae_certs_dir / "revoked"
        revoked_dir.mkdir(exist_ok=True)

        # Move files to revoked directory
        revoked_cert = revoked_dir / f"{sae_id}_certificate.pem"
        revoked_key = revoked_dir / f"{sae_id}_private_key.pem"

        cert_file.rename(revoked_cert)
        if key_file.exists():
            key_file.rename(revoked_key)

        print(f"Certificate revoked for SAE: {sae_id}")
        return True

    def validate_ca_setup(self) -> bool:
        """Validate that CA certificate and key are available"""
        if not self.ca_dir.exists():
            print(f"❌ CA directory not found: {self.ca_dir}")
            return False

        if not self.ca_dir.joinpath("ca_cert.pem").exists():
            print(f"❌ CA certificate not found: {self.ca_dir / 'ca_cert.pem'}")
            return False

        if not self.ca_dir.joinpath("ca_key.pem").exists():
            print(f"❌ CA private key not found: {self.ca_dir / 'ca_key.pem'}")
            return False

        try:
            # Try to load CA credentials
            ca_cert, ca_key = self._load_ca_credentials()
            print(f"✅ CA setup validated successfully")
            print(f"   CA Certificate: {self.ca_dir / 'ca_cert.pem'}")
            print(f"   CA Private Key: {self.ca_dir / 'ca_key.pem'}")
            return True
        except Exception as e:
            print(f"❌ CA setup validation failed: {e}")
            return False


def main():
    """Test certificate generator"""
    generator = CertificateGenerator()

    print("=== SAE Certificate Generator Test ===")

    # Validate CA setup
    if not generator.validate_ca_setup():
        print("CA setup validation failed. Please check certs/ directory.")
        return 1

    # List existing certificates
    certificates = generator.list_sae_certificates()
    print(f"\nExisting SAE certificates: {len(certificates)}")
    for cert in certificates:
        print(f"  - {cert['sae_id']}: {cert['subject']}")

    # Generate test certificate
    print("\nGenerating test certificate...")
    try:
        result = generator.generate_sae_certificate(
            sae_id="TEST001ABCDEFGHIJ",
            sae_name="Test Encryption Module",
            validity_days=365,
        )
        print(f"✅ Test certificate generated: {result['certificate_path']}")
    except Exception as e:
        print(f"❌ Certificate generation failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
