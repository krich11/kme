#!/usr/bin/env python3
"""
Secure Credentials Reader

Loads test credentials from .test_credentials file.
This file should NEVER be committed to version control.
"""

import os
from pathlib import Path
from typing import Dict, Optional


class CredentialsManager:
    """Manages test credentials securely"""

    def __init__(self):
        self.credentials_file = Path(__file__).parent / ".test_credentials"
        self._credentials = None

    def _load_credentials(self) -> dict[str, str]:
        """Load credentials from file"""
        if self._credentials is not None:
            return self._credentials

        credentials = {}

        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_file}"
            )

        with open(self.credentials_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    credentials[key.strip()] = value.strip()

        self._credentials = credentials
        return credentials

    def get_postgres_user(self) -> str:
        """Get PostgreSQL username"""
        return self._load_credentials().get("POSTGRES_USER", "krich")

    def get_postgres_password(self) -> str:
        """Get PostgreSQL password"""
        return self._load_credentials().get("POSTGRES_PASSWORD", "")

    def get_sudo_password(self) -> str:
        """Get sudo password"""
        return self._load_credentials().get("SUDO_PASSWORD", "")

    def get_database_url(
        self, host: str = "localhost", port: str = "5432", database: str = "kme_db"
    ) -> str:
        """Get database URL"""
        user = self.get_postgres_user()
        password = self.get_postgres_password()
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    def get_database_config(self) -> dict[str, str]:
        """Get database configuration"""
        return {
            "host": "localhost",
            "port": "5432",
            "user": self.get_postgres_user(),
            "password": self.get_postgres_password(),
            "database": "kme_db",
        }


# Global credentials manager instance
credentials = CredentialsManager()
