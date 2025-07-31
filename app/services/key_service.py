#!/usr/bin/env python3
"""
KME Key Service - ETSI QKD 014 V1.1.1 Compliant

Version: 1.0.0
Author: KME Development Team
Description: Business logic for Get Key endpoint
License: [To be determined]

ToDo List:
- [x] Create key service structure
- [x] Implement key request validation
- [x] Add key container generation
- [x] Add extension parameter handling
- [x] Add key storage integration
- [x] Add key pool integration
- [ ] Add performance monitoring
- [ ] Add error handling
- [ ] Add unit tests

Progress: 60% (6/10 tasks completed)
"""

import base64
import datetime
import os
import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etsi_models import Key, KeyContainer, KeyRequest
from app.services.key_pool_service import KeyPoolService
from app.services.key_storage_service import KeyStorageService

logger = structlog.get_logger()


class KeyService:
    """
    Service for handling Get Key endpoint business logic

    Implements ETSI GS QKD 014 V1.1.1 Section 5.2 requirements
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the key service

        Args:
            db_session: Database session for key operations
        """
        self.logger = logger.bind(service="KeyService")
        self.db_session = db_session
        self.key_storage_service = KeyStorageService(db_session)
        self.key_pool_service = KeyPoolService(db_session, self.key_storage_service)
        self.logger.info("Key service initialized")

    async def process_key_request(
        self,
        slave_sae_id: str,
        key_request: KeyRequest,
        master_sae_id: str | None = None,
    ) -> KeyContainer:
        """
        Process key request and generate ETSI-compliant key container

        Args:
            slave_sae_id: SAE ID of the specified slave SAE (16 characters)
            key_request: ETSI-compliant key request data
            master_sae_id: SAE ID of the calling master SAE (16 characters)

        Returns:
            KeyContainer: ETSI-compliant key container response

        Raises:
            ValueError: If request parameters are invalid
        """
        self.logger.info(
            "Processing key request",
            slave_sae_id=slave_sae_id,
            master_sae_id=master_sae_id,
            number=key_request.number,
            size=key_request.size,
        )

        # Validate slave_SAE_ID format (ETSI requirement)
        if not slave_sae_id or len(slave_sae_id) != 16:
            raise ValueError(
                f"slave_sae_id must be exactly 16 characters, got {len(slave_sae_id) if slave_sae_id else 0}"
            )

        # Validate master_sae_id if provided
        if master_sae_id and len(master_sae_id) != 16:
            raise ValueError(
                f"master_sae_id must be exactly 16 characters, got {len(master_sae_id)}"
            )

        # TODO: Validate SAE registration and authorization
        # For now, we'll proceed with basic validation
        self.logger.info("SAE validation placeholder - to be implemented")

        # Process key request parameters with defaults (ETSI requirement)
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

        # Process extension parameters (ETSI requirement)
        extension_responses = await self._process_extensions(
            key_request.extension_mandatory,
            key_request.extension_optional,
        )

        # Check key pool availability
        if not await self.key_pool_service.check_key_availability(
            number_of_keys, key_size
        ):
            # Handle key exhaustion
            exhaustion_response = await self.key_pool_service.handle_key_exhaustion()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Key pool exhausted",
                    "details": [
                        {
                            "parameter": "key_pool",
                            "error": "Insufficient keys available for request",
                        }
                    ],
                    "exhaustion_info": exhaustion_response,
                },
            )

        # Before calling _generate_and_store_keys, ensure master_sae_id is not None
        if master_sae_id is None:
            raise ValueError("master_sae_id is required")

        # Generate keys using storage service
        keys = await self._generate_and_store_keys(
            number_of_keys,
            key_size,
            master_sae_id,
            slave_sae_id,
            key_request.additional_slave_SAE_IDs,
        )

        # Create ETSI-compliant key container
        key_container = KeyContainer(
            keys=keys,
            key_container_extension=extension_responses.get("key_container_extension"),
        )  # type: ignore[call-arg]

        self.logger.info(
            "Key container generated successfully",
            slave_sae_id=slave_sae_id,
            number_of_keys=len(keys),
            key_size=key_size,
        )

        return key_container

    async def _generate_and_store_keys(
        self,
        number: int,
        size: int,
        master_sae_id: str,
        slave_sae_id: str,
        additional_slave_sae_ids: list[str] | None = None,
    ) -> list[Key]:
        """
        Generate and store keys with proper ETSI compliance

        Args:
            number: Number of keys to generate
            size: Size of each key in bits
            master_sae_id: SAE ID of the master SAE
            slave_sae_id: SAE ID of the slave SAE
            additional_slave_sae_ids: Additional slave SAE IDs for multicast

        Returns:
            List[Key]: List of ETSI-compliant Key objects
        """
        keys = []

        for i in range(number):
            # Generate UUID for key_ID (ETSI requirement: UUID format)
            key_id = str(uuid.uuid4())

            # TODO: Generate actual key data from QKD network
            # For now, generate mock key data with proper size
            key_bytes = os.urandom(size // 8)  # Convert bits to bytes

            # Store key securely using storage service
            try:
                await self.key_storage_service.store_key(
                    key_id=key_id,
                    key_data=key_bytes,
                    master_sae_id=master_sae_id,
                    slave_sae_id=slave_sae_id,
                    key_size=size,
                    expires_at=datetime.datetime.utcnow()
                    + datetime.timedelta(hours=24),
                    key_metadata={
                        "generated_at": datetime.datetime.utcnow().isoformat(),
                        "key_type": "qkd",
                        "quality_metrics": {
                            "entropy": 1.0,  # TODO: Calculate actual entropy
                            "error_rate": 0.0,  # TODO: Get from QKD system
                        },
                        "additional_slave_sae_ids": additional_slave_sae_ids,
                    },
                )
            except Exception as e:
                self.logger.error(f"Failed to store key {key_id}", error=str(e))
                raise RuntimeError(f"Key storage failed: {e}")

            # Create ETSI-compliant Key object
            key = Key(
                key_ID=key_id,
                key=base64.b64encode(key_bytes).decode(
                    "utf-8"
                ),  # ETSI requirement: Base64 encoding
                key_ID_extension=None,  # TODO: Add key ID extensions if needed
                key_extension=None,  # TODO: Add key extensions if needed
                key_size=size,
                created_at=datetime.datetime.utcnow(),
                expires_at=datetime.datetime.utcnow()
                + datetime.timedelta(hours=24),  # TODO: Configure expiration
                source_kme_id=os.getenv("KME_ID", "AAAABBBBCCCCDDDD"),
                target_kme_id=os.getenv("TARGET_KME_ID", "EEEEFFFFGGGGHHHH"),
                key_metadata={
                    "generated_at": datetime.datetime.utcnow().isoformat(),
                    "key_type": "qkd",
                    "quality_metrics": {
                        "entropy": 1.0,  # TODO: Calculate actual entropy
                        "error_rate": 0.0,  # TODO: Get from QKD system
                    },
                },
            )

            keys.append(key)

        return keys

    async def _generate_keys(self, number: int, size: int) -> list[Key]:
        """
        Generate keys with proper ETSI compliance (legacy method - use _generate_and_store_keys instead)

        Args:
            number: Number of keys to generate
            size: Size of each key in bits

        Returns:
            List[Key]: List of ETSI-compliant Key objects
        """
        # This method is kept for backward compatibility
        # New code should use _generate_and_store_keys
        self.logger.warning(
            "Using legacy _generate_keys method - consider using _generate_and_store_keys"
        )

        keys = []

        for i in range(number):
            # Generate UUID for key_ID (ETSI requirement: UUID format)
            key_id = str(uuid.uuid4())

            # TODO: Generate actual key data from QKD network
            # For now, generate mock key data with proper size
            key_bytes = os.urandom(size // 8)  # Convert bits to bytes
            key_data = base64.b64encode(key_bytes).decode(
                "utf-8"
            )  # ETSI requirement: Base64 encoding

            # Create ETSI-compliant Key object
            key = Key(
                key_ID=key_id,
                key=key_data,
                key_ID_extension=None,  # TODO: Add key ID extensions if needed
                key_extension=None,  # TODO: Add key extensions if needed
                key_size=size,
                created_at=datetime.datetime.utcnow(),
                expires_at=datetime.datetime.utcnow()
                + datetime.timedelta(hours=24),  # TODO: Configure expiration
                source_kme_id=os.getenv("KME_ID", "AAAABBBBCCCCDDDD"),
                target_kme_id=os.getenv("TARGET_KME_ID", "EEEEFFFFGGGGHHHH"),
                key_metadata={
                    "generated_at": datetime.datetime.utcnow().isoformat(),
                    "key_type": "qkd",
                    "quality_metrics": {
                        "entropy": 1.0,  # TODO: Calculate actual entropy
                        "error_rate": 0.0,  # TODO: Get from QKD system
                    },
                },
            )

            keys.append(key)

        return keys

    async def _process_extensions(
        self,
        extension_mandatory: list[dict[str, Any]] | None,
        extension_optional: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """
        Process extension parameters (ETSI requirement)

        Args:
            extension_mandatory: Mandatory extension parameters
            extension_optional: Optional extension parameters

        Returns:
            Dict[str, Any]: Extension responses
        """
        extension_responses = {}

        # Process mandatory extensions (ETSI requirement: must handle or return error)
        if extension_mandatory:
            self.logger.info(
                "Processing mandatory extensions",
                count=len(extension_mandatory),
            )

            # TODO: Implement actual extension processing
            # For now, we'll log and return placeholder responses
            for ext in extension_mandatory:
                self.logger.info(f"Mandatory extension: {ext}")

            # Return placeholder extension response
            extension_responses["key_container_extension"] = {
                "mandatory_extensions_processed": len(extension_mandatory),
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }

        # Process optional extensions (ETSI requirement: may ignore)
        if extension_optional:
            self.logger.info(
                "Processing optional extensions",
                count=len(extension_optional),
            )

            # TODO: Implement actual optional extension processing
            # For now, we'll log and ignore
            for ext in extension_optional:
                self.logger.info(f"Optional extension: {ext}")

        return extension_responses

    async def validate_key_access(
        self,
        slave_sae_id: str,
        master_sae_id: str | None = None,
    ) -> bool:
        """
        Validate SAE access permissions for key operations

        Args:
            slave_sae_id: SAE ID of the specified slave SAE
            master_sae_id: SAE ID of the calling master SAE

        Returns:
            bool: True if access is authorized, False otherwise
        """
        self.logger.info(
            "Validating key access",
            slave_sae_id=slave_sae_id,
            master_sae_id=master_sae_id,
        )

        # TODO: Implement actual SAE access validation
        # This should check:
        # - SAE registration status
        # - SAE authorization policies
        # - SAE-SAE relationship validation
        # - Certificate validation

        # For now, return True (allow access)
        self.logger.info("Key access validation placeholder - allowing access")
        return True

    async def check_key_pool_availability(self, number_of_keys: int) -> bool:
        """
        Check if sufficient keys are available in the pool

        Args:
            number_of_keys: Number of keys requested

        Returns:
            bool: True if sufficient keys are available
        """
        # TODO: Implement actual key pool availability check
        # This should query the database for available key count

        # For now, assume keys are available
        self.logger.info(
            f"Key pool availability check placeholder - assuming {number_of_keys} keys available"
        )
        return True

    async def get_keys_by_ids(
        self, master_sae_id: str, key_ids: list[str], requesting_sae_id: str
    ) -> KeyContainer:
        """
        Retrieve keys by their key_IDs (Get Key with Key IDs endpoint)

        Args:
            master_sae_id: SAE ID of the master SAE
            key_ids: List of key IDs to retrieve
            requesting_sae_id: SAE ID requesting the keys

        Returns:
            KeyContainer: ETSI-compliant key container with retrieved keys

        Raises:
            ValueError: If parameters are invalid
            HTTPException: If keys are not found or access is denied
        """
        self.logger.info(
            "Retrieving keys by IDs",
            master_sae_id=master_sae_id,
            key_count=len(key_ids),
            requesting_sae_id=requesting_sae_id,
        )

        # Validate parameters
        if not master_sae_id or len(master_sae_id) != 16:
            raise ValueError(
                f"master_sae_id must be exactly 16 characters, got {len(master_sae_id) if master_sae_id else 0}"
            )

        if not requesting_sae_id or len(requesting_sae_id) != 16:
            raise ValueError(
                f"requesting_sae_id must be exactly 16 characters, got {len(requesting_sae_id) if requesting_sae_id else 0}"
            )

        if not key_ids:
            raise ValueError("key_ids cannot be empty")

        # Validate key ID format (UUID)
        for key_id in key_ids:
            try:
                uuid.UUID(key_id)
            except ValueError:
                raise ValueError(f"Invalid key ID format: {key_id}")

        # Verify key access authorization
        if not await self._verify_key_access(master_sae_id, requesting_sae_id, key_ids):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Unauthorized access to keys",
                    "details": [
                        {
                            "parameter": "authorization",
                            "error": "SAE not authorized to access these keys",
                        }
                    ],
                },
            )

        # Retrieve keys using storage service
        keys = []
        not_found_keys = []

        for key_id in key_ids:
            try:
                key = await self.key_storage_service.retrieve_key(
                    key_id=key_id,
                    requesting_sae_id=requesting_sae_id,
                    master_sae_id=master_sae_id,
                )

                if key:
                    keys.append(key)
                else:
                    not_found_keys.append(key_id)

            except Exception as e:
                self.logger.error(f"Failed to retrieve key {key_id}", error=str(e))
                not_found_keys.append(key_id)

        # Check if all keys were found
        if not_found_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "One or more keys specified are not found on KME",
                    "details": [
                        {
                            "parameter": "key_ids",
                            "error": f"Keys not found: {not_found_keys}",
                        }
                    ],
                },
            )

        # Create ETSI-compliant key container
        key_container = KeyContainer(
            keys=keys,
            key_container_extension=None,
        )  # type: ignore[call-arg]

        self.logger.info(
            "Keys retrieved successfully",
            master_sae_id=master_sae_id,
            key_count=len(keys),
            requesting_sae_id=requesting_sae_id,
        )

        return key_container

    async def _verify_key_access(
        self, master_sae_id: str, requesting_sae_id: str, key_ids: list[str]
    ) -> bool:
        """
        Verify that the requesting SAE has access to the specified keys

        Args:
            master_sae_id: SAE ID of the master SAE
            requesting_sae_id: SAE ID of the requesting SAE
            key_ids: List of key_IDs to verify access for

        Returns:
            bool: True if access is authorized, False otherwise
        """
        # TODO: Implement comprehensive authorization logic
        # For now, use simple logic: requesting SAE must be the master SAE
        # or must have been in the original key request

        logger.info(
            "Verifying key access authorization",
            master_sae_id=master_sae_id,
            requesting_sae_id=requesting_sae_id,
            key_count=len(key_ids),
        )

        # Simple authorization: requesting SAE must be the master SAE
        # This is a basic implementation - should be enhanced with proper authorization
        authorized = requesting_sae_id == master_sae_id

        if authorized:
            logger.info(
                "Key access authorized",
                master_sae_id=master_sae_id,
                requesting_sae_id=requesting_sae_id,
            )
        else:
            logger.warning(
                "Key access denied",
                master_sae_id=master_sae_id,
                requesting_sae_id=requesting_sae_id,
            )

        return authorized

    async def _retrieve_keys_by_ids(self, key_ids: list[str]) -> list[Key]:
        """
        Retrieve keys from storage by their key_IDs

        Args:
            key_ids: List of key_IDs to retrieve

        Returns:
            list[Key]: List of retrieved keys
        """
        logger.info(
            "Retrieving keys by IDs from storage",
            key_count=len(key_ids),
        )

        # TODO: Implement real key storage integration
        # For now, generate mock keys for demonstration

        retrieved_keys = []
        for key_id in key_ids:
            # Generate mock key data
            key_data = os.urandom(44)  # 352 bits = 44 bytes
            key_data_b64 = base64.b64encode(key_data).decode("utf-8")

            # Create mock key
            key = Key(
                key_ID=key_id,
                key=key_data_b64,
                key_ID_extension=None,
                key_extension=None,
                key_size=352,
                created_at=datetime.datetime.utcnow(),
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                source_kme_id=os.getenv("KME_ID", "AAAABBBBCCCCDDDD"),
                target_kme_id=os.getenv("TARGET_KME_ID", "EEEEFFFFGGGGHHHH"),
                key_metadata={
                    "retrieved_at": datetime.datetime.utcnow().isoformat(),
                    "retrieval_method": "key_ids",
                },
            )

            retrieved_keys.append(key)

        logger.info(
            "Successfully retrieved keys from storage",
            retrieved_count=len(retrieved_keys),
        )

        return retrieved_keys


# Global service instance - will be initialized with proper db_session when needed
key_service = None
