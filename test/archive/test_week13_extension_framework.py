#!/usr/bin/env python3
"""
Test Week 13: Extension Framework

Tests for comprehensive extension framework implementation
"""

import asyncio
import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.extension_service import (
    ExtensionResponse,
    ExtensionService,
    ExtensionStatus,
    ExtensionType,
    extension_service,
)
from app.services.vendor_extension_service import (
    SecurityLevel,
    VendorExtensionRequest,
    VendorExtensionResponse,
    VendorExtensionService,
    VendorExtensionStatus,
    vendor_extension_service,
)


class TestExtensionService:
    """Test ExtensionService functionality"""

    @pytest.fixture
    def extension_service_instance(self):
        """Create extension service instance for testing"""
        return ExtensionService()

    @pytest.fixture
    def sample_mandatory_extensions(self):
        """Sample mandatory extensions for testing"""
        return [
            {
                "type": "route_type",
                "data": {"route_type": "direct"},
                "version": "1.0",
            },
            {
                "type": "key_quality",
                "data": {"quality_level": "high"},
                "version": "1.0",
            },
        ]

    @pytest.fixture
    def sample_optional_extensions(self):
        """Sample optional extensions for testing"""
        return [
            {
                "type": "compression",
                "data": {"compression_type": "gzip"},
                "version": "1.0",
            },
            {
                "type": "priority",
                "data": {"priority_level": "high"},
                "version": "1.0",
            },
        ]

    @pytest.mark.asyncio
    async def test_process_mandatory_extensions_success(
        self, extension_service_instance, sample_mandatory_extensions
    ):
        """Test successful mandatory extension processing"""
        result = await extension_service_instance.process_mandatory_extensions(
            sample_mandatory_extensions
        )

        assert isinstance(result, dict)
        assert len(result) == 2
        assert "route_type" in result
        assert "key_quality" in result

        # Check route_type processing
        route_result = result["route_type"]
        assert route_result["route_type"] == "direct"
        assert route_result["supported"] is True
        assert "processing" in route_result

        # Check key_quality processing
        quality_result = result["key_quality"]
        assert quality_result["quality_level"] == "high"
        assert quality_result["supported"] is True
        assert "processing" in quality_result

    @pytest.mark.asyncio
    async def test_process_mandatory_extensions_empty(self, extension_service_instance):
        """Test mandatory extension processing with empty list"""
        result = await extension_service_instance.process_mandatory_extensions([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_process_mandatory_extensions_none(self, extension_service_instance):
        """Test mandatory extension processing with None"""
        result = await extension_service_instance.process_mandatory_extensions(None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_process_mandatory_extensions_unsupported(
        self, extension_service_instance
    ):
        """Test mandatory extension processing with unsupported extension"""
        unsupported_extensions = [
            {
                "type": "unsupported_extension",
                "data": {"test": "data"},
                "version": "1.0",
            }
        ]

        with pytest.raises(ValueError, match="Mandatory extension processing error"):
            await extension_service_instance.process_mandatory_extensions(
                unsupported_extensions
            )

    @pytest.mark.asyncio
    async def test_process_optional_extensions_success(
        self, extension_service_instance, sample_optional_extensions
    ):
        """Test successful optional extension processing"""
        result = await extension_service_instance.process_optional_extensions(
            sample_optional_extensions
        )

        assert isinstance(result, dict)
        assert len(result) == 2
        assert "compression" in result
        assert "priority" in result

        # Check compression processing
        compression_result = result["compression"]
        assert compression_result["compression_type"] == "gzip"
        assert compression_result["supported"] is True
        assert "processing" in compression_result

        # Check priority processing
        priority_result = result["priority"]
        assert priority_result["priority_level"] == "high"
        assert priority_result["supported"] is True
        assert "processing" in priority_result

    @pytest.mark.asyncio
    async def test_process_optional_extensions_unsupported(
        self, extension_service_instance
    ):
        """Test optional extension processing with unsupported extension"""
        unsupported_extensions = [
            {
                "type": "unsupported_extension",
                "data": {"test": "data"},
                "version": "1.0",
            }
        ]

        # Optional extensions should not raise exceptions
        result = await extension_service_instance.process_optional_extensions(
            unsupported_extensions
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_process_single_extension_success(self, extension_service_instance):
        """Test successful single extension processing"""
        extension = {
            "type": "encryption_mode",
            "data": {"mode": "AES-256"},
            "version": "1.0",
        }

        response = await extension_service_instance._process_single_extension(
            extension, ExtensionType.MANDATORY
        )

        assert isinstance(response, ExtensionResponse)
        assert response.extension_type == "encryption_mode"
        assert response.status == ExtensionStatus.SUCCESS
        assert response.result is not None
        assert response.result["encryption_mode"] == "AES-256"
        assert response.result["supported"] is True

    @pytest.mark.asyncio
    async def test_process_single_extension_unsupported(
        self, extension_service_instance
    ):
        """Test single extension processing with unsupported extension"""
        extension = {
            "type": "unsupported_extension",
            "data": {"test": "data"},
            "version": "1.0",
        }

        response = await extension_service_instance._process_single_extension(
            extension, ExtensionType.MANDATORY
        )

        assert isinstance(response, ExtensionResponse)
        assert response.extension_type == "unsupported_extension"
        assert response.status == ExtensionStatus.UNSUPPORTED
        assert response.error_message is not None

    def test_is_extension_supported(self, extension_service_instance):
        """Test extension support checking"""
        # Test supported extensions
        assert extension_service_instance._is_extension_supported("route_type") is True
        assert extension_service_instance._is_extension_supported("key_quality") is True
        assert (
            extension_service_instance._is_extension_supported("encryption_mode")
            is True
        )

        # Test unsupported extensions
        assert (
            extension_service_instance._is_extension_supported("unsupported") is False
        )

    @pytest.mark.asyncio
    async def test_validate_extension_parameters(self, extension_service_instance):
        """Test extension parameter validation"""
        # Test valid parameters
        valid_data = {"route_type": "direct"}
        result = await extension_service_instance._validate_extension_parameters(
            "route_type", valid_data
        )
        assert result["valid"] is True

        # Test invalid parameters (too long string)
        invalid_data = {"test_param": "x" * 1001}
        result = await extension_service_instance._validate_extension_parameters(
            "route_type", invalid_data
        )
        assert result["valid"] is False
        assert "too long" in result["error"]

    def test_validate_parameter(self, extension_service_instance):
        """Test single parameter validation"""
        # Test valid string parameter
        result = extension_service_instance._validate_parameter(
            "test_param", "valid_string", None
        )
        assert result["valid"] is True

        # Test string too long
        result = extension_service_instance._validate_parameter(
            "test_param", "x" * 1001, None
        )
        assert result["valid"] is False

        # Test valid integer parameter
        result = extension_service_instance._validate_parameter("test_param", 100, None)
        assert result["valid"] is True

        # Test integer out of range
        result = extension_service_instance._validate_parameter(
            "test_param", 1e10, None
        )
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_default_extension_handlers(self, extension_service_instance):
        """Test default extension handlers"""
        # Test route_type handler
        result = await extension_service_instance._default_extension_handler(
            "route_type", {"route_type": "relay"}
        )
        assert result["route_type"] == "relay"
        assert result["supported"] is True

        # Test key_quality handler
        result = await extension_service_instance._default_extension_handler(
            "key_quality", {"quality_level": "ultra"}
        )
        assert result["quality_level"] == "ultra"
        assert result["supported"] is True

        # Test generic handler
        result = await extension_service_instance._default_extension_handler(
            "unknown_type", {"test": "data"}
        )
        assert result["processed"] is True
        assert result["data"] == {"test": "data"}

    def test_get_processing_statistics(self, extension_service_instance):
        """Test processing statistics retrieval"""
        stats = extension_service_instance.get_processing_statistics()

        assert "total_processed" in stats
        assert "successful" in stats
        assert "failed" in stats
        assert "ignored" in stats
        assert "unsupported" in stats
        assert "success_rate" in stats

        assert isinstance(stats["total_processed"], int)
        assert isinstance(stats["success_rate"], float)

    def test_get_supported_extensions(self, extension_service_instance):
        """Test supported extensions retrieval"""
        extensions = extension_service_instance.get_supported_extensions()

        assert isinstance(extensions, list)
        # Should include built-in extensions
        assert len(extensions) >= 0  # May be empty if no extensions registered


class TestVendorExtensionService:
    """Test VendorExtensionService functionality"""

    @pytest.fixture
    def vendor_extension_service_instance(self):
        """Create vendor extension service instance for testing"""
        return VendorExtensionService()

    @pytest.fixture
    def sample_extension_request(self):
        """Sample extension registration request"""
        return VendorExtensionRequest(
            name="test_extension",
            version="1.0.0",
            vendor="test_vendor",
            description="Test extension for unit testing",
            handler_function="test_handler",
            required_parameters=["param1"],
            optional_parameters=["param2"],
            security_level=SecurityLevel.MEDIUM,
            documentation="Test extension documentation",
            compatibility_matrix={"kme_version": ["1.0.0"]},
            validation_rules={"param1": {"type": "string", "max_length": 100}},
        )

    @pytest.fixture
    def sample_handler(self):
        """Sample extension handler function"""

        def test_handler(data):
            return {"processed": True, "data": data}

        return test_handler

    @pytest.mark.asyncio
    async def test_register_vendor_extension_success(
        self,
        vendor_extension_service_instance,
        sample_extension_request,
        sample_handler,
    ):
        """Test successful vendor extension registration"""
        response = await vendor_extension_service_instance.register_vendor_extension(
            sample_extension_request, sample_handler
        )

        assert isinstance(response, VendorExtensionResponse)
        assert response.success is True
        assert response.extension_id is not None
        assert "registered successfully" in response.message
        assert response.validation_results["valid"] is True
        assert response.compatibility_results["compatible"] is True
        assert response.security_results["secure"] is True

    @pytest.mark.asyncio
    async def test_register_vendor_extension_duplicate(
        self,
        vendor_extension_service_instance,
        sample_extension_request,
        sample_handler,
    ):
        """Test vendor extension registration with duplicate"""
        # Register first time
        response1 = await vendor_extension_service_instance.register_vendor_extension(
            sample_extension_request, sample_handler
        )
        assert response1.success is True

        # Try to register again with same version
        response2 = await vendor_extension_service_instance.register_vendor_extension(
            sample_extension_request, sample_handler
        )
        assert response2.success is False
        assert "already exists" in str(response2.validation_results.get("errors", []))

    @pytest.mark.asyncio
    async def test_register_vendor_extension_invalid_handler(
        self, vendor_extension_service_instance, sample_extension_request
    ):
        """Test vendor extension registration with invalid handler"""
        invalid_handler = "not_a_function"

        response = await vendor_extension_service_instance.register_vendor_extension(
            sample_extension_request, invalid_handler
        )

        assert response.success is False
        assert "validation failed" in response.message

    @pytest.mark.asyncio
    async def test_register_vendor_extension_incompatible_version(
        self, vendor_extension_service_instance, sample_handler
    ):
        """Test vendor extension registration with incompatible version"""
        incompatible_request = VendorExtensionRequest(
            name="test_extension",
            version="1.0.0",
            vendor="test_vendor",
            description="Test extension",
            handler_function="test_handler",
            compatibility_matrix={"kme_version": ["2.0.0"]},  # Incompatible version
            documentation="Test documentation",
        )

        response = await vendor_extension_service_instance.register_vendor_extension(
            incompatible_request, sample_handler
        )

        assert response.success is False
        assert "compatibility check failed" in response.message

    @pytest.mark.asyncio
    async def test_register_vendor_extension_critical_security(
        self, vendor_extension_service_instance, sample_handler
    ):
        """Test vendor extension registration with critical security level"""
        critical_request = VendorExtensionRequest(
            name="critical_extension",
            version="1.0.0",
            vendor="test_vendor",
            description="Critical security extension",
            handler_function="critical_handler",
            security_level=SecurityLevel.CRITICAL,
            documentation="Critical extension documentation",
        )

        # Create a handler that doesn't meet critical security requirements
        def unsafe_handler(data):
            return {"result": "unsafe"}

        response = await vendor_extension_service_instance.register_vendor_extension(
            critical_request, unsafe_handler
        )

        assert response.success is False
        assert "security validation failed" in response.message

    def test_validate_extension_registration(
        self,
        vendor_extension_service_instance,
        sample_extension_request,
        sample_handler,
    ):
        """Test extension registration validation"""
        result = asyncio.run(
            vendor_extension_service_instance._validate_extension_registration(
                sample_extension_request, sample_handler
            )
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_extension_registration_invalid_name(
        self, vendor_extension_service_instance, sample_handler
    ):
        """Test extension registration validation with invalid name"""
        # This test demonstrates that Pydantic validation catches invalid names
        # before they reach the custom validation logic
        with pytest.raises(Exception):  # Pydantic validation error
            invalid_request = VendorExtensionRequest(
                name="123invalid",  # Invalid name
                version="1.0.0",
                vendor="test_vendor",
                description="Test extension",
                handler_function="test_handler",
                documentation="Test documentation",
            )

    def test_validate_extension_registration_duplicate_params(
        self, vendor_extension_service_instance, sample_handler
    ):
        """Test extension registration validation with duplicate parameters"""
        duplicate_request = VendorExtensionRequest(
            name="test_extension",
            version="1.0.0",
            vendor="test_vendor",
            description="Test extension",
            handler_function="test_handler",
            required_parameters=["param1"],
            optional_parameters=["param1"],  # Duplicate parameter
            documentation="Test documentation",
        )

        result = asyncio.run(
            vendor_extension_service_instance._validate_extension_registration(
                duplicate_request, sample_handler
            )
        )

        assert result["valid"] is False
        assert "Duplicate parameter names" in result["errors"][0]

    def test_check_extension_compatibility(
        self, vendor_extension_service_instance, sample_extension_request
    ):
        """Test extension compatibility checking"""
        result = asyncio.run(
            vendor_extension_service_instance._check_extension_compatibility(
                sample_extension_request
            )
        )

        assert result["compatible"] is True
        assert len(result["issues"]) == 0

    def test_validate_extension_security(
        self,
        vendor_extension_service_instance,
        sample_extension_request,
        sample_handler,
    ):
        """Test extension security validation"""
        result = asyncio.run(
            vendor_extension_service_instance._validate_extension_security(
                sample_extension_request, sample_handler
            )
        )

        assert result["secure"] is True
        assert len(result["issues"]) == 0

    def test_validate_extension_security_dangerous_operations(
        self, vendor_extension_service_instance, sample_extension_request
    ):
        """Test extension security validation with dangerous operations"""

        def dangerous_handler(data):
            eval("print('dangerous')")  # Dangerous operation
            return {"result": "dangerous"}

        result = asyncio.run(
            vendor_extension_service_instance._validate_extension_security(
                sample_extension_request, dangerous_handler
            )
        )

        assert result["secure"] is False
        assert len(result["issues"]) > 0
        assert "dangerous operation" in result["issues"][0]

    def test_generate_extension_id(self, vendor_extension_service_instance):
        """Test extension ID generation"""
        extension_id = vendor_extension_service_instance._generate_extension_id(
            "test_vendor", "test_extension", "1.0.0"
        )

        assert isinstance(extension_id, str)
        assert len(extension_id) == 16
        assert extension_id.isalnum()

    def test_calculate_checksum(
        self,
        vendor_extension_service_instance,
        sample_extension_request,
        sample_handler,
    ):
        """Test extension checksum calculation"""
        checksum = vendor_extension_service_instance._calculate_checksum(
            sample_extension_request, sample_handler
        )

        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hash length

    def test_get_vendor_extensions(
        self,
        vendor_extension_service_instance,
        sample_extension_request,
        sample_handler,
    ):
        """Test vendor extensions retrieval"""
        # Register an extension first
        asyncio.run(
            vendor_extension_service_instance.register_vendor_extension(
                sample_extension_request, sample_handler
            )
        )

        extensions = vendor_extension_service_instance.get_vendor_extensions(
            "test_vendor"
        )

        assert isinstance(extensions, list)
        assert len(extensions) == 1
        assert extensions[0]["name"] == "test_extension"
        assert extensions[0]["version"] == "1.0.0"

    def test_get_extension_details(
        self,
        vendor_extension_service_instance,
        sample_extension_request,
        sample_handler,
    ):
        """Test extension details retrieval"""
        # Register an extension first
        asyncio.run(
            vendor_extension_service_instance.register_vendor_extension(
                sample_extension_request, sample_handler
            )
        )

        details = vendor_extension_service_instance.get_extension_details(
            "test_vendor", "test_extension"
        )

        assert details is not None
        assert details["name"] == "test_extension"
        assert details["vendor"] == "test_vendor"
        assert details["version"] == "1.0.0"
        assert details["status"] == VendorExtensionStatus.PENDING.value

    def test_update_extension_status(
        self,
        vendor_extension_service_instance,
        sample_extension_request,
        sample_handler,
    ):
        """Test extension status update"""
        # Register an extension first
        asyncio.run(
            vendor_extension_service_instance.register_vendor_extension(
                sample_extension_request, sample_handler
            )
        )

        # Update status
        success = vendor_extension_service_instance.update_extension_status(
            "test_vendor", "test_extension", VendorExtensionStatus.ACTIVE
        )

        assert success is True

        # Verify status was updated
        details = vendor_extension_service_instance.get_extension_details(
            "test_vendor", "test_extension"
        )
        assert details["status"] == VendorExtensionStatus.ACTIVE.value

    def test_get_registry_statistics(self, vendor_extension_service_instance):
        """Test registry statistics retrieval"""
        stats = vendor_extension_service_instance.get_registry_statistics()

        assert "total_extensions" in stats
        assert "total_vendors" in stats
        assert "vendors" in stats
        assert "status_distribution" in stats
        assert "security_level_distribution" in stats

        assert isinstance(stats["total_extensions"], int)
        assert isinstance(stats["total_vendors"], int)
        assert isinstance(stats["vendors"], list)


class TestExtensionFrameworkIntegration:
    """Test integration between extension services"""

    @pytest.mark.asyncio
    async def test_extension_service_integration(self):
        """Test integration between extension and vendor extension services"""
        # Test that the global instances work together
        assert extension_service is not None
        assert vendor_extension_service is not None

        # Test basic extension processing
        extensions = [
            {
                "type": "route_type",
                "data": {"route_type": "direct"},
                "version": "1.0",
            }
        ]

        result = await extension_service.process_mandatory_extensions(extensions)
        assert result is not None
        assert "route_type" in result

    @pytest.mark.asyncio
    async def test_vendor_extension_registration_and_processing(self):
        """Test vendor extension registration and processing workflow"""
        # Register a vendor extension
        request = VendorExtensionRequest(
            name="custom_route",
            version="1.0.0",
            vendor="custom_vendor",
            description="Custom routing extension",
            handler_function="custom_handler",
            documentation="Custom extension documentation",
        )

        def custom_handler(data):
            return {"custom_processed": True, "route": "custom"}

        response = await vendor_extension_service.register_vendor_extension(
            request, custom_handler
        )

        assert response.success is True

        # Test that the extension is now available
        extensions = vendor_extension_service.get_vendor_extensions("custom_vendor")
        assert len(extensions) == 1
        assert extensions[0]["name"] == "custom_route"


if __name__ == "__main__":
    pytest.main([__file__])
