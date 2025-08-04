#!/usr/bin/env python3
"""
KME Vendor Extension Service - ETSI QKD 014 V1.1.1 Compliant

Version: 1.0.0
Author: KME Development Team
Description: Vendor extension support for KME
License: [To be determined]

Week 13.2: Vendor Extension Support
- Vendor extension registry
- Extension compatibility checking
- Extension documentation generation
- Extension validation framework
- Extension versioning
- Extension security validation
"""

import datetime
import hashlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel, Field, field_validator

from app.services.extension_service import ExtensionDefinition, ExtensionType

logger = structlog.get_logger()


class VendorExtensionStatus(str, Enum):
    """Vendor extension status"""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    PENDING = "pending"


class SecurityLevel(str, Enum):
    """Extension security levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VendorExtensionDefinition:
    """Vendor extension definition"""

    name: str
    version: str
    vendor: str
    description: str
    handler: Callable
    required_parameters: list[str]
    optional_parameters: list[str]
    security_level: SecurityLevel
    status: VendorExtensionStatus
    documentation: str
    compatibility_matrix: dict[str, list[str]]
    validation_rules: dict[str, Any]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    checksum: str


class VendorExtensionRequest(BaseModel):
    """Vendor extension registration request"""

    name: str = Field(..., description="Extension name")
    version: str = Field(..., description="Extension version")
    vendor: str = Field(..., description="Vendor identifier")
    description: str = Field(..., description="Extension description")
    handler_function: str = Field(..., description="Handler function name")
    required_parameters: list[str] = Field(
        default=[], description="Required parameters"
    )
    optional_parameters: list[str] = Field(
        default=[], description="Optional parameters"
    )
    security_level: SecurityLevel = Field(
        default=SecurityLevel.MEDIUM, description="Security level"
    )
    documentation: str = Field(..., description="Extension documentation")
    compatibility_matrix: dict[str, list[str]] = Field(
        default={}, description="Compatibility matrix"
    )
    validation_rules: dict[str, Any] = Field(default={}, description="Validation rules")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate extension name format"""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError(
                "Extension name must start with letter and contain only alphanumeric characters and underscores"
            )
        if len(v) > 50:
            raise ValueError("Extension name too long (max 50 characters)")
        return v

    @field_validator("vendor")
    @classmethod
    def validate_vendor(cls, v: str) -> str:
        """Validate vendor identifier"""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError(
                "Vendor identifier must start with letter and contain only alphanumeric characters and underscores"
            )
        if len(v) > 30:
            raise ValueError("Vendor identifier too long (max 30 characters)")
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format"""
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Version must be in format X.Y.Z")
        return v


class VendorExtensionResponse(BaseModel):
    """Vendor extension registration response"""

    success: bool = Field(..., description="Registration success")
    extension_id: str = Field(..., description="Unique extension identifier")
    message: str = Field(..., description="Response message")
    validation_results: dict[str, Any] = Field(
        default={}, description="Validation results"
    )
    compatibility_results: dict[str, Any] = Field(
        default={}, description="Compatibility results"
    )
    security_results: dict[str, Any] = Field(
        default={}, description="Security validation results"
    )


class VendorExtensionService:
    """
    Vendor extension service for KME

    Implements vendor extension registry, validation, and management
    """

    def __init__(self):
        """Initialize the vendor extension service"""
        self.logger = logger.bind(service="VendorExtensionService")
        self.vendor_registry: dict[str, dict[str, VendorExtensionDefinition]] = {}
        self.extension_handlers: dict[str, Callable] = {}
        self.validation_results: dict[str, dict[str, Any]] = {}
        self.logger.info("Vendor extension service initialized")

    async def register_vendor_extension(
        self, request: VendorExtensionRequest, handler: Callable
    ) -> VendorExtensionResponse:
        """
        Register a vendor extension

        Args:
            request: Extension registration request
            handler: Extension handler function

        Returns:
            VendorExtensionResponse with registration results
        """
        try:
            self.logger.info(
                "Registering vendor extension",
                name=request.name,
                vendor=request.vendor,
                version=request.version,
            )

            # Generate unique extension ID
            extension_id = self._generate_extension_id(
                request.vendor, request.name, request.version
            )

            # Validate extension
            validation_results = await self._validate_extension_registration(
                request, handler
            )
            if not validation_results["valid"]:
                return VendorExtensionResponse(
                    success=False,
                    extension_id=extension_id,
                    message="Extension validation failed",
                    validation_results=validation_results,
                )

            # Check compatibility
            compatibility_results = await self._check_extension_compatibility(request)
            if not compatibility_results["compatible"]:
                return VendorExtensionResponse(
                    success=False,
                    extension_id=extension_id,
                    message="Extension compatibility check failed",
                    compatibility_results=compatibility_results,
                )

            # Security validation
            security_results = await self._validate_extension_security(request, handler)
            if not security_results["secure"]:
                return VendorExtensionResponse(
                    success=False,
                    extension_id=extension_id,
                    message="Extension security validation failed",
                    security_results=security_results,
                )

            # Create extension definition
            extension_def = VendorExtensionDefinition(
                name=request.name,
                version=request.version,
                vendor=request.vendor,
                description=request.description,
                handler=handler,
                required_parameters=request.required_parameters,
                optional_parameters=request.optional_parameters,
                security_level=request.security_level,
                status=VendorExtensionStatus.PENDING,
                documentation=request.documentation,
                compatibility_matrix=request.compatibility_matrix,
                validation_rules=request.validation_rules,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
                checksum=self._calculate_checksum(request, handler),
            )

            # Register extension
            if request.vendor not in self.vendor_registry:
                self.vendor_registry[request.vendor] = {}

            self.vendor_registry[request.vendor][request.name] = extension_def
            self.extension_handlers[extension_id] = handler

            # Generate documentation
            doc_result = await self._generate_extension_documentation(extension_def)

            self.logger.info(
                "Vendor extension registered successfully",
                extension_id=extension_id,
                vendor=request.vendor,
                name=request.name,
            )

            return VendorExtensionResponse(
                success=True,
                extension_id=extension_id,
                message="Extension registered successfully",
                validation_results=validation_results,
                compatibility_results=compatibility_results,
                security_results=security_results,
            )

        except Exception as e:
            self.logger.error(
                "Vendor extension registration failed",
                error=str(e),
                request=request.dict(),
            )
            return VendorExtensionResponse(
                success=False,
                extension_id="",
                message=f"Registration failed: {str(e)}",
            )

    async def _validate_extension_registration(
        self, request: VendorExtensionRequest, handler: Callable
    ) -> dict[str, Any]:
        """
        Validate extension registration

        Args:
            request: Extension request
            handler: Extension handler

        Returns:
            Dict containing validation results
        """
        try:
            validation_results: dict[str, Any] = {
                "valid": True,
                "errors": [],
                "warnings": [],
            }

            # Check if extension already exists
            if (
                request.vendor in self.vendor_registry
                and request.name in self.vendor_registry[request.vendor]
            ):
                existing_ext = self.vendor_registry[request.vendor][request.name]
                if existing_ext.version == request.version:
                    validation_results["valid"] = False
                    validation_results["errors"].append(
                        f"Extension {request.name} version {request.version} already exists"
                    )

            # Validate handler function
            if not callable(handler):
                validation_results["valid"] = False
                validation_results["errors"].append(
                    "Handler must be a callable function"
                )

            # Validate parameter names
            all_params = request.required_parameters + request.optional_parameters
            for param in all_params:
                if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", param):
                    validation_results["valid"] = False
                    validation_results["errors"].append(
                        f"Invalid parameter name: {param}"
                    )

            # Check for duplicate parameters
            if len(all_params) != len(set(all_params)):
                validation_results["valid"] = False
                validation_results["errors"].append("Duplicate parameter names found")

            # Validate documentation
            if len(request.documentation) < 10:
                validation_results["warnings"].append("Documentation seems too short")

            return validation_results

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
            }

    async def _check_extension_compatibility(
        self, request: VendorExtensionRequest
    ) -> dict[str, Any]:
        """
        Check extension compatibility

        Args:
            request: Extension request

        Returns:
            Dict containing compatibility results
        """
        try:
            compatibility_results: dict[str, Any] = {
                "compatible": True,
                "issues": [],
                "recommendations": [],
            }

            # Check KME version compatibility
            kme_version = "1.0.0"  # Current KME version
            if "kme_version" in request.compatibility_matrix:
                supported_versions = request.compatibility_matrix["kme_version"]
                if kme_version not in supported_versions:
                    compatibility_results["compatible"] = False
                    compatibility_results["issues"].append(
                        f"KME version {kme_version} not supported"
                    )

            # Check extension naming conflicts
            for vendor, extensions in self.vendor_registry.items():
                for ext_name in extensions:
                    if ext_name == request.name and vendor != request.vendor:
                        compatibility_results["warnings"].append(
                            f"Extension name conflict with vendor {vendor}"
                        )

            # Check parameter naming conflicts
            existing_params = set()
            for vendor, extensions in self.vendor_registry.items():
                for ext in extensions.values():
                    existing_params.update(ext.required_parameters)
                    existing_params.update(ext.optional_parameters)

            new_params = set(request.required_parameters + request.optional_parameters)
            conflicts = existing_params.intersection(new_params)
            if conflicts:
                compatibility_results["warnings"].append(
                    f"Parameter name conflicts: {list(conflicts)}"
                )

            return compatibility_results

        except Exception as e:
            return {
                "compatible": False,
                "issues": [f"Compatibility check error: {str(e)}"],
                "recommendations": [],
            }

    async def _validate_extension_security(
        self, request: VendorExtensionRequest, handler: Callable
    ) -> dict[str, Any]:
        """
        Validate extension security

        Args:
            request: Extension request
            handler: Extension handler

        Returns:
            Dict containing security validation results
        """
        try:
            security_results: dict[str, Any] = {
                "secure": True,
                "issues": [],
                "recommendations": [],
                "warnings": [],
            }

            # Check security level appropriateness
            if request.security_level == SecurityLevel.CRITICAL:
                # Critical extensions require additional validation
                if not self._validate_critical_extension(request, handler):
                    security_results["secure"] = False
                    security_results["issues"].append(
                        "Critical extension validation failed"
                    )

            # Check for potentially dangerous operations
            handler_source = self._get_handler_source(handler)
            dangerous_patterns = [
                "eval(",
                "exec(",
                "os.system(",
                "subprocess.call(",
                "open(",
            ]

            for pattern in dangerous_patterns:
                if pattern in handler_source:
                    security_results["secure"] = False
                    security_results["issues"].append(
                        f"Potentially dangerous operation detected: {pattern}"
                    )

            # Check parameter validation
            if not request.validation_rules:
                security_results["warnings"].append(
                    "No validation rules specified for parameters"
                )

            # Check documentation completeness
            if len(request.documentation) < 50:
                security_results["warnings"].append(
                    "Security documentation seems incomplete"
                )

            return security_results

        except Exception as e:
            return {
                "secure": False,
                "issues": [f"Security validation error: {str(e)}"],
                "recommendations": [],
                "warnings": [],
            }

    def _validate_critical_extension(
        self, request: VendorExtensionRequest, handler: Callable
    ) -> bool:
        """
        Validate critical extension

        Args:
            request: Extension request
            handler: Extension handler

        Returns:
            bool: True if critical extension is valid
        """
        try:
            # Critical extensions require additional checks
            if request.security_level == SecurityLevel.CRITICAL:
                # Check for proper error handling
                handler_source = self._get_handler_source(handler)
                if "try:" not in handler_source or "except:" not in handler_source:
                    return False

                # Check for proper logging
                if "logger" not in handler_source and "log" not in handler_source:
                    return False

                # Check for input validation
                if "validate" not in handler_source and "check" not in handler_source:
                    return False

            return True

        except Exception:
            return False

    def _get_handler_source(self, handler: Callable) -> str:
        """
        Get handler source code

        Args:
            handler: Extension handler

        Returns:
            str: Handler source code
        """
        try:
            import inspect

            return inspect.getsource(handler)
        except Exception:
            return str(handler)

    async def _generate_extension_documentation(
        self, extension_def: VendorExtensionDefinition
    ) -> dict[str, Any]:
        """
        Generate extension documentation

        Args:
            extension_def: Extension definition

        Returns:
            Dict containing documentation generation results
        """
        try:
            doc_result: dict[str, Any] = {
                "generated": True,
                "file_path": None,
                "content": None,
            }

            # Generate documentation content
            doc_content = f"""
