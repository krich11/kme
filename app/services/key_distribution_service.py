#!/usr/bin/env python3
"""
Key Distribution Service - Week 12 Implementation

Orchestrates key distribution across the KME system by integrating:
- Week 9: Key Storage Service (encryption, versioning, cleanup)
- Week 10: Key Pool Service (availability, health, replenishment)
- Week 10.5: Key Generation Service (mock/QKD dual architecture)
- Week 11: QKD Network Interface (link management, key exchange)

Provides complete end-to-end key distribution from request to delivery.
"""

import asyncio
import base64
import datetime
import uuid
from typing import Any, Dict, List, Optional

import structlog

from app.models.etsi_models import Error, ErrorDetail, Key, KeyContainer, KeyRequest
from app.services.key_generation_service import KeyGenerationFactory
from app.services.key_pool_service import KeyPoolService
from app.services.key_storage_service import KeyStorageService
from app.services.qkd_network_service import QKDNetworkService

logger = structlog.get_logger()


class KeyRequestProcessor:
    """Processes and validates key requests"""

    def __init__(self):
        self.logger = logger.bind(service="KeyRequestProcessor")

    def validate_sae_id(self, sae_id: str) -> bool:
        """
        Validate SAE ID format according to ETSI specification

        Args:
            sae_id: SAE ID to validate

        Returns:
            True if valid, False otherwise
        """
        return len(sae_id) == 16

    async def validate_request(self, request: KeyRequest) -> dict[str, Any]:
        """
        Validate key request for completeness and permissions

        Args:
            request: KeyRequest to validate

        Returns:
            Dict containing validation result
        """
        self.logger.info("Validating key request", request_id=request.request_id)

        validation_result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "request_id": request.request_id,
        }

        # Validate required fields
        if not request.request_id:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing request_id")

        # Validate number field (key count)
        if request.number is not None and request.number <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("Invalid number (key count)")

        # Validate size field (key size)
        if request.size is not None and request.size <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("Invalid size (key size)")

        # Validate key size is reasonable
        if request.size and request.size > 4096:
            validation_result["warnings"].append("Large key size requested")

        # Validate key count is reasonable
        if request.number and request.number > 1000:
            validation_result["warnings"].append("Large key count requested")

        # Validate additional slave SAE IDs if present
        if request.additional_slave_SAE_IDs:
            for sae_id in request.additional_slave_SAE_IDs:
                if not self.validate_sae_id(sae_id):
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"Invalid SAE ID format: {sae_id} (must be 16 characters)"
                    )

        # Process extension parameters
        extension_result = await self.process_extension_parameters(request)
        if not extension_result["valid"]:
            validation_result["valid"] = False
            validation_result["errors"].extend(extension_result["errors"])

        self.logger.info(
            "Key request validation completed",
            request_id=request.request_id,
            valid=validation_result["valid"],
            error_count=len(validation_result["errors"]),
            warning_count=len(validation_result["warnings"]),
        )

        return validation_result

    async def determine_distribution_strategy(
        self, request: KeyRequest, pool_status: dict[str, Any]
    ) -> str:
        """
        Determine the best distribution strategy for the request

        Args:
            request: KeyRequest to process
            pool_status: Current key pool status

        Returns:
            Strategy string: 'direct_delivery', 'network_routing', 'key_generation'
        """
        key_count = request.number or 1  # Default to 1 if not specified

        self.logger.info(
            "Determining distribution strategy",
            request_id=request.request_id,
            key_count=key_count,
            pool_available=pool_status.get("available_keys", 0),
        )

        available_keys = pool_status.get("available_keys", 0)
        required_keys = key_count

        # If we have enough keys in pool, use direct delivery
        if available_keys >= required_keys:
            strategy = "direct_delivery"
            self.logger.info(
                "Strategy: Direct delivery from pool",
                request_id=request.request_id,
                available=available_keys,
                required=required_keys,
            )
        # If we need to generate keys, use key generation
        elif available_keys < required_keys:
            strategy = "key_generation"
            self.logger.info(
                "Strategy: Key generation required",
                request_id=request.request_id,
                available=available_keys,
                required=required_keys,
                shortfall=required_keys - available_keys,
            )
        else:
            # Fallback to network routing if needed
            strategy = "network_routing"
            self.logger.info(
                "Strategy: Network routing",
                request_id=request.request_id,
            )

        return strategy

    async def optimize_key_selection(
        self, available_keys: list[Key], required_count: int
    ) -> list[Key]:
        """
        Select optimal keys based on criteria

        Args:
            available_keys: List of available keys
            required_count: Number of keys required

        Returns:
            List of selected keys
        """
        self.logger.info(
            "Optimizing key selection",
            available_count=len(available_keys),
            required_count=required_count,
        )

        if len(available_keys) <= required_count:
            # Return all available keys if we don't have enough
            return available_keys

        # Sort keys by creation time (newest first) for optimal freshness
        sorted_keys = sorted(available_keys, key=lambda k: k.created_at, reverse=True)

        # Select the required number of keys
        selected_keys = sorted_keys[:required_count]

        self.logger.info(
            "Key selection optimized",
            selected_count=len(selected_keys),
            oldest_key=selected_keys[-1].created_at if selected_keys else None,
            newest_key=selected_keys[0].created_at if selected_keys else None,
        )

        return selected_keys

    async def process_extension_parameters(self, request: KeyRequest) -> dict[str, Any]:
        """
        Process extension parameters according to ETSI specification

        Args:
            request: KeyRequest containing extension parameters

        Returns:
            Dict containing processing result
        """
        result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "processed_mandatory": [],
            "processed_optional": [],
        }

        # Process mandatory extensions (KME shall handle or return error)
        if request.extension_mandatory:
            for ext in request.extension_mandatory:
                try:
                    # For now, we'll accept all mandatory extensions
                    # In a real implementation, specific extensions would be validated
                    result["processed_mandatory"].append(ext)
                    self.logger.info("Processed mandatory extension", extension=ext)
                except Exception as e:
                    result["valid"] = False
                    result["errors"].append(
                        f"Failed to process mandatory extension {ext}: {str(e)}"
                    )

        # Process optional extensions (KME may ignore)
        if request.extension_optional:
            for ext in request.extension_optional:
                try:
                    # For now, we'll process all optional extensions
                    # In a real implementation, specific extensions would be handled
                    result["processed_optional"].append(ext)
                    self.logger.info("Processed optional extension", extension=ext)
                except Exception as e:
                    # Optional extensions can be ignored, so we just log the warning
                    self.logger.warning(
                        "Failed to process optional extension",
                        extension=ext,
                        error=str(e),
                    )

        return result


