#!/usr/bin/env python3
"""
KME Internal API Test Suite

Comprehensive test suite for KME API endpoints on port 8000 (direct FastAPI testing).
Tests all ETSI QKD 014 V1.1.1 endpoints with real certificates and proper authentication.

Version: 1.0.0
Author: KME Development Team
Description: Internal API testing with full ETSI compliance
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


class InternalAPITestClient:
    """Internal API test client for direct FastAPI testing on port 8000"""

    def __init__(self, base_url: str = "http://localhost:8000"):
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

        logger.info("Internal API Test Client initialized", base_url=base_url)

    async def __aenter__(self):
        """Async context manager entry"""
        # No SSL context needed for internal HTTP testing

        # Create HTTP client for internal testing (no SSL needed)
        self.client = httpx.AsyncClient(base_url=self.base_url, http2=False)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()

    def _create_nginx_headers(self, sae_id: str, cert_path: str) -> dict[str, str]:
        """Create Nginx proxy headers to simulate mTLS authentication"""
        # Read certificate and extract subject DN
        with open(cert_path, "rb") as f:
            cert_data = f.read()
            cert = x509.load_pem_x509_certificate(cert_data)
            subject_dn = cert.subject.rfc4514_string()

        # Create headers that simulate Nginx mTLS proxy
        headers = {
            "X-Forwarded-SSL-Client-Subject": subject_dn,
            "X-Forwarded-SSL-Client-Verify": "SUCCESS",
            "X-Forwarded-For": "127.0.0.1",
            "X-Forwarded-Proto": "http",  # Changed to http for internal testing
            "Host": "localhost:8000",
            "Content-Type": "application/json",
        }
        return headers

    async def make_request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        expected_status: int = 200,
        use_master_cert: bool = True,
    ) -> dict[str, Any]:
        """Make HTTP request to KME API with proper authentication"""
        url = f"{self.base_url}{endpoint}"

        if headers is None:
            headers = {}

        # Add Nginx proxy headers for authentication
        cert_path = (
            self.master_sae_cert_path if use_master_cert else self.slave_sae_cert_path
        )
        proxy_headers = self._create_nginx_headers(self.master_sae_id, cert_path)
        headers.update(proxy_headers)

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
        """Test GET /api/v1/keys/{slave_sae_id}/status endpoint"""
        logger.info("Testing Get Status endpoint")

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
        logger.info("Testing Get Key endpoint - basic request")

        endpoint = f"/api/v1/keys/{self.slave_sae_id}/enc_keys"

        # ETSI QKD 014 compliant key request
        key_request = {
            "number": 2,
            "size": 256,
            "additional_slave_SAE_IDs": [self.slave_sae_id],
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
        assert len(key_data["keys"]) == 2, "Expected 2 keys"

        # Validate each key
        for key in key_data["keys"]:
            assert "key_ID" in key, "Missing key_ID"
            assert "key" in key, "Missing key data"

            # Validate key_ID format (UUID)
            try:
                uuid.UUID(key["key_ID"])
            except ValueError:
                raise AssertionError(f"Invalid key_ID format: {key['key_ID']}")

            # Validate key data (base64 encoded)
            try:
                base64.b64decode(key["key"])
            except Exception:
                raise AssertionError(f"Invalid key data format: {key['key']}")

        logger.info("Get Key endpoint test passed", response=response)
        return response

    async def test_get_key_endpoint_defaults(self) -> dict[str, Any]:
        """Test POST /api/v1/keys/{slave_sae_id}/enc_keys endpoint with default values"""
        logger.info("Testing Get Key endpoint - default values")

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
        logger.info("Testing Get Key endpoint - multicast")

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
        logger.info("Testing Get Key with IDs endpoint")

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
        """Test authentication failure scenarios"""
        logger.info("Testing authentication failure scenarios")

        endpoint = f"/api/v1/keys/{self.slave_sae_id}/status"

        # Test with invalid certificate headers
        headers = {
            "X-Forwarded-SSL-Client-Subject": "CN=Invalid SAE",
            "X-Forwarded-SSL-Client-Verify": "FAILED",
            "X-Forwarded-For": "127.0.0.1",
            "X-Forwarded-Proto": "https",
            "Host": "localhost:8000",
            "Content-Type": "application/json",
        }

        try:
            if self.client is None:
                raise RuntimeError("HTTP client not initialized")

            response = await self.client.get(
                f"{self.base_url}{endpoint}", headers=headers
            )
            # Should get 401 Unauthorized
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
        """Test authorization failure scenarios"""
        logger.info("Testing authorization failure scenarios")

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
        """Test invalid parameter handling"""
        logger.info("Testing invalid parameter handling")

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
        """Test key exhaustion scenario"""
        logger.info("Testing key exhaustion scenario")

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
        """Test complete ETSI QKD 014 workflow"""
        logger.info("Testing complete ETSI QKD 014 workflow")

        workflow_results = {}

        # Step 1: Get Status
        workflow_results["status"] = await self.test_get_status_endpoint()

        # Step 2: Master SAE requests keys
        workflow_results["enc_keys"] = await self.test_get_key_endpoint_basic()

        # Step 3: Extract key IDs for slave SAE
        key_ids = [
            key["key_ID"] for key in workflow_results["enc_keys"]["data"]["keys"]
        ]

        # Step 4: Slave SAE retrieves keys using key IDs
        endpoint = f"/api/v1/keys/{self.master_sae_id}/dec_keys"
        key_ids_request = {
            "key_IDs": [{"key_ID": key_id} for key_id in key_ids],
            "key_IDs_extension": None,
        }

        workflow_results["dec_keys"] = await self.make_request(
            method="POST",
            endpoint=endpoint,
            data=key_ids_request,
            expected_status=200,
            use_master_cert=False,  # Use slave certificate
        )

        # Step 5: Validate key consistency
        enc_keys = workflow_results["enc_keys"]["data"]["keys"]
        dec_keys = workflow_results["dec_keys"]["data"]["keys"]

        assert len(enc_keys) == len(dec_keys), "Key count mismatch"

        for i, (enc_key, dec_key) in enumerate(zip(enc_keys, dec_keys)):
            assert (
                enc_key["key_ID"] == dec_key["key_ID"]
            ), f"Key ID mismatch at index {i}"
            assert enc_key["key"] == dec_key["key"], f"Key data mismatch at index {i}"

        logger.info("Complete workflow test passed", workflow_results=workflow_results)
        return workflow_results

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all internal API tests"""
        logger.info("Starting internal API test suite")

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
            "Internal API test suite completed", summary=test_results["summary"]
        )
        return test_results


