#!/usr/bin/env python3
"""
Test Week 5.6 Authentication Middleware Implementation

This test verifies that the enhanced authentication middleware
for Week 5.6 works correctly with proper test certificates.
"""

import asyncio
import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.authentication_middleware import (
    AuthenticationMiddleware,
    get_auth_middleware,
)
from app.core.security import CertificateInfo, CertificateType


class TestWeek56AuthenticationMiddleware:
    """Test Week 5.6 authentication middleware implementation"""

    @pytest.fixture
    def auth_middleware(self):
        """Get authentication middleware instance"""
        return get_auth_middleware()

    @pytest.fixture
    def test_certs_dir(self):
        """Get test certificates directory"""
        return Path(__file__).parent.parent / "test_certs"

    @pytest.fixture
    def master_sae_cert_data(self, test_certs_dir):
        """Load master SAE certificate data"""
        cert_path = test_certs_dir / "master_sae_cert.pem"
        return cert_path.read_bytes()

    @pytest.fixture
    def slave_sae_cert_data(self, test_certs_dir):
        """Load slave SAE certificate data"""
        cert_path = test_certs_dir / "slave_sae_cert.pem"
        return cert_path.read_bytes()

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request"""
        request = MagicMock()
        request.client.host = "192.168.1.100"
        request.headers = {"user-agent": "TestClient/1.0"}
        request.query_params = {}
        return request

    def test_middleware_initialization(self, auth_middleware):
        """Test authentication middleware initialization"""
        assert auth_middleware is not None
        assert isinstance(auth_middleware, AuthenticationMiddleware)
        assert auth_middleware.auth_attempts == 0
        assert auth_middleware.auth_successes == 0
        assert auth_middleware.auth_failures == 0

    def test_extract_certificate_from_request_tls(
        self, auth_middleware, mock_request, master_sae_cert_data
    ):
        """Test certificate extraction from TLS context"""
        # Mock TLS context with certificate
        mock_request.scope = {"ssl": {"client_cert": master_sae_cert_data}}

        cert_data = auth_middleware._extract_certificate_from_request(mock_request)
        assert cert_data == master_sae_cert_data

    def test_extract_certificate_from_request_header(
        self, auth_middleware, mock_request, master_sae_cert_data
    ):
        """Test certificate extraction from header"""
        # Mock header with certificate
        mock_request.headers = {"X-Client-Certificate": master_sae_cert_data.decode()}

        cert_data = auth_middleware._extract_certificate_from_request(mock_request)
        assert cert_data == master_sae_cert_data

    def test_extract_certificate_from_request_param(
        self, auth_middleware, mock_request, master_sae_cert_data
    ):
        """Test certificate extraction from query parameter"""
        # Mock query parameter with certificate
        mock_request.query_params = {"cert": master_sae_cert_data.decode()}

        cert_data = auth_middleware._extract_certificate_from_request(mock_request)
        assert cert_data == master_sae_cert_data

    def test_extract_certificate_from_request_not_found(
        self, auth_middleware, mock_request
    ):
        """Test certificate extraction when no certificate is found"""
        mock_request.scope = {}
        mock_request.headers = {}
        mock_request.query_params = {}

        with pytest.raises(Exception, match="No certificate found in request"):
            auth_middleware._extract_certificate_from_request(mock_request)

    @pytest.mark.asyncio
    async def test_authenticate_request_status_endpoint_success(
        self, auth_middleware, mock_request, master_sae_cert_data
    ):
        """Test successful authentication for status endpoint"""
        # Mock certificate extraction
        with patch.object(
            auth_middleware,
            "_extract_certificate_from_request",
            return_value=master_sae_cert_data,
        ):
            # Mock certificate validation
            mock_cert_info = CertificateInfo(
                subject="CN=Master SAE A1B2C3D4E5F6A7B8",
                issuer="CN=KME Test CA",
                serial_number="123456789",
                not_before=datetime.datetime(2024, 1, 1),
                not_after=datetime.datetime(2025, 1, 1),
                key_usage=[],
                extended_key_usage=[],
                subject_alt_names=[],
                certificate_type=CertificateType.SAE,
                is_valid=True,
                validation_errors=[],
            )

            with patch.object(
                auth_middleware.certificate_manager,
                "validate_certificate",
                return_value=mock_cert_info,
            ):
                with patch.object(
                    auth_middleware.certificate_auth,
                    "extract_sae_id_from_certificate",
                    return_value="A1B2C3D4E5F6A7B8",
                ):
                    with patch.object(
                        auth_middleware.certificate_auth,
                        "_validate_sae_id_format",
                        return_value=True,
                    ):
                        with patch.object(
                            auth_middleware.sae_auth,
                            "validate_status_access",
                            return_value=True,
                        ):
                            (
                                requesting_sae_id,
                                cert_info,
                                audit_data,
                            ) = await auth_middleware.authenticate_request(
                                request=mock_request,
                                endpoint_type="status",
                                resource_id="C1D2E3F4A5B6C7D8",
                            )

                            assert requesting_sae_id == "A1B2C3D4E5F6A7B8"
                            assert cert_info == mock_cert_info
                            assert audit_data["success"] is True
                            assert audit_data["endpoint_type"] == "status"
                            assert audit_data["resource_id"] == "C1D2E3F4A5B6C7D8"
                            assert "request_id" in audit_data
                            assert "authentication_time" in audit_data

    @pytest.mark.asyncio
    async def test_authenticate_request_key_endpoint_success(
        self, auth_middleware, mock_request, master_sae_cert_data
    ):
        """Test successful authentication for key endpoint"""
        # Mock certificate extraction
        with patch.object(
            auth_middleware,
            "_extract_certificate_from_request",
            return_value=master_sae_cert_data,
        ):
            # Mock certificate validation
            mock_cert_info = CertificateInfo(
                subject="CN=Master SAE A1B2C3D4E5F6A7B8",
                issuer="CN=KME Test CA",
                serial_number="123456789",
                not_before=datetime.datetime(2024, 1, 1),
                not_after=datetime.datetime(2025, 1, 1),
                key_usage=[],
                extended_key_usage=[],
                subject_alt_names=[],
                certificate_type=CertificateType.SAE,
                is_valid=True,
                validation_errors=[],
            )

            with patch.object(
                auth_middleware.certificate_manager,
                "validate_certificate",
                return_value=mock_cert_info,
            ):
                with patch.object(
                    auth_middleware.certificate_auth,
                    "extract_sae_id_from_certificate",
                    return_value="A1B2C3D4E5F6A7B8",
                ):
                    with patch.object(
                        auth_middleware.certificate_auth,
                        "_validate_sae_id_format",
                        return_value=True,
                    ):
                        with patch.object(
                            auth_middleware.sae_auth,
                            "validate_key_access",
                            return_value=True,
                        ):
                            (
                                requesting_sae_id,
                                cert_info,
                                audit_data,
                            ) = await auth_middleware.authenticate_request(
                                request=mock_request,
                                endpoint_type="key",
                                resource_id="C1D2E3F4A5B6C7D8",
                            )

                            assert requesting_sae_id == "A1B2C3D4E5F6A7B8"
                            assert cert_info == mock_cert_info
                            assert audit_data["success"] is True
                            assert audit_data["endpoint_type"] == "key"
                            assert audit_data["resource_id"] == "C1D2E3F4A5B6C7D8"

    @pytest.mark.asyncio
    async def test_authenticate_request_key_ids_endpoint_success(
        self, auth_middleware, mock_request, slave_sae_cert_data
    ):
        """Test successful authentication for key_ids endpoint"""
        # Mock certificate extraction
        with patch.object(
            auth_middleware,
            "_extract_certificate_from_request",
            return_value=slave_sae_cert_data,
        ):
            # Mock certificate validation
            mock_cert_info = CertificateInfo(
                subject="CN=Slave SAE C1D2E3F4A5B6C7D8",
                issuer="CN=KME Test CA",
                serial_number="987654321",
                not_before=datetime.datetime(2024, 1, 1),
                not_after=datetime.datetime(2025, 1, 1),
                key_usage=[],
                extended_key_usage=[],
                subject_alt_names=[],
                certificate_type=CertificateType.SAE,
                is_valid=True,
                validation_errors=[],
            )

            with patch.object(
                auth_middleware.certificate_manager,
                "validate_certificate",
                return_value=mock_cert_info,
            ):
                with patch.object(
                    auth_middleware.certificate_auth,
                    "extract_sae_id_from_certificate",
                    return_value="C1D2E3F4A5B6C7D8",
                ):
                    with patch.object(
                        auth_middleware.certificate_auth,
                        "_validate_sae_id_format",
                        return_value=True,
                    ):
                        with patch.object(
                            auth_middleware.sae_auth,
                            "validate_key_access",
                            return_value=True,
                        ):
                            (
                                requesting_sae_id,
                                cert_info,
                                audit_data,
                            ) = await auth_middleware.authenticate_request(
                                request=mock_request,
                                endpoint_type="key_ids",
                                resource_id="A1B2C3D4E5F6A7B8",
                            )

                            assert requesting_sae_id == "C1D2E3F4A5B6C7D8"
                            assert cert_info == mock_cert_info
                            assert audit_data["success"] is True
                            assert audit_data["endpoint_type"] == "key_ids"
                            assert audit_data["resource_id"] == "A1B2C3D4E5F6A7B8"

    @pytest.mark.asyncio
    async def test_authenticate_request_certificate_validation_failure(
        self, auth_middleware, mock_request
    ):
        """Test authentication failure due to certificate validation"""
        with patch.object(
            auth_middleware,
            "_extract_certificate_from_request",
            side_effect=Exception("Certificate not found"),
        ):
            with pytest.raises(Exception):
                await auth_middleware.authenticate_request(
                    request=mock_request,
                    endpoint_type="status",
                    resource_id="C1D2E3F4A5B6C7D8",
                )

    @pytest.mark.asyncio
    async def test_authenticate_request_authorization_failure(
        self, auth_middleware, mock_request, master_sae_cert_data
    ):
        """Test authentication failure due to authorization failure"""
        # Mock certificate extraction and validation
        with patch.object(
            auth_middleware,
            "_extract_certificate_from_request",
            return_value=master_sae_cert_data,
        ):
            mock_cert_info = CertificateInfo(
                subject="CN=Master SAE A1B2C3D4E5F6A7B8",
                issuer="CN=KME Test CA",
                serial_number="123456789",
                not_before=datetime.datetime(2024, 1, 1),
                not_after=datetime.datetime(2025, 1, 1),
                key_usage=[],
                extended_key_usage=[],
                subject_alt_names=[],
                certificate_type=CertificateType.SAE,
                is_valid=True,
                validation_errors=[],
            )

            with patch.object(
                auth_middleware.certificate_manager,
                "validate_certificate",
                return_value=mock_cert_info,
            ):
                with patch.object(
                    auth_middleware.certificate_auth,
                    "extract_sae_id_from_certificate",
                    return_value="A1B2C3D4E5F6A7B8",
                ):
                    with patch.object(
                        auth_middleware.certificate_auth,
                        "_validate_sae_id_format",
                        return_value=True,
                    ):
                        with patch.object(
                            auth_middleware.sae_auth,
                            "validate_status_access",
                            return_value=False,
                        ):
                            with pytest.raises(Exception):
                                await auth_middleware.authenticate_request(
                                    request=mock_request,
                                    endpoint_type="status",
                                    resource_id="C1D2E3F4A5B6C7D8",
                                )

    @pytest.mark.asyncio
    async def test_authenticate_request_unknown_endpoint_type(
        self, auth_middleware, mock_request, master_sae_cert_data
    ):
        """Test authentication failure due to unknown endpoint type"""
        # Mock certificate extraction and validation
        with patch.object(
            auth_middleware,
            "_extract_certificate_from_request",
            return_value=master_sae_cert_data,
        ):
            mock_cert_info = CertificateInfo(
                subject="CN=Master SAE A1B2C3D4E5F6A7B8",
                issuer="CN=KME Test CA",
                serial_number="123456789",
                not_before=datetime.datetime(2024, 1, 1),
                not_after=datetime.datetime(2025, 1, 1),
                key_usage=[],
                extended_key_usage=[],
                subject_alt_names=[],
                certificate_type=CertificateType.SAE,
                is_valid=True,
                validation_errors=[],
            )

            with patch.object(
                auth_middleware.certificate_manager,
                "validate_certificate",
                return_value=mock_cert_info,
            ):
                with patch.object(
                    auth_middleware.certificate_auth,
                    "extract_sae_id_from_certificate",
                    return_value="A1B2C3D4E5F6A7B8",
                ):
                    with patch.object(
                        auth_middleware.certificate_auth,
                        "_validate_sae_id_format",
                        return_value=True,
                    ):
                        with pytest.raises(Exception):
                            await auth_middleware.authenticate_request(
                                request=mock_request,
                                endpoint_type="invalid",
                                resource_id="C1D2E3F4A5B6C7D8",
                            )

    def test_get_authentication_metrics(self, auth_middleware):
        """Test authentication metrics collection"""
        # Reset metrics
        auth_middleware.auth_attempts = 0
        auth_middleware.auth_successes = 0
        auth_middleware.auth_failures = 0
        auth_middleware.cert_validation_failures = 0
        auth_middleware.authorization_failures = 0

        # Simulate some authentication attempts
        auth_middleware.auth_attempts = 10
        auth_middleware.auth_successes = 8
        auth_middleware.auth_failures = 2
        auth_middleware.cert_validation_failures = 1
        auth_middleware.authorization_failures = 1

        metrics = auth_middleware.get_authentication_metrics()

        assert metrics["total_attempts"] == 10
        assert metrics["successful_authentications"] == 8
        assert metrics["failed_authentications"] == 2
        assert metrics["success_rate_percent"] == 80.0
        assert metrics["certificate_validation_failures"] == 1
        assert metrics["authorization_failures"] == 1

    def test_get_authentication_metrics_zero_attempts(self, auth_middleware):
        """Test authentication metrics with zero attempts"""
        # Reset metrics
        auth_middleware.auth_attempts = 0
        auth_middleware.auth_successes = 0
        auth_middleware.auth_failures = 0

        metrics = auth_middleware.get_authentication_metrics()

        assert metrics["total_attempts"] == 0
        assert metrics["successful_authentications"] == 0
        assert metrics["failed_authentications"] == 0
        assert metrics["success_rate_percent"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
