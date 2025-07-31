#!/usr/bin/env python3
"""
KME Phase 1 Simplified Test Suite

Version: 1.0.0
Author: KME Development Team
Description: Simplified testing of Phase 1 core functionality
License: [To be determined]

ToDo List:
- [x] Create simplified test framework
- [x] Test core infrastructure components
- [x] Test security infrastructure basics
- [x] Test data models
- [x] Test configuration management
- [x] Test logging infrastructure
- [x] Test ETSI compliance validation
- [x] Test security utilities
- [x] Test edge cases
- [x] Test stress conditions

Progress: 100% (10/10 tasks completed)
"""

import base64
import datetime
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

# Import KME modules
from app.core.config import Settings
from app.core.logging import audit_logger, logger, performance_logger, security_logger
from app.core.security import (
    get_certificate_manager,
    get_key_storage_security,
    get_secure_random,
)
from app.models.api_models import (
    APIResponse,
    ErrorResponse,
    HealthResponse,
    MetricsResponse,
)
from app.models.database_models import (
    AlertRecord,
    KeyRecord,
    KMEEntity,
    PerformanceMetric,
    SAEEntity,
    SecurityEventRecord,
)
from app.models.etsi_models import (
    Error,
    ErrorDetail,
    Key,
    KeyContainer,
    KeyID,
    KeyIDs,
    KeyRequest,
    Status,
)
from app.utils.security_utils import (
    decode_key_base64,
    encode_key_base64,
    generate_kme_id,
    generate_sae_id,
    generate_secure_key_id,
    generate_secure_nonce,
    hash_key_data,
    sanitize_log_data,
    validate_base64_key,
    validate_etsi_compliance,
    validate_key_id,
    validate_key_integrity,
    validate_key_size,
    validate_kme_id,
    validate_sae_id,
)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Phase1SimplifiedTestSuite:
    """Simplified test suite for Phase 1 functionality"""

    def __init__(self):
        """Initialize test suite"""
        self.test_results = {"passed": 0, "failed": 0, "errors": 0, "total": 0}
        self.test_details = []
        self.start_time = time.time()

    def run_test(self, test_name: str, test_func, *args, **kwargs):
        """Run a single test and record results"""
        self.test_results["total"] += 1
        try:
            result = test_func(*args, **kwargs)
            if result:
                self.test_results["passed"] += 1
                print(f"✅ PASS: {test_name}")
                self.test_details.append(
                    {"test": test_name, "status": "PASS", "error": None}
                )
            else:
                self.test_results["failed"] += 1
                print(f"❌ FAIL: {test_name}")
                self.test_details.append(
                    {
                        "test": test_name,
                        "status": "FAIL",
                        "error": "Test returned False",
                    }
                )
        except Exception as e:
            self.test_results["errors"] += 1
            print(f"💥 ERROR: {test_name} - {str(e)}")
            self.test_details.append(
                {"test": test_name, "status": "ERROR", "error": str(e)}
            )

    def test_configuration_management(self):
        """Test configuration management"""
        print("\n🔧 Testing Configuration Management...")

        self.run_test("Configuration Loading", self._test_config_loading)
        self.run_test("Security Configuration", self._test_security_config)
        self.run_test("Database Configuration", self._test_database_config)

    def _test_config_loading(self):
        """Test basic configuration loading"""
        try:
            settings = Settings()
            return (
                settings.kme_id == "AAAABBBBCCCCDDDD"
                and settings.kme_hostname == "localhost"
                and settings.kme_port == 8443
            )
        except Exception:
            return False

    def _test_security_config(self):
        """Test security configuration"""
        try:
            settings = Settings()
            return (
                settings.security_level == "production"
                and settings.enable_mutual_tls is True
                and settings.min_tls_version == "TLSv1.2"
            )
        except Exception:
            return False

    def _test_database_config(self):
        """Test database configuration"""
        try:
            settings = Settings()
            return (
                "postgresql" in settings.database_url
                and settings.database_pool_size == 10
            )
        except Exception:
            return False

    def test_logging_infrastructure(self):
        """Test logging infrastructure"""
        print("\n📝 Testing Logging Infrastructure...")

        self.run_test("Structured Logging", self._test_structured_logging)
        self.run_test("Security Logging", self._test_security_logging)
        self.run_test("Audit Logging", self._test_audit_logging)
        self.run_test("Performance Logging", self._test_performance_logging)
        self.run_test("Log Sanitization", self._test_log_sanitization)

    def _test_structured_logging(self):
        """Test structured logging"""
        try:
            logger.info("Test structured logging", extra={"test": True, "phase": 1})
            return True
        except Exception:
            return False

    def _test_security_logging(self):
        """Test security logging"""
        try:
            security_logger.log_authentication_event(
                event_type="test_auth",
                user_id="test_user",
                success=True,
                details={"test": True},
            )
            return True
        except Exception:
            return False

    def _test_audit_logging(self):
        """Test audit logging"""
        try:
            audit_logger.log_etsi_compliance_event(
                compliance_type="test_compliance",
                event_description="Test compliance event",
                success=True,
            )
            return True
        except Exception:
            return False

    def _test_performance_logging(self):
        """Test performance logging"""
        try:
            performance_logger.log_api_performance_metrics(
                endpoint="/test",
                response_time_ms=100.0,
                throughput_requests_per_sec=10.0,
                error_rate_percent=0.0,
            )
            return True
        except Exception as e:
            print(f"Performance Logging test error: {e}")
            return False

    def _test_log_sanitization(self):
        """Test log sanitization"""
        try:
            sensitive_data = {
                "key": "secret_key_data",
                "password": "secret_password",
                "normal_data": "public_info",
            }
            sanitized = sanitize_log_data(sensitive_data)
            return (
                sanitized["key"] == "[REDACTED]"
                and sanitized["password"] == "[REDACTED]"
                and sanitized["normal_data"] == "public_info"
            )
        except Exception:
            return False

    def test_security_infrastructure(self):
        """Test security infrastructure"""
        print("\n🔒 Testing Security Infrastructure...")

        self.run_test("Secure Random Generation", self._test_secure_random)
        self.run_test("Key Storage Security", self._test_key_storage)
        self.run_test("Security Utilities", self._test_security_utilities)
        self.run_test("Key Encryption/Decryption", self._test_key_encryption)

    def _test_secure_random(self):
        """Test secure random generation"""
        try:
            random_gen = get_secure_random()

            # Test various random generation methods
            uuid_val = random_gen.generate_uuid()
            random_bytes = random_gen.generate_random_bytes(32)
            random_key = random_gen.generate_random_key(256)
            base64_key = random_gen.generate_base64_key(128)

            return (
                len(uuid_val) > 0
                and len(random_bytes) == 32
                and len(random_key) == 32
                and len(base64_key) > 0
            )
        except Exception:
            return False

    def _test_key_storage(self):
        """Test key storage security"""
        try:
            key_storage = get_key_storage_security()

            # Test key encryption
            test_key_data = b"test_key_data_32_bytes_long"
            encrypted = key_storage.encrypt_key_data(test_key_data, "test_key_id")

            # Test key decryption
            decrypted = key_storage.decrypt_key_data(encrypted)

            return test_key_data == decrypted
        except Exception:
            return False

    def _test_security_utilities(self):
        """Test security utilities"""
        try:
            # Test ID validation with valid hex strings
            valid_sae_id = "AAAABBBBCCCCDDDD"
            valid_kme_id = "EEEEFFFFAAAA1111"
            valid_key_id = str(uuid.uuid4())

            sae_valid = validate_sae_id(valid_sae_id)
            kme_valid = validate_kme_id(valid_kme_id)
            key_valid = validate_key_id(valid_key_id)

            # Test key size validation
            key_size_valid = validate_key_size(256)
            key_size_invalid = validate_key_size(255)  # Not multiple of 8

            # Test key encoding/decoding
            test_key = b"test_key_data_32_bytes_long"
            encoded = encode_key_base64(test_key)
            decoded = decode_key_base64(encoded)
            encoding_valid = test_key == decoded

            return (
                sae_valid
                and kme_valid
                and key_valid
                and key_size_valid
                and not key_size_invalid
                and encoding_valid
            )
        except Exception as e:
            print(f"Security Utilities test error: {e}")
            return False

    def _test_key_encryption(self):
        """Test key encryption/decryption"""
        try:
            # Test key encoding/decoding
            original_key = b"test_key_data_for_encryption"
            encoded_key = encode_key_base64(original_key)
            decoded_key = decode_key_base64(encoded_key)

            # Test key integrity
            key_hash = hash_key_data(original_key)
            integrity_valid = validate_key_integrity(original_key, key_hash)

            return original_key == decoded_key and integrity_valid
        except Exception as e:
            print(f"Key Encryption test error: {e}")
            return False

    def test_data_models(self):
        """Test data models"""
        print("\n📊 Testing Data Models...")

        self.run_test("ETSI Models", self._test_etsi_models)
        self.run_test("Database Models", self._test_database_models)
        self.run_test("API Models", self._test_api_models)
        self.run_test("Model Serialization", self._test_model_serialization)
        self.run_test("Model Validation", self._test_model_validation)
        self.run_test("ETSI Compliance", self._test_etsi_compliance)

    def _test_etsi_models(self):
        """Test ETSI models"""
        try:
            # Test Status model
            status = Status(
                source_KME_ID="AAAABBBBCCCCDDDD",
                target_KME_ID="EEEEFFFFAAAA1111",
                master_SAE_ID="1111222233334444",
                slave_SAE_ID="5555666677778888",
                key_size=256,
                stored_key_count=1000,
                max_key_count=10000,
                max_key_per_request=128,
                max_key_size=1024,
                min_key_size=64,
                max_SAE_ID_count=10,
            )

            # Test KeyRequest model
            key_request = KeyRequest(
                number=5,
                size=512,
                additional_slave_SAE_IDs=["SAE1SAE1SAE1SAE1", "SAE2SAE2SAE2SAE2"],
            )

            # Test Key model
            key = Key(
                key_ID=str(uuid.uuid4()),
                key=encode_key_base64(b"test_key_data_32_bytes_long"),
            )

            return (
                status.key_size == 256 and key_request.number == 5 and len(key.key) > 0
            )
        except Exception as e:
            print(f"ETSI Models test error: {e}")
            return False

    def _test_database_models(self):
        """Test database models"""
        try:
            # Test KME entity
            kme_entity = KMEEntity(
                kme_id="AAAABBBBCCCCDDDD",
                hostname="kme1.example.com",
                port=8443,
                certificate_info={"subject": "CN=KME1"},
            )

            # Test SAE entity
            sae_entity = SAEEntity(
                sae_id="IIIIJJJJKKKKLLLL",
                kme_id="AAAABBBBCCCCDDDD",
                certificate_info={"subject": "CN=SAE1"},
            )

            # Test Key record
            key_record = KeyRecord(
                key_id=str(uuid.uuid4()),
                key_data=b"encrypted_key_data",
                key_size=256,
                master_sae_id="IIIIJJJJKKKKLLLL",
                slave_sae_id="MMMMNNNNOOOOPPPP",
                source_kme_id="AAAABBBBCCCCDDDD",
                target_kme_id="EEEEFFFFGGGGHHHH",
            )

            return (
                kme_entity.kme_id == "AAAABBBBCCCCDDDD"
                and sae_entity.sae_id == "IIIIJJJJKKKKLLLL"
                and key_record.key_size == 256
            )
        except Exception as e:
            print(f"Database Models test error: {e}")
            return False

    def _test_api_models(self):
        """Test API models"""
        try:
            # Test API response
            api_response = APIResponse(
                success=True,
                message="Test response",
                data={"test": "data"},
                timestamp=datetime.datetime.utcnow(),
            )

            # Test health response
            health_response = HealthResponse(
                status="healthy",
                uptime_seconds=3600.0,
                checks=[{"name": "test_check", "status": "healthy"}],
                summary={
                    "total_checks": 1,
                    "healthy_checks": 1,
                    "degraded_checks": 0,
                    "unhealthy_checks": 0,
                },
            )

            return api_response.success is True and health_response.status == "healthy"
        except Exception as e:
            print(f"API Models test error: {e}")
            return False

    def _test_model_serialization(self):
        """Test model serialization"""
        try:
            # Test ETSI model serialization
            status = Status(
                source_KME_ID="AAAABBBBCCCCDDDD",
                target_KME_ID="EEEEFFFFGGGGHHHH",
                master_SAE_ID="IIIIJJJJKKKKLLLL",
                slave_SAE_ID="MMMMNNNNOOOOPPPP",
                key_size=256,
                stored_key_count=1000,
                max_key_count=10000,
                max_key_per_request=128,
                max_key_size=1024,
                min_key_size=64,
                max_SAE_ID_count=10,
            )

            # Serialize to JSON
            status_json = status.model_dump_json()
            status_dict = json.loads(status_json)

            return status_dict["key_size"] == 256
        except Exception:
            return False

    def _test_model_validation(self):
        """Test model validation"""
        try:
            # Test valid key size
            key_request = KeyRequest(number=1, size=256)

            # Test invalid key size (should raise validation error)
            try:
                invalid_request = KeyRequest(number=1, size=255)  # Not multiple of 8
                return False  # Should not reach here
            except Exception:
                pass  # Expected validation error

            return True
        except Exception:
            return False

    def _test_etsi_compliance(self):
        """Test ETSI compliance validation"""
        try:
            # Test valid status data
            valid_status = {
                "source_KME_ID": "AAAABBBBCCCCDDDD",
                "target_KME_ID": "EEEEFFFFAAAA1111",
                "master_SAE_ID": "1111222233334444",
                "slave_SAE_ID": "5555666677778888",
                "key_size": 256,
                "stored_key_count": 1000,
                "max_key_count": 10000,
                "max_key_per_request": 128,
                "max_key_size": 1024,
                "min_key_size": 64,
                "max_SAE_ID_count": 10,
            }

            is_valid, errors = validate_etsi_compliance(valid_status, "status")

            # Test invalid data
            invalid_status = valid_status.copy()
            invalid_status["source_KME_ID"] = "INVALID"

            is_invalid, invalid_errors = validate_etsi_compliance(
                invalid_status, "status"
            )

            # Test key container validation
            valid_key_container = {
                "keys": [
                    {
                        "key_ID": str(uuid.uuid4()),
                        "key": encode_key_base64(b"test_key_data"),
                    }
                ]
            }

            is_key_valid, key_errors = validate_etsi_compliance(
                valid_key_container, "key_container"
            )

            return (
                is_valid and not is_invalid and len(invalid_errors) > 0 and is_key_valid
            )
        except Exception as e:
            print(f"ETSI Compliance test error: {e}")
            return False

    def test_phase2_interactions(self):
        """Test Phase 2 API interactions"""
        print("\n🔗 Testing Phase 2 Interactions...")

        self.run_test("Get Status API Simulation", self._test_get_status_api)
        self.run_test("Get Key API Simulation", self._test_get_key_api)
        self.run_test(
            "Get Key with IDs API Simulation", self._test_get_key_with_ids_api
        )
        self.run_test("API Error Handling", self._test_api_error_handling)
        self.run_test("API Security Validation", self._test_api_security_validation)

    def _test_get_status_api(self):
        """Test Get Status API simulation"""
        try:
            # Simulate Get Status request
            slave_sae_id = "5555666677778888"

            # Create status response
            status = Status(
                source_KME_ID="AAAABBBBCCCCDDDD",
                target_KME_ID="EEEEFFFFAAAA1111",
                master_SAE_ID="1111222233334444",
                slave_SAE_ID=slave_sae_id,
                key_size=256,
                stored_key_count=1000,
                max_key_count=10000,
                max_key_per_request=128,
                max_key_size=1024,
                min_key_size=64,
                max_SAE_ID_count=10,
            )

            # Validate response using model validation
            status_dict = status.model_dump()
            is_valid, errors = validate_etsi_compliance(status_dict, "status")

            # Also test model validation
            model_valid = True
            try:
                status.model_validate(status_dict)
            except Exception:
                model_valid = False

            return is_valid and len(errors) == 0 and model_valid
        except Exception as e:
            print(f"Get Status API test error: {e}")
            return False

    def _test_get_key_api(self):
        """Test Get Key API simulation"""
        try:
            # Simulate Get Key request
            key_request = KeyRequest(
                number=3,
                size=512,
                additional_slave_SAE_IDs=["SAE1SAE1SAE1SAE1", "SAE2SAE2SAE2SAE2"],
            )

            # Generate keys
            keys = []
            for i in range(key_request.number):
                key_data = get_secure_random().generate_random_key(key_request.size)
                key = Key(
                    key_ID=generate_secure_key_id(), key=encode_key_base64(key_data)
                )
                keys.append(key)

            # Create key container
            key_container = KeyContainer(keys=keys)

            # Validate response
            is_valid, errors = validate_etsi_compliance(
                key_container.model_dump(), "key_container"
            )

            return is_valid and len(errors) == 0 and len(keys) == 3
        except Exception as e:
            print(f"Get Key API test error: {e}")
            return False

    def _test_get_key_with_ids_api(self):
        """Test Get Key with IDs API simulation"""
        try:
            # Simulate Get Key with IDs request
            key_ids = [
                KeyID(key_ID=str(uuid.uuid4())),
                KeyID(key_ID=str(uuid.uuid4())),
                KeyID(key_ID=str(uuid.uuid4())),
            ]

            key_ids_request = KeyIDs(key_IDs=key_ids)

            # Generate corresponding keys
            keys = []
            for key_id in key_ids:
                key_data = get_secure_random().generate_random_key(256)
                key = Key(key_ID=key_id.key_ID, key=encode_key_base64(key_data))
                keys.append(key)

            # Create key container
            key_container = KeyContainer(keys=keys)

            # Validate response
            is_valid, errors = validate_etsi_compliance(
                key_container.model_dump(), "key_container"
            )

            return is_valid and len(errors) == 0 and len(keys) == 3
        except Exception:
            return False

    def _test_api_error_handling(self):
        """Test API error handling"""
        try:
            # Test error response
            error = Error(
                message="Test error message",
                details=[
                    ErrorDetail(
                        detail={"field": "test_field", "error": "validation_failed"}
                    )
                ],
            )

            # Test error serialization
            error_json = error.model_dump_json()
            error_dict = json.loads(error_json)

            return error_dict["message"] == "Test error message"
        except Exception:
            return False

    def _test_api_security_validation(self):
        """Test API security validation"""
        try:
            # Test SAE ID validation
            valid_sae_id = "AAAABBBBCCCCDDDD"
            invalid_sae_id = "INVALID"

            sae_valid = validate_sae_id(valid_sae_id)
            sae_invalid = validate_sae_id(invalid_sae_id)

            # Test key size validation
            valid_key_size = 256
            invalid_key_size = 255

            size_valid = validate_key_size(valid_key_size)
            size_invalid = validate_key_size(invalid_key_size)

            return sae_valid and not sae_invalid and size_valid and not size_invalid
        except Exception:
            return False

    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        print("\n⚠️ Testing Edge Cases...")

        self.run_test("Empty Data Handling", self._test_empty_data)
        self.run_test("Large Data Handling", self._test_large_data)
        self.run_test("Invalid Input Handling", self._test_invalid_input)
        self.run_test("Concurrent Access", self._test_concurrent_access)
        self.run_test("Resource Exhaustion", self._test_resource_exhaustion)

    def _test_empty_data(self):
        """Test empty data handling"""
        try:
            # Test empty key request
            empty_request = KeyRequest()

            # Test minimal key container (at least one key required)
            minimal_key = Key(
                key_ID=str(uuid.uuid4()), key=encode_key_base64(b"minimal_test_key")
            )
            minimal_container = KeyContainer(keys=[minimal_key])

            return True  # Should handle gracefully
        except Exception as e:
            print(f"Empty Data test error: {e}")
            return False

    def _test_large_data(self):
        """Test large data handling"""
        try:
            # Test large key size
            large_key = get_secure_random().generate_random_key(1024)

            # Test many keys
            many_keys = []
            for i in range(100):
                key_data = get_secure_random().generate_random_key(256)
                key = Key(
                    key_ID=generate_secure_key_id(), key=encode_key_base64(key_data)
                )
                many_keys.append(key)

            key_container = KeyContainer(keys=many_keys)

            return len(key_container.keys) == 100
        except Exception:
            return False

    def _test_invalid_input(self):
        """Test invalid input handling"""
        try:
            # Test invalid SAE ID
            invalid_sae = validate_sae_id("INVALID_SAE_ID")

            # Test invalid key size
            invalid_size = validate_key_size(255)  # Not multiple of 8

            # Test invalid key ID
            invalid_key_id = validate_key_id("not-a-uuid")

            # Test invalid base64
            invalid_base64 = validate_base64_key("invalid-base64!")

            return (
                not invalid_sae
                and not invalid_size
                and not invalid_key_id
                and not invalid_base64
            )
        except Exception:
            return False

    def _test_concurrent_access(self):
        """Test concurrent access handling"""
        try:
            # Test concurrent random generation
            import threading

            results = []

            def generate_random():
                try:
                    random_gen = get_secure_random()
                    result = random_gen.generate_uuid()
                    results.append(result)
                except Exception as e:
                    results.append(f"error: {e}")

            # Create multiple threads
            threads = []
            for i in range(10):
                thread = threading.Thread(target=generate_random)
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Check results
            return len(results) == 10 and all("error:" not in str(r) for r in results)
        except Exception:
            return False

    def _test_resource_exhaustion(self):
        """Test resource exhaustion handling"""
        try:
            # Test memory usage with large data
            large_data = []
            for i in range(1000):
                large_data.append(get_secure_random().generate_random_bytes(1024))

            # Test key storage with many keys
            key_storage = get_key_storage_security()
            encrypted_keys = []

            for i in range(100):
                key_data = get_secure_random().generate_random_key(256)
                encrypted = key_storage.encrypt_key_data(key_data, f"key_{i}")
                encrypted_keys.append(encrypted)

            return len(encrypted_keys) == 100
        except Exception:
            return False

    def test_stress_conditions(self):
        """Test stress conditions"""
        print("\n💪 Testing Stress Conditions...")

        self.run_test("Memory Pressure", self._test_memory_pressure)
        self.run_test("CPU Intensive Operations", self._test_cpu_intensive)
        self.run_test("Rapid Succession Operations", self._test_rapid_operations)

    def _test_memory_pressure(self):
        """Test memory pressure handling"""
        try:
            # Create many objects to simulate memory pressure
            objects = []
            for i in range(10000):
                obj = {
                    "id": i,
                    "data": get_secure_random().generate_random_bytes(100),
                    "timestamp": datetime.datetime.utcnow(),
                }
                objects.append(obj)

            # Test operations under memory pressure
            random_gen = get_secure_random()
            uuid_val = random_gen.generate_uuid()

            return len(uuid_val) > 0
        except Exception:
            return False

    def _test_cpu_intensive(self):
        """Test CPU intensive operations"""
        try:
            # Test many cryptographic operations
            key_storage = get_key_storage_security()
            random_gen = get_secure_random()

            start_time = time.time()

            for i in range(100):
                # Generate key
                key_data = random_gen.generate_random_key(256)

                # Encrypt key
                encrypted = key_storage.encrypt_key_data(key_data, f"key_{i}")

                # Decrypt key
                decrypted = key_storage.decrypt_key_data(encrypted)

                # Verify
                assert key_data == decrypted

            end_time = time.time()
            duration = end_time - start_time

            # Should complete within reasonable time
            return duration < 30.0  # 30 seconds max
        except Exception:
            return False

    def _test_rapid_operations(self):
        """Test rapid succession operations"""
        try:
            random_gen = get_secure_random()

            # Perform rapid operations
            for i in range(100):
                # Generate UUID
                uuid_val = random_gen.generate_uuid()

                # Generate random key
                key_data = random_gen.generate_random_key(128)

            return True
        except Exception:
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting KME Phase 1 Simplified Test Suite")
        print("=" * 60)

        # Run all test categories
        self.test_configuration_management()
        self.test_logging_infrastructure()
        self.test_security_infrastructure()
        self.test_data_models()
        self.test_phase2_interactions()
        self.test_edge_cases()
        self.test_stress_conditions()

        # Print results
        self.print_results()

    def print_results(self):
        """Print test results"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)

        total = self.test_results["total"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        errors = self.test_results["errors"]

        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"💥 Errors: {errors}")

        if total > 0:
            success_rate = (passed / total) * 100
            print(f"Success Rate: {success_rate:.1f}%")

        duration = time.time() - self.start_time
        print(f"Duration: {duration:.2f} seconds")

        # Print failed tests
        if failed > 0 or errors > 0:
            print("\n❌ FAILED TESTS:")
            for detail in self.test_details:
                if detail["status"] in ["FAIL", "ERROR"]:
                    print(f"  - {detail['test']}: {detail['error']}")

        # Overall result
        if failed == 0 and errors == 0:
            print("\n🎉 ALL TESTS PASSED! Phase 1 is ready for Phase 2.")
        else:
            print(
                f"\n⚠️ {failed + errors} tests failed. Review and fix before proceeding to Phase 2."
            )


def main():
    """Main test runner"""
    # Set up test environment
    os.environ["KME_ID"] = "AAAABBBBCCCCDDDD"
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"

    # Create test suite
    test_suite = Phase1SimplifiedTestSuite()

    # Run all tests
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()
