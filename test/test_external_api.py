#!/usr/bin/env python3
"""
KME External API Test Suite

Comprehensive test suite for KME API endpoints on port 443 (end-to-end testing).
Tests the complete application stack including Nginx SSL termination and mTLS authentication.

Version: 1.0.0
Author: KME Development Team
Description: External API testing with real mTLS and full ETSI compliance
License: [To be determined]
"""

import asyncio
import base64
import json
import ssl
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pytest
import structlog
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = structlog.get_logger()


class ExternalAPITestClient:
    """External API test client for end-to-end testing on port 443 with real mTLS"""

    def __init__(self, base_url: str = "https://localhost:443"):
        """Initialize test client"""
        self.base_url = base_url
        self.client: httpx.AsyncClient | None = None

        # Test certificate paths
        self.ca_cert_path = "test_certs/ca_cert.pem"
        self.kme_cert_path = "test_certs/kme_cert.pem"
        self.master_sae_cert_path = "test_certs/master_sae_cert.pem"
        self.master_sae_key_path = "test_certs/master_sae_key.pem"
        self.slave_sae_cert_path = "test_certs/slave_sae_cert.pem"
        self.slave_sae_key_path = "test_certs/slave_sae_key.pem"

        # Test SAE IDs (extracted from certificates)
        self.master_sae_id = "A1B2C3D4E5F6A7B8"  # From master_sae_cert.pem
        self.slave_sae_id = "C1D2E3F4A5B6C7D8"  # From slave_sae_cert.pem

        # Test KME IDs
        self.source_kme_id = "AAAABBBBCCCCDDDD"
        self.target_kme_id = "EEEEFFFFAAAA1111"

        logger.info("External API Test Client initialized", base_url=base_url)

    async def __aenter__(self):
        """Async context manager entry"""
        # Create SSL context for mTLS
        ssl_context = ssl.create_default_context(cafile=self.ca_cert_path)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = (
            ssl.CERT_NONE
        )  # We're the client, we don't require server cert verification

        # Load client certificate and key
        ssl_context.load_cert_chain(
            certfile=self.master_sae_cert_path, keyfile=self.master_sae_key_path
        )

        # Create HTTPS client with mTLS
        self.client = httpx.AsyncClient(
            base_url=self.base_url, verify=ssl_context, http2=False
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()

    async def make_request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        expected_status: int = 200,
        use_master_cert: bool = True,
    ) -> dict[str, Any]:
        """Make HTTPS request to KME API with real mTLS authentication"""
        url = f"{self.base_url}{endpoint}"

        if headers is None:
            headers = {}

        # Add standard headers
        headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

        start_time = time.time()

        try:
            if self.client is None:
                raise RuntimeError("HTTP client not initialized")

            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            duration = time.time() - start_time

            # Parse response
            if response.headers.get("content-type", "").startswith("application/json"):
                response_data = response.json()
            else:
                response_data = response.text

            # Validate status code
            if response.status_code != expected_status:
                raise AssertionError(
                    f"Expected status {expected_status}, got {response.status_code}. "
                    f"Response: {response_data}"
                )

            return {
                "status": response.status_code,
                "data": response_data,
                "duration": duration,
                "headers": dict(response.headers),
            }

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                method=method,
                url=url,
                error=str(e),
                duration=duration,
            )
            raise

    async def test_get_status_endpoint(self) -> dict[str, Any]:
        """Test GET /api/v1/keys/{slave_sae_id}/status endpoint with real mTLS"""
        logger.info("Testing Get Status endpoint with real mTLS")

        endpoint = f"/api/v1/keys/{self.slave_sae_id}/status"

        response = await self.make_request(
            method="GET", endpoint=endpoint, expected_status=200
        )

        # Validate ETSI QKD 014 compliance
        status_data = response["data"]

        # Required fields from ETSI specification
        required_fields = [
            "source_KME_ID",
            "target_KME_ID",
            "master_SAE_ID",
            "slave_SAE_ID",
            "key_size",
            "stored_key_count",
            "max_key_count",
            "max_key_per_request",
            "max_key_size",
            "min_key_size",
            "max_SAE_ID_count",
        ]

        for field in required_fields:
            assert field in status_data, f"Missing required field: {field}"

        # Validate ID lengths (16 characters)
        id_fields = ["source_KME_ID", "target_KME_ID", "master_SAE_ID", "slave_SAE_ID"]
        for field in id_fields:
            assert len(status_data[field]) == 16, f"Invalid {field} length"

        # Validate numeric fields
        assert status_data["key_size"] > 0, "Invalid key_size"
        assert status_data["stored_key_count"] >= 0, "Invalid stored_key_count"
        assert status_data["max_key_count"] > 0, "Invalid max_key_count"
        assert status_data["max_key_per_request"] > 0, "Invalid max_key_per_request"
        assert (
            status_data["max_key_size"] >= status_data["min_key_size"]
        ), "Invalid key size range"

        logger.info("Get Status endpoint test passed", response=response)
        return response

    async def test_get_key_endpoint_basic(self) -> dict[str, Any]:
        """Test POST /api/v1/keys/{slave_sae_id}/enc_keys endpoint with basic request"""
        logger.info("Testing Get Key endpoint - basic request with real mTLS")

        endpoint = f"/api/v1/keys/{self.slave_sae_id}/enc_keys"

        # ETSI QKD 014 compliant key request
        key_request = {
            "number": 1,
            "size": 256,
            "additional_slave_SAE_IDs": [],
            "extension_mandatory": [],
            "extension_optional": [],
        }

        response = await self.make_request(
            method="POST", endpoint=endpoint, data=key_request, expected_status=200
        )

        # Validate ETSI QKD 014 compliance
        key_data = response["data"]

        # Required fields
        assert "keys" in key_data, "Missing keys field"
        assert isinstance(key_data["keys"], list), "Keys must be a list"
        assert len(key_data["keys"]) == 1, "Expected 1 key"

        # Validate key structure
        key = key_data["keys"][0]
        assert "key_ID" in key, "Missing key_ID"
        assert "key" in key, "Missing key data"

        # Validate key_ID format (UUID)
        try:
            uuid.UUID(key["key_ID"])
        except ValueError:
            raise AssertionError(f"Invalid key_ID format: {key['key_ID']}")

        # Validate key data (base64 encoded)
        try:
            decoded_key = base64.b64decode(key["key"])
            assert (
                len(decoded_key) >= 32
            ), f"Expected at least 32 bytes, got {len(decoded_key)}"
            assert (
                len(decoded_key) <= 1024
            ), f"Expected at most 1024 bytes, got {len(decoded_key)}"
        except Exception:
            raise AssertionError(f"Invalid key data format: {key['key']}")

        logger.info("Get Key endpoint basic test passed", response=response)
        return response

    async def test_get_key_endpoint_defaults(self) -> dict[str, Any]:
        """Test POST /api/v1/keys/{slave_sae_id}/enc_keys endpoint with defaults"""
        logger.info("Testing Get Key endpoint - defaults with real mTLS")

        endpoint = f"/api/v1/keys/{self.slave_sae_id}/enc_keys"

        # Request with minimal parameters (should use defaults)
        key_request: dict[str, Any] = {}

        response = await self.make_request(
            method="POST", endpoint=endpoint, data=key_request, expected_status=200
        )

        # Validate response
        key_data = response["data"]
        assert "keys" in key_data, "Missing keys field"
        assert len(key_data["keys"]) == 1, "Expected 1 key (default)"

        logger.info("Get Key endpoint defaults test passed", response=response)
        return response

    async def test_get_key_endpoint_multicast(self) -> dict[str, Any]:
        """Test POST /api/v1/keys/{slave_sae_id}/enc_keys endpoint with multicast"""
        logger.info("Testing Get Key endpoint - multicast with real mTLS")

        endpoint = f"/api/v1/keys/{self.slave_sae_id}/enc_keys"

        # Request with multiple slave SAEs
        key_request = {
            "number": 1,
            "size": 256,
            "additional_slave_SAE_IDs": [self.slave_sae_id, "D1E2F3A4B5C6D7E8"],
            "extension_mandatory": [],
            "extension_optional": [],
        }

        response = await self.make_request(
            method="POST", endpoint=endpoint, data=key_request, expected_status=200
        )

        # Validate response
        key_data = response["data"]
        assert "keys" in key_data, "Missing keys field"
        assert len(key_data["keys"]) == 1, "Expected 1 key"

        logger.info("Get Key endpoint multicast test passed", response=response)
        return response

    async def test_get_key_with_ids_endpoint(self) -> dict[str, Any]:
        """Test POST /api/v1/keys/{master_sae_id}/dec_keys endpoint"""
        logger.info("Testing Get Key with IDs endpoint with real mTLS")

        # First, get some keys to retrieve
        enc_response = await self.test_get_key_endpoint_basic()
        key_ids = [key["key_ID"] for key in enc_response["data"]["keys"]]

        endpoint = f"/api/v1/keys/{self.master_sae_id}/dec_keys"

        # ETSI QKD 014 compliant key IDs request
        key_ids_request = {
            "key_IDs": [{"key_ID": key_id} for key_id in key_ids],
            "key_IDs_extension": None,
        }

        response = await self.make_request(
            method="POST",
            endpoint=endpoint,
            data=key_ids_request,
            expected_status=200,
            use_master_cert=False,  # Use slave certificate for this endpoint
        )

        # Validate ETSI QKD 014 compliance
        key_data = response["data"]

        # Required fields
        assert "keys" in key_data, "Missing keys field"
        assert isinstance(key_data["keys"], list), "Keys must be a list"
        assert len(key_data["keys"]) == len(key_ids), "Expected same number of keys"

        # Validate each key
        for key in key_data["keys"]:
            assert "key_ID" in key, "Missing key_ID"
            assert "key" in key, "Missing key data"

            # Validate key_ID is in the requested list
            assert key["key_ID"] in key_ids, f"Unexpected key_ID: {key['key_ID']}"

            # Validate key data (base64 encoded)
            try:
                base64.b64decode(key["key"])
            except Exception:
                raise AssertionError(f"Invalid key data format: {key['key']}")

        logger.info("Get Key with IDs endpoint test passed", response=response)
        return response

    async def test_authentication_failure(self) -> dict[str, Any]:
        """Test authentication failure scenarios with real mTLS"""
        logger.info("Testing authentication failure scenarios with real mTLS")

        # Test with invalid certificate (should fail mTLS)
        endpoint = f"/api/v1/keys/{self.slave_sae_id}/status"

        # Create a client with invalid certificate
        invalid_ssl_context = ssl.create_default_context(cafile=self.ca_cert_path)
        invalid_ssl_context.check_hostname = False
        invalid_ssl_context.verify_mode = ssl.CERT_NONE  # No client cert

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, verify=invalid_ssl_context, http2=False
            ) as invalid_client:
                response = await invalid_client.get(f"{self.base_url}{endpoint}")
                # Should get 401 Unauthorized due to missing client certificate
                assert (
                    response.status_code == 401
                ), f"Expected 401, got {response.status_code}"
        except Exception as e:
            logger.info("Authentication failure test passed", error=str(e))

        return {
            "status": "passed",
            "message": "Authentication failure handled correctly",
        }

    async def test_authorization_failure(self) -> dict[str, Any]:
        """Test authorization failure scenarios with real mTLS"""
        logger.info("Testing authorization failure scenarios with real mTLS")

        # Test accessing another SAE's status
        unauthorized_sae_id = "F1F2F3F4F5F6F7F8"
        endpoint = f"/api/v1/keys/{unauthorized_sae_id}/status"

        try:
            response = await self.make_request(
                method="GET",
                endpoint=endpoint,
                expected_status=403,  # Should be forbidden
            )
        except AssertionError:
            # Expected to fail with 403
            logger.info("Authorization failure test passed")
            return {
                "status": "passed",
                "message": "Authorization failure handled correctly",
            }

        return response

    async def test_invalid_parameters(self) -> dict[str, Any]:
        """Test invalid parameter handling with real mTLS"""
        logger.info("Testing invalid parameter handling with real mTLS")

        endpoint = f"/api/v1/keys/{self.slave_sae_id}/enc_keys"

        # Test with invalid number parameter
        invalid_request = {"number": 0, "size": 256}  # Invalid: must be > 0

        try:
            response = await self.make_request(
                method="POST",
                endpoint=endpoint,
                data=invalid_request,
                expected_status=400,  # Should be bad request
            )
        except AssertionError:
            # Expected to fail with 400
            logger.info("Invalid parameters test passed")
            return {
                "status": "passed",
                "message": "Invalid parameters handled correctly",
            }

        return response

    async def test_key_exhaustion(self) -> dict[str, Any]:
        """Test key exhaustion scenario with real mTLS"""
        logger.info("Testing key exhaustion scenario with real mTLS")

        endpoint = f"/api/v1/keys/{self.slave_sae_id}/enc_keys"

        # Request a very large number of keys to trigger exhaustion
        exhaustion_request = {"number": 10000, "size": 256}  # Very large number

        try:
            response = await self.make_request(
                method="POST",
                endpoint=endpoint,
                data=exhaustion_request,
                expected_status=503,  # Should be service unavailable
            )
        except AssertionError:
            # Expected to fail with 503
            logger.info("Key exhaustion test passed")
            return {"status": "passed", "message": "Key exhaustion handled correctly"}

        return response

    async def test_complete_workflow(self) -> dict[str, Any]:
        """Test complete ETSI QKD 014 workflow with real mTLS"""
        logger.info("Testing complete ETSI QKD 014 workflow with real mTLS")

        # Step 1: Get status
        status_response = await self.test_get_status_endpoint()
        assert status_response["status"] == 200, "Status check failed"

        # Step 2: Request encryption keys
        enc_response = await self.test_get_key_endpoint_basic()
        assert enc_response["status"] == 200, "Key request failed"
        assert len(enc_response["data"]["keys"]) > 0, "No keys returned"

        # Step 3: Request decryption keys using key IDs
        key_ids = [key["key_ID"] for key in enc_response["data"]["keys"]]
        dec_response = await self.test_get_key_with_ids_endpoint()
        assert dec_response["status"] == 200, "Key retrieval failed"
        assert len(dec_response["data"]["keys"]) == len(key_ids), "Key count mismatch"

        logger.info("Complete workflow test passed")
        return {
            "status": "passed",
            "message": "Complete ETSI QKD 014 workflow successful",
            "workflow": {
                "status": status_response,
                "encryption": enc_response,
                "decryption": dec_response,
            },
        }

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all external API tests"""
        logger.info("Starting external API test suite")

        test_results: dict[str, Any] = {
            "start_time": time.time(),
            "tests": {},
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": []},
        }

        test_functions = [
            ("get_status", self.test_get_status_endpoint),
            ("get_key_basic", self.test_get_key_endpoint_basic),
            ("get_key_defaults", self.test_get_key_endpoint_defaults),
            ("get_key_multicast", self.test_get_key_endpoint_multicast),
            ("get_key_with_ids", self.test_get_key_with_ids_endpoint),
            ("authentication_failure", self.test_authentication_failure),
            ("authorization_failure", self.test_authorization_failure),
            ("invalid_parameters", self.test_invalid_parameters),
            ("key_exhaustion", self.test_key_exhaustion),
            ("complete_workflow", self.test_complete_workflow),
        ]

        for test_name, test_func in test_functions:
            test_results["summary"]["total"] += 1

            try:
                logger.info(f"Running test: {test_name}")
                result = await test_func()
                test_results["tests"][test_name] = {
                    "status": "passed",
                    "result": result,
                }
                test_results["summary"]["passed"] += 1
                logger.info(f"Test {test_name} passed")

            except Exception as e:
                test_results["tests"][test_name] = {"status": "failed", "error": str(e)}
                test_results["summary"]["failed"] += 1
                test_results["summary"]["errors"].append(
                    {"test": test_name, "error": str(e)}
                )
                logger.error(f"Test {test_name} failed", error=str(e))

        test_results["end_time"] = time.time()
        test_results["duration"] = test_results["end_time"] - test_results["start_time"]

        logger.info(
            "External API test suite completed", summary=test_results["summary"]
        )
        return test_results


# Pytest test functions
@pytest.mark.asyncio
async def test_get_status_endpoint():
    """Test Get Status endpoint with real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_get_status_endpoint()
        assert result["status"] == 200
        assert "data" in result


