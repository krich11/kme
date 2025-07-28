#!/usr/bin/env python3
"""
KME Version Tracking Module

Version: 1.0.0
Author: KME Development Team
Description: Version tracking and management system
License: [To be determined]

ToDo List:
- [x] Create version tracking system
- [ ] Add version validation
- [ ] Implement version comparison
- [ ] Add version history
- [ ] Create version migration
- [ ] Add version compatibility checking
- [ ] Implement version rollback
- [ ] Add version documentation
- [ ] Create version testing
- [ ] Add version monitoring

Progress: 10% (1/10 tasks completed)
"""

import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class VersionInfo:
    """Version information container"""

    major: int
    minor: int
    patch: int
    build: str | None = None
    release_date: datetime.date | None = None
    description: str | None = None

    def __str__(self) -> str:
        """String representation of version"""
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version_str += f"+{self.build}"
        return version_str

    def __repr__(self) -> str:
        """Detailed representation of version"""
        return f"VersionInfo({self.major}, {self.minor}, {self.patch}, build='{self.build}')"


class VersionManager:
    """Version management system"""

    def __init__(self):
        """Initialize version manager"""
        self.current_version = VersionInfo(
            major=1,
            minor=0,
            patch=0,
            build="dev",
            release_date=datetime.date.today(),
            description="Initial development version",
        )

        self.version_history = [self.current_version]

    def get_current_version(self) -> VersionInfo:
        """Get current version"""
        return self.current_version

    def get_version_string(self) -> str:
        """Get current version as string"""
        return str(self.current_version)

    def get_version_dict(self) -> dict[str, Any]:
        """Get current version as dictionary"""
        version = self.current_version
        return {
            "version": str(version),
            "major": version.major,
            "minor": version.minor,
            "patch": version.patch,
            "build": version.build,
            "release_date": version.release_date.isoformat()
            if version.release_date
            else None,
            "description": version.description,
        }

    def is_compatible_with(self, other_version: VersionInfo) -> bool:
        """Check if current version is compatible with another version"""
        # Major version must match for compatibility
        return self.current_version.major == other_version.major

    def get_version_info(self) -> dict[str, Any]:
        """Get comprehensive version information"""
        return {
            "current_version": self.get_version_dict(),
            "specification": "ETSI GS QKD 014 V1.1.1",
            "python_version": "3.10+",
            "framework": "FastAPI",
            "database": "PostgreSQL",
            "cache": "Redis",
            "security": "TLS 1.2+",
            "compliance": "ETSI QKD 014 V1.1.1",
        }


# Global version manager instance
version_manager = VersionManager()


def get_version() -> str:
    """Get current version string"""
    return version_manager.get_version_string()


def get_version_info() -> dict[str, Any]:
    """Get comprehensive version information"""
    return version_manager.get_version_info()


def is_compatible_with(version_string: str) -> bool:
    """Check compatibility with version string"""
    try:
        parts = version_string.split(".")
        if len(parts) >= 3:
            other_version = VersionInfo(
                major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2])
            )
            return version_manager.is_compatible_with(other_version)
    except (ValueError, IndexError):
        pass
    return False


# Version constants
VERSION = get_version()
VERSION_INFO = get_version_info()
