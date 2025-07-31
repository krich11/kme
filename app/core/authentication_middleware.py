#!/usr/bin/env python3
"""
Authentication Middleware - Week 5.6 Implementation

Enhanced certificate authentication middleware for API routes.
Provides detailed authentication logging, audit trails, and monitoring.

Version: 1.0.0
Author: KME Development Team
Description: Enhanced authentication middleware for ETSI QKD 014 compliance
License: [To be determined]
"""

import time
import uuid
from typing import Any, Dict, Optional, Tuple

import structlog
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException, Request, status

from app.core.authentication import (
    AuthenticationError,
    AuthorizationError,
    get_certificate_auth,
    get_sae_authorization,
)
from app.core.security import CertificateInfo, get_certificate_manager

logger = structlog.get_logger()


class AuthenticationMiddleware:
    """
    Enhanced authentication middleware for API routes.

    Provides detailed certificate authentication, logging, audit trails,
    and monitoring capabilities for Week 5.6 implementation.
    """

    def __init__(self):
        """Initialize the authentication middleware."""
        self.certificate_auth = get_certificate_auth()
        self.sae_auth = get_sae_authorization()
        self.certificate_manager = get_certificate_manager()

        # Authentication metrics
        self.auth_attempts = 0
        self.auth_successes = 0
        self.auth_failures = 0
        self.cert_validation_failures = 0
        self.authorization_failures = 0

    async def authenticate_request(
        self,
        request: Request,
        endpoint_type: str,
        resource_id: str,
    ) -> tuple[str, CertificateInfo, dict[str, Any]]:
        """
        Authenticate and authorize a request with enhanced logging and monitoring.

        Args:
            request: FastAPI request object
            endpoint_type: Type of endpoint (status, key, key_ids)
            resource_id: Resource identifier (SAE ID, etc.)

        Returns:
            Tuple of (requesting_sae_id, certificate_info, audit_data)

        Raises:
            HTTPException: 401 for authentication failures, 403 for authorization failures
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        self.auth_attempts += 1

        # Initialize audit data
        audit_data = {
            "request_id": request_id,
            "endpoint_type": endpoint_type,
            "resource_id": resource_id,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": start_time,
            "authentication_time": 0,
            "certificate_validation": {},
            "authorization_check": {},
            "success": False,
        }

        try:
            # Step 1: Extract and validate certificate
            logger.info(
                "Starting certificate authentication",
                request_id=request_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                client_ip=audit_data["client_ip"],
            )

            requesting_sae_id, cert_info = await self._extract_and_validate_certificate(
                request, request_id, audit_data
            )

            # Step 2: Perform authorization check
            await self._perform_authorization_check(
                requesting_sae_id, endpoint_type, resource_id, request_id, audit_data
            )

            # Step 3: Update metrics and audit data
            self.auth_successes += 1
            audit_data["success"] = True
            audit_data["authentication_time"] = time.time() - start_time

            logger.info(
                "Authentication successful",
                request_id=request_id,
                requesting_sae_id=requesting_sae_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                auth_time=audit_data["authentication_time"],
            )

            return requesting_sae_id, cert_info, audit_data

        except AuthenticationError as e:
            self.auth_failures += 1
            self.cert_validation_failures += 1
            audit_data["authentication_time"] = time.time() - start_time
            audit_data["error"] = str(e)
            audit_data["error_type"] = "authentication"

            logger.warning(
                "Authentication failed",
                request_id=request_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                error=str(e),
                auth_time=audit_data["authentication_time"],
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}",
            )

        except AuthorizationError as e:
            self.auth_failures += 1
            self.authorization_failures += 1
            audit_data["authentication_time"] = time.time() - start_time
            audit_data["error"] = str(e)
            audit_data["error_type"] = "authorization"

            logger.warning(
                "Authorization failed",
                request_id=request_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                error=str(e),
                auth_time=audit_data["authentication_time"],
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Authorization failed: {str(e)}",
            )

        except Exception as e:
            self.auth_failures += 1
            audit_data["authentication_time"] = time.time() - start_time
            audit_data["error"] = str(e)
            audit_data["error_type"] = "unexpected"

            logger.error(
                "Unexpected authentication error",
                request_id=request_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                error=str(e),
                auth_time=audit_data["authentication_time"],
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal authentication error",
            )

    async def _extract_and_validate_certificate(
        self,
        request: Request,
        request_id: str,
        audit_data: dict[str, Any],
    ) -> tuple[str, CertificateInfo]:
        """
        Extract and validate certificate with detailed logging.

        Args:
            request: FastAPI request object
            request_id: Request identifier for tracking
            audit_data: Audit data dictionary to update

        Returns:
            Tuple of (requesting_sae_id, certificate_info)

        Raises:
            AuthenticationError: If certificate extraction or validation fails
        """
        cert_start_time = time.time()

        try:
            # Extract certificate from request
            cert_data = self._extract_certificate_from_request(request)
            audit_data["certificate_validation"]["certificate_found"] = True
            audit_data["certificate_validation"]["certificate_size"] = (
                len(cert_data) if cert_data else 0
            )

            # Parse certificate
            cert = x509.load_pem_x509_certificate(cert_data)
            audit_data["certificate_validation"]["certificate_parsed"] = True
            audit_data["certificate_validation"]["subject"] = str(cert.subject)
            audit_data["certificate_validation"]["issuer"] = str(cert.issuer)
            audit_data["certificate_validation"]["serial_number"] = str(
                cert.serial_number
            )
            audit_data["certificate_validation"][
                "not_valid_before"
            ] = cert.not_valid_before.isoformat()
            audit_data["certificate_validation"][
                "not_valid_after"
            ] = cert.not_valid_after.isoformat()

            # Validate certificate using certificate manager
            cert_info = self.certificate_manager.validate_certificate(cert_data)
            audit_data["certificate_validation"][
                "certificate_valid"
            ] = cert_info.is_valid
            audit_data["certificate_validation"][
                "certificate_type"
            ] = cert_info.certificate_type.value

            if not cert_info.is_valid:
                raise AuthenticationError("Certificate validation failed")

            # Extract SAE ID
            requesting_sae_id = (
                self.certificate_manager.extract_sae_id_from_certificate(cert_data)
            )
            audit_data["certificate_validation"]["sae_id_extracted"] = requesting_sae_id
            audit_data["certificate_validation"][
                "sae_id_valid"
            ] = self.certificate_auth._validate_sae_id_format(requesting_sae_id)

            if not requesting_sae_id:
                raise AuthenticationError("Failed to extract SAE ID from certificate")

            if not self.certificate_auth._validate_sae_id_format(requesting_sae_id):
                raise AuthenticationError("Invalid SAE ID format in certificate")

            audit_data["certificate_validation"]["validation_time"] = (
                time.time() - cert_start_time
            )

            logger.debug(
                "Certificate validation successful",
                request_id=request_id,
                sae_id=requesting_sae_id,
                cert_type=cert_info.certificate_type.value,
                validation_time=audit_data["certificate_validation"]["validation_time"],
            )

            return requesting_sae_id, cert_info

        except Exception as e:
            audit_data["certificate_validation"]["validation_time"] = (
                time.time() - cert_start_time
            )
            audit_data["certificate_validation"]["error"] = str(e)

            logger.error(
                "Certificate validation failed",
                request_id=request_id,
                error=str(e),
                validation_time=audit_data["certificate_validation"]["validation_time"],
            )

            raise AuthenticationError(f"Certificate validation failed: {str(e)}")

    async def _perform_authorization_check(
        self,
        requesting_sae_id: str,
        endpoint_type: str,
        resource_id: str,
        request_id: str,
        audit_data: dict[str, Any],
    ) -> None:
        """
        Perform authorization check with detailed logging.

        Args:
            requesting_sae_id: SAE ID of the requesting entity
            endpoint_type: Type of endpoint being accessed
            resource_id: Resource identifier
            request_id: Request identifier for tracking
            audit_data: Audit data dictionary to update

        Raises:
            AuthorizationError: If authorization check fails
        """
        auth_start_time = time.time()

        try:
            if endpoint_type == "status":
                # Status endpoint authorization
                access_granted = await self.sae_auth.validate_status_access(
                    requesting_sae_id=requesting_sae_id,
                    slave_sae_id=resource_id,
                    master_sae_id=requesting_sae_id,
                )

            elif endpoint_type == "key":
                # Key request authorization
                access_granted = await self.sae_auth.validate_key_access(
                    requesting_sae_id=requesting_sae_id,
                    slave_sae_id=resource_id,
                    master_sae_id=requesting_sae_id,
                )

            elif endpoint_type == "key_ids":
                # Key retrieval authorization
                access_granted = await self.sae_auth.validate_key_access(
                    requesting_sae_id=requesting_sae_id,
                    slave_sae_id=requesting_sae_id,
                    master_sae_id=resource_id,
                )

            else:
                raise AuthorizationError(f"Unknown endpoint type: {endpoint_type}")

            audit_data["authorization_check"]["access_granted"] = access_granted
            audit_data["authorization_check"]["authorization_time"] = (
                time.time() - auth_start_time
            )

            if not access_granted:
                raise AuthorizationError("Access denied")

            logger.debug(
                "Authorization check successful",
                request_id=request_id,
                requesting_sae_id=requesting_sae_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                authorization_time=audit_data["authorization_check"][
                    "authorization_time"
                ],
            )

        except Exception as e:
            audit_data["authorization_check"]["authorization_time"] = (
                time.time() - auth_start_time
            )
            audit_data["authorization_check"]["error"] = str(e)

            logger.error(
                "Authorization check failed",
                request_id=request_id,
                requesting_sae_id=requesting_sae_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                error=str(e),
                authorization_time=audit_data["authorization_check"][
                    "authorization_time"
                ],
            )

            raise AuthorizationError(f"Authorization check failed: {str(e)}")

    def _extract_certificate_from_request(self, request: Request) -> bytes:
        """
        Extract certificate from request with enhanced error handling.

        Args:
            request: FastAPI request object

        Returns:
            Certificate data as bytes

        Raises:
            AuthenticationError: If certificate cannot be extracted
        """
        # Try to get certificate from TLS context
        if hasattr(request, "scope") and "ssl" in request.scope:
            ssl_context = request.scope["ssl"]
            if ssl_context and "client_cert" in ssl_context:
                return ssl_context["client_cert"]

        # Try to get certificate from header (for testing)
        cert_header = request.headers.get("X-Client-Certificate")
        if cert_header:
            return cert_header.encode()

        # Try to get certificate from query parameter (for testing)
        cert_param = request.query_params.get("cert")
        if cert_param:
            return cert_param.encode()

        raise AuthenticationError("No certificate found in request")

    def get_authentication_metrics(self) -> dict[str, Any]:
        """
        Get authentication metrics for monitoring.

        Returns:
            Dictionary containing authentication metrics
        """
        total_attempts = self.auth_attempts
        success_rate = (
            (self.auth_successes / total_attempts * 100) if total_attempts > 0 else 0
        )

        return {
            "total_attempts": total_attempts,
            "successful_authentications": self.auth_successes,
            "failed_authentications": self.auth_failures,
            "success_rate_percent": round(success_rate, 2),
            "certificate_validation_failures": self.cert_validation_failures,
            "authorization_failures": self.authorization_failures,
        }


# Global instance for use across the application
auth_middleware = AuthenticationMiddleware()


def get_auth_middleware() -> AuthenticationMiddleware:
    """
    Get the global authentication middleware instance.

    Returns:
        AuthenticationMiddleware instance
    """
    return auth_middleware
