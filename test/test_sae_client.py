#!/usr/bin/env python3
"""
Minimal SAE Test Client

Simulates two SAEs performing ETSI QKD 014 key exchange workflow:
1. SAE A requests keys for encryption
2. SAE A triggers SAE B with key IDs
3. SAE B retrieves keys using key IDs
4. Compare results between SAE A and SAE B

Version: 1.0.0
Author: KME Development Team
"""

import asyncio
import base64
import json
import time
import uuid
from typing import Any, Dict, List

import aiohttp
import structlog

logger = structlog.get_logger()


class SAEClient:
    """Minimal SAE client for testing key exchange workflow"""

    def __init__(self, base_url: str = "https://localhost:8000"):
        """Initialize SAE client"""
        self.base_url = base_url
        self.session: aiohttp.ClientSession | None = None

        # SAE IDs
        self.sae_a_id = "SAE001ABCDEFGHIJ"
        self.sae_b_id = "SAE002ABCDEFGHIJ"

        # Test certificate (simplified for testing)
        self.test_certificate = self._create_test_certificate()

    def _create_test_certificate(self) -> str:
        """Create a simple test certificate for SAE A"""
        # Use the same certificate generation as the working test suite
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

        # Create certificate with correct SAE ID format (16 uppercase alphanumeric characters)
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(
                    NameOID.COMMON_NAME, "SAE001ABCDEFGHIJ"
                ),  # Use valid SAE ID format
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

    async def sae_a_request_keys(self) -> dict[str, Any]:
        """SAE A (Master SAE) requests keys for encryption"""
        print("🔑 Phase 1: SAE A (Master SAE) requesting keys for encryption...")

        # ETSI QKD 014 compliant key request format
        key_request = {
            "number": 2,  # Number of keys requested
            "size": 256,  # Key size in bits
            "additional_slave_SAE_IDs": [self.sae_b_id],  # Include SAE B as slave
            "extension_mandatory": [],  # Mandatory extensions
            "extension_optional": [],  # Optional extensions
        }

        response = await self.make_request(
            method="POST",
            endpoint=f"/api/v1/keys/{self.sae_a_id}/enc_keys",
            data=key_request,
        )

        if response["status"] == 200:
            keys_data = response["data"]
            print(f"✅ SAE A received {len(keys_data.get('keys', []))} keys")

            # Extract key IDs for SAE B
            key_ids = [key["key_ID"] for key in keys_data.get("keys", [])]
            print(f"📋 Key IDs: {key_ids}")

            return {
                "keys": keys_data.get("keys", []),
                "key_ids": key_ids,
                "response": response,
            }
        else:
            raise Exception(f"SAE A key request failed: {response}")

    async def sae_b_retrieve_keys(self, key_ids: list[str]) -> dict[str, Any]:
        """SAE B (Slave SAE) retrieves keys using key IDs"""
        print(f"🔑 Phase 2: SAE B (Slave SAE) retrieving keys using key IDs: {key_ids}")

        # ETSI QKD 014 compliant key IDs request format
        key_ids_objects = [{"key_ID": key_id} for key_id in key_ids]

        key_ids_request = {
            "key_IDs": key_ids_objects,  # Array of key ID objects
            "key_IDs_extension": None,  # Key IDs extension (optional)
        }

        response = await self.make_request(
            method="POST",
            endpoint=f"/api/v1/keys/{self.sae_b_id}/dec_keys",
            data=key_ids_request,
        )

        if response["status"] == 200:
            keys_data = response["data"]
            print(f"✅ SAE B received {len(keys_data.get('keys', []))} keys")

            return {
                "keys": keys_data.get("keys", []),
                "response": response,
            }
        else:
            raise Exception(f"SAE B key retrieval failed: {response}")

    def compare_keys(
        self, sae_a_keys: list[dict], sae_b_keys: list[dict]
    ) -> dict[str, Any]:
        """Compare keys between SAE A (Master) and SAE B (Slave) for ETSI compliance"""
        print("🔍 Phase 3: Comparing keys between SAE A (Master) and SAE B (Slave)...")

        comparison: dict[str, Any] = {
            "key_count_match": len(sae_a_keys) == len(sae_b_keys),
            "key_ids_match": [],
            "key_values_match": [],
            "etsi_compliance": [],
            "details": [],
        }

        for i, (sae_a_key, sae_b_key) in enumerate(zip(sae_a_keys, sae_b_keys)):
            # Basic key matching
            key_id_match = sae_a_key["key_ID"] == sae_b_key["key_ID"]
            key_value_match = sae_a_key["key"] == sae_b_key["key"]

            # ETSI compliance checks
            etsi_compliant = self._validate_etsi_key_compliance(sae_a_key, sae_b_key)

            comparison["key_ids_match"].append(key_id_match)
            comparison["key_values_match"].append(key_value_match)
            comparison["etsi_compliance"].append(etsi_compliant)

            comparison["details"].append(
                {
                    "key_index": i,
                    "key_id": sae_a_key["key_ID"],
                    "key_id_match": key_id_match,
                    "key_value_match": key_value_match,
                    "etsi_compliant": etsi_compliant,
                    "sae_a_key_size": sae_a_key.get("key_size"),
                    "sae_b_key_size": sae_b_key.get("key_size"),
                }
            )

        return comparison

    def _validate_etsi_key_compliance(self, key_a: dict, key_b: dict) -> bool:
        """Validate ETSI QKD 014 compliance for key data"""
        try:
            # Check required ETSI fields
            required_fields = ["key_ID", "key"]
            for field in required_fields:
                if field not in key_a or field not in key_b:
                    return False

            # Validate UUID format for key_ID
            try:
                uuid.UUID(key_a["key_ID"])
                uuid.UUID(key_b["key_ID"])
            except ValueError:
                return False

            # Validate Base64 encoding for key data
            try:
                base64.b64decode(key_a["key"])
                base64.b64decode(key_b["key"])
            except Exception:
                return False

            # Check that keys are identical (Master and Slave should have same keys)
            if key_a["key_ID"] != key_b["key_ID"] or key_a["key"] != key_b["key"]:
                return False

            return True

        except Exception:
            return False

    async def run_test_workflow(self):
        """Run the complete SAE test workflow"""
        print("🚀 Starting SAE Test Client Workflow")
        print("=" * 50)

        try:
            # Phase 1: SAE A requests keys
            sae_a_result = await self.sae_a_request_keys()
            sae_a_keys = sae_a_result["keys"]
            key_ids = sae_a_result["key_ids"]

            print(f"📊 SAE A Keys Retrieved:")
            for i, key in enumerate(sae_a_keys):
                print(f"  Key {i+1}: ID={key['key_ID']}, Size={key['key_size']} bits")
                print(f"    Key Data: {key['key']}")

            print()

            # Phase 2: SAE B retrieves keys using key IDs
            sae_b_result = await self.sae_b_retrieve_keys(key_ids)
            sae_b_keys = sae_b_result["keys"]

            print(f"📊 SAE B Keys Retrieved:")
            for i, key in enumerate(sae_b_keys):
                print(f"  Key {i+1}: ID={key['key_ID']}, Size={key['key_size']} bits")
                print(f"    Key Data: {key['key']}")

            print()

            # Phase 3: Compare results
            comparison = self.compare_keys(sae_a_keys, sae_b_keys)

            # Final output
            print("📋 FINAL RESULTS:")
            print("=" * 50)
            print(f"Key Count Match: {'✅' if comparison['key_count_match'] else '❌'}")
            print(f"Key IDs Match: {'✅' if all(comparison['key_ids_match']) else '❌'}")
            print(
                f"Key Values Match: {'✅' if all(comparison['key_values_match']) else '❌'}"
            )
            print(
                f"ETSI Compliance: {'✅' if all(comparison['etsi_compliance']) else '❌'}"
            )
            print()

            print("🔍 DETAILED COMPARISON:")
            for detail in comparison["details"]:
                status = (
                    "✅"
                    if detail["key_id_match"]
                    and detail["key_value_match"]
                    and detail["etsi_compliant"]
                    else "❌"
                )
                print(f"  Key {detail['key_index']+1}: {status}")
                print(f"    ID: {detail['key_id']}")
                print(f"    ID Match: {'✅' if detail['key_id_match'] else '❌'}")
                print(f"    Value Match: {'✅' if detail['key_value_match'] else '❌'}")
                print(f"    ETSI Compliant: {'✅' if detail['etsi_compliant'] else '❌'}")
                print(f"    Size: {detail['sae_a_key_size']} bits")
                print()

            # Overall success (including ETSI compliance)
            all_match = (
                comparison["key_count_match"]
                and all(comparison["key_ids_match"])
                and all(comparison["key_values_match"])
                and all(comparison["etsi_compliance"])
            )

            print("🎯 OVERALL RESULT:")
            print("=" * 50)
            if all_match:
                print("✅ SUCCESS: All keys match and ETSI QKD 014 compliance verified!")
                print("   The ETSI QKD key exchange workflow is working correctly.")
                print("   - Master SAE (SAE A) successfully requested keys")
                print("   - Slave SAE (SAE B) successfully retrieved keys")
                print("   - All keys are ETSI QKD 014 compliant")
                print("   - UUID format, Base64 encoding, and data structures verified")
            else:
                print("❌ FAILURE: ETSI QKD 014 compliance issues detected!")
                print("   Issues found:")
                if not comparison["key_count_match"]:
                    print("   - Key count mismatch between Master and Slave SAEs")
                if not all(comparison["key_ids_match"]):
                    print("   - Key ID mismatch between Master and Slave SAEs")
                if not all(comparison["key_values_match"]):
                    print("   - Key value mismatch between Master and Slave SAEs")
                if not all(comparison["etsi_compliance"]):
                    print("   - ETSI QKD 014 format compliance issues")
                print()
                print("   Expected ETSI QKD 014 behavior:")
                print("   - Master SAE requests keys for encryption")
                print("   - Slave SAE retrieves identical keys using key IDs")
                print("   - Both SAEs can use the same keys for encryption/decryption")

            return {
                "success": all_match,
                "sae_a_keys": sae_a_keys,
                "sae_b_keys": sae_b_keys,
                "comparison": comparison,
            }

        except Exception as e:
            print(f"❌ Test workflow failed: {e}")
            raise


async def main():
    """Main function to run the SAE test client"""
    print("🔧 SAE Test Client - ETSI QKD 014 Key Exchange Simulation")
    print("=" * 60)

    async with SAEClient() as client:
        try:
            result = await client.run_test_workflow()
            return 0 if result["success"] else 1
        except Exception as e:
            print(f"❌ Test client failed: {e}")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
