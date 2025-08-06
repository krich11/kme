#!/usr/bin/env python3
"""
Certificate Validation Tests

Tests for enhanced certificate validation including expiration warnings.
"""

import datetime
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.core.security import CertificateManager, CertificateType


class TestCertificateValidation:
    """Test certificate validation functionality"""

    def setup_method(self):
        """Setup test method"""
        self.cert_manager = CertificateManager()
        self.test_cert_data = self._create_test_certificate()

    def _create_test_certificate(
        self, days_valid: int = 365, common_name: str = "test-sae.example.com"
    ) -> bytes:
        """Create a test certificate"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_agreement=True,
                    data_encipherment=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                    content_commitment=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256())
        )

        return cert.public_bytes(serialization.Encoding.PEM)

    def test_valid_certificate_validation(self):
        """Test validation of a valid certificate"""
        cert_info = self.cert_manager.validate_certificate(self.test_cert_data)

        assert cert_info.is_valid is True
        assert len(cert_info.validation_errors) == 0
        assert cert_info.certificate_type == CertificateType.SAE
        assert "test-sae.example.com" in cert_info.subject

    def test_expired_certificate_validation(self):
        """Test validation of an expired certificate"""
        # Create expired certificate by setting valid dates in the past
        expired_cert_data = self._create_test_certificate_with_dates(
            not_before=datetime.datetime.utcnow() - datetime.timedelta(days=10),
            not_after=datetime.datetime.utcnow() - datetime.timedelta(days=1),
        )

        cert_info = self.cert_manager.validate_certificate(expired_cert_data)

        assert cert_info.is_valid is False
        assert len(cert_info.validation_errors) > 0
        assert any("expired" in error.lower() for error in cert_info.validation_errors)

    def test_future_certificate_validation(self):
        """Test validation of a certificate not yet valid"""
        # Create future certificate (valid from tomorrow)
        future_cert_data = self._create_test_certificate_with_dates(
            not_before=datetime.datetime.utcnow() + datetime.timedelta(days=1),
            not_after=datetime.datetime.utcnow() + datetime.timedelta(days=366),
        )

        cert_info = self.cert_manager.validate_certificate(future_cert_data)

        assert cert_info.is_valid is False
        assert len(cert_info.validation_errors) > 0
        assert any(
            "not yet valid" in error.lower() for error in cert_info.validation_errors
        )

    def test_certificate_expiration_warning(self):
        """Test certificate expiration warning functionality"""
        # Create certificate expiring in 5 days
        expiring_cert_data = self._create_test_certificate_with_dates(
            not_before=datetime.datetime.utcnow() - datetime.timedelta(days=360),
            not_after=datetime.datetime.utcnow() + datetime.timedelta(days=5),
        )

        with patch("app.core.security.logger") as mock_logger:
            cert_info = self.cert_manager.validate_certificate(expiring_cert_data)

            # Should still be valid but with warning
            assert cert_info.is_valid is True
            assert len(cert_info.validation_errors) == 0

            # Check that warning was logged
            mock_logger.warning.assert_called()
            # Check the first argument (message) contains the warning
            call_args = mock_logger.warning.call_args
            assert "Certificate expiration warning" in str(call_args)

    def test_certificate_expiration_notice(self):
        """Test certificate expiration notice functionality"""
        # Create certificate expiring in 15 days
        expiring_cert_data = self._create_test_certificate_with_dates(
            not_before=datetime.datetime.utcnow() - datetime.timedelta(days=350),
            not_after=datetime.datetime.utcnow() + datetime.timedelta(days=15),
        )

        with patch("app.core.security.logger") as mock_logger:
            cert_info = self.cert_manager.validate_certificate(expiring_cert_data)

            # Should still be valid but with notice
            assert cert_info.is_valid is True
            assert len(cert_info.validation_errors) == 0

            # Check that info was logged
            mock_logger.info.assert_called()
            # Check the first argument (message) contains the notice
            call_args = mock_logger.info.call_args
            assert "Certificate expiration notice" in str(call_args)

    def test_certificate_expiration_today(self):
        """Test certificate expiring today"""
        # Create certificate expiring today (end of day)
        today_cert_data = self._create_test_certificate_with_dates(
            not_before=datetime.datetime.utcnow() - datetime.timedelta(days=365),
            not_after=datetime.datetime.utcnow().replace(hour=23, minute=59, second=59),
        )

        cert_info = self.cert_manager.validate_certificate(today_cert_data)

        # Should be invalid
        assert cert_info.is_valid is False
        assert len(cert_info.validation_errors) > 0
        assert any(
            "expires today" in error.lower() for error in cert_info.validation_errors
        )

    def _create_test_certificate_with_dates(
        self,
        not_before: datetime.datetime,
        not_after: datetime.datetime,
        common_name: str = "test-sae.example.com",
    ) -> bytes:
        """Create a test certificate with specific dates"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_agreement=True,
                    data_encipherment=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                    content_commitment=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256())
        )

        return cert.public_bytes(serialization.Encoding.PEM)

    def test_certificate_with_invalid_format(self):
        """Test certificate with invalid format"""
        invalid_cert_data = b"invalid certificate data"

        with pytest.raises(Exception):
            self.cert_manager.validate_certificate(invalid_cert_data)

    def test_certificate_caching(self):
        """Test certificate caching functionality"""
        # First validation
        cert_info1 = self.cert_manager.validate_certificate(self.test_cert_data)

        # Second validation should use cache
        cert_info2 = self.cert_manager.validate_certificate(self.test_cert_data)

        # Should have the same values (cached)
        assert cert_info1.serial_number == cert_info2.serial_number
        assert cert_info1.subject == cert_info2.subject
        assert cert_info1.is_valid == cert_info2.is_valid
        assert cert_info1.certificate_type == cert_info2.certificate_type

    def test_certificate_type_detection(self):
        """Test certificate type detection"""
        # Test SAE certificate
        sae_cert_data = self._create_test_certificate(common_name="sae.example.com")
        cert_info = self.cert_manager.validate_certificate(sae_cert_data)
        assert cert_info.certificate_type == CertificateType.SAE

        # Test KME certificate
        kme_cert_data = self._create_test_certificate(common_name="kme.example.com")
        cert_info = self.cert_manager.validate_certificate(kme_cert_data)
        assert cert_info.certificate_type == CertificateType.KME

    def test_certificate_extensions_extraction(self):
        """Test certificate extensions extraction"""
        cert_info = self.cert_manager.validate_certificate(self.test_cert_data)

        # Should have key usage extensions
        assert len(cert_info.key_usage) > 0
        assert "digital_signature" in cert_info.key_usage
        assert "key_encipherment" in cert_info.key_usage
        assert "key_agreement" in cert_info.key_usage

    def test_certificate_validation_with_expected_id(self):
        """Test certificate validation with expected ID"""
        # Test with matching expected ID
        cert_info = self.cert_manager.validate_certificate(
            self.test_cert_data, expected_id="test-sae.example.com"
        )
        assert cert_info.is_valid is True

        # Test with non-matching expected ID
        cert_info = self.cert_manager.validate_certificate(
            self.test_cert_data, expected_id="different-sae.example.com"
        )
        assert cert_info.is_valid is False
        assert len(cert_info.validation_errors) > 0
        assert any("ID mismatch" in error for error in cert_info.validation_errors)


if __name__ == "__main__":
    pytest.main([__file__])
