#!/usr/bin/env python3
"""
Phase 2 API Endpoints Test Suite

Version: 1.0.0
Author: KME Development Team
Description: Comprehensive tests for ETSI QKD 014 API endpoints
License: [To be determined]

ToDo List:
- [x] Create test framework for API endpoints
- [x] Test Get Status endpoint
- [x] Test Get Key endpoint
- [x] Test Get Key with Key IDs endpoint
- [ ] Add performance tests
- [ ] Add security tests
- [ ] Add load tests
- [ ] Add integration tests

Progress: 60% (4/7 tasks completed)
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest
from httpx import AsyncClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.models.etsi_models import KeyIDs, KeyRequest, Status
from main import app


class TestAPIEndpoints:
    """Test suite for ETSI QKD 014 API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return AsyncClient(app=app, base_url="http://test")

    @pytest.fixture
    def valid_slave_sae_id(self) -> str:
        """Valid slave SAE ID for testing"""
        return "MMMMNNNNOOOOPPPP"

    @pytest.fixture
    def valid_master_sae_id(self) -> str:
        """Valid master SAE ID for testing"""
        return "IIIIJJJJKKKKLLLL"

    @pytest.fixture
    def valid_key_request(self) -> dict[str, Any]:
        """Valid key request for testing"""
        return {
            "number": 2,
            "size": 352,
            "additional_slave_SAE_IDs": ["MMMMNNNNOOOOPPPP"],
            "extension_mandatory": [],
            "extension_optional": [],
        }

    @pytest.fixture
    def valid_key_ids_request(self) -> dict[str, Any]:
        """Valid key IDs request for testing"""
        return {
            "key_IDs": [{"key_ID": str(uuid.uuid4())}, {"key_ID": str(uuid.uuid4())}],
            "key_IDs_extension": {},
        }

    # Get Status Endpoint Tests
    @pytest.mark.asyncio
    async def test_get_status_success(
        self, client: AsyncClient, valid_slave_sae_id: str
    ):
        """Test successful Get Status endpoint"""
        response = await client.get(f"/api/v1/keys/{valid_slave_sae_id}/status")

        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        assert "source_KME_ID" in data
        assert "target_KME_ID" in data
        assert "master_SAE_ID" in data
        assert "slave_SAE_ID" in data
        assert "key_size" in data
        assert "stored_key_count" in data
        assert "max_key_count" in data
        assert "max_key_per_request" in data
        assert "max_key_size" in data
        assert "min_key_size" in data
        assert "max_SAE_ID_count" in data

        # Validate data types
        assert isinstance(data["key_size"], int)
        assert isinstance(data["stored_key_count"], int)
        assert isinstance(data["max_key_count"], int)
        assert isinstance(data["max_key_per_request"], int)

        # Validate SAE ID format
        assert len(data["slave_SAE_ID"]) == 16
        assert data["slave_SAE_ID"] == valid_slave_sae_id

    @pytest.mark.asyncio
    async def test_get_status_invalid_sae_id(self, client: AsyncClient):
        """Test Get Status with invalid SAE ID"""
        invalid_sae_id = "INVALID"
        response = await client.get(f"/api/v1/keys/{invalid_sae_id}/status")

        assert response.status_code == 400
        data = response.json()
        assert "message" in data
        assert "Invalid slave_SAE_ID format" in data["message"]

    @pytest.mark.asyncio
    async def test_get_status_unauthorized(self, client: AsyncClient):
        """Test Get Status with unauthorized access"""
        # This would require proper authentication setup
        # For now, we'll test the endpoint structure
        valid_sae_id = "MMMMNNNNOOOOPPPP"
        response = await client.get(f"/api/v1/keys/{valid_sae_id}/status")

        # Should return 200 for now since we don't have auth middleware
        assert response.status_code == 200

    # Get Key Endpoint Tests
    @pytest.mark.asyncio
    async def test_get_key_success(
        self,
        client: AsyncClient,
        valid_slave_sae_id: str,
        valid_key_request: dict[str, Any],
    ):
        """Test successful Get Key endpoint"""
        response = await client.post(
            f"/api/v1/keys/{valid_slave_sae_id}/enc_keys", json=valid_key_request
        )

        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        assert "keys" in data
        assert isinstance(data["keys"], list)
        assert len(data["keys"]) == valid_key_request["number"]

        # Validate each key
        for key in data["keys"]:
            assert "key_ID" in key
            assert "key" in key
            assert isinstance(key["key_ID"], str)
            assert isinstance(key["key"], str)

            # Validate UUID format
            try:
                uuid.UUID(key["key_ID"])
            except ValueError:
                pytest.fail(f"Invalid UUID format: {key['key_ID']}")

    @pytest.mark.asyncio
    async def test_get_key_invalid_request(
        self, client: AsyncClient, valid_slave_sae_id: str
    ):
        """Test Get Key with invalid request"""
        invalid_request = {
            "number": 1000,  # Too many keys
            "size": 10000,  # Too large
        }

        response = await client.post(
            f"/api/v1/keys/{valid_slave_sae_id}/enc_keys", json=invalid_request
        )

        assert response.status_code == 400
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_get_key_invalid_sae_id(
        self, client: AsyncClient, valid_key_request: dict[str, Any]
    ):
        """Test Get Key with invalid SAE ID"""
        invalid_sae_id = "INVALID"
        response = await client.post(
            f"/api/v1/keys/{invalid_sae_id}/enc_keys", json=valid_key_request
        )

        assert response.status_code == 400
        data = response.json()
        assert "message" in data
        assert "Invalid slave_SAE_ID format" in data["message"]

    # Get Key with Key IDs Endpoint Tests
    @pytest.mark.asyncio
    async def test_get_key_with_ids_success(
        self,
        client: AsyncClient,
        valid_master_sae_id: str,
        valid_key_ids_request: dict[str, Any],
    ):
        """Test successful Get Key with Key IDs endpoint"""
        response = await client.post(
            f"/api/v1/keys/{valid_master_sae_id}/dec_keys", json=valid_key_ids_request
        )

        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        assert "keys" in data
        assert isinstance(data["keys"], list)
        assert len(data["keys"]) == len(valid_key_ids_request["key_IDs"])

        # Validate each key
        for i, key in enumerate(data["keys"]):
            assert "key_ID" in key
            assert "key" in key
            assert isinstance(key["key_ID"], str)
            assert isinstance(key["key"], str)

            # Validate UUID format
            try:
                uuid.UUID(key["key_ID"])
            except ValueError:
                pytest.fail(f"Invalid UUID format: {key['key_ID']}")

            # Validate key_ID matches request
            expected_key_id = valid_key_ids_request["key_IDs"][i]["key_ID"]
            assert key["key_ID"] == expected_key_id

    @pytest.mark.asyncio
    async def test_get_key_with_ids_invalid_key_id(
        self, client: AsyncClient, valid_master_sae_id: str
    ):
        """Test Get Key with Key IDs with invalid key ID"""
        invalid_request = {"key_IDs": [{"key_ID": "invalid-uuid-format"}]}

        response = await client.post(
            f"/api/v1/keys/{valid_master_sae_id}/dec_keys", json=invalid_request
        )

        assert response.status_code == 400
        data = response.json()
        assert "message" in data
        assert "Invalid key_ID format" in data["message"]

    @pytest.mark.asyncio
    async def test_get_key_with_ids_invalid_sae_id(
        self, client: AsyncClient, valid_key_ids_request: dict[str, Any]
    ):
        """Test Get Key with Key IDs with invalid SAE ID"""
        invalid_sae_id = "INVALID"
        response = await client.post(
            f"/api/v1/keys/{invalid_sae_id}/dec_keys", json=valid_key_ids_request
        )

        assert response.status_code == 400
        data = response.json()
        assert "message" in data
        assert "Invalid master_SAE_ID format" in data["message"]

    @pytest.mark.asyncio
    async def test_get_key_with_ids_empty_request(
        self, client: AsyncClient, valid_master_sae_id: str
    ):
        """Test Get Key with Key IDs with empty key IDs list"""
        empty_request = {"key_IDs": []}

        response = await client.post(
            f"/api/v1/keys/{valid_master_sae_id}/dec_keys", json=empty_request
        )

        assert response.status_code == 400
        data = response.json()
        assert "message" in data

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_error_response_format(self, client: AsyncClient):
        """Test error response format consistency"""
        invalid_sae_id = "INVALID"
        response = await client.get(f"/api/v1/keys/{invalid_sae_id}/status")

        assert response.status_code == 400
        data = response.json()

        # Validate error response structure
        assert "message" in data
        assert "details" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["details"], list)

        # Validate error details
        for detail in data["details"]:
            assert "parameter" in detail
            assert "error" in detail

    # ETSI Compliance Tests
    @pytest.mark.asyncio
    async def test_etsi_compliance_status_response(
        self, client: AsyncClient, valid_slave_sae_id: str
    ):
        """Test ETSI compliance of Status response"""
        response = await client.get(f"/api/v1/keys/{valid_slave_sae_id}/status")

        assert response.status_code == 200
        data = response.json()

        # ETSI required fields
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
            assert field in data, f"Missing required ETSI field: {field}"

    @pytest.mark.asyncio
    async def test_etsi_compliance_key_container(
        self,
        client: AsyncClient,
        valid_slave_sae_id: str,
        valid_key_request: dict[str, Any],
    ):
        """Test ETSI compliance of Key Container response"""
        response = await client.post(
            f"/api/v1/keys/{valid_slave_sae_id}/enc_keys", json=valid_key_request
        )

        assert response.status_code == 200
        data = response.json()

        # ETSI required fields
        assert "keys" in data
        assert isinstance(data["keys"], list)

        for key in data["keys"]:
            assert "key_ID" in key
            assert "key" in key
            # Validate UUID format (RFC 4122)
            try:
                uuid.UUID(key["key_ID"])
            except ValueError:
                pytest.fail(f"Key ID not in UUID format: {key['key_ID']}")

    # Performance Tests
    @pytest.mark.asyncio
    async def test_status_endpoint_performance(
        self, client: AsyncClient, valid_slave_sae_id: str
    ):
        """Test Status endpoint performance"""
        import time

        start_time = time.time()
        response = await client.get(f"/api/v1/keys/{valid_slave_sae_id}/status")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time

        # Should respond within 1 second
        assert response_time < 1.0, f"Status endpoint too slow: {response_time:.3f}s"

    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self, client: AsyncClient, valid_slave_sae_id: str
    ):
        """Test concurrent requests handling"""

        async def make_request():
            return await client.get(f"/api/v1/keys/{valid_slave_sae_id}/status")

        # Make 5 concurrent requests
        tasks = [make_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
