#!/usr/bin/env python3
"""
Generate Test Certificates for KME Development

This script generates test certificates for KME development and testing.
These certificates follow the ETSI QKD 014 format requirements.

WARNING: These are test certificates only - do not use in production!
"""

import os
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def generate_private_key():
    """Generate a new RSA private key."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def create_ca_certificate():
    """Create CA certificate and key."""
    print("Generating CA certificate...")

    # Generate private key
    ca_key = generate_private_key()

    # Create certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "KME Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "KME Test CA"),
        ]
    )

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
                content_commitment=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # Save certificate and key
    with open("ca_cert.pem", "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    with open("ca_key.pem", "wb") as f:
        f.write(
            ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    print("CA certificate generated: ca_cert.pem, ca_key.pem")
    return ca_cert, ca_key


def create_sae_certificate(ca_cert, ca_key, sae_type, sae_id, common_name):
    """Create SAE certificate and key."""
    print(f"Generating {sae_type} SAE certificate...")

    # Generate private key
    sae_key = generate_private_key()

    # Create certificate
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "KME Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    sae_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(sae_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                key_cert_sign=False,
                crl_sign=False,
                digital_signature=True,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=True,
                encipher_only=False,
                decipher_only=False,
                content_commitment=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(sae_id),
                ]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # Save certificate and key
    cert_filename = f"{sae_type.lower()}_sae_cert.pem"
    key_filename = f"{sae_type.lower()}_sae_key.pem"

    with open(cert_filename, "wb") as f:
        f.write(sae_cert.public_bytes(serialization.Encoding.PEM))

    with open(key_filename, "wb") as f:
        f.write(
            sae_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    print(f"{sae_type} SAE certificate generated: {cert_filename}, {key_filename}")
    return sae_cert, sae_key


def create_kme_certificate(ca_cert, ca_key):
    """Create KME server certificate and key."""
    print("Generating KME server certificate...")

    # Generate private key
    kme_key = generate_private_key()

    # Create certificate
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "KME Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "KME Server E1F2A3B4C5D6E7F8"),
        ]
    )

    kme_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(kme_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                key_cert_sign=False,
                crl_sign=False,
                digital_signature=True,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=True,
                encipher_only=False,
                decipher_only=False,
                content_commitment=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.SERVER_AUTH,
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                ]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # Save certificate and key
    with open("kme_cert.pem", "wb") as f:
        f.write(kme_cert.public_bytes(serialization.Encoding.PEM))

    with open("kme_key.pem", "wb") as f:
        f.write(
            kme_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    print("KME server certificate generated: kme_cert.pem, kme_key.pem")
    return kme_cert, kme_key


def main():
    """Generate all test certificates."""
    print("Generating test certificates for KME development...")
    print("WARNING: These are test certificates only - do not use in production!")
    print()

    # Create CA certificate
    ca_cert, ca_key = create_ca_certificate()
    print()

    # Create Master SAE certificate
    create_sae_certificate(
        ca_cert, ca_key, "Master", "A1B2C3D4E5F6A7B8", "Master SAE A1B2C3D4E5F6A7B8"
    )
    print()

    # Create Slave SAE certificate
    create_sae_certificate(
        ca_cert, ca_key, "Slave", "C1D2E3F4A5B6C7D8", "Slave SAE C1D2E3F4A5B6C7D8"
    )
    print()

    # Create KME server certificate
    create_kme_certificate(ca_cert, ca_key)
    print()

    print("All test certificates generated successfully!")
    print()
    print("Certificate files created:")
    print("- ca_cert.pem, ca_key.pem (Certificate Authority)")
    print("- master_sae_cert.pem, master_sae_key.pem (Master SAE)")
    print("- slave_sae_cert.pem, slave_sae_key.pem (Slave SAE)")
    print("- kme_cert.pem, kme_key.pem (KME Server)")
    print()
    print("SAE IDs:")
    print("- Master SAE: A1B2C3D4E5F6A7B8")
    print("- Slave SAE: C1D2E3F4A5B6C7D8")
    print("- KME Server: E1F2A3B4C5D6E7F8")


if __name__ == "__main__":
    main()
