#!/usr/bin/env python3
"""
KME Extension Service - ETSI QKD 014 V1.1.1 Compliant

Version: 1.0.0
Author: KME Development Team
Description: Comprehensive extension framework for vendor-specific and future extensions
License: [To be determined]

Week 13.1: Extension Handler Implementation
- Extension parameter processing
- Mandatory extension validation
- Optional extension handling
- Extension response generation
- Extension error handling
- Extension logging

Week 13.2: Vendor Extension Support
- Vendor extension registry
- Extension compatibility checking
- Extension documentation generation
- Extension validation framework
- Extension versioning
- Extension security validation
"""

import asyncio
import datetime
import json
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger()


class ExtensionType(str, Enum):
    """Extension types supported by the KME"""

    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    VENDOR = "vendor"


class ExtensionStatus(str, Enum):
    """Extension processing status"""

    SUCCESS = "success"
    FAILED = "failed"
    IGNORED = "ignored"
    UNSUPPORTED = "unsupported"


@dataclass
class ExtensionDefinition:
    """Extension definition for registry"""

    name: str
    version: str
    type: ExtensionType
    description: str
    handler: Callable
    required_parameters: list[str]
    optional_parameters: list[str]
    security_level: str
    vendor: str | None = None
    documentation: str | None = None


class ExtensionParameter(BaseModel):
    """Extension parameter model"""

    name: str = Field(..., description="Parameter name")
    value: Any = Field(..., description="Parameter value")
    type: str = Field(..., description="Parameter type")
    required: bool = Field(default=False, description="Whether parameter is required")
    validation_rules: dict[str, Any] | None = Field(
        None, description="Validation rules"
    )


class ExtensionRequest(BaseModel):
    """Extension request model"""

    extension_type: str = Field(..., description="Extension type")
    parameters: list[ExtensionParameter] = Field(
        default=[], description="Extension parameters"
    )
    version: str = Field(default="1.0", description="Extension version")
    vendor: str | None = Field(None, description="Vendor identifier")


class ExtensionResponse(BaseModel):
    """Extension response model"""

    extension_type: str = Field(..., description="Extension type")
    status: ExtensionStatus = Field(..., description="Processing status")
    result: dict[str, Any] | None = Field(None, description="Processing result")
    error_message: str | None = Field(None, description="Error message if failed")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    processing_time_ms: float | None = Field(
        None, description="Processing time in milliseconds"
    )


class ExtensionError(BaseModel):
    """Extension error model"""

    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    extension_type: str = Field(..., description="Extension type that caused error")
    details: dict[str, Any] | None = Field(None, description="Error details")