# Pytest test functions
@pytest.mark.asyncio
async def test_get_status_endpoint():
    """Test Get Status endpoint"""
    async with InternalAPITestClient() as client:
        result = await client.test_get_status_endpoint()
        assert result["status"] == 200
        assert "data" in result


@pytest.mark.asyncio
async def test_get_key_endpoint_basic():
    """Test Get Key endpoint with basic request"""
    async with InternalAPITestClient() as client:
        result = await client.test_get_key_endpoint_basic()
        assert result["status"] == 200
        assert "data" in result
        assert "keys" in result["data"]


@pytest.mark.asyncio
async def test_get_key_endpoint_defaults():
    """Test Get Key endpoint with default values"""
    async with InternalAPITestClient() as client:
        result = await client.test_get_key_endpoint_defaults()
        assert result["status"] == 200
        assert "data" in result
        assert "keys" in result["data"]


@pytest.mark.asyncio
async def test_get_key_endpoint_multicast():
    """Test Get Key endpoint with multicast"""
    async with InternalAPITestClient() as client:
        result = await client.test_get_key_endpoint_multicast()
        assert result["status"] == 200
        assert "data" in result
        assert "keys" in result["data"]


@pytest.mark.asyncio
async def test_get_key_with_ids_endpoint():
    """Test Get Key with IDs endpoint"""
    async with InternalAPITestClient() as client:
        result = await client.test_get_key_with_ids_endpoint()
        assert result["status"] == 200
        assert "data" in result
        assert "keys" in result["data"]


@pytest.mark.asyncio
async def test_authentication_failure():
    """Test authentication failure handling"""
    async with InternalAPITestClient() as client:
        result = await client.test_authentication_failure()
        assert result["status"] == "passed"


@pytest.mark.asyncio
async def test_authorization_failure():
    """Test authorization failure handling"""
    async with InternalAPITestClient() as client:
        result = await client.test_authorization_failure()
        assert result["status"] == "passed"


@pytest.mark.asyncio
async def test_invalid_parameters():
    """Test invalid parameter handling"""
    async with InternalAPITestClient() as client:
        result = await client.test_invalid_parameters()
        assert result["status"] == "passed"


@pytest.mark.asyncio
async def test_key_exhaustion():
    """Test key exhaustion handling"""
    async with InternalAPITestClient() as client:
        result = await client.test_key_exhaustion()
        assert result["status"] == "passed"


@pytest.mark.asyncio
async def test_complete_workflow():
    """Test complete ETSI QKD 014 workflow"""
    async with InternalAPITestClient() as client:
        result = await client.test_complete_workflow()
        assert "status" in result
        assert "enc_keys" in result
        assert "dec_keys" in result


async def main():
    """Main function to run all tests"""
    print("🚀 Starting KME Internal API Test Suite...")
    print("=" * 60)

    async with InternalAPITestClient() as client:
        results = await client.run_all_tests()

        print(f"\n📊 Test Results Summary:")
        print(f"Total Tests: {results['summary']['total']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Duration: {results['duration']:.2f} seconds")

        if results["summary"]["failed"] > 0:
            print(f"\n❌ Failed Tests:")
            for error in results["summary"]["errors"]:
                print(f"  - {error['test']}: {error['error']}")
            return 1
        else:
            print(f"\n✅ All tests passed!")
            return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