class KeyDistributionOptimizer:
    """Optimizes key distribution performance"""

    def __init__(self):
        self.logger = logger.bind(service="KeyDistributionOptimizer")
        self.request_cache = {}
        self.performance_metrics = {
            "total_requests": 0,
            "average_processing_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    async def batch_process_requests(
        self, requests: list[KeyRequest]
    ) -> list[dict[str, Any]]:
        """
        Batch process multiple key requests for efficiency

        Args:
            requests: List of key requests to process

        Returns:
            List of processing results
        """
        self.logger.info("Batch processing requests", request_count=len(requests))

        start_time = datetime.datetime.utcnow()
        results = []

        # Process requests in parallel where possible
        tasks = []
        for request in requests:
            task = asyncio.create_task(self._process_single_request(request))
            tasks.append(task)

        # Wait for all tasks to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                self.logger.error(
                    "Request processing failed",
                    request_id=requests[i].request_id,
                    error=str(result),
                )
                results.append(
                    {
                        "success": False,
                        "error": str(result),
                        "request_id": requests[i].request_id,
                    }
                )
            else:
                results.append(result)  # type: ignore[arg-type]

        processing_time = (datetime.datetime.utcnow() - start_time).total_seconds()
        self.logger.info(
            "Batch processing completed",
            request_count=len(requests),
            processing_time=processing_time,
            success_count=len([r for r in results if r.get("success", False)]),
        )

        return results

    async def _process_single_request(self, request: KeyRequest) -> dict[str, Any]:
        """Process a single key request (placeholder for batch processing)"""
        # This would integrate with the main distribution service
        return {
            "success": True,
            "request_id": request.request_id,
            "status": "processed",
        }

    async def implement_caching_strategy(
        self, request: KeyRequest
    ) -> KeyContainer | None:
        """
        Implement caching strategy for frequently requested keys

        Args:
            request: KeyRequest to check cache for

        Returns:
            Cached KeyContainer if available, None otherwise
        """
        cache_key = f"{request.request_id}_{request.number or 1}_{request.size or 256}"

        if cache_key in self.request_cache:
            cached_result = self.request_cache[cache_key]
            cache_age = (
                datetime.datetime.utcnow() - cached_result["timestamp"]
            ).total_seconds()

            # Cache valid for 5 minutes
            if cache_age < 300:
                self.performance_metrics["cache_hits"] += 1
                self.logger.info(
                    "Cache hit", cache_key=cache_key, age_seconds=cache_age
                )
                return cached_result["key_container"]

        self.performance_metrics["cache_misses"] += 1
        self.logger.info("Cache miss", cache_key=cache_key)
        return None

    async def update_cache(self, request: KeyRequest, key_container: KeyContainer):
        """Update cache with new key container"""
        cache_key = f"{request.request_id}_{request.number or 1}_{request.size or 256}"

        self.request_cache[cache_key] = {
            "key_container": key_container,
            "timestamp": datetime.datetime.utcnow(),
        }

        self.logger.info("Cache updated", cache_key=cache_key)

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.performance_metrics,
            "cache_size": len(self.request_cache),
            "cache_hit_rate": (
                self.performance_metrics["cache_hits"]
                / max(
                    self.performance_metrics["cache_hits"]
                    + self.performance_metrics["cache_misses"],
                    1,
                )
            ),
        }