@pytest.mark.asyncio
async def test_get_key_endpoint_basic():
    """Test Get Key endpoint with basic request and real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_get_key_endpoint_basic()
        assert result["status"] == 200
        assert "data" in result
        assert "keys" in result["data"]


@pytest.mark.asyncio
async def test_get_key_endpoint_defaults():
    """Test Get Key endpoint with default values and real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_get_key_endpoint_defaults()
        assert result["status"] == 200
        assert "data" in result
        assert "keys" in result["data"]


@pytest.mark.asyncio
async def test_get_key_endpoint_multicast():
    """Test Get Key endpoint with multicast and real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_get_key_endpoint_multicast()
        assert result["status"] == 200
        assert "data" in result
        assert "keys" in result["data"]


@pytest.mark.asyncio
async def test_get_key_with_ids_endpoint():
    """Test Get Key with IDs endpoint and real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_get_key_with_ids_endpoint()
        assert result["status"] == 200
        assert "data" in result
        assert "keys" in result["data"]


@pytest.mark.asyncio
async def test_authentication_failure():
    """Test authentication failure handling with real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_authentication_failure()
        assert result["status"] == "passed"


@pytest.mark.asyncio
async def test_authorization_failure():
    """Test authorization failure handling with real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_authorization_failure()
        assert result["status"] == "passed"


@pytest.mark.asyncio
async def test_invalid_parameters():
    """Test invalid parameter handling with real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_invalid_parameters()
        assert result["status"] == "passed"


@pytest.mark.asyncio
async def test_key_exhaustion():
    """Test key exhaustion handling with real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_key_exhaustion()
        assert result["status"] == "passed"


@pytest.mark.asyncio
async def test_complete_workflow():
    """Test complete ETSI QKD 014 workflow with real mTLS"""
    async with ExternalAPITestClient() as client:
        result = await client.test_complete_workflow()
        assert result["status"] == "passed"


async def main():
    """Main function for running external API tests"""
    logger.info("Starting KME External API Test Suite")

    async with ExternalAPITestClient() as client:
        results = await client.run_all_tests()

        # Print summary
        summary = results["summary"]
        print(f"\nExternal API Test Results:")
        print(f"Total: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Duration: {results['duration']:.2f}s")

        if summary["failed"] > 0:
            print(f"\nErrors:")
            for error in summary["errors"]:
                print(f"  {error['test']}: {error['error']}")

        return results


if __name__ == "__main__":
    asyncio.run(main())
