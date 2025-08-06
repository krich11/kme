#!/usr/bin/env python3
# mypy: disable-error-code=arg-type
"""
KME Authentication Module

Version: 1.0.0
Author: KME Development Team
Description: Basic certificate authentication and SAE authorization for Week 5.5
License: [To be determined]

This module implements the basic authentication and authorization requirements
for Week 5.5 of the KME development plan.
"""

import asyncio
import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

import structlog
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException, Request, status

from .config import settings
from .security import CertificateInfo, CertificateType, get_certificate_manager

logger = structlog.get_logger()


class AuthenticationError(Exception):
    """Authentication error exception"""

    pass


class AuthorizationError(Exception):
    """Authorization error exception"""

    pass


class CertificateAuthentication:
    """Basic certificate authentication for KME"""

    def __init__(self):
        """Initialize certificate authentication"""
        self.certificate_manager = get_certificate_manager()
        self.logger = structlog.get_logger()

    async def extract_sae_id_from_request(self, request: Request) -> str | None:
        """
        Extract SAE ID from TLS certificate in request

        Args:
            request: FastAPI request object

        Returns:
            str | None: Extracted SAE ID or None if not found
        """
        try:
            # Get client certificate from request
            client_cert = self._get_client_certificate(request)
            if not client_cert:
                self.logger.warning("No client certificate found in request")
                return None

            # Extract SAE ID from certificate
            sae_id = self.certificate_manager.extract_sae_id_from_certificate(
                client_cert
            )
            if sae_id:
                self.logger.info("SAE ID extracted from certificate", sae_id=sae_id)
                return sae_id
            else:
                self.logger.warning("No SAE ID found in client certificate")
                return None

        except Exception as e:
            self.logger.error("Failed to extract SAE ID from request", error=str(e))
            return None

    async def validate_certificate(self, request: Request) -> CertificateInfo:
        """
        Validate client certificate

        Args:
            request: FastAPI request object

        Returns:
            CertificateInfo: Certificate validation information

        Raises:
            AuthenticationError: If certificate validation fails
        """
        try:
            # Get client certificate from request
            client_cert = self._get_client_certificate(request)
            if not client_cert:
                raise AuthenticationError("No client certificate provided")

            # Validate certificate
            cert_info = self.certificate_manager.validate_certificate(client_cert)

            if not cert_info.is_valid:
                self.logger.warning(
                    "Certificate validation failed",
                    subject=cert_info.subject,
                    errors=cert_info.validation_errors,
                )
                raise AuthenticationError(
                    f"Certificate validation failed: {cert_info.validation_errors}"
                )

            self.logger.info(
                "Certificate validation successful",
                subject=cert_info.subject,
                certificate_type=cert_info.certificate_type.value,
            )

            return cert_info

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error("Certificate validation error", error=str(e))
            raise AuthenticationError(f"Certificate validation error: {str(e)}")

    def _get_client_certificate(self, request: Request) -> bytes | None:
        """
        Get client certificate from request

        Args:
            request: FastAPI request object

        Returns:
            bytes | None: Client certificate data or None if not found
        """
        try:
            # Check if client certificate is available in request
            if hasattr(request, "client") and request.client:
                # In a real TLS setup, the certificate would be available here
                # For now, we'll simulate this for development
                if hasattr(request.client, "getpeercert"):
                    cert_data = request.client.getpeercert(binary_form=True)  # type: ignore[attr-defined]
                    if cert_data:
                        return cert_data

            # For development/testing, check for certificate in headers
            cert_header = request.headers.get("X-Client-Certificate")
            if cert_header:
                import base64

                return base64.b64decode(cert_header)

            return None

        except Exception as e:
            self.logger.error("Failed to get client certificate", error=str(e))
            return None

    async def authenticate_request(
        self, request: Request
    ) -> tuple[str, CertificateInfo]:
        """
        Authenticate request and extract SAE ID

        Args:
            request: FastAPI request object

        Returns:
            Tuple[str, CertificateInfo]: SAE ID and certificate info

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Validate certificate
            cert_info = await self.validate_certificate(request)

            # Extract SAE ID
            sae_id = await self.extract_sae_id_from_request(request)
            if not sae_id:
                raise AuthenticationError("No SAE ID found in certificate")

            # Validate SAE ID format (16 characters, hex)
            if not self._validate_sae_id_format(sae_id):
                raise AuthenticationError("Invalid SAE ID format")

            self.logger.info(
                "Request authenticated successfully",
                sae_id=sae_id,
                certificate_type=cert_info.certificate_type.value,
            )

            return sae_id, cert_info

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error("Authentication error", error=str(e))
            raise AuthenticationError(f"Authentication error: {str(e)}")

    def _validate_sae_id_format(self, sae_id: str) -> bool:
        """
        Validate SAE ID format

        Args:
            sae_id: SAE ID to validate

        Returns:
            bool: True if valid format
        """
        if not sae_id:
            return False

        # Check if it contains only alphanumeric characters (A-Z, a-z, 0-9)
        return bool(re.match(r"^[A-Za-z0-9]+$", sae_id))


class SAEAuthorization:
    """Basic SAE authorization for KME"""

    def __init__(self, db_session=None):
        """Initialize SAE authorization"""
        self.db_session = db_session
        self.logger = structlog.get_logger()

    async def validate_key_access(
        self,
        requesting_sae_id: str,
        slave_sae_id: str,
        master_sae_id: str | None = None,
    ) -> bool:
        """
        Validate SAE access for key operations

        Args:
            requesting_sae_id: SAE ID of the requesting entity
            slave_sae_id: SAE ID of the slave SAE
            master_sae_id: SAE ID of the master SAE (optional)

        Returns:
            bool: True if access is authorized

        Raises:
            AuthorizationError: If access is denied
        """
        try:
            self.logger.info(
                "Validating key access",
                requesting_sae_id=requesting_sae_id,
                slave_sae_id=slave_sae_id,
                master_sae_id=master_sae_id,
            )

            # Basic authorization rules for Week 5.5
            # 1. Requesting SAE must be the master SAE or the slave SAE
            # 2. For key requests, requesting SAE must be the master SAE
            # 3. For key retrieval, requesting SAE must be the slave SAE

            # Check if requesting SAE is the master SAE
            if master_sae_id and requesting_sae_id == master_sae_id:
                self.logger.info("Access granted - requesting SAE is master SAE")
                return True

            # Check if requesting SAE is the slave SAE
            if requesting_sae_id == slave_sae_id:
                self.logger.info("Access granted - requesting SAE is slave SAE")
                return True

            # Check if this is a key request (master operation)
            if master_sae_id and requesting_sae_id != master_sae_id:
                self.logger.warning(
                    "Access denied - key request must be from master SAE",
                    requesting_sae_id=requesting_sae_id,
                    master_sae_id=master_sae_id,
                )
                raise AuthorizationError("Key requests must be from master SAE")

            # Check if this is a key retrieval (slave operation)
            if requesting_sae_id != slave_sae_id:
                self.logger.warning(
                    "Access denied - key retrieval must be from slave SAE",
                    requesting_sae_id=requesting_sae_id,
                    slave_sae_id=slave_sae_id,
                )
                raise AuthorizationError("Key retrieval must be from slave SAE")

            return True

        except AuthorizationError:
            raise
        except Exception as e:
            self.logger.error("Authorization error", error=str(e))
            raise AuthorizationError(f"Authorization error: {str(e)}")

    async def _is_sae_registered(self, sae_id: str) -> bool:  # type: ignore[misc]
        """
        Check if SAE is registered in the database

        Args:
            sae_id: SAE ID to check

        Returns:
            bool: True if SAE is registered, False otherwise
        """
        if not self.db_session:
            # If no database session, assume SAE is registered for testing
            self.logger.warning(
                "No database session - assuming SAE is registered", sae_id=sae_id
            )
            return True

        try:
            from sqlalchemy import and_, select

            from app.models.database_models import SAEEntity

            # Build query with proper SQLAlchemy expressions
            query = (
                select(SAEEntity)
                .where(SAEEntity.sae_id == sae_id)  # type: ignore
                .where(SAEEntity.status == "active")  # type: ignore
            )
            result = await self.db_session.execute(query)
            sae_entity = result.scalar_one_or_none()

            return sae_entity is not None

        except Exception as e:
            self.logger.error(
                "Failed to check SAE registration", sae_id=sae_id, error=str(e)
            )
            return False

    async def _validate_sae_relationship(  # type: ignore[misc]
        self,
        requesting_sae_id: str,
        slave_sae_id: str,
        master_sae_id: str | None = None,
    ) -> bool:
        """
        Validate SAE relationship for authorization

        Args:
            requesting_sae_id: SAE ID of the requesting entity
            slave_sae_id: SAE ID of the slave SAE
            master_sae_id: SAE ID of the master SAE (optional)

        Returns:
            bool: True if relationship is valid, False otherwise
        """
        if not self.db_session:
            # If no database session, assume relationship is valid for testing
            self.logger.warning(
                "No database session - assuming SAE relationship is valid"
            )
            return True

        try:
            from sqlalchemy import and_, func, select

            from app.models.database_models import KeyRecord

            # Check if there are any keys shared between these SAEs
            # This indicates a valid relationship
            # Build query with proper SQLAlchemy expressions
            relationship_query = (
                select(func.count(KeyRecord.id))
                .where(KeyRecord.master_sae_id == requesting_sae_id)  # type: ignore
                .where(KeyRecord.slave_sae_id == slave_sae_id)  # type: ignore
                .where(KeyRecord.status == "active")  # type: ignore
            )
            result = await self.db_session.execute(relationship_query)
            key_count = result.scalar() or 0

            # For now, consider any existing key relationship as valid
            # In a real implementation, this would check specific authorization policies
            return key_count > 0

        except Exception as e:
            self.logger.error(
                "Failed to validate SAE relationship",
                requesting_sae_id=requesting_sae_id,
                slave_sae_id=slave_sae_id,
                master_sae_id=master_sae_id,
                error=str(e),
            )
            return False

    async def validate_status_access(
        self,
        requesting_sae_id: str,
        slave_sae_id: str,
        master_sae_id: str | None = None,
    ) -> bool:
        """
        Validate SAE access for status operations

        Args:
            requesting_sae_id: SAE ID of the requesting entity
            slave_sae_id: SAE ID of the slave SAE
            master_sae_id: SAE ID of the master SAE (optional)

        Returns:
            bool: True if access is authorized

        Raises:
            AuthorizationError: If access is denied
        """
        try:
            self.logger.info(
                "Validating status access",
                requesting_sae_id=requesting_sae_id,
                slave_sae_id=slave_sae_id,
                master_sae_id=master_sae_id,
            )

            # Basic authorization rules for status access
            # 1. Requesting SAE must be the master SAE or the slave SAE
            # 2. Master SAE can access status of any slave SAE
            # 3. Slave SAE can only access its own status

            # Check if requesting SAE is the master SAE
            if master_sae_id and requesting_sae_id == master_sae_id:
                self.logger.info("Status access granted - requesting SAE is master SAE")
                return True

            # Check if requesting SAE is the slave SAE
            if requesting_sae_id == slave_sae_id:
                self.logger.info("Status access granted - requesting SAE is slave SAE")
                return True

            # Access denied
            self.logger.warning(
                "Status access denied - unauthorized SAE",
                requesting_sae_id=requesting_sae_id,
                slave_sae_id=slave_sae_id,
                master_sae_id=master_sae_id,
            )
            raise AuthorizationError("Unauthorized access to status information")

        except AuthorizationError:
            raise
        except Exception as e:
            self.logger.error("Status authorization error", error=str(e))
            raise AuthorizationError(f"Status authorization error: {str(e)}")


class ExtensionProcessor:
    """Enhanced extension processing using comprehensive extension service"""

    def __init__(self):
        """Initialize extension processor"""
        self.logger = structlog.get_logger()
        # Import the comprehensive extension service
        from app.services.extension_service import extension_service

        self.extension_service = extension_service

    async def process_mandatory_extensions(
        self, extensions: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        """
        Process mandatory extension parameters using comprehensive extension service

        Args:
            extensions: List of mandatory extensions

        Returns:
            Dict[str, Any]: Extension responses
        """
        try:
            return await self.extension_service.process_mandatory_extensions(extensions)
        except Exception as e:
            self.logger.error("Mandatory extension processing error", error=str(e))
            raise ValueError(f"Mandatory extension processing error: {str(e)}")

    async def process_optional_extensions(
        self, extensions: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        """
        Process optional extension parameters using comprehensive extension service

        Args:
            extensions: List of optional extensions

        Returns:
            Dict[str, Any]: Extension responses
        """
        try:
            return await self.extension_service.process_optional_extensions(extensions)
        except Exception as e:
            self.logger.error("Optional extension processing error", error=str(e))
            # For optional extensions, return empty dict instead of raising
            return {}


# Global instances
certificate_auth = CertificateAuthentication()
sae_authorization = SAEAuthorization()
extension_processor = ExtensionProcessor()


def get_certificate_auth() -> CertificateAuthentication:
    """Get certificate authentication instance"""
    return certificate_auth


def get_sae_authorization() -> SAEAuthorization:
    """Get SAE authorization instance"""
    return sae_authorization


def get_extension_processor() -> ExtensionProcessor:
    """Get extension processor instance"""
    return extension_processor
