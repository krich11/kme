#!/usr/bin/env python3
"""
KME Error Handling - Standardized Error Responses

Version: 1.0.0
Author: KME Development Team
Description: Standardized error handling for ETSI QKD 014 V1.1.1 API endpoints
License: [To be determined]

ToDo List:
- [x] Create standardized error response functions
- [x] Add ETSI-compliant error formats
- [x] Add validation error handling
- [x] Add authentication error handling
- [x] Add authorization error handling
- [x] Add service error handling
- [x] Add logging integration
- [ ] Add error code mapping
- [ ] Add error localization
- [ ] Add error metrics collection

Progress: 70% (7/10 tasks completed)
"""

import datetime
import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import HTTPException, status

from app.models.etsi_models import Error, ErrorDetail

logger = structlog.get_logger()


class KMEErrorHandler:
    """
    Standardized error handler for KME API endpoints.
    
    Ensures consistent error response format across all endpoints
    according to ETSI GS QKD 014 V1.1.1 specification.
    """

    @staticmethod
    def create_error_response(
        message: str,
        details: Optional[List[Dict[str, Any]]] = None,
        error_code: Optional[str] = None,
        severity: str = "error",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            message: Human-readable error message
            details: List of error details with parameter and error fields
            error_code: Optional error code for programmatic handling
            severity: Error severity (error, warning, info)
            request_id: Optional request ID for tracking
            
        Returns:
            Standardized error response dictionary
        """
        error_details = []
        if details:
            for detail in details:
                error_details.append(ErrorDetail(detail=detail))

        error_response = Error(
            message=message,
            details=error_details,
            error_code=error_code,
            timestamp=datetime.datetime.utcnow(),
            request_id=request_id,
            severity=severity,
        )

        return error_response.dict()

    @staticmethod
    def raise_validation_error(
        parameter: str,
        error_message: str,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Raise a standardized validation error (400 Bad Request).
        
        Args:
            parameter: Parameter name that caused the validation error
            error_message: Specific error message
            request_id: Optional request ID for tracking
        """
        error_response = KMEErrorHandler.create_error_response(
            message="Invalid request parameters",
            details=[{"parameter": parameter, "error": error_message}],
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

        logger.warning(
            "Validation error",
            parameter=parameter,
            error=error_message,
            request_id=request_id,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response,
        )

    @staticmethod
    def raise_authentication_error(
        error_message: str = "SAE authentication failed",
        request_id: Optional[str] = None,
    ) -> None:
        """
        Raise a standardized authentication error (401 Unauthorized).
        
        Args:
            error_message: Specific authentication error message
            request_id: Optional request ID for tracking
        """
        error_response = KMEErrorHandler.create_error_response(
            message=error_message,
            details=[{"parameter": "authentication", "error": "Invalid or expired certificate"}],
            error_code="AUTHENTICATION_ERROR",
            request_id=request_id,
        )

        logger.warning(
            "Authentication error",
            error=error_message,
            request_id=request_id,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response,
        )

    @staticmethod
    def raise_authorization_error(
        resource: str,
        error_message: str = "SAE not authorized to access this resource",
        request_id: Optional[str] = None,
    ) -> None:
        """
        Raise a standardized authorization error (401 Unauthorized).
        
        Args:
            resource: Resource that the SAE is not authorized to access
            error_message: Specific authorization error message
            request_id: Optional request ID for tracking
        """
        error_response = KMEErrorHandler.create_error_response(
            message=error_message,
            details=[{"parameter": "authorization", "error": f"SAE not authorized to access {resource}"}],
            error_code="AUTHORIZATION_ERROR",
            request_id=request_id,
        )

        logger.warning(
            "Authorization error",
            resource=resource,
            error=error_message,
            request_id=request_id,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response,
        )

    @staticmethod
    def raise_service_unavailable_error(
        error_message: str = "KME service temporarily unavailable",
        details: Optional[List[Dict[str, Any]]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Raise a standardized service unavailable error (503 Service Unavailable).
        
        Args:
            error_message: Specific service error message
            details: Additional error details
            request_id: Optional request ID for tracking
        """
        if not details:
            details = [{"parameter": "service", "error": "Internal server error occurred"}]

        error_response = KMEErrorHandler.create_error_response(
            message=error_message,
            details=details,
            error_code="SERVICE_UNAVAILABLE",
            request_id=request_id,
        )

        logger.error(
            "Service unavailable error",
            error=error_message,
            details=details,
            request_id=request_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_response,
        )

    @staticmethod
    def raise_key_exhaustion_error(
        request_id: Optional[str] = None,
    ) -> None:
        """
        Raise a standardized key exhaustion error (503 Service Unavailable).
        
        Args:
            request_id: Optional request ID for tracking
        """
        error_response = KMEErrorHandler.create_error_response(
            message="Key pool exhausted",
            details=[{"parameter": "key_pool", "error": "Insufficient keys available for request"}],
            error_code="KEY_EXHAUSTION",
            request_id=request_id,
        )

        logger.warning(
            "Key exhaustion error",
            request_id=request_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_response,
        )

    @staticmethod
    def raise_not_found_error(
        resource: str,
        resource_id: str,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Raise a standardized not found error (404 Not Found).
        
        Args:
            resource: Type of resource not found
            resource_id: ID of the resource not found
            request_id: Optional request ID for tracking
        """
        error_response = KMEErrorHandler.create_error_response(
            message=f"{resource} not found",
            details=[{"parameter": resource.lower(), "error": f"{resource} with ID '{resource_id}' not found"}],
            error_code="NOT_FOUND",
            request_id=request_id,
        )

        logger.warning(
            "Resource not found",
            resource=resource,
            resource_id=resource_id,
            request_id=request_id,
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response,
        )

    @staticmethod
    def handle_unexpected_error(
        error: Exception,
        context: str,
        request_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Handle unexpected errors and raise standardized service unavailable error.
        
        Args:
            error: The unexpected exception
            context: Context where the error occurred
            request_id: Optional request ID for tracking
            **kwargs: Additional context information
        """
        logger.error(
            f"Unexpected error in {context}",
            error=str(error),
            error_type=type(error).__name__,
            request_id=request_id,
            **kwargs,
        )

        KMEErrorHandler.raise_service_unavailable_error(
            error_message="KME service temporarily unavailable",
            details=[{"parameter": "service", "error": "Internal server error occurred"}],
            request_id=request_id,
        )


# Global error handler instance
error_handler = KMEErrorHandler()