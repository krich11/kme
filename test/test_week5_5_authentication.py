#!/usr/bin/env python3
"""
Test Week 5.5 Authentication Implementation

This test verifies that the basic authentication and authorization
implementation for Week 5.5 works correctly with proper test certificates.
"""

import asyncio
from pathlib import Path

import pytest

from app.core.authentication import (
    AuthenticationError,
    AuthorizationError,
    get_certificate_auth,
    get_extension_processor,
    get_sae_authorization,
)
from app.core.security import get_certificate_manager


class TestWeek55Authentication:
    """Test Week 5.5 authentication implementation"""

    @pytest.fixture
    def certificate_auth(self):
        """Get certificate authentication instance"""
        return get_certificate_auth()

    @pytest.fixture
    def sae_auth(self):
        """Get SAE authorization instance"""
        return get_sae_authorization()

    @pytest.fixture
    def extension_processor(self):
        """Get extension processor instance"""
        return get_extension_processor()

    @pytest.fixture
    def certificate_manager(self):
        """Get certificate manager instance"""
        return get_certificate_manager()

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
    def kme_cert_data(self, test_certs_dir):
        """Load KME certificate data"""
        cert_path = test_certs_dir / "kme_cert.pem"
        return cert_path.read_bytes()

    def test_extract_sae_id_from_master_certificate(
        self, certificate_manager, master_sae_cert_data
    ):
        """Test SAE ID extraction from master SAE certificate"""
        sae_id = certificate_manager.extract_sae_id_from_certificate(
            master_sae_cert_data
        )
        assert sae_id == "A1B2C3D4E5F6A7B8"
        assert len(sae_id) == 16
        assert all(c in "0123456789ABCDEF" for c in sae_id)

    def test_extract_sae_id_from_slave_certificate(
        self, certificate_manager, slave_sae_cert_data
    ):
        """Test SAE ID extraction from slave SAE certificate"""
        sae_id = certificate_manager.extract_sae_id_from_certificate(
            slave_sae_cert_data
        )
        assert sae_id == "C1D2E3F4A5B6C7D8"
        assert len(sae_id) == 16
        assert all(c in "0123456789ABCDEF" for c in sae_id)

    def test_extract_sae_id_from_kme_certificate(
        self, certificate_manager, kme_cert_data
    ):
        """Test SAE ID extraction from KME certificate"""
        sae_id = certificate_manager.extract_sae_id_from_certificate(kme_cert_data)
        assert sae_id == "E1F2A3B4C5D6E7F8"
        assert len(sae_id) == 16
        assert all(c in "0123456789ABCDEF" for c in sae_id)

    def test_validate_certificate_master_sae(
        self, certificate_manager, master_sae_cert_data
    ):
        """Test certificate validation for master SAE"""
        cert_info = certificate_manager.validate_certificate(master_sae_cert_data)
        assert cert_info.is_valid is True
        assert cert_info.certificate_type.value == "sae"
        assert "A1B2C3D4E5F6A7B8" in cert_info.subject

    def test_validate_certificate_slave_sae(
        self, certificate_manager, slave_sae_cert_data
    ):
        """Test certificate validation for slave SAE"""
        cert_info = certificate_manager.validate_certificate(slave_sae_cert_data)
        assert cert_info.is_valid is True
        assert cert_info.certificate_type.value == "sae"
        assert "C1D2E3F4A5B6C7D8" in cert_info.subject

    def test_validate_certificate_kme(self, certificate_manager, kme_cert_data):
        """Test certificate validation for KME"""
        cert_info = certificate_manager.validate_certificate(kme_cert_data)
        assert cert_info.is_valid is True
        assert cert_info.certificate_type.value == "kme"
        assert "E1F2A3B4C5D6E7F8" in cert_info.subject

    @pytest.mark.asyncio
    async def test_validate_key_access_master_to_slave(self, sae_auth):
        """Test key access validation for master SAE accessing slave SAE"""
        # Master SAE requesting keys for slave SAE
        access_granted = await sae_auth.validate_key_access(
            requesting_sae_id="A1B2C3D4E5F6A7B8",  # Master SAE
            slave_sae_id="C1D2E3F4A5B6C7D8",  # Slave SAE
            master_sae_id="A1B2C3D4E5F6A7B8",  # Master SAE
        )
        assert access_granted is True

    @pytest.mark.asyncio
    async def test_validate_key_access_slave_to_own_keys(self, sae_auth):
        """Test key access validation for slave SAE accessing own keys"""
        # Slave SAE retrieving own keys
        access_granted = await sae_auth.validate_key_access(
            requesting_sae_id="C1D2E3F4A5B6C7D8",  # Slave SAE
            slave_sae_id="C1D2E3F4A5B6C7D8",  # Slave SAE
            master_sae_id="A1B2C3D4E5F6A7B8",  # Master SAE
        )
        assert access_granted is True

    @pytest.mark.asyncio
    async def test_validate_key_access_unauthorized(self, sae_auth):
        """Test key access validation for unauthorized access"""
        # Unauthorized SAE trying to access keys
        with pytest.raises(
            AuthorizationError, match="Key requests must be from master SAE"
        ):
            await sae_auth.validate_key_access(
                requesting_sae_id="X1X2X3X4X5X6X7X8",  # Unauthorized SAE
                slave_sae_id="C1D2E3F4A5B6C7D8",  # Slave SAE
                master_sae_id="A1B2C3D4E5F6A7B8",  # Master SAE
            )

    @pytest.mark.asyncio
    async def test_validate_status_access_master_to_slave(self, sae_auth):
        """Test status access validation for master SAE accessing slave SAE status"""
        # Master SAE requesting status for slave SAE
        access_granted = await sae_auth.validate_status_access(
            requesting_sae_id="A1B2C3D4E5F6A7B8",  # Master SAE
            slave_sae_id="C1D2E3F4A5B6C7D8",  # Slave SAE
            master_sae_id="A1B2C3D4E5F6A7B8",  # Master SAE
        )
        assert access_granted is True

    @pytest.mark.asyncio
    async def test_validate_status_access_slave_to_own_status(self, sae_auth):
        """Test status access validation for slave SAE accessing own status"""
        # Slave SAE requesting own status
        access_granted = await sae_auth.validate_status_access(
            requesting_sae_id="C1D2E3F4A5B6C7D8",  # Slave SAE
            slave_sae_id="C1D2E3F4A5B6C7D8",  # Slave SAE
            master_sae_id="A1B2C3D4E5F6A7B8",  # Master SAE
        )
        assert access_granted is True

    @pytest.mark.asyncio
    async def test_validate_status_access_unauthorized(self, sae_auth):
        """Test status access validation for unauthorized access"""
        # Unauthorized SAE trying to access status
        with pytest.raises(
            AuthorizationError, match="Unauthorized access to status information"
        ):
            await sae_auth.validate_status_access(
                requesting_sae_id="X1X2X3X4X5X6X7X8",  # Unauthorized SAE
                slave_sae_id="C1D2E3F4A5B6C7D8",  # Slave SAE
                master_sae_id="A1B2C3D4E5F6A7B8",  # Master SAE
            )

    @pytest.mark.asyncio
    async def test_process_mandatory_extensions(self, extension_processor):
        """Test mandatory extension processing"""
        extensions = [
            {"type": "key_lifetime", "data": {"lifetime": 3600}},
            {"type": "key_quality", "data": {"min_entropy": 256}},
        ]

        responses = await extension_processor.process_mandatory_extensions(extensions)

        assert len(responses) == 2
        assert "mandatory_key_lifetime" in responses
        assert "mandatory_key_quality" in responses
        assert responses["mandatory_key_lifetime"]["processed"] is True
        assert responses["mandatory_key_quality"]["processed"] is True

    @pytest.mark.asyncio
    async def test_process_optional_extensions(self, extension_processor):
        """Test optional extension processing"""
        extensions = [
            {"type": "vendor_specific", "data": {"vendor": "test"}},
            {"type": "custom_metadata", "data": {"metadata": "test"}},
        ]

        responses = await extension_processor.process_optional_extensions(extensions)

        assert len(responses) == 2
        assert "optional_vendor_specific" in responses
        assert "optional_custom_metadata" in responses
        assert responses["optional_vendor_specific"]["processed"] is False
        assert responses["optional_vendor_specific"]["ignored"] is True

    @pytest.mark.asyncio
    async def test_process_no_extensions(self, extension_processor):
        """Test processing when no extensions are provided"""
        mandatory_responses = await extension_processor.process_mandatory_extensions(
            None
        )
        optional_responses = await extension_processor.process_optional_extensions(None)

        assert mandatory_responses == {}
        assert optional_responses == {}

    def test_sae_id_format_validation(self, certificate_auth):
        """Test SAE ID format validation"""
        # Valid SAE IDs
        assert certificate_auth._validate_sae_id_format("A1B2C3D4E5F6A7B8") is True
        assert certificate_auth._validate_sae_id_format("C1D2E3F4A5B6C7D8") is True
        assert certificate_auth._validate_sae_id_format("E1F2A3B4C5D6E7F8") is True

        # Invalid SAE IDs
        assert (
            certificate_auth._validate_sae_id_format("A1B2C3D4E5F6A7B") is False
        )  # Too short
        assert (
            certificate_auth._validate_sae_id_format("A1B2C3D4E5F6A7B8X") is False
        )  # Too long
        assert (
            certificate_auth._validate_sae_id_format("A1B2C3D4E5F6A7B!") is False
        )  # Invalid char
        assert certificate_auth._validate_sae_id_format("") is False  # Empty
        assert certificate_auth._validate_sae_id_format(None) is False  # None


if __name__ == "__main__":
    pytest.main([__file__])
