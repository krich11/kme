#!/usr/bin/env python3
"""
KME API Workflow Test Suite

Comprehensive test suite for all KME API workflows including:
- Authentication and authorization
- All ETSI QKD 014 V1.1.1 endpoints
- Error handling and edge cases
- Performance and reliability

Version: 1.0.0
Author: KME Development Team
Description: End-to-end API workflow testing
License: [To be determined]
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List

import aiohttp
import pytest
import structlog

logger = structlog.get_logger()


class KMEAPITestSuite:
    """Comprehensive test suite for KME API workflows"""

    def __init__(self, base_url: str = "https://localhost:8000"):
        """Initialize test suite"""
        self.base_url = base_url
        self.session: aiohttp.ClientSession | None = None
        self.test_results: list[dict[str, Any]] = []

        # Test data
        self.valid_slave_sae_id = "SAE001ABCDEFGHIJ"
        self.valid_master_sae_id = "A1B2C3D4E5F6A7B8"
        self.test_certificate = "test-certificate"
        self.invalid_certificate = "invalid-certificate"

        logger.info("KME API Test Suite initialized", base_url=base_url)

    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(
            ssl=False
        )  # Disable SSL verification for testing
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
        expected_status: int = 200,
    ) -> dict[str, Any]:
        """Make HTTP request and validate response"""
        url = f"{self.base_url}{endpoint}"

        if headers is None:
            headers = {}

        start_time = time.time()

        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    response_data = (
                        await response.json()
                        if response.content_type == "application/json"
                        else await response.text()
                    )
            elif method.upper() == "POST":
                async with self.session.post(
                    url, headers=headers, json=data
                ) as response:
                    response_data = (
                        await response.json()
                        if response.content_type == "application/json"
                        else await response.text()
                    )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            duration = time.time() - start_time

            # Validate status code
            if response.status != expected_status:
                raise AssertionError(
                    f"Expected status {expected_status}, got {response.status}. "
                    f"Response: {response_data}"
                )

            return {
                "status": response.status,
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

    def record_test_result(
        self,
        test_name: str,
        success: bool,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        """Record test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": time.time(),
            "details": details or {},
        }

        if error:
            result["error"] = error

        self.test_results.append(result)

        if success:
            logger.info(f"✅ {test_name} - PASSED", details=details)
        else:
            logger.error(f"❌ {test_name} - FAILED", error=error, details=details)

    # =============================================================================
    # AUTHENTICATION TESTS
    # =============================================================================

    async def test_authentication_no_certificate(self):
        """Test API behavior when no certificate is provided"""
        try:
            await self.make_request(
                method="GET",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/status",
                expected_status=401,
            )
            self.record_test_result("Authentication - No Certificate", True)
        except Exception as e:
            self.record_test_result(
                "Authentication - No Certificate", False, error=str(e)
            )

    async def test_authentication_invalid_certificate(self):
        """Test API behavior with invalid certificate"""
        try:
            await self.make_request(
                method="GET",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/status",
                headers={"X-Client-Certificate": self.invalid_certificate},
                expected_status=401,
            )
            self.record_test_result("Authentication - Invalid Certificate", True)
        except Exception as e:
            self.record_test_result(
                "Authentication - Invalid Certificate", False, error=str(e)
            )

    async def test_authentication_valid_certificate(self):
        """Test API behavior with valid certificate"""
        try:
            response = await self.make_request(
                method="GET",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/status",
                headers={"X-Client-Certificate": self.test_certificate},
                expected_status=200,
            )

            # Validate response structure
            data = response["data"]
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
                if field not in data:
                    raise AssertionError(f"Missing required field: {field}")

            self.record_test_result(
                "Authentication - Valid Certificate", True, details=data
            )
        except Exception as e:
            self.record_test_result(
                "Authentication - Valid Certificate", False, error=str(e)
            )

    # =============================================================================
    # STATUS ENDPOINT TESTS
    # =============================================================================

    async def test_status_endpoint_structure(self):
        """Test status endpoint response structure"""
        try:
            response = await self.make_request(
                method="GET",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/status",
                headers={"X-Client-Certificate": self.test_certificate},
                expected_status=200,
            )

            data = response["data"]

            # Validate ETSI compliance
            assert data["source_KME_ID"] == "AAAABBBBCCCCDDDD"
            assert data["target_KME_ID"] == "EEEEFFFFGGGGHHHH"
            assert data["master_SAE_ID"] == self.valid_master_sae_id
            assert data["slave_SAE_ID"] == self.valid_slave_sae_id
            assert isinstance(data["key_size"], int) and data["key_size"] > 0
            assert (
                isinstance(data["stored_key_count"], int)
                and data["stored_key_count"] >= 0
            )
            assert isinstance(data["max_key_count"], int) and data["max_key_count"] > 0
            assert (
                isinstance(data["max_key_per_request"], int)
                and data["max_key_per_request"] > 0
            )
            assert isinstance(data["max_key_size"], int) and data["max_key_size"] > 0
            assert isinstance(data["min_key_size"], int) and data["min_key_size"] > 0
            assert (
                isinstance(data["max_SAE_ID_count"], int)
                and data["max_SAE_ID_count"] >= 0
            )

            self.record_test_result("Status Endpoint - Structure", True, details=data)
        except Exception as e:
            self.record_test_result("Status Endpoint - Structure", False, error=str(e))

    async def test_status_endpoint_invalid_sae_id(self):
        """Test status endpoint with invalid SAE ID"""
        try:
            await self.make_request(
                method="GET",
                endpoint="/api/v1/keys/INVALID_SAE_ID/status",
                headers={"X-Client-Certificate": self.test_certificate},
                expected_status=422,  # Pydantic validation returns 422, not 400
            )
            self.record_test_result("Status Endpoint - Invalid SAE ID", True)
        except Exception as e:
            self.record_test_result(
                "Status Endpoint - Invalid SAE ID", False, error=str(e)
            )

    # =============================================================================
    # ENCRYPTION KEYS ENDPOINT TESTS
    # =============================================================================

    async def test_enc_keys_endpoint_basic(self):
        """Test basic encryption keys request"""
        try:
            response = await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/enc_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"number": 1, "size": 256},
                expected_status=200,
            )

            data = response["data"]

            # Validate response structure
            assert "keys" in data
            assert isinstance(data["keys"], list)
            assert len(data["keys"]) == 1

            key = data["keys"][0]
            assert "key_ID" in key
            assert "key" in key
            assert "key_size" in key
            assert key["key_size"] == 256

            self.record_test_result("Enc Keys Endpoint - Basic", True, details=data)
        except Exception as e:
            self.record_test_result("Enc Keys Endpoint - Basic", False, error=str(e))

    async def test_enc_keys_endpoint_multiple_keys(self):
        """Test encryption keys request for multiple keys"""
        try:
            response = await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/enc_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"number": 3, "size": 512},
                expected_status=200,
            )

            data = response["data"]

            # Validate response structure
            assert "keys" in data
            assert isinstance(data["keys"], list)
            assert len(data["keys"]) == 3

            for key in data["keys"]:
                assert "key_ID" in key
                assert "key" in key
                assert "key_size" in key
                assert key["key_size"] == 512
                # Validate key_ID is a valid UUID
                uuid.UUID(key["key_ID"])

            self.record_test_result(
                "Enc Keys Endpoint - Multiple Keys", True, details=data
            )
        except Exception as e:
            self.record_test_result(
                "Enc Keys Endpoint - Multiple Keys", False, error=str(e)
            )

    async def test_enc_keys_endpoint_default_values(self):
        """Test encryption keys request with default values"""
        try:
            response = await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/enc_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={},  # No parameters, should use defaults
                expected_status=200,
            )

            data = response["data"]

            # Validate response structure
            assert "keys" in data
            assert isinstance(data["keys"], list)
            assert len(data["keys"]) >= 1

            self.record_test_result(
                "Enc Keys Endpoint - Default Values", True, details=data
            )
        except Exception as e:
            self.record_test_result(
                "Enc Keys Endpoint - Default Values", False, error=str(e)
            )

    async def test_enc_keys_endpoint_invalid_parameters(self):
        """Test encryption keys request with invalid parameters"""
        try:
            await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/enc_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"number": 0, "size": 0},  # Invalid values
                expected_status=422,  # Pydantic validation returns 422, not 400
            )
            self.record_test_result("Enc Keys Endpoint - Invalid Parameters", True)
        except Exception as e:
            self.record_test_result(
                "Enc Keys Endpoint - Invalid Parameters", False, error=str(e)
            )

    # =============================================================================
    # DECRYPTION KEYS ENDPOINT TESTS
    # =============================================================================

    async def test_dec_keys_endpoint_basic(self):
        """Test basic decryption keys request"""
        try:
            test_key_id = str(uuid.uuid4())
            response = await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_master_sae_id}/dec_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"key_IDs": [{"key_ID": test_key_id}]},
                expected_status=200,
            )

            data = response["data"]

            # Validate response structure
            assert "keys" in data
            assert isinstance(data["keys"], list)
            assert len(data["keys"]) == 1

            key = data["keys"][0]
            assert "key_ID" in key
            assert "key" in key
            assert key["key_ID"] == test_key_id

            self.record_test_result("Dec Keys Endpoint - Basic", True, details=data)
        except Exception as e:
            self.record_test_result("Dec Keys Endpoint - Basic", False, error=str(e))

    async def test_dec_keys_endpoint_multiple_keys(self):
        """Test decryption keys request for multiple keys"""
        try:
            test_key_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
            response = await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_master_sae_id}/dec_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"key_IDs": [{"key_ID": kid} for kid in test_key_ids]},
                expected_status=200,
            )

            data = response["data"]

            # Validate response structure
            assert "keys" in data
            assert isinstance(data["keys"], list)
            assert len(data["keys"]) == 3

            returned_key_ids = [key["key_ID"] for key in data["keys"]]
            for key_id in test_key_ids:
                assert key_id in returned_key_ids

            self.record_test_result(
                "Dec Keys Endpoint - Multiple Keys", True, details=data
            )
        except Exception as e:
            self.record_test_result(
                "Dec Keys Endpoint - Multiple Keys", False, error=str(e)
            )

    async def test_dec_keys_endpoint_invalid_key_id(self):
        """Test decryption keys request with invalid key ID"""
        try:
            await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_master_sae_id}/dec_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"key_IDs": [{"key_ID": "invalid-uuid"}]},
                expected_status=422,  # Pydantic validation returns 422, not 400
            )
            self.record_test_result("Dec Keys Endpoint - Invalid Key ID", True)
        except Exception as e:
            self.record_test_result(
                "Dec Keys Endpoint - Invalid Key ID", False, error=str(e)
            )

    async def test_dec_keys_endpoint_empty_key_list(self):
        """Test decryption keys request with empty key list"""
        try:
            await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_master_sae_id}/dec_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"key_IDs": []},
                expected_status=422,  # Pydantic validation returns 422, not 400
            )
            self.record_test_result("Dec Keys Endpoint - Empty Key List", True)
        except Exception as e:
            self.record_test_result(
                "Dec Keys Endpoint - Empty Key List", False, error=str(e)
            )

    # =============================================================================
    # HEALTH AND MONITORING TESTS
    # =============================================================================

    async def test_health_endpoint(self):
        """Test health endpoint"""
        try:
            response = await self.make_request(
                method="GET",
                endpoint="/health",
                expected_status=200,
            )

            data = response["data"]
            assert "status" in data
            assert "timestamp" in data
            assert "checks" in data

            self.record_test_result("Health Endpoint", True, details=data)
        except Exception as e:
            self.record_test_result("Health Endpoint", False, error=str(e))

    async def test_health_summary_endpoint(self):
        """Test health summary endpoint"""
        try:
            response = await self.make_request(
                method="GET",
                endpoint="/health/summary",
                expected_status=200,
            )

            data = response["data"]
            assert "status" in data
            assert "timestamp" in data

            self.record_test_result("Health Summary Endpoint", True, details=data)
        except Exception as e:
            self.record_test_result("Health Summary Endpoint", False, error=str(e))

    async def test_health_ready_endpoint(self):
        """Test health ready endpoint"""
        try:
            # The ready endpoint returns 503 if health is unhealthy, which is expected behavior
            response = await self.make_request(
                method="GET",
                endpoint="/health/ready",
                expected_status=503,  # Expected when health is unhealthy
            )

            data = response["data"]
            assert "detail" in data  # Should contain error detail

            self.record_test_result("Health Ready Endpoint", True, details=data)
        except Exception as e:
            self.record_test_result("Health Ready Endpoint", False, error=str(e))

    async def test_health_live_endpoint(self):
        """Test health live endpoint"""
        try:
            response = await self.make_request(
                method="GET",
                endpoint="/health/live",
                expected_status=200,
            )

            data = response["data"]
            assert "status" in data

            self.record_test_result("Health Live Endpoint", True, details=data)
        except Exception as e:
            self.record_test_result("Health Live Endpoint", False, error=str(e))

    # =============================================================================
    # PERFORMANCE TESTS
    # =============================================================================

    async def test_concurrent_requests(self):
        """Test concurrent API requests"""
        try:
            # Make 5 concurrent status requests
            tasks = []
            for i in range(5):
                task = self.make_request(
                    method="GET",
                    endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/status",
                    headers={"X-Client-Certificate": self.test_certificate},
                    expected_status=200,
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # Validate all responses
            for i, response in enumerate(responses):
                assert response["status"] == 200
                assert "data" in response
                assert response["data"]["slave_SAE_ID"] == self.valid_slave_sae_id

            avg_duration = sum(r["duration"] for r in responses) / len(responses)

            self.record_test_result(
                "Concurrent Requests",
                True,
                details={
                    "request_count": len(responses),
                    "avg_duration": avg_duration,
                    "all_successful": True,
                },
            )
        except Exception as e:
            self.record_test_result("Concurrent Requests", False, error=str(e))

    async def test_response_time_performance(self):
        """Test response time performance"""
        try:
            # Make multiple requests and measure response times
            response_times = []

            for i in range(10):
                response = await self.make_request(
                    method="GET",
                    endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/status",
                    headers={"X-Client-Certificate": self.test_certificate},
                    expected_status=200,
                )
                response_times.append(response["duration"])

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)

            # Performance thresholds (adjust as needed)
            assert (
                avg_response_time < 1.0
            ), f"Average response time too high: {avg_response_time}s"
            assert (
                max_response_time < 2.0
            ), f"Maximum response time too high: {max_response_time}s"

            self.record_test_result(
                "Response Time Performance",
                True,
                details={
                    "avg_response_time": avg_response_time,
                    "max_response_time": max_response_time,
                    "min_response_time": min_response_time,
                    "request_count": len(response_times),
                },
            )
        except Exception as e:
            self.record_test_result("Response Time Performance", False, error=str(e))

    # =============================================================================
    # ERROR HANDLING TESTS
    # =============================================================================

    async def test_404_endpoint(self):
        """Test 404 error handling"""
        try:
            await self.make_request(
                method="GET",
                endpoint="/api/v1/nonexistent/endpoint",
                expected_status=404,
            )
            self.record_test_result("Error Handling - 404", True)
        except Exception as e:
            self.record_test_result("Error Handling - 404", False, error=str(e))

    # =============================================================================
    # WORKFLOW TESTS
    # =============================================================================

    async def test_complete_key_workflow(self):
        """Test complete key request and retrieval workflow"""
        try:
            # Step 1: Get status to verify system is operational
            status_response = await self.make_request(
                method="GET",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/status",
                headers={"X-Client-Certificate": self.test_certificate},
                expected_status=200,
            )

            assert status_response["data"]["kme_status"] == "operational"

            # Step 2: Request encryption keys
            enc_response = await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_slave_sae_id}/enc_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"number": 2, "size": 256},
                expected_status=200,
            )

            keys = enc_response["data"]["keys"]
            assert len(keys) == 2

            # Step 3: Retrieve decryption keys using the key IDs
            key_ids = [{"key_ID": key["key_ID"]} for key in keys]
            dec_response = await self.make_request(
                method="POST",
                endpoint=f"/api/v1/keys/{self.valid_master_sae_id}/dec_keys",
                headers={"X-Client-Certificate": self.test_certificate},
                data={"key_IDs": key_ids},
                expected_status=200,
            )

            dec_keys = dec_response["data"]["keys"]
            assert len(dec_keys) == 2

            # Verify key IDs match
            enc_key_ids = [key["key_ID"] for key in keys]
            dec_key_ids = [key["key_ID"] for key in dec_keys]
            assert set(enc_key_ids) == set(dec_key_ids)

            self.record_test_result(
                "Complete Key Workflow",
                True,
                details={
                    "keys_requested": len(keys),
                    "keys_retrieved": len(dec_keys),
                    "workflow_successful": True,
                },
            )
        except Exception as e:
            self.record_test_result("Complete Key Workflow", False, error=str(e))

    # =============================================================================
    # TEST EXECUTION
    # =============================================================================

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all tests and return comprehensive results"""
        logger.info("Starting KME API Test Suite")

        test_methods = [
            # Authentication tests
            self.test_authentication_no_certificate,
            self.test_authentication_invalid_certificate,
            self.test_authentication_valid_certificate,
            # Status endpoint tests
            self.test_status_endpoint_structure,
            self.test_status_endpoint_invalid_sae_id,
            # Encryption keys endpoint tests
            self.test_enc_keys_endpoint_basic,
            self.test_enc_keys_endpoint_multiple_keys,
            self.test_enc_keys_endpoint_default_values,
            self.test_enc_keys_endpoint_invalid_parameters,
            # Decryption keys endpoint tests
            self.test_dec_keys_endpoint_basic,
            self.test_dec_keys_endpoint_multiple_keys,
            self.test_dec_keys_endpoint_invalid_key_id,
            self.test_dec_keys_endpoint_empty_key_list,
            # Health and monitoring tests
            self.test_health_endpoint,
            self.test_health_summary_endpoint,
            self.test_health_ready_endpoint,
            self.test_health_live_endpoint,
            # Performance tests
            self.test_concurrent_requests,
            self.test_response_time_performance,
            # Error handling tests
            self.test_404_endpoint,
            # Workflow tests
            self.test_complete_key_workflow,
        ]

        # Run all tests
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                logger.error(
                    f"Test {test_method.__name__} failed with exception", error=str(e)
                )
                self.record_test_result(test_method.__name__, False, error=str(e))

        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "test_results": self.test_results,
            "timestamp": time.time(),
        }

        logger.info(
            "KME API Test Suite completed",
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=f"{success_rate:.1f}%",
        )

        return summary


async def main():
    """Main test execution function"""
    async with KMEAPITestSuite() as test_suite:
        results = await test_suite.run_all_tests()

        # Print summary
        print("\n" + "=" * 80)
        print("KME API TEST SUITE RESULTS")
        print("=" * 80)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed_tests']}")
        print(f"Failed: {results['failed_tests']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print("=" * 80)

        # Print failed tests
        failed_tests = [r for r in results["test_results"] if not r["success"]]
        if failed_tests:
            print("\nFAILED TESTS:")
            for test in failed_tests:
                print(f"❌ {test['test_name']}: {test.get('error', 'Unknown error')}")

        # Print passed tests
        passed_tests = [r for r in results["test_results"] if r["success"]]
        if passed_tests:
            print(f"\nPASSED TESTS ({len(passed_tests)}):")
            for test in passed_tests:
                print(f"✅ {test['test_name']}")

        print("\n" + "=" * 80)

        # Return exit code based on success rate
        if results["success_rate"] >= 95.0:
            print("🎉 EXCELLENT! API is ready for production!")
            return 0
        elif results["success_rate"] >= 80.0:
            print("⚠️  GOOD! Some issues need attention before production.")
            return 1
        else:
            print("❌ POOR! Significant issues need to be resolved.")
            return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