class KeyDistributionService:
    """Main key distribution service - orchestrates all components"""

    def __init__(self, db_session):
        self.db_session = db_session
        self.key_storage_service = KeyStorageService(db_session)
        self.key_pool_service = KeyPoolService(db_session, self.key_storage_service)
        self.key_generator = KeyGenerationFactory.create_generator()
        self.qkd_network_service = QKDNetworkService()

        self.request_processor = KeyRequestProcessor()
        self.optimizer = KeyDistributionOptimizer()

        self.logger = logger.bind(service="KeyDistributionService")
        self.logger.info("Key distribution service initialized")

    def create_etsi_error_response(
        self, message: str, details: list[dict] = None
    ) -> Error:
        """
        Create ETSI-compliant error response

        Args:
            message: Error message
            details: Optional error details

        Returns:
            ETSI Error object
        """
        return Error(
            message=message,
            details=[ErrorDetail(detail=d) for d in details] if details else None,
            error_code=None,
            timestamp=None,
            request_id=None,
            severity=None,
        )

    async def distribute_keys_to_sae(self, request: KeyRequest) -> dict[str, Any]:
        """
        Distribute keys to a single SAE

        Args:
            request: KeyRequest containing distribution parameters

        Returns:
            Dict containing distribution result
        """
        self.logger.info(
            "Distributing keys to SAE",
            request_id=request.request_id,
            key_count=request.number or 1,
            key_size=request.size,
        )

        start_time = datetime.datetime.utcnow()

        try:
            # Step 1: Validate request
            validation_result = await self.request_processor.validate_request(request)
            if not validation_result["valid"]:
                error_details = [{"validation_errors": validation_result["errors"]}]
                etsi_error = self.create_etsi_error_response(
                    "Request validation failed", error_details
                )
                return {
                    "success": False,
                    "etsi_error": etsi_error,
                    "request_id": request.request_id,
                }

            # Step 2: Check cache first
            cached_result = await self.optimizer.implement_caching_strategy(request)
            if cached_result:
                return {
                    "success": True,
                    "key_container": cached_result,
                    "source": "cache",
                    "request_id": request.request_id,
                    "processing_time": (
                        datetime.datetime.utcnow() - start_time
                    ).total_seconds(),
                }

            # Step 3: Get pool status
            pool_status = await self.key_pool_service.get_pool_status()

            # Step 4: Determine distribution strategy
            strategy = await self.request_processor.determine_distribution_strategy(
                request, pool_status
            )

            # Step 5: Execute distribution strategy
            if strategy == "direct_delivery":
                result = await self._execute_direct_delivery(request)
            elif strategy == "key_generation":
                result = await self._execute_key_generation(request)
            elif strategy == "network_routing":
                result = await self._execute_network_routing(request)
            else:
                etsi_error = self.create_etsi_error_response(
                    f"Unknown distribution strategy: {strategy}"
                )
                result = {
                    "success": False,
                    "etsi_error": etsi_error,
                    "request_id": request.request_id,
                }

            # Step 6: Update cache if successful
            if result.get("success") and result.get("key_container"):
                await self.optimizer.update_cache(request, result["key_container"])

            # Step 7: Add processing time
            result["processing_time"] = (
                datetime.datetime.utcnow() - start_time
            ).total_seconds()
            result["strategy"] = strategy

            self.logger.info(
                "Key distribution completed",
                request_id=request.request_id,
                success=result.get("success"),
                strategy=strategy,
                processing_time=result.get("processing_time"),
            )

            return result

        except Exception as e:
            self.logger.error(
                "Key distribution failed",
                request_id=request.request_id,
                error=str(e),
            )
            etsi_error = self.create_etsi_error_response(
                f"Key distribution failed: {str(e)}"
            )
            return {
                "success": False,
                "etsi_error": etsi_error,
                "request_id": request.request_id,
                "processing_time": (
                    datetime.datetime.utcnow() - start_time
                ).total_seconds(),
            }

    async def _execute_direct_delivery(self, request: KeyRequest) -> dict[str, Any]:
        """Execute direct delivery from key pool"""
        self.logger.info("Executing direct delivery", request_id=request.request_id)

        try:
            key_count = request.number or 1
            key_size = request.size or 256  # Default to 256 bits

            # Check key availability in pool
            pool_status = await self.key_pool_service.get_pool_status()
            available_keys_count = pool_status.get("active_keys", 0)

            if available_keys_count < key_count:
                etsi_error = self.create_etsi_error_response(
                    f"Insufficient keys in pool. Available: {available_keys_count}, Required: {key_count}"
                )
                return {
                    "success": False,
                    "etsi_error": etsi_error,
                    "request_id": request.request_id,
                }

            # For now, create mock keys since we don't have direct access to individual keys
            # In a real implementation, this would retrieve actual keys from storage
            mock_keys = []
            for i in range(key_count):
                key_data = await self.key_generator.generate_keys(1, key_size)
                key = Key(
                    key_ID=str(uuid.uuid4()),
                    key=base64.b64encode(key_data[0]).decode("utf-8"),
                    key_size=key_size,
                    created_at=datetime.datetime.utcnow(),
                    expires_at=datetime.datetime.utcnow()
                    + datetime.timedelta(hours=24),
                    key_ID_extension=None,
                    key_extension=None,
                    source_kme_id=None,
                    target_kme_id=None,
                    key_metadata=None,
                )
                mock_keys.append(key)

            # Create key container
            key_container = KeyContainer(
                keys=mock_keys,
                key_container_extension=None,
                container_id=None,
                created_at=None,
                master_sae_id=None,
                slave_sae_id=None,
                total_key_size=None,
            )

            return {
                "success": True,
                "key_container": key_container,
                "source": "pool",
                "request_id": request.request_id,
            }

        except Exception as e:
            self.logger.error(
                "Direct delivery failed", request_id=request.request_id, error=str(e)
            )
            etsi_error = self.create_etsi_error_response(
                f"Direct delivery failed: {str(e)}"
            )
            return {
                "success": False,
                "etsi_error": etsi_error,
                "request_id": request.request_id,
            }

    async def _execute_key_generation(self, request: KeyRequest) -> dict[str, Any]:
        """Execute key generation strategy"""
        self.logger.info("Executing key generation", request_id=request.request_id)

        try:
            key_count = request.number or 1
            key_size = request.size or 256  # Default to 256 bits

            # Generate new keys
            generated_key_data = await self.key_generator.generate_keys(
                key_count, key_size
            )

            # Validate key quality
            quality_results = []
            for key_data in generated_key_data:
                quality = await self.key_generator.validate_key_quality(key_data)
                quality_results.append(quality)

            # Create Key objects
            keys = []
            for i, key_data in enumerate(generated_key_data):
                key = Key(
                    key_ID=str(uuid.uuid4()),
                    key=base64.b64encode(key_data).decode("utf-8"),
                    key_size=key_size,
                    created_at=datetime.datetime.utcnow(),
                    expires_at=datetime.datetime.utcnow()
                    + datetime.timedelta(hours=24),
                    key_ID_extension=None,
                    key_extension=None,
                    source_kme_id=None,
                    target_kme_id=None,
                    key_metadata={"quality_metrics": quality_results[i]},
                )
                keys.append(key)

            # Store keys in storage service
            stored_keys = []
            for key in keys:
                stored_key = await self.key_storage_service.store_key(key)
                stored_keys.append(stored_key)

            # Note: In a real implementation, keys would be added to the pool
            # For now, we'll just store them in the storage service

            # Create key container
            key_container = KeyContainer(
                keys=stored_keys,
                key_container_extension=None,
                container_id=None,
                created_at=None,
                master_sae_id=None,
                slave_sae_id=None,
                total_key_size=None,
            )

            return {
                "success": True,
                "key_container": key_container,
                "source": "generated",
                "request_id": request.request_id,
                "quality_metrics": quality_results,
            }

        except Exception as e:
            self.logger.error(
                "Key generation failed", request_id=request.request_id, error=str(e)
            )
            etsi_error = self.create_etsi_error_response(
                f"Key generation failed: {str(e)}"
            )
            return {
                "success": False,
                "etsi_error": etsi_error,
                "request_id": request.request_id,
            }

    async def _execute_network_routing(self, request: KeyRequest) -> dict[str, Any]:
        """Execute network routing strategy"""
        self.logger.info("Executing network routing", request_id=request.request_id)

        try:
            # Establish QKD link if needed
            link_params = {"protocol": "bb84", "security_level": "high"}
            link_result = await self.qkd_network_service.establish_secure_link(
                request.master_sae_id, link_params
            )

            if not link_result["success"]:
                etsi_error = self.create_etsi_error_response(
                    "Failed to establish QKD link"
                )
                return {
                    "success": False,
                    "etsi_error": etsi_error,
                    "request_id": request.request_id,
                }

            key_count = request.number or 1
            key_size = request.size or 256

            # Perform key exchange
            exchange_result = (
                await self.qkd_network_service.perform_secure_key_exchange(
                    "KME_MASTER_01", key_count, key_size  # Use default KME ID for now
                )
            )

            if not exchange_result["success"]:
                etsi_error = self.create_etsi_error_response(
                    "Failed to perform key exchange"
                )
                return {
                    "success": False,
                    "etsi_error": etsi_error,
                    "request_id": request.request_id,
                }

            # Create mock keys for now (in real implementation, these would come from QKD)
            generated_key_data = await self.key_generator.generate_keys(
                key_count, key_size
            )

            keys = []
            for i, key_data in enumerate(generated_key_data):
                key = Key(
                    key_ID=str(uuid.uuid4()),
                    key=base64.b64encode(key_data).decode("utf-8"),
                    key_size=key_size,
                    created_at=datetime.datetime.utcnow(),
                    expires_at=datetime.datetime.utcnow()
                    + datetime.timedelta(hours=24),
                    key_ID_extension=None,
                    key_extension=None,
                    source_kme_id=None,
                    target_kme_id=None,
                    key_metadata=None,
                )
                keys.append(key)

            # Store and add to pool
            stored_keys = []
            for key in keys:
                stored_key = await self.key_storage_service.store_key(key)
                stored_keys.append(stored_key)

            # Note: In a real implementation, keys would be added to the pool
            # For now, we'll just store them in the storage service

            # Create key container
            key_container = KeyContainer(
                keys=stored_keys,
                key_container_extension=None,
                container_id=None,
                created_at=None,
                master_sae_id=None,
                slave_sae_id=None,
                total_key_size=None,
            )

            return {
                "success": True,
                "key_container": key_container,
                "source": "network",
                "request_id": request.request_id,
                "network_metrics": {
                    "link_id": link_result.get("link_id"),
                    "exchange_id": exchange_result.get("exchange_id"),
                },
            }

        except Exception as e:
            self.logger.error(
                "Network routing failed", request_id=request.request_id, error=str(e)
            )
            etsi_error = self.create_etsi_error_response(
                f"Network routing failed: {str(e)}"
            )
            return {
                "success": False,
                "etsi_error": etsi_error,
                "request_id": request.request_id,
            }

    async def handle_multi_sae_distribution(
        self, requests: list[KeyRequest]
    ) -> dict[str, Any]:
        """
        Handle multiple SAE key distribution requests

        Args:
            requests: List of key requests to process

        Returns:
            Dict containing results for all requests
        """
        self.logger.info("Handling multi-SAE distribution", request_count=len(requests))

        start_time = datetime.datetime.utcnow()
        results = {}

        # Process requests in parallel
        tasks = []
        for request in requests:
            task = asyncio.create_task(self.distribute_keys_to_sae(request))
            tasks.append((request.request_id, task))

        # Wait for all tasks to complete
        for request_id, task in tasks:
            try:
                result = await task
                results[request_id] = result
            except Exception as e:
                self.logger.error(
                    "Multi-SAE request failed", request_id=request_id, error=str(e)
                )
                etsi_error = self.create_etsi_error_response(
                    f"Multi-SAE request failed: {str(e)}"
                )
                results[request_id] = {
                    "success": False,
                    "etsi_error": etsi_error,
                    "request_id": request_id,
                }

        processing_time = (datetime.datetime.utcnow() - start_time).total_seconds()

        success_count = len([r for r in results.values() if r.get("success", False)])

        self.logger.info(
            "Multi-SAE distribution completed",
            total_requests=len(requests),
            success_count=success_count,
            processing_time=processing_time,
        )

        return {
            "success": success_count == len(requests),
            "results": results,
            "total_requests": len(requests),
            "success_count": success_count,
            "processing_time": processing_time,
        }

    async def get_distribution_metrics(self) -> dict[str, Any]:
        """Get key distribution performance metrics"""
        optimizer_metrics = await self.optimizer.get_performance_metrics()
        pool_status = await self.key_pool_service.get_pool_status()
        generator_status = await self.key_generator.get_system_status()
        network_status = await self.qkd_network_service.get_network_status()

        return {
            "optimizer_metrics": optimizer_metrics,
            "pool_status": pool_status,
            "generator_status": generator_status,
            "network_status": network_status,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
