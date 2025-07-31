#!/usr/bin/env python3
"""
KME API Routes - ETSI QKD 014 V1.1.1 Compliant

Version: 1.0.0
Author: KME Development Team
Description: REST API endpoints for ETSI GS QKD 014 V1.1.1 specification
License: [To be determined]

ToDo List:
- [x] Create API routes structure
- [x] Implement Get Status endpoint (ETSI compliant)
- [x] Implement Get Key endpoint (ETSI compliant)
- [x] Implement Get Key with Key IDs endpoint (ETSI compliant)
- [ ] Add authentication middleware
- [x] Add comprehensive error handling
- [ ] Add request/response validation
- [ ] Add logging and monitoring
- [ ] Add rate limiting
- [ ] Add API documentation

Progress: 50% (5/10 tasks completed)
"""

import datetime
import os
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from app.core.authentication_middleware import get_auth_middleware
from app.core.error_handling import error_handler
from app.models.etsi_models import Error, KeyContainer, KeyIDs, KeyRequest, Status
from app.services.key_service import key_service
from app.services.status_service import status_service

logger = structlog.get_logger()

# Create API router
api_router = APIRouter(prefix="/api/v1", tags=["QKD API"])


@api_router.get(
    "/keys/{slave_sae_id}/status",
    response_model=Status,
    summary="Get Status",
    description="Get KME status and capabilities for a specific slave SAE",
    responses={
        200: {
            "description": "Successful status response",
            "model": Status,
        },
        400: {
            "description": "Bad Request - Invalid slave_SAE_ID format",
            "model": Error,
        },
        401: {
            "description": "Unauthorized - SAE authentication failed",
            "model": Error,
        },
        503: {
            "description": "Service Unavailable - KME not operational",
            "model": Error,
        },
    },
)
async def get_status(
    slave_sae_id: str,
    request: Request,
) -> Status:
    """
    Get Status endpoint - ETSI GS QKD 014 V1.1.1 Section 5.1

    Returns KME status and capabilities for the specified slave SAE.

    Args:
        slave_sae_id: SAE ID of the specified slave SAE (16 characters)
        request: FastAPI request object for authentication and logging

    Returns:
        Status: ETSI-compliant status response

    Raises:
        HTTPException: 400, 401, or 503 with appropriate error details
    """
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())

    logger.info(
        "Get Status request received",
        slave_sae_id=slave_sae_id,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request_id,
    )

    try:
        # Use enhanced authentication middleware
        auth_middleware = get_auth_middleware()

        # Authenticate and authorize request with enhanced logging
        (
            requesting_sae_id,
            cert_info,
            audit_data,
        ) = await auth_middleware.authenticate_request(
            request=request,
            endpoint_type="status",
            resource_id=slave_sae_id,
        )

        master_sae_id = (
            requesting_sae_id  # For status requests, the requesting SAE is the master
        )

        # Log authentication audit data
        logger.info(
            "Status endpoint authentication completed",
            request_id=audit_data["request_id"],
            requesting_sae_id=requesting_sae_id,
            slave_sae_id=slave_sae_id,
            auth_time=audit_data["authentication_time"],
            success=audit_data["success"],
        )

        # Generate ETSI-compliant status response using status service
        status_response = await status_service.generate_status_response(
            slave_sae_id=slave_sae_id,
            master_sae_id=master_sae_id,
        )

        logger.info(
            "Get Status response generated successfully",
            slave_sae_id=slave_sae_id,
            key_size=status_response.key_size,
            stored_key_count=status_response.stored_key_count,
            max_key_count=status_response.max_key_count,
            request_id=request_id,
        )

        return status_response

    except ValueError as e:
        # Handle validation errors
        error_handler.raise_validation_error(
            parameter="slave_sae_id",
            error_message=str(e),
            request_id=request_id,
        )
        raise  # This line is unreachable but satisfies MyPy
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle unexpected errors
        error_handler.handle_unexpected_error(
            error=e,
            context="Get Status endpoint",
            request_id=request_id,
            slave_sae_id=slave_sae_id,
        )
        raise  # This line is unreachable but satisfies MyPy