class ExtensionService:
    """
    Comprehensive extension service for KME

    Implements ETSI GS QKD 014 V1.1.1 extension requirements
    """

    def __init__(self):
        """Initialize the extension service"""
        self.logger = logger.bind(service="ExtensionService")
        self.extension_registry: dict[str, ExtensionDefinition] = {}
        self.vendor_extensions: dict[str, dict[str, ExtensionDefinition]] = {}
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "ignored": 0,
            "unsupported": 0,
        }
        self.logger.info("Extension service initialized")

    async def process_mandatory_extensions(
        self, extensions: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        """
        Process mandatory extension parameters (ETSI requirement)

        Args:
            extensions: List of mandatory extensions

        Returns:
            Dict containing extension responses

        Raises:
            ValueError: If mandatory extension processing fails
        """
        start_time = datetime.datetime.utcnow()

        try:
            if not extensions:
                self.logger.info("No mandatory extensions to process")
                return {}

            self.logger.info(
                "Processing mandatory extensions",
                count=len(extensions),
            )

            extension_responses = {}
            failed_extensions = []

            for ext in extensions:
                try:
                    response = await self._process_single_extension(
                        ext, ExtensionType.MANDATORY
                    )

                    if response.status == ExtensionStatus.SUCCESS:
                        extension_responses[response.extension_type] = response.result
                    else:
                        failed_extensions.append(
                            {
                                "extension": ext,
                                "error": response.error_message,
                            }
                        )
                        # For mandatory extensions, failures are critical
                        raise ValueError(
                            f"Mandatory extension failed: {response.error_message}"
                        )

                except Exception as e:
                    self.logger.error(
                        "Mandatory extension processing failed",
                        extension=ext,
                        error=str(e),
                    )
                    failed_extensions.append(
                        {
                            "extension": ext,
                            "error": str(e),
                        }
                    )
                    raise ValueError(f"Mandatory extension processing failed: {str(e)}")

            processing_time = (
                datetime.datetime.utcnow() - start_time
            ).total_seconds() * 1000

            self.logger.info(
                "Mandatory extensions processed successfully",
                count=len(extension_responses),
                processing_time_ms=processing_time,
            )

            # Update statistics
            self.processing_stats["total_processed"] += len(extensions)
            self.processing_stats["successful"] += len(extension_responses)

            return extension_responses

        except Exception as e:
            self.logger.error("Mandatory extension processing error", error=str(e))
            self.processing_stats["failed"] += len(extensions) if extensions else 0
            raise ValueError(f"Mandatory extension processing error: {str(e)}")

    async def process_optional_extensions(
        self, extensions: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        """
        Process optional extension parameters (ETSI requirement)

        Args:
            extensions: List of optional extensions

        Returns:
            Dict containing extension responses
        """
        start_time = datetime.datetime.utcnow()

        try:
            if not extensions:
                self.logger.info("No optional extensions to process")
                return {}

            self.logger.info(
                "Processing optional extensions",
                count=len(extensions),
            )

            extension_responses = {}
            ignored_extensions = []

            for ext in extensions:
                try:
                    response = await self._process_single_extension(
                        ext, ExtensionType.OPTIONAL
                    )

                    if response.status == ExtensionStatus.SUCCESS:
                        extension_responses[response.extension_type] = response.result
                    elif response.status == ExtensionStatus.IGNORED:
                        ignored_extensions.append(
                            {
                                "extension": ext,
                                "reason": "Not supported by KME",
                            }
                        )
                    else:
                        # For optional extensions, failures are logged but don't stop processing
                        self.logger.warning(
                            "Optional extension processing failed",
                            extension=ext,
                            error=response.error_message,
                        )
                        ignored_extensions.append(
                            {
                                "extension": ext,
                                "error": response.error_message or "Unknown error",
                            }
                        )

                except Exception as e:
                    self.logger.warning(
                        "Optional extension processing failed",
                        extension=ext,
                        error=str(e),
                    )
                    ignored_extensions.append(
                        {
                            "extension": ext,
                            "error": str(e),
                        }
                    )

            processing_time = (
                datetime.datetime.utcnow() - start_time
            ).total_seconds() * 1000

            self.logger.info(
                "Optional extensions processed",
                successful=len(extension_responses),
                ignored=len(ignored_extensions),
                processing_time_ms=processing_time,
            )

            # Update statistics
            self.processing_stats["total_processed"] += len(extensions)
            self.processing_stats["successful"] += len(extension_responses)
            self.processing_stats["ignored"] += len(ignored_extensions)

            return extension_responses

        except Exception as e:
            self.logger.error("Optional extension processing error", error=str(e))
            self.processing_stats["failed"] += len(extensions) if extensions else 0
            return {}

    async def _process_single_extension(
        self, extension: dict[str, Any], extension_type: ExtensionType
    ) -> ExtensionResponse:
        """
        Process a single extension

        Args:
            extension: Extension data
            extension_type: Type of extension

        Returns:
            ExtensionResponse with processing result
        """
        start_time = datetime.datetime.utcnow()

        try:
            ext_type = extension.get("type", "unknown")
            ext_data = extension.get("data", {})
            ext_version = extension.get("version", "1.0")
            ext_vendor = extension.get("vendor")

            self.logger.info(
                "Processing extension",
                type=ext_type,
                version=ext_version,
                vendor=ext_vendor,
                extension_type=extension_type.value,
            )

            # Check if extension is supported
            if not self._is_extension_supported(ext_type, ext_vendor):
                processing_time = (
                    datetime.datetime.utcnow() - start_time
                ).total_seconds() * 1000
                return ExtensionResponse(
                    extension_type=ext_type,
                    status=ExtensionStatus.UNSUPPORTED,
                    result=None,
                    error_message=f"Extension {ext_type} is not supported",
                    processing_time_ms=processing_time,
                )

            # Validate extension parameters
            validation_result = await self._validate_extension_parameters(
                ext_type, ext_data, ext_vendor
            )
            if not validation_result["valid"]:
                processing_time = (
                    datetime.datetime.utcnow() - start_time
                ).total_seconds() * 1000
                return ExtensionResponse(
                    extension_type=ext_type,
                    status=ExtensionStatus.FAILED,
                    result=None,
                    error_message=f"Extension validation failed: {validation_result['error']}",
                    processing_time_ms=processing_time,
                )

            # Execute extension handler
            handler_result = await self._execute_extension_handler(
                ext_type, ext_data, ext_vendor
            )

            processing_time = (
                datetime.datetime.utcnow() - start_time
            ).total_seconds() * 1000

            return ExtensionResponse(
                extension_type=ext_type,
                status=ExtensionStatus.SUCCESS,
                result=handler_result,
                error_message=None,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = (
                datetime.datetime.utcnow() - start_time
            ).total_seconds() * 1000
            self.logger.error(
                "Extension processing failed",
                extension=extension,
                error=str(e),
            )
            return ExtensionResponse(
                extension_type=extension.get("type", "unknown"),
                status=ExtensionStatus.FAILED,
                result=None,
                error_message=str(e),
                processing_time_ms=processing_time,
            )

    def _is_extension_supported(self, ext_type: str, vendor: str | None = None) -> bool:
        """
        Check if extension is supported

        Args:
            ext_type: Extension type
            vendor: Vendor identifier

        Returns:
            bool: True if supported
        """
        # Check built-in extensions
        if ext_type in self.extension_registry:
            return True

        # Check vendor extensions
        if vendor and vendor in self.vendor_extensions:
            if ext_type in self.vendor_extensions[vendor]:
                return True

        # For now, support basic extensions
        supported_extensions: list[str] = [
            "route_type",
            "key_quality",
            "encryption_mode",
            "compression",
            "priority",
        ]

        return ext_type in supported_extensions

    async def _validate_extension_parameters(
        self, ext_type: str, data: dict[str, Any], vendor: str | None = None
    ) -> dict[str, Any]:
        """
        Validate extension parameters

        Args:
            ext_type: Extension type
            data: Extension data
            vendor: Vendor identifier

        Returns:
            Dict containing validation result
        """
        try:
            # Get extension definition
            ext_def = self._get_extension_definition(ext_type, vendor)

            if not ext_def:
                # Use default validation for unknown extensions
                for param_name, param_value in data.items():
                    validation_result = self._validate_parameter(
                        param_name,
                        param_value,
                        ext_def
                        or ExtensionDefinition(
                            name="default",
                            version="1.0",
                            type=ExtensionType.OPTIONAL,
                            description="Default extension",
                            handler=lambda x: x,
                            required_parameters=[],
                            optional_parameters=[],
                            security_level="low",
                        ),
                    )
                    if not validation_result["valid"]:
                        return validation_result
                return {"valid": True, "error": None}

            # Validate required parameters
            for param in ext_def.required_parameters:
                if param not in data:
                    return {
                        "valid": False,
                        "error": f"Required parameter '{param}' missing",
                    }

            # Validate parameter types and values
            for param_name, param_value in data.items():
                validation_result = self._validate_parameter(
                    param_name, param_value, ext_def
                )
                if not validation_result["valid"]:
                    return validation_result

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _validate_parameter(
        self, param_name: str, param_value: Any, ext_def: ExtensionDefinition
    ) -> dict[str, Any]:
        """
        Validate a single parameter

        Args:
            param_name: Parameter name
            param_value: Parameter value
            ext_def: Extension definition

        Returns:
            Dict containing validation result
        """
        try:
            # Basic type validation
            if isinstance(param_value, str):
                if len(param_value) > 1000:  # Reasonable limit
                    return {
                        "valid": False,
                        "error": f"Parameter '{param_name}' value too long",
                    }
            elif isinstance(param_value, (int, float)):
                if param_value < 0 or param_value > 1e9:  # Reasonable range
                    return {
                        "valid": False,
                        "error": f"Parameter '{param_name}' value out of range",
                    }
            elif isinstance(param_value, dict):
                if len(param_value) > 100:  # Reasonable limit
                    return {
                        "valid": False,
                        "error": f"Parameter '{param_name}' too complex",
                    }

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"Parameter validation error: {str(e)}"}

    async def _execute_extension_handler(
        self, ext_type: str, data: dict[str, Any], vendor: str | None = None
    ) -> dict[str, Any]:
        """
        Execute extension handler

        Args:
            ext_type: Extension type
            data: Extension data
            vendor: Vendor identifier

        Returns:
            Dict containing handler result
        """
        try:
            ext_def = self._get_extension_definition(ext_type, vendor)

            if ext_def and ext_def.handler is not None:
                # Execute custom handler
                if asyncio.iscoroutinefunction(ext_def.handler):
                    result = await ext_def.handler(data)
                else:
                    result = ext_def.handler(data)
                return result
            else:
                # Use default handler
                return await self._default_extension_handler(ext_type, data)

        except Exception as e:
            self.logger.error(
                "Extension handler execution failed",
                ext_type=ext_type,
                error=str(e),
            )
            raise RuntimeError(f"Extension handler execution failed: {str(e)}")

    async def _default_extension_handler(
        self, ext_type: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Default extension handler

        Args:
            ext_type: Extension type
            data: Extension data

        Returns:
            Dict containing default processing result
        """
        # Default handlers for common extensions
        handlers = {
            "route_type": self._handle_route_type,
            "key_quality": self._handle_key_quality,
            "encryption_mode": self._handle_encryption_mode,
            "compression": self._handle_compression,
            "priority": self._handle_priority,
        }

        handler = handlers.get(ext_type, self._handle_generic)

        if asyncio.iscoroutinefunction(handler):
            return await handler(data)
        else:
            return handler(data)

    def _handle_route_type(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle route_type extension"""
        route_type = data.get("route_type", "direct")
        return {
            "route_type": route_type,
            "supported": route_type in ["direct", "relay", "multicast"],
            "processing": "Route type processed successfully",
        }

    def _handle_key_quality(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle key_quality extension"""
        quality_level = data.get("quality_level", "standard")
        return {
            "quality_level": quality_level,
            "supported": quality_level in ["standard", "high", "ultra"],
            "processing": "Key quality requirements processed",
        }

    def _handle_encryption_mode(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle encryption_mode extension"""
        mode = data.get("mode", "AES-256")
        return {
            "encryption_mode": mode,
            "supported": mode in ["AES-256", "AES-128", "ChaCha20"],
            "processing": "Encryption mode processed",
        }

    def _handle_compression(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle compression extension"""
        compression_type = data.get("compression_type", "none")
        return {
            "compression_type": compression_type,
            "supported": compression_type in ["none", "gzip", "lz4"],
            "processing": "Compression requirements processed",
        }

    def _handle_priority(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle priority extension"""
        priority_level = data.get("priority_level", "normal")
        return {
            "priority_level": priority_level,
            "supported": priority_level in ["low", "normal", "high", "urgent"],
            "processing": "Priority requirements processed",
        }

    def _handle_generic(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle generic extension"""
        return {
            "processed": True,
            "data": data,
            "processing": "Generic extension processed",
        }

    def _get_extension_definition(
        self, ext_type: str, vendor: str | None = None
    ) -> ExtensionDefinition | None:
        """
        Get extension definition

        Args:
            ext_type: Extension type
            vendor: Vendor identifier

        Returns:
            ExtensionDefinition or None
        """
        # Check built-in extensions
        if ext_type in self.extension_registry:
            return self.extension_registry[ext_type]

        # Check vendor extensions
        if vendor and vendor in self.vendor_extensions:
            if ext_type in self.vendor_extensions[vendor]:
                return self.vendor_extensions[vendor][ext_type]

        return None

    def get_processing_statistics(self) -> dict[str, Any]:
        """
        Get extension processing statistics

        Returns:
            Dict containing processing statistics
        """
        return {
            **self.processing_stats,
            "success_rate": (
                self.processing_stats["successful"]
                / max(self.processing_stats["total_processed"], 1)
            )
            * 100,
        }

    def get_supported_extensions(self) -> list[dict[str, Any]]:
        """
        Get list of supported extensions

        Returns:
            List of supported extensions
        """
        extensions = []

        # Built-in extensions
        for ext_name, ext_def in self.extension_registry.items():
            extensions.append(
                {
                    "name": ext_name,
                    "version": ext_def.version,
                    "type": ext_def.type.value,
                    "description": ext_def.description,
                    "vendor": ext_def.vendor,
                }
            )

        # Vendor extensions
        for vendor, vendor_exts in self.vendor_extensions.items():
            for ext_name, ext_def in vendor_exts.items():
                extensions.append(
                    {
                        "name": ext_name,
                        "version": ext_def.version,
                        "type": ext_def.type.value,
                        "description": ext_def.description,
                        "vendor": vendor,
                    }
                )

        return extensions


# Global extension service instance
extension_service = ExtensionService()