# Vendor Extension Documentation

## Extension Details
- **Name**: {extension_def.name}
- **Vendor**: {extension_def.vendor}
- **Version**: {extension_def.version}
- **Status**: {extension_def.status.value}
- **Security Level**: {extension_def.security_level.value}

## Description
{extension_def.description}

## Parameters

### Required Parameters
{chr(10).join([f"- {param}" for param in extension_def.required_parameters])}

### Optional Parameters
{chr(10).join([f"- {param}" for param in extension_def.optional_parameters])}

## Validation Rules
```json
{json.dumps(extension_def.validation_rules, indent=2)}
```

## Compatibility Matrix
```json
{json.dumps(extension_def.compatibility_matrix, indent=2)}
```

## Security Considerations
- Security Level: {extension_def.security_level.value}
- Created: {extension_def.created_at.isoformat()}
- Updated: {extension_def.updated_at.isoformat()}
- Checksum: {extension_def.checksum}

## Usage Examples
[To be provided by vendor]

## Support
Contact vendor {extension_def.vendor} for support and updates.
"""

            doc_result["content"] = doc_content

            # Save documentation to file
            doc_filename = f"docs/extensions/{extension_def.vendor}_{extension_def.name}_{extension_def.version}.md"
            # Note: In a real implementation, this would write to a file
            doc_result["file_path"] = doc_filename

            self.logger.info(
                "Extension documentation generated",
                extension_name=extension_def.name,
                vendor=extension_def.vendor,
                file_path=doc_filename,
            )

            return doc_result

        except Exception as e:
            self.logger.error(
                "Documentation generation failed",
                error=str(e),
                extension_name=extension_def.name,
            )
            return {
                "generated": False,
                "error": str(e),
            }

    def _generate_extension_id(self, vendor: str, name: str, version: str) -> str:
        """
        Generate unique extension ID

        Args:
            vendor: Vendor identifier
            name: Extension name
            version: Extension version

        Returns:
            str: Unique extension ID
        """
        content = f"{vendor}:{name}:{version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _calculate_checksum(
        self, request: VendorExtensionRequest, handler: Callable
    ) -> str:
        """
        Calculate extension checksum

        Args:
            request: Extension request
            handler: Extension handler

        Returns:
            str: Extension checksum
        """
        try:
            content = json.dumps(request.model_dump(), sort_keys=True)
            handler_source = self._get_handler_source(handler)
            full_content = content + handler_source
            return hashlib.sha256(full_content.encode()).hexdigest()
        except Exception:
            return "unknown"

    def get_vendor_extensions(self, vendor: str) -> list[dict[str, Any]]:
        """
        Get extensions for a specific vendor

        Args:
            vendor: Vendor identifier

        Returns:
            List of vendor extensions
        """
        extensions = []
        if vendor in self.vendor_registry:
            for ext_name, ext_def in self.vendor_registry[vendor].items():
                extensions.append(
                    {
                        "name": ext_name,
                        "version": ext_def.version,
                        "description": ext_def.description,
                        "status": ext_def.status.value,
                        "security_level": ext_def.security_level.value,
                        "created_at": ext_def.created_at.isoformat(),
                        "updated_at": ext_def.updated_at.isoformat(),
                    }
                )
        return extensions

    def get_extension_details(self, vendor: str, name: str) -> dict[str, Any] | None:
        """
        Get detailed information about an extension

        Args:
            vendor: Vendor identifier
            name: Extension name

        Returns:
            Extension details or None
        """
        if vendor in self.vendor_registry and name in self.vendor_registry[vendor]:
            ext_def = self.vendor_registry[vendor][name]
            return {
                "name": ext_def.name,
                "version": ext_def.version,
                "vendor": ext_def.vendor,
                "description": ext_def.description,
                "status": ext_def.status.value,
                "security_level": ext_def.security_level.value,
                "required_parameters": ext_def.required_parameters,
                "optional_parameters": ext_def.optional_parameters,
                "documentation": ext_def.documentation,
                "compatibility_matrix": ext_def.compatibility_matrix,
                "validation_rules": ext_def.validation_rules,
                "created_at": ext_def.created_at.isoformat(),
                "updated_at": ext_def.updated_at.isoformat(),
                "checksum": ext_def.checksum,
            }
        return None

    def update_extension_status(
        self, vendor: str, name: str, status: VendorExtensionStatus
    ) -> bool:
        """
        Update extension status

        Args:
            vendor: Vendor identifier
            name: Extension name
            status: New status

        Returns:
            bool: True if updated successfully
        """
        try:
            if vendor in self.vendor_registry and name in self.vendor_registry[vendor]:
                ext_def = self.vendor_registry[vendor][name]
                ext_def.status = status
                ext_def.updated_at = datetime.datetime.utcnow()

                self.logger.info(
                    "Extension status updated",
                    vendor=vendor,
                    name=name,
                    status=status.value,
                )
                return True
            return False

        except Exception as e:
            self.logger.error(
                "Failed to update extension status",
                vendor=vendor,
                name=name,
                error=str(e),
            )
            return False

    def get_registry_statistics(self) -> dict[str, Any]:
        """
        Get vendor extension registry statistics

        Returns:
            Dict containing registry statistics
        """
        total_extensions = 0
        vendors = list(self.vendor_registry.keys())
        status_counts = {status.value: 0 for status in VendorExtensionStatus}
        security_counts = {level.value: 0 for level in SecurityLevel}

        for vendor, extensions in self.vendor_registry.items():
            total_extensions += len(extensions)
            for ext_def in extensions.values():
                status_counts[ext_def.status.value] += 1
                security_counts[ext_def.security_level.value] += 1

        return {
            "total_extensions": total_extensions,
            "total_vendors": len(vendors),
            "vendors": vendors,
            "status_distribution": status_counts,
            "security_level_distribution": security_counts,
        }


# Global vendor extension service instance
vendor_extension_service = VendorExtensionService()
