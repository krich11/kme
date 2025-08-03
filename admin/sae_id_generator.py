#!/usr/bin/env python3
"""
SAE ID Generator

Generates random SAE IDs using Base64 encoding to create 16-character identifiers.
"""

import base64
import re
import secrets
from typing import Optional


class SAEIDGenerator:
    """Generates random SAE IDs"""

    @staticmethod
    def generate_sae_id() -> str:
        """
        Generate a random SAE ID.

        Returns:
            str: 16-character Base64 encoded SAE ID
        """
        # Generate 12 random bytes (96 bits of entropy)
        # This will give us 16 characters when Base64 encoded
        random_bytes = secrets.token_bytes(12)

        # Encode to Base64 and remove padding
        encoded = base64.urlsafe_b64encode(random_bytes).decode("ascii")
        sae_id = encoded.rstrip("=")

        # Ensure it's exactly 16 characters
        if len(sae_id) != 16:
            # If not 16 characters, pad or truncate
            if len(sae_id) < 16:
                sae_id = sae_id.ljust(16, "A")
            else:
                sae_id = sae_id[:16]

        return sae_id

    @staticmethod
    def validate_sae_id(sae_id: str) -> bool:
        """
        Validate a SAE ID format.

        Args:
            sae_id: The SAE ID to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not sae_id:
            return False

        # Check length
        if len(sae_id) != 16:
            return False

        # Check if it contains only valid Base64 characters
        # Base64 URL safe: A-Z, a-z, 0-9, -, _
        pattern = r"^[A-Za-z0-9\-_]{16}$"
        if not re.match(pattern, sae_id):
            return False

        return True

    @staticmethod
    def generate_readable_sae_id(prefix: str = "SAE") -> str:
        """
        Generate a SAE ID with a readable prefix.

        Args:
            prefix: Prefix to add before the random part

        Returns:
            str: SAE ID with prefix
        """
        random_part = SAEIDGenerator.generate_sae_id()
        return f"{prefix}{random_part}"

    @staticmethod
    def extract_random_part(sae_id: str) -> str | None:
        """
        Extract the random part from a SAE ID.

        Args:
            sae_id: The SAE ID to extract from

        Returns:
            str: The random part, or None if invalid
        """
        if not sae_id:
            return None

        # Remove common prefixes
        prefixes = ["SAE", "KME", "MASTER", "SLAVE"]
        for prefix in prefixes:
            if sae_id.startswith(prefix):
                return sae_id[len(prefix) :]

        # If no prefix found, return the whole ID
        return sae_id


def main():
    """Test SAE ID generation"""
    print("=== SAE ID Generator Test ===")

    # Generate some test IDs
    print("\nGenerated SAE IDs:")
    for i in range(5):
        sae_id = SAEIDGenerator.generate_sae_id()
        print(f"  {i+1}. {sae_id}")

    print("\nGenerated SAE IDs with prefix:")
    for i in range(3):
        sae_id = SAEIDGenerator.generate_readable_sae_id("SAE")
        print(f"  {i+1}. {sae_id}")

    # Test validation
    print("\nValidation tests:")
    test_ids = [
        "ABCDEFGHIJKLMNOP",  # Valid
        "1234567890123456",  # Valid
        "ABCDEFGHIJKLMN",  # Too short
        "ABCDEFGHIJKLMNOPQ",  # Too long
        "ABCDEFGHIJKLMN@P",  # Invalid character
        "",  # Empty
    ]

    for test_id in test_ids:
        is_valid = SAEIDGenerator.validate_sae_id(test_id)
        print(f"  '{test_id}': {'✅ Valid' if is_valid else '❌ Invalid'}")

    # Test extraction
    print("\nExtraction tests:")
    test_ids_with_prefix = [
        "SAEABCDEFGHIJKLM",
        "KME12345678901234",
        "MASTERABCDEFGHIJ",
        "ABCDEFGHIJKLMNOP",  # No prefix
    ]

    for test_id in test_ids_with_prefix:
        random_part = SAEIDGenerator.extract_random_part(test_id)
        print(f"  '{test_id}' -> '{random_part}'")


if __name__ == "__main__":
    main()
