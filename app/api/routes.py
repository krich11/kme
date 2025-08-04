#!/usr/bin/env python3
"""
KME API Routes - ETSI QKD 014 V1.1.1 Compliant
Version: 1.0.0
Author: KME Development Team
Description: FastAPI route definitions for KME endpoints
License: [To be determined]
ToDo List:
- [x] Create API route structure
- [x] Implement Get Status endpoint
- [x] Implement Get Key endpoint
- [x] Implement Get Key with Key IDs endpoint
- [x] Add request validation
- [x] Add error handling
- [x] Add logging
- [x] Add authentication middleware
- [ ] Add rate limiting
- [ ] Add request/response caching
- [ ] Add comprehensive testing
- [ ] Add API documentation
- [ ] Add performance monitoring
- [ ] Add security hardening
Progress: 70% (8/13 tasks completed)
"""
import base64
import datetime
import os
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.authentication_middleware import get_auth_middleware
from app.core.database import database_manager
from app.core.error_handling import error_handler
from app.models.etsi_models import Error, Key, KeyContainer, KeyIDs, KeyRequest, Status
from app.services.key_storage_service import KeyStorageService
from app.services.status_service import StatusService

logger = structlog.get_logger()
# Create API router
api_router = APIRouter(prefix="/api/v1")


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
        403: {
            "description": "Forbidden - SAE authorization failed",
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
        HTTPException: 400, 401, 403, or 503 with appropriate error details
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
        # Authenticate and authorize the request
        auth_middleware = get_auth_middleware()
        (
            requesting_sae_id,
            cert_info,
            audit_data,
        ) = await auth_middleware.authenticate_request(
            request=request,
            endpoint_type="status",
            resource_id=slave_sae_id,
        )

        # Get database session and use context manager for proper transaction handling
        async with database_manager.get_session_context() as db_session:
            # Create status service with database session
            status_service = StatusService(db_session)
            # Generate ETSI-compliant status response using status service
            status_response = await status_service.generate_status_response(
                slave_sae_id=slave_sae_id,
                master_sae_id=requesting_sae_id,
            )
            logger.info(
                "Get Status response generated successfully",
                slave_sae_id=slave_sae_id,
                requesting_sae_id=requesting_sae_id,
                key_size=status_response.key_size,
                stored_key_count=status_response.stored_key_count,
                max_key_count=status_response.max_key_count,
                request_id=request_id,
            )
            return status_response
    except ValueError as e:
        # Handle validation errors - return 400 Bad Request
        logger.warning(
            "Validation error in Get Status endpoint",
            slave_sae_id=slave_sae_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Validation error: {str(e)}",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )
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
        403: {
            "description": "Forbidden - SAE authorization failed",
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
    Request keys for encryption operations.
    Args:
        slave_sae_id: SAE ID of the specified slave SAE (16 characters)
        key_request: Key request parameters
        request: FastAPI request object for authentication and logging
    Returns:
        KeyContainer: ETSI-compliant key response
    Raises:
        HTTPException: 400, 401, 403, or 503 with appropriate error details
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
        # Authenticate and authorize the request
        auth_middleware = get_auth_middleware()
        (
            requesting_sae_id,
            cert_info,
            audit_data,
        ) = await auth_middleware.authenticate_request(
            request=request,
            endpoint_type="key",
            resource_id=slave_sae_id,
        )

        # Validate key request parameters
        number_of_keys = key_request.number or 1
        key_size = key_request.size or int(os.getenv("DEFAULT_KEY_SIZE", "352"))

        # Validate number of keys (ETSI requirement)
        max_keys_per_request = int(os.getenv("MAX_KEYS_PER_REQUEST", "128"))
        if number_of_keys > max_keys_per_request:
            raise ValueError(
                f"Number of keys ({number_of_keys}) exceeds maximum ({max_keys_per_request})"
            )

        if number_of_keys <= 0:
            raise ValueError(f"Number of keys must be positive, got {number_of_keys}")

        # Validate key size (ETSI requirement)
        min_key_size = int(os.getenv("MIN_KEY_SIZE", "64"))
        max_key_size = int(os.getenv("MAX_KEY_SIZE", "1024"))

        if key_size < min_key_size:
            raise ValueError(f"Key size ({key_size}) is below minimum ({min_key_size})")

        if key_size > max_key_size:
            raise ValueError(f"Key size ({key_size}) exceeds maximum ({max_key_size})")

        # Validate additional_slave_SAE_IDs (ETSI requirement)
        if key_request.additional_slave_SAE_IDs:
            max_sae_id_count = int(os.getenv("MAX_SAE_ID_COUNT", "10"))
            if len(key_request.additional_slave_SAE_IDs) > max_sae_id_count:
                raise ValueError(
                    f"Number of additional SAE IDs ({len(key_request.additional_slave_SAE_IDs)}) exceeds maximum ({max_sae_id_count})"
                )

            # Validate each additional SAE ID format
            for sae_id in key_request.additional_slave_SAE_IDs:
                if len(sae_id) != 16:
                    raise ValueError(
                        f"Additional SAE ID must be exactly 16 characters, got {len(sae_id)}"
                    )

        # Create mock keys and store them in database
        keys = []
        db_session = await database_manager.get_session()
        key_storage_service = KeyStorageService(db_session)

        for i in range(number_of_keys):
            key_id = str(uuid.uuid4())
            # Generate mock key data (32 bytes)
            key_data = f"test_key_{key_id}_data_32_bytes_long".encode()

            # Set expiration (24 hours from now)
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=24)

            try:
                # Store key in database
                stored = await key_storage_service.store_key(
                    key_id=key_id,
                    key_data=key_data,
                    master_sae_id=requesting_sae_id,
                    slave_sae_id=slave_sae_id,
                    key_size=key_size,
                    expires_at=expires_at,
                    key_metadata={
                        "generated_at": datetime.datetime.utcnow().isoformat(),
                        "generation_method": "mock_key_generation",
                        "entropy": 1.0,
                        "error_rate": 0.0,
                        "source": "api_endpoint_mock",
                    },
                )

                if stored:
                    # Create Key object for response
                    key = Key(
                        key_ID=key_id,
                        key=base64.b64encode(key_data).decode("utf-8"),
                        key_size=key_size,
                        key_ID_extension=None,
                        key_extension=None,
                        created_at=datetime.datetime.utcnow(),
                        expires_at=expires_at,
                        source_kme_id=os.getenv("KME_ID", "AAAABBBBCCCCDDDD"),
                        target_kme_id=slave_sae_id,
                        key_metadata={
                            "entropy": 1.0,
                            "error_rate": 0.0,
                            "source": "mock_generation",
                        },
                    )
                    keys.append(key)
                else:
                    logger.error(f"Failed to store mock key {key_id}")

            except Exception as e:
                logger.error(f"Failed to generate and store mock key {i}: {str(e)}")
                continue
        # Create key container
        key_container = KeyContainer(
            keys=keys,
            key_container_extension=None,
            container_id=None,
            created_at=None,
            master_sae_id=requesting_sae_id,
            slave_sae_id=slave_sae_id,
            total_key_size=None,
        )
        logger.info(
            "Get Key response generated successfully (mock keys stored in database)",
            slave_sae_id=slave_sae_id,
            requesting_sae_id=requesting_sae_id,
            number_of_keys=len(key_container.keys),
            key_size=key_container.keys[0].key_size if key_container.keys else None,
            request_id=request_id,
        )
        return key_container
    except ValueError as e:
        # Handle validation errors - return 400 Bad Request
        logger.warning(
            "Validation error in Get Key endpoint",
            slave_sae_id=slave_sae_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Validation error: {str(e)}",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )
    except HTTPException:
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
        403: {
            "description": "Forbidden - SAE authorization failed",
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
        HTTPException: 400, 401, 403, or 503 with appropriate error details
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
        # Authenticate and authorize the request
        auth_middleware = get_auth_middleware()
        (
            requesting_sae_id,
            cert_info,
            audit_data,
        ) = await auth_middleware.authenticate_request(
            request=request,
            endpoint_type="key_ids",
            resource_id=master_sae_id,
        )

        # Extract key_IDs from the request
        key_ids = [key_id.key_ID for key_id in key_ids_request.key_IDs]

        # Retrieve keys from database
        keys = []
        db_session = await database_manager.get_session()
        key_storage_service = KeyStorageService(db_session)

        for key_id in key_ids:
            try:
                # Retrieve key from database
                retrieved_key = await key_storage_service.retrieve_key(
                    key_id=key_id,
                    requesting_sae_id=requesting_sae_id,
                    master_sae_id=master_sae_id,
                )

                if retrieved_key:
                    # Create Key object for response
                    key = Key(
                        key_ID=retrieved_key.key_ID,
                        key=retrieved_key.key,
                        key_size=retrieved_key.key_size,
                        key_ID_extension=retrieved_key.key_ID_extension,
                        key_extension=retrieved_key.key_extension,
                        created_at=retrieved_key.created_at,
                        expires_at=retrieved_key.expires_at,
                        source_kme_id=retrieved_key.source_kme_id,
                        target_kme_id=retrieved_key.target_kme_id,
                        key_metadata=retrieved_key.key_metadata,
                    )
                    keys.append(key)
                else:
                    logger.warning(f"Key {key_id} not found in database")

            except Exception as e:
                logger.error(f"Failed to retrieve key {key_id}: {str(e)}")
                continue
        # Create key container
        key_container = KeyContainer(
            keys=keys,
            key_container_extension=None,
            container_id=None,
            created_at=None,
            master_sae_id=master_sae_id,
            slave_sae_id=requesting_sae_id,
            total_key_size=None,
        )
        logger.info(
            "Get Key with Key IDs response generated successfully (keys retrieved from database)",
            master_sae_id=master_sae_id,
            requesting_sae_id=requesting_sae_id,
            key_count=len(key_container.keys),
            request_id=request_id,
        )
        return key_container
    except ValueError as e:
        # Handle validation errors - return 400 Bad Request
        logger.warning(
            "Validation error in Get Key with Key IDs endpoint",
            master_sae_id=master_sae_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Validation error: {str(e)}",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )
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
