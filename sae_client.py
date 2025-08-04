#!/usr/bin/env python3
"""
SAE Client - ETSI QKD 014 Master SAE Implementation

A single SAE client that acts as a Master SAE to request keys for encryption
from the KME according to ETSI GS QKD 014 V1.1.1 specification.

Usage:
    python sae_client.py --master [OPTIONS]

Version: 1.0.0
Author: KME Development Team
"""

import argparse
import asyncio
import base64
import json
import sys
import time
import uuid
from typing import Any, Dict, List

import aiohttp
import structlog

logger = structlog.get_logger()


class SAEClient:
    """Single SAE client for ETSI QKD 014 key requests"""

    def __init__(
        self, base_url: str = "http://localhost:8000", sae_id: str = "qnFFr9m6Re3EWs7C"
    ):
        """Initialize SAE client"""
        self.base_url = base_url
        self.sae_id = sae_id
        self.session: aiohttp.ClientSession | None = None

        # Test certificate for authentication
        self.test_certificate = self._create_test_certificate()

    def _create_test_certificate(self) -> str:
        """Create a test certificate for SAE authentication"""
        import datetime

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate with SAE ID
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, self.sae_id),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_agreement=True,
                    data_encipherment=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                    content_commitment=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        return base64.b64encode(cert_pem.encode()).decode()

    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def make_request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to KME API"""
        url = f"{self.base_url}{endpoint}"

        if headers is None:
            headers = {}

        # Add certificate for authentication
        headers["X-Client-Certificate"] = self.test_certificate

        if self.session is None:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    response_data = await response.json()
            elif method.upper() == "POST":
                async with self.session.post(
                    url, headers=headers, json=data
                ) as response:
                    response_data = await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return {
                "status": response.status,
                "data": response_data,
                "headers": dict(response.headers),
            }

        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    async def get_status(self) -> dict[str, Any]:
        """Get KME status for this SAE"""
        print(f"📊 Getting KME status for SAE {self.sae_id}...")

        response = await self.make_request(
            method="GET",
            endpoint=f"/api/v1/keys/{self.sae_id}/status",
        )

        if response["status"] == 200:
            status_data = response["data"]
            print("✅ KME Status Retrieved Successfully")
            print(f"   Source KME ID: {status_data.get('source_KME_ID')}")
            print(f"   Target KME ID: {status_data.get('target_KME_ID')}")
            print(f"   Key Size: {status_data.get('key_size')} bits")
            print(f"   Stored Key Count: {status_data.get('stored_key_count')}")
            print(f"   Max Key Count: {status_data.get('max_key_count')}")
            print(f"   Max Key Per Request: {status_data.get('max_key_per_request')}")
            print(f"   Max Key Size: {status_data.get('max_key_size')} bits")
            print(f"   Min Key Size: {status_data.get('min_key_size')} bits")
            print(f"   Max SAE ID Count: {status_data.get('max_SAE_ID_count')}")
            return status_data
        else:
            raise Exception(f"Status request failed: {response}")

    async def request_keys(
        self,
        number: int = 1,
        size: int = 256,
        additional_slave_sae_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Request keys for encryption (Master SAE operation)"""
        print(f"🔑 Requesting {number} keys of {size} bits each...")

        # ETSI QKD 014 compliant key request format
        key_request = {
            "number": number,
            "size": size,
            "additional_slave_SAE_IDs": additional_slave_sae_ids or [],
            "extension_mandatory": [],
            "extension_optional": [],
        }

        response = await self.make_request(
            method="POST",
            endpoint=f"/api/v1/keys/{self.sae_id}/enc_keys",
            data=key_request,
        )

        if response["status"] == 200:
            keys_data = response["data"]
            print(f"✅ Successfully received {len(keys_data.get('keys', []))} keys")

            # Display key details
            print("\n📋 Key Details:")
            for i, key in enumerate(keys_data.get("keys", [])):
                print(f"  Key {i+1}:")
                print(f"    ID: {key['key_ID']}")
                print(f"    Size: {key.get('key_size', 'N/A')} bits")
                print(f"    Key Data: {key['key']}")
                print()

            return {
                "keys": keys_data.get("keys", []),
                "key_ids": [key["key_ID"] for key in keys_data.get("keys", [])],
                "response": response,
            }
        else:
            raise Exception(f"Key request failed: {response}")

    async def retrieve_keys(self, key_ids: list[str]) -> dict[str, Any]:
        """Retrieve keys using key IDs (Slave SAE operation)"""
        print(f"🔑 Retrieving {len(key_ids)} keys using key IDs...")

        # ETSI QKD 014 compliant key IDs request format
        key_ids_objects = [{"key_ID": key_id} for key_id in key_ids]

        key_ids_request = {
            "key_IDs": key_ids_objects,
            "key_IDs_extension": None,
        }

        response = await self.make_request(
            method="POST",
            endpoint=f"/api/v1/keys/{self.sae_id}/dec_keys",
            data=key_ids_request,
        )

        if response["status"] == 200:
            keys_data = response["data"]
            print(f"✅ Successfully retrieved {len(keys_data.get('keys', []))} keys")

            # Display key details
            print("\n📋 Retrieved Key Details:")
            for i, key in enumerate(keys_data.get("keys", [])):
                print(f"  Key {i+1}:")
                print(f"    ID: {key['key_ID']}")
                print(f"    Size: {key.get('key_size', 'N/A')} bits")
                print(f"    Key Data: {key['key']}")
                print()

            return {
                "keys": keys_data.get("keys", []),
                "response": response,
            }
        else:
            raise Exception(f"Key retrieval failed: {response}")

    async def run_master_operation(self, number: int = 1, size: int = 256):
        """Run the master SAE operation to request keys"""
        print("🚀 Starting Master SAE Operation")
        print("=" * 50)
        print(f"SAE ID: {self.sae_id}")
        print(f"KME URL: {self.base_url}")
        print(f"Requesting: {number} keys of {size} bits each")
        print()

        try:
            # Step 1: Get KME status
            await self.get_status()
            print()

            # Step 2: Request keys
            result = await self.request_keys(number=number, size=size)

            print("🎯 Master SAE Operation Completed Successfully!")
            print(f"   Total keys received: {len(result['keys'])}")
            print(f"   Key IDs: {result['key_ids']}")

            return result

        except Exception as e:
            print(f"❌ Master SAE operation failed: {e}")
            raise