@api_router.post(
    "/keys/{slave_sae_id}/enc_keys",
    response_model=KeyContainer,
    summary="Get Key",
    description="Request keys for encryption (Master SAE operation)",
    responses={
        200: {
            "description": "Successful key response",
            "model": KeyContainer,
        },
        400: {
            "description": "Bad Request - Invalid request format or parameters",
            "model": Error,
        },
        401: {
            "description": "Unauthorized - SAE authentication failed",
            "model": Error,
        },
        503: {
            "description": "Service Unavailable - Key exhaustion or KME not operational",
            "model": Error,
        },
    },
)
async def get_key(
    slave_sae_id: str,
    key_request: KeyRequest,
    request: Request,
) -> KeyContainer:
    """
    Get Key endpoint - ETSI GS QKD 014 V1.1.1 Section 5.2

    Request keys for encryption (Master SAE operation).

    Args:
        slave_sae_id: SAE ID of the specified slave SAE (16 characters)
        key_request: ETSI-compliant key request data
        request: FastAPI request object for authentication and logging

    Returns:
        KeyContainer: ETSI-compliant key container response

    Raises:
        HTTPException: 400, 401, or 503 with appropriate error details
    """
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())

    logger.info(
        "Get Key request received",
        slave_sae_id=slave_sae_id,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        number=key_request.number,
        size=key_request.size,
        request_id=request_id,
    )

    try:
        # Use enhanced authentication middleware
        auth_middleware = get_auth_middleware()

        # Authenticate and authorize request with enhanced logging
        (
            requesting_sae_id,
            cert_info,
            audit_data,
        ) = await auth_middleware.authenticate_request(
            request=request,
            endpoint_type="key",
            resource_id=slave_sae_id,
        )

        master_sae_id = (
            requesting_sae_id  # For key requests, the requesting SAE is the master
        )

        # Log authentication audit data
        logger.info(
            "Get Key endpoint authentication completed",
            request_id=audit_data["request_id"],
            requesting_sae_id=requesting_sae_id,
            slave_sae_id=slave_sae_id,
            auth_time=audit_data["authentication_time"],
            success=audit_data["success"],
        )

        # Process key request using key service
        key_container = await key_service.process_key_request(  # type: ignore[attr-defined]
            slave_sae_id=slave_sae_id,
            key_request=key_request,
            master_sae_id=master_sae_id,
        )

        logger.info(
            "Get Key response generated successfully",
            slave_sae_id=slave_sae_id,
            number_of_keys=len(key_container.keys),
            key_size=key_container.keys[0].key_size if key_container.keys else None,
            request_id=request_id,
        )

        return key_container

    except ValueError as e:
        # Handle validation errors
        error_handler.raise_validation_error(
            parameter="request",
            error_message=str(e),
            request_id=request_id,
        )
        raise  # This line is unreachable but satisfies MyPy
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle unexpected errors
        error_handler.handle_unexpected_error(
            error=e,
            context="Get Key endpoint",
            request_id=request_id,
            slave_sae_id=slave_sae_id,
        )
        raise  # This line is unreachable but satisfies MyPy


@api_router.post(
    "/keys/{master_sae_id}/dec_keys",
    response_model=KeyContainer,
    summary="Get Key with Key IDs",
    description="Retrieve keys using key IDs (Slave SAE operation)",
    responses={
        200: {
            "description": "Successful key response",
            "model": KeyContainer,
        },
        400: {
            "description": "Bad Request - Invalid key IDs format",
            "model": Error,
        },
        401: {
            "description": "Unauthorized - SAE authentication failed",
            "model": Error,
        },
        503: {
            "description": "Service Unavailable - KME not operational",
            "model": Error,
        },
    },
)
async def get_key_with_ids(
    master_sae_id: str,
    key_ids_request: KeyIDs,
    request: Request,
) -> KeyContainer:
    """
    Get Key with Key IDs endpoint - ETSI GS QKD 014 V1.1.1 Section 5.3

    Retrieve keys using key IDs (Slave SAE operation).

    Args:
        master_sae_id: SAE ID of the master SAE (16 characters)
        key_ids_request: KeyIDs request containing the key_IDs to retrieve
        request: FastAPI request object for authentication and logging

    Returns:
        KeyContainer: ETSI-compliant key container response

    Raises:
        HTTPException: 400, 401, or 503 with appropriate error details
    """
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())

    logger.info(
        "Get Key with Key IDs request received",
        master_sae_id=master_sae_id,
        key_count=len(key_ids_request.key_IDs),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request_id,
    )

    try:
        # Use enhanced authentication middleware
        auth_middleware = get_auth_middleware()

        # Authenticate and authorize request with enhanced logging
        (
            requesting_sae_id,
            cert_info,
            audit_data,
        ) = await auth_middleware.authenticate_request(
            request=request,
            endpoint_type="key_ids",
            resource_id=master_sae_id,
        )

        # Log authentication audit data
        logger.info(
            "Get Key with IDs endpoint authentication completed",
            request_id=audit_data["request_id"],
            requesting_sae_id=requesting_sae_id,
            master_sae_id=master_sae_id,
            auth_time=audit_data["authentication_time"],
            success=audit_data["success"],
        )

        # Extract key_IDs from the request
        key_ids = [key_id.key_ID for key_id in key_ids_request.key_IDs]

        # Process the request using key service
        key_container = await key_service.get_keys_by_ids(  # type: ignore[attr-defined]
            master_sae_id=master_sae_id,
            key_ids=key_ids,
            requesting_sae_id=requesting_sae_id,
        )

        logger.info(
            "Get Key with Key IDs response generated successfully",
            master_sae_id=master_sae_id,
            key_count=len(key_container.keys),
            request_id=request_id,
        )

        return key_container

    except ValueError as e:
        # Handle validation errors
        error_handler.raise_validation_error(
            parameter="key_ids",
            error_message=str(e),
            request_id=request_id,
        )
        raise  # This line is unreachable but satisfies MyPy
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle unexpected errors
        error_handler.handle_unexpected_error(
            error=e,
            context="Get Key with Key IDs endpoint",
            request_id=request_id,
            master_sae_id=master_sae_id,
        )
        raise  # This line is unreachable but satisfies MyPy
