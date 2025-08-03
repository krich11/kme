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

import datetime
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
                "🚀 Starting certificate authentication",
                request_id=request_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                client_ip=audit_data["client_ip"],
                path=request.url.path,
                method=request.method,
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

            logger.error(
                "❌ Authentication failed",
                request_id=request_id,
                endpoint_type=endpoint_type,
                resource_id=resource_id,
                error=str(e),
                auth_time=audit_data["authentication_time"],
                path=request.url.path,
                method=request.method,
                client_ip=audit_data["client_ip"],
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
            # Method 1: Try to extract from Nginx header first (production setup)
            cert_header = request.headers.get("x-ssl-client-cert")
            if cert_header:
                logger.info(
                    "✅ Found certificate in X-SSL-Client-Cert header (nginx)",
                    cert_header_preview=cert_header[:100]
                    + ("..." if len(cert_header) > 100 else ""),
                )
                # Nginx passes PEM with literal newlines replaced by spaces, so fix it
                cert_pem = (
                    cert_header.replace(" ", "\n")
                    .replace(
                        "-----BEGIN\nCERTIFICATE-----", "-----BEGIN CERTIFICATE-----"
                    )
                    .replace("-----END\nCERTIFICATE-----", "-----END CERTIFICATE-----")
                )
                cert_data = cert_pem.encode("utf-8")
            else:
                # Method 2: Try to extract from base64 encoded header
                cert_header_b64 = request.headers.get("x-ssl-client-cert-b64")
                if cert_header_b64:
                    logger.info(
                        "✅ Found base64 encoded certificate in X-SSL-Client-Cert-B64 header (nginx)",
                        cert_header_preview=cert_header_b64[:50]
                        + ("..." if len(cert_header_b64) > 50 else ""),
                    )
                    try:
                        import base64

                        cert_pem = base64.b64decode(cert_header_b64).decode("utf-8")
                        cert_data = cert_pem.encode("utf-8")
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to decode base64 certificate header: {e}"
                        )
                        raise AuthenticationError(
                            "Invalid base64 certificate format in header"
                        )
                else:
                    # Method 3: Production setup - trust Nginx validation and extract identity from headers
                    client_subject = request.headers.get(
                        "x-forwarded-ssl-client-subject"
                    )
                    client_verify = request.headers.get("x-forwarded-ssl-client-verify")

                    logger.info(
                        "🔍 Checking production setup headers",
                        client_subject=client_subject,
                        client_verify=client_verify,
                        has_subject=bool(client_subject),
                        has_verify=bool(client_verify),
                        verify_success=client_verify == "SUCCESS"
                        if client_verify
                        else False,
                    )

                    if client_subject and client_verify == "SUCCESS":
                        logger.info(
                            "✅ Found validated client identity in headers (production setup)",
                            client_subject=client_subject,
                            client_verify=client_verify,
                        )
                        # In production setup, we trust that Nginx has already validated the certificate
                        # We can extract the SAE ID from the subject DN
                        try:
                            # Extract CN from subject DN (format: CN=SAE_ID,O=KME Test,L=San Francisco,ST=CA,C=US)
                            if "CN=" in client_subject:
                                # Extract the CN part and get the SAE ID
                                cn_part = client_subject.split("CN=")[1].split(",")[0]
                                # Extract just the SAE ID part (e.g., "A1B2C3D4E5F6A7B8" from "Master SAE A1B2C3D4E5F6A7B8")
                                if " " in cn_part:
                                    sae_id = cn_part.split(" ")[-1]  # Get the last part
                                else:
                                    sae_id = cn_part
                                logger.info(
                                    f"✅ Extracted SAE ID from subject DN: {sae_id}"
                                )

                                # For production setup, we trust Nginx validation and skip certificate parsing
                                # Create a mock certificate info object
                                from app.core.security import (
                                    CertificateInfo,
                                    CertificateType,
                                )

                                cert_info = CertificateInfo(
                                    is_valid=True,
                                    certificate_type=CertificateType.SAE,
                                    subject=client_subject,
                                    issuer="Nginx Validated",
                                    serial_number="0",
                                    not_before=datetime.datetime.now(),
                                    not_after=datetime.datetime.now()
                                    + datetime.timedelta(days=365),
                                    key_usage=[],
                                    extended_key_usage=[],
                                    subject_alt_names=[],
                                    validation_errors=[],
                                )

                                audit_data["certificate_validation"][
                                    "certificate_found"
                                ] = True
                                audit_data["certificate_validation"][
                                    "certificate_size"
                                ] = 0
                                audit_data["certificate_validation"][
                                    "certificate_parsed"
                                ] = True
                                audit_data["certificate_validation"][
                                    "subject"
                                ] = client_subject
                                audit_data["certificate_validation"][
                                    "issuer"
                                ] = "Nginx Validated"
                                audit_data["certificate_validation"][
                                    "serial_number"
                                ] = "0"
                                audit_data["certificate_validation"][
                                    "certificate_valid"
                                ] = True
                                audit_data["certificate_validation"][
                                    "certificate_type"
                                ] = "SAE"
                                audit_data["certificate_validation"][
                                    "sae_id_extracted"
                                ] = sae_id
                                audit_data["certificate_validation"][
                                    "sae_id_valid"
                                ] = True
                                audit_data["certificate_validation"][
                                    "validation_time"
                                ] = (time.time() - cert_start_time)

                                logger.info(
                                    "✅ Production setup authentication successful",
                                    sae_id=sae_id,
                                )
                                return sae_id, cert_info
                            else:
                                logger.error(
                                    "❌ No CN found in client subject",
                                    client_subject=client_subject,
                                )
                                raise AuthenticationError(
                                    "Invalid client subject format"
                                )
                        except Exception as e:
                            logger.error(
                                f"❌ Failed to extract SAE ID from subject: {e}"
                            )
                            raise AuthenticationError(
                                "Failed to extract client identity from headers"
                            )
                    else:
                        # Method 4: Fallback to old logic for direct SSL connections
                        # Enhanced debugging for certificate extraction
                        logger.info(
                            "🔍 Starting certificate extraction",
                            path=request.url.path,
                            method=request.method,
                            has_scope=hasattr(request, "scope"),
                        )

                        if hasattr(request, "scope"):
                            logger.info(
                                "📋 Request scope details",
                                scope_keys=list(request.scope.keys()),
                                ssl_present="ssl" in request.scope,
                            )

                            if "ssl" in request.scope:
                                ssl_context = request.scope["ssl"]
                                logger.info(
                                    "🔐 SSL context details",
                                    ssl_context_keys=list(ssl_context.keys())
                                    if ssl_context
                                    else [],
                                    has_client_cert="client_cert" in ssl_context
                                    if ssl_context
                                    else False,
                                    client_cert_present=bool(
                                        ssl_context.get("client_cert")
                                        if ssl_context
                                        else None
                                    ),
                                )

                                if ssl_context and "client_cert" in ssl_context:
                                    client_cert = ssl_context["client_cert"]
                                    if client_cert:
                                        logger.info(
                                            "✅ Found certificate in SSL context",
                                            cert_size=len(client_cert),
                                            cert_preview=client_cert[:100].decode(
                                                "utf-8", errors="ignore"
                                            )
                                            + "..."
                                            if len(client_cert) > 100
                                            else client_cert.decode(
                                                "utf-8", errors="ignore"
                                            ),
                                        )
                                        cert_data = client_cert
                                    else:
                                        logger.warning(
                                            "❌ SSL context has 'client_cert' key but value is None/empty"
                                        )
                                        raise AuthenticationError(
                                            "No certificate found in request"
                                        )
                                else:
                                    logger.warning("❌ No 'client_cert' in SSL context")
                                    raise AuthenticationError(
                                        "No certificate found in request"
                                    )
                            else:
                                logger.warning("❌ No SSL context in request scope")
                                raise AuthenticationError(
                                    "No certificate found in request"
                                )
                        else:
                            logger.warning("❌ Request has no scope attribute")
                            raise AuthenticationError("No certificate found in request")

            # Extract certificate data
            logger.info(
                "✅ Certificate extracted successfully", cert_size=len(cert_data)
            )
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
            logger.info("🔍 Extracting SAE ID from certificate...")
            requesting_sae_id = (
                self.certificate_manager.extract_sae_id_from_certificate(cert_data)
            )
            logger.info(
                "📋 SAE ID extraction result",
                sae_id=requesting_sae_id,
                sae_id_type=type(requesting_sae_id),
            )
            audit_data["certificate_validation"]["sae_id_extracted"] = requesting_sae_id
            audit_data["certificate_validation"][
                "sae_id_valid"
            ] = self.certificate_auth._validate_sae_id_format(requesting_sae_id)

            if not requesting_sae_id:
                logger.error("❌ Failed to extract SAE ID from certificate")
                raise AuthenticationError("Failed to extract SAE ID from certificate")

            if not self.certificate_auth._validate_sae_id_format(requesting_sae_id):
                logger.error("❌ Invalid SAE ID format", sae_id=requesting_sae_id)
                raise AuthenticationError("Invalid SAE ID format in certificate")

            logger.info(
                "✅ SAE ID extracted and validated successfully",
                sae_id=requesting_sae_id,
            )

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
                "❌ Certificate validation failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
                validation_time=audit_data["certificate_validation"]["validation_time"],
                path=request.url.path,
                method=request.method,
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
        Extract certificate from request using multiple methods.

        Priority order:
        1. Nginx headers (production setup)
        2. SSL context (direct SSL setup)
        3. Fallback methods
        """
        logger.info("🔍 Starting certificate extraction method")

        # Method 1: Try to extract from Nginx header first (production setup)
        cert_header = request.headers.get("x-ssl-client-cert")
        if cert_header:
            logger.info(
                "✅ Found certificate in X-SSL-Client-Cert header (nginx)",
                cert_header_preview=cert_header[:100]
                + ("..." if len(cert_header) > 100 else ""),
            )
            # Nginx passes PEM with literal newlines replaced by spaces, so fix it
            cert_pem = (
                cert_header.replace(" ", "\n")
                .replace("-----BEGIN\nCERTIFICATE-----", "-----BEGIN CERTIFICATE-----")
                .replace("-----END\nCERTIFICATE-----", "-----END CERTIFICATE-----")
            )
            return cert_pem.encode("utf-8")

        # Method 2: Try to extract from base64 encoded header
        cert_header_b64 = request.headers.get("x-ssl-client-cert-b64")
        if cert_header_b64:
            logger.info(
                "✅ Found base64 encoded certificate in X-SSL-Client-Cert-B64 header (nginx)",
                cert_header_preview=cert_header_b64[:50]
                + ("..." if len(cert_header_b64) > 50 else ""),
            )
            try:
                import base64

                cert_pem = base64.b64decode(cert_header_b64).decode("utf-8")
                return cert_pem.encode("utf-8")
            except Exception as e:
                logger.error(f"❌ Failed to decode base64 certificate header: {e}")
                raise AuthenticationError("Invalid base64 certificate format in header")

        # Method 3: Production setup - trust Nginx validation and extract identity from headers
        client_subject = request.headers.get("x-forwarded-ssl-client-subject")
        client_verify = request.headers.get("x-forwarded-ssl-client-verify")

        logger.info(
            "🔍 Checking production setup headers",
            client_subject=client_subject,
            client_verify=client_verify,
            has_subject=bool(client_subject),
            has_verify=bool(client_verify),
            verify_success=client_verify == "SUCCESS" if client_verify else False,
        )

        if client_subject and client_verify == "SUCCESS":
            logger.info(
                "✅ Found validated client identity in headers (production setup)",
                client_subject=client_subject,
                client_verify=client_verify,
            )
            # In production setup, we trust that Nginx has already validated the certificate
            # We can extract the SAE ID from the subject DN
            try:
                # Extract CN from subject DN (format: CN=SAE_ID,O=KME Test,L=San Francisco,ST=CA,C=US)
                if "CN=" in client_subject:
                    # Extract the CN part and get the SAE ID
                    cn_part = client_subject.split("CN=")[1].split(",")[0]
                    # Extract just the SAE ID part (e.g., "A1B2C3D4E5F6A7B8" from "Master SAE A1B2C3D4E5F6A7B8")
                    if " " in cn_part:
                        sae_id = cn_part.split(" ")[-1]  # Get the last part
                    else:
                        sae_id = cn_part
                    logger.info(f"✅ Extracted SAE ID from subject DN: {sae_id}")
                    # For now, we'll create a mock certificate validation result
                    # In a real implementation, you might want to store the full subject DN
                    # and validate it against your certificate manager
                    return self._create_mock_certificate_data(sae_id)
                else:
                    logger.error(
                        "❌ No CN found in client subject", client_subject=client_subject
                    )
                    raise AuthenticationError("Invalid client subject format")
            except Exception as e:
                logger.error(f"❌ Failed to extract SAE ID from subject: {e}")
                raise AuthenticationError(
                    "Failed to extract client identity from headers"
                )

        # Method 4: Fallback to old logic for direct SSL connections
        # Enhanced debugging for certificate extraction
        logger.info(
            "🔍 Starting certificate extraction",
            path=request.url.path,
            method=request.method,
            has_scope=hasattr(request, "scope"),
        )

        if hasattr(request, "scope"):
            logger.info(
                "📋 Request scope details",
                scope_keys=list(request.scope.keys()),
                ssl_present="ssl" in request.scope,
            )

            if "ssl" in request.scope:
                ssl_context = request.scope["ssl"]
                logger.info(
                    "🔐 SSL context details",
                    ssl_context_keys=list(ssl_context.keys()) if ssl_context else [],
                    has_client_cert="client_cert" in ssl_context
                    if ssl_context
                    else False,
                    client_cert_present=bool(
                        ssl_context.get("client_cert") if ssl_context else None
                    ),
                )

                if ssl_context and "client_cert" in ssl_context:
                    client_cert = ssl_context["client_cert"]
                    if client_cert:
                        logger.info(
                            "✅ Found certificate in SSL context",
                            cert_size=len(client_cert),
                            cert_preview=client_cert[:100].decode(
                                "utf-8", errors="ignore"
                            )
                            + "..."
                            if len(client_cert) > 100
                            else client_cert.decode("utf-8", errors="ignore"),
                        )
                        return client_cert
                    else:
                        logger.warning(
                            "❌ SSL context has 'client_cert' key but value is None/empty"
                        )
                else:
                    logger.warning("❌ No 'client_cert' in SSL context")
            else:
                logger.warning("❌ No SSL context in request scope")
        else:
            logger.warning("❌ Request has no scope attribute")

        # Log headers for additional debugging
        logger.info(
            "📨 Request headers",
            headers=list(request.headers.keys()),
            content_type=request.headers.get("content-type"),
            user_agent=request.headers.get("user-agent"),
        )

        # Log client information
        logger.info(
            "🌐 Client information",
            client_host=request.client.host if request.client else None,
            client_port=request.client.port if request.client else None,
        )

        raise AuthenticationError("No certificate found in request")

    def _create_mock_certificate_data(self, sae_id: str) -> bytes:
        """
        Create mock certificate data for production setup where we trust Nginx validation.
        This is a temporary solution until we implement proper certificate passing.
        """
        # Create a minimal PEM certificate structure for the certificate manager
        # In a real implementation, you might want to store the actual certificate
        # or implement a different validation strategy
        mock_cert = f"""-----BEGIN CERTIFICATE-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA
{sae_id}
-----END CERTIFICATE-----"""
        return mock_cert.encode("utf-8")

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