def print_usage():
    """Print usage information"""
    print("SAE Client - ETSI QKD 014 Master SAE Implementation")
    print("=" * 60)
    print()
    print("Usage:")
    print("  python sae_client.py --master [OPTIONS]")
    print()
    print("Required Arguments:")
    print("  --master                    Run as Master SAE")
    print()
    print("Optional Arguments:")
    print(
        "  --url URL                   KME server URL (default: http://localhost:8000)"
    )
    print("  --sae-id SAE_ID             SAE ID (default: qnFFr9m6Re3EWs7C)")
    print("  --number NUMBER             Number of keys to request (default: 1)")
    print("  --size SIZE                 Key size in bits (default: 256)")
    print("  --help                      Show this help message")
    print()
    print("Examples:")
    print("  python sae_client.py --master")
    print("  python sae_client.py --master --number 3 --size 512")
    print(
        "  python sae_client.py --master --url http://kme.example.com --sae-id qnFFr9m6Re3EWs7C"
    )
    print()
    print("Description:")
    print("  This client acts as a Master SAE to request keys for encryption")
    print("  from the KME according to ETSI GS QKD 014 V1.1.1 specification.")
    print()
    print("  The client will:")
    print("  1. Get KME status for the SAE")
    print("  2. Request the specified number of keys")
    print("  3. Display detailed key information")
    print()


async def main():
    """Main function to run the SAE client"""
    parser = argparse.ArgumentParser(
        description="SAE Client - ETSI QKD 014 Master SAE Implementation",
        add_help=False,
    )

    parser.add_argument("--master", action="store_true", help="Run as Master SAE")
    parser.add_argument("--url", default="http://localhost:8000", help="KME server URL")
    parser.add_argument("--sae-id", default="qnFFr9m6Re3EWs7C", help="SAE ID")
    parser.add_argument(
        "--number", type=int, default=1, help="Number of keys to request"
    )
    parser.add_argument("--size", type=int, default=256, help="Key size in bits")
    parser.add_argument("--help", action="store_true", help="Show help message")

    args = parser.parse_args()

    # Check if --master argument is provided
    if not args.master:
        print_usage()
        return 1

    # Show help if requested
    if args.help:
        print_usage()
        return 0

    # Validate arguments
    if args.number < 1:
        print("❌ Error: Number of keys must be at least 1")
        return 1

    if args.size < 1:
        print("❌ Error: Key size must be at least 1 bit")
        return 1

    if len(args.sae_id) != 16:
        print("❌ Error: SAE ID must be exactly 16 characters")
        return 1

    async with SAEClient(base_url=args.url, sae_id=args.sae_id) as client:
        try:
            result = await client.run_master_operation(
                number=args.number, size=args.size
            )
            return 0
        except Exception as e:
            print(f"❌ SAE client failed: {e}")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
