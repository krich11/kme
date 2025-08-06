#!/usr/bin/env python3
"""
Test Week 10.5 Key Generation Service Implementation

This test verifies that the dual key generation service architecture
works correctly with both mock and QKD generators.
"""

import asyncio
import datetime
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.key_generation_service import (
    KeyGenerationFactory,
    KeyGeneratorInterface,
    MockKeyGenerator,
    QKDKeyGenerator,
)


class TestWeek105KeyGeneration:
    """Test Week 10.5 key generation implementation"""

    @pytest.fixture
    def mock_generator(self):
        """Create mock key generator instance"""
        return MockKeyGenerator()

    @pytest.fixture
    def qkd_generator(self):
        """Create QKD key generator instance"""
        return QKDKeyGenerator()

    def test_mock_generator_initialization(self, mock_generator):
        """Test mock key generator initialization"""
        assert mock_generator is not None
        assert mock_generator.generation_count == 0
        assert mock_generator.total_bytes_generated == 0
        assert mock_generator.last_generation_time is None
        assert mock_generator.error_count == 0

    def test_qkd_generator_initialization(self, qkd_generator):
        """Test QKD key generator initialization"""
        assert qkd_generator is not None
        assert qkd_generator.mock_generator is not None
        assert isinstance(qkd_generator.mock_generator, MockKeyGenerator)
        assert qkd_generator.qkd_network_url == "mock://qkd-system"
        assert qkd_generator.qkd_auth_token == "mock-token"
        assert qkd_generator.qkd_connected is False

    @pytest.mark.asyncio
    async def test_mock_key_generation(self, mock_generator):
        """Test mock key generation functionality"""
        # Generate keys
        keys = await mock_generator.generate_keys(5, 256)

        # Verify results
        assert len(keys) == 5
        assert all(isinstance(key, bytes) for key in keys)
        assert all(len(key) == 32 for key in keys)  # 256 bits = 32 bytes
        assert mock_generator.generation_count == 5
        assert mock_generator.total_bytes_generated == 160  # 5 * 32
        assert mock_generator.last_generation_time is not None

    @pytest.mark.asyncio
    async def test_mock_key_generation_metrics(self, mock_generator):
        """Test mock key generation metrics"""
        # Generate some keys first
        await mock_generator.generate_keys(10, 128)

        # Get metrics
        metrics = await mock_generator.get_generation_metrics()

        assert metrics["generator_type"] == "mock"
        assert metrics["keys_per_second"] == 1000
        assert metrics["success_rate"] == 1.0
        assert metrics["total_generated"] == 10
        assert metrics["total_bytes"] == 160  # 10 * 16 bytes
        assert "last_generation" in metrics

    @pytest.mark.asyncio
    async def test_mock_system_status(self, mock_generator):
        """Test mock system status"""
        # Generate some keys first
        await mock_generator.generate_keys(3, 512)

        # Get status
        status = await mock_generator.get_system_status()

        assert status["generator_type"] == "mock"
        assert status["status"] == "operational"
        assert status["generation_count"] == 3
        assert status["total_bytes_generated"] == 192  # 3 * 64 bytes
        assert status["availability"] == "100%"
        assert status["quality_level"] == "simulated"

    @pytest.mark.asyncio
    async def test_mock_key_quality_validation(self, mock_generator):
        """Test mock key quality validation"""
        # Generate a test key
        keys = await mock_generator.generate_keys(1, 256)
        test_key = keys[0]

        # Validate quality
        quality = await mock_generator.validate_key_quality(test_key)

        assert quality["entropy"] == 1.0
        assert quality["error_rate"] == 0.0
        assert quality["quality_score"] == 1.0
        assert quality["validation_status"] == "passed"
        assert quality["quality_level"] == "simulated"

    @pytest.mark.asyncio
    async def test_qkd_generator_fallback_to_mock(self, qkd_generator):
        """Test QKD generator falls back to mock when QKD unavailable"""
        # QKD connection should fail and fall back to mock
        keys = await qkd_generator.generate_keys(3, 256)

        # Should get keys from mock generator
        assert len(keys) == 3
        assert all(isinstance(key, bytes) for key in keys)
        assert all(len(key) == 32 for key in keys)

        # Verify mock generator was used
        assert qkd_generator.mock_generator.generation_count == 3

    @pytest.mark.asyncio
    async def test_qkd_generator_status(self, qkd_generator):
        """Test QKD generator status reporting"""
        status = await qkd_generator.get_system_status()

        assert status["generator_type"] == "qkd"
        assert status["status"] == "fallback_to_mock"
        assert status["qkd_connected"] is False
        assert status["fallback_generator"] == "mock"
        assert status["qkd_interface_status"] == "not_implemented"
        assert "mock_status" in status
        assert "note" in status

    @pytest.mark.asyncio
    async def test_qkd_generator_metrics(self, qkd_generator):
        """Test QKD generator metrics"""
        # Generate some keys to populate metrics
        await qkd_generator.generate_keys(2, 128)

        metrics = await qkd_generator.get_generation_metrics()

        assert metrics["generator_type"] == "qkd"
        assert metrics["qkd_metrics"] == "not_available"
        assert "fallback_metrics" in metrics
        assert metrics["qkd_network_status"] == "not_connected"
        assert "note" in metrics

    @pytest.mark.asyncio
    async def test_qkd_generator_quality_validation(self, qkd_generator):
        """Test QKD generator quality validation"""
        # Generate a test key
        keys = await qkd_generator.generate_keys(1, 256)
        test_key = keys[0]

        # Validate quality
        quality = await qkd_generator.validate_key_quality(test_key)

        assert quality["generator_type"] == "qkd"
        assert quality["validation_method"] == "mock_fallback"
        assert quality["qkd_quality_metrics"] == "not_available"
        assert "mock_validation" in quality
        assert "note" in quality

    def test_key_generation_factory_mock_mode(self):
        """Test factory creates mock generator in mock mode"""
        with patch.dict(os.environ, {"KEY_GENERATION_MODE": "mock"}):
            generator = KeyGenerationFactory.create_generator()
            assert isinstance(generator, MockKeyGenerator)

    def test_key_generation_factory_qkd_mode(self):
        """Test factory creates QKD generator in QKD mode"""
        with patch.dict(os.environ, {"KEY_GENERATION_MODE": "qkd"}):
            generator = KeyGenerationFactory.create_generator()
            assert isinstance(generator, QKDKeyGenerator)

    def test_key_generation_factory_default_mode(self):
        """Test factory defaults to mock mode"""
        with patch.dict(os.environ, {}, clear=True):
            generator = KeyGenerationFactory.create_generator()
            assert isinstance(generator, MockKeyGenerator)

    def test_key_generation_factory_unknown_mode(self):
        """Test factory handles unknown mode gracefully"""
        with patch.dict(os.environ, {"KEY_GENERATION_MODE": "unknown"}):
            generator = KeyGenerationFactory.create_generator()
            assert isinstance(generator, MockKeyGenerator)

    def test_factory_available_modes(self):
        """Test factory returns available modes"""
        modes = KeyGenerationFactory.get_available_modes()
        assert "mock" in modes
        assert "qkd" in modes
        assert len(modes) == 2

    def test_factory_current_mode(self):
        """Test factory returns current mode"""
        with patch.dict(os.environ, {"KEY_GENERATION_MODE": "qkd"}):
            mode = KeyGenerationFactory.get_current_mode()
            assert mode == "qkd"

    def test_factory_current_mode_default(self):
        """Test factory returns default mode when not set"""
        with patch.dict(os.environ, {}, clear=True):
            mode = KeyGenerationFactory.get_current_mode()
            assert mode == "mock"

    @pytest.mark.asyncio
    async def test_mock_generator_error_handling(self, mock_generator):
        """Test mock generator error handling"""
        # Mock os.urandom to raise an exception
        with patch("os.urandom", side_effect=Exception("Random generation failed")):
            with pytest.raises(RuntimeError, match="Mock key generation failed"):
                await mock_generator.generate_keys(1, 256)

        # Verify error count was incremented
        assert mock_generator.error_count == 1

    @pytest.mark.asyncio
    async def test_mock_generator_multiple_generations(self, mock_generator):
        """Test mock generator handles multiple generations correctly"""
        # First generation
        keys1 = await mock_generator.generate_keys(2, 128)
        assert len(keys1) == 2
        assert mock_generator.generation_count == 2

        # Second generation
        keys2 = await mock_generator.generate_keys(3, 256)
        assert len(keys2) == 3
        assert mock_generator.generation_count == 5

        # Verify total bytes
        expected_bytes = (2 * 16) + (3 * 32)  # 128 bits = 16 bytes, 256 bits = 32 bytes
        assert mock_generator.total_bytes_generated == expected_bytes

    @pytest.mark.asyncio
    async def test_qkd_generator_connection_attempt(self, qkd_generator):
        """Test QKD generator connection attempt"""
        # Test connection attempt
        connected = await qkd_generator._connect_to_qkd_network()

        # Should return False (QKD not available)
        assert connected is False
        assert qkd_generator.qkd_connected is False

    @pytest.mark.asyncio
    async def test_key_generation_interface_compliance(self, mock_generator):
        """Test that generators comply with the interface"""
        # Verify all required methods exist
        assert hasattr(mock_generator, "generate_keys")
        assert hasattr(mock_generator, "get_system_status")
        assert hasattr(mock_generator, "validate_key_quality")
        assert hasattr(mock_generator, "get_generation_metrics")

        # Verify methods are callable
        assert callable(mock_generator.generate_keys)
        assert callable(mock_generator.get_system_status)
        assert callable(mock_generator.validate_key_quality)
        assert callable(mock_generator.get_generation_metrics)


if __name__ == "__main__":
    pytest.main([__file__])
