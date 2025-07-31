#!/usr/bin/env python3
"""
Script to fix Pydantic V1 @validator decorators to V2 @field_validator
"""

import re


def fix_validators():
    """Fix all @validator decorators in database_models.py"""

    # Read the file
    with open("app/models/database_models.py") as f:
        content = f.read()

    # Replace all @validator with @field_validator and add @classmethod
    # Pattern: @validator("...") followed by def validate_...
    pattern = r'@validator\("([^"]+)"\)\s*\n\s*def\s+(\w+)\s*\('
    replacement = r'@field_validator("\1")\n    @classmethod\n    def \2('

    content = re.sub(pattern, replacement, content)

    # Write back to file
    with open("app/models/database_models.py", "w") as f:
        f.write(content)

    print("Fixed all @validator decorators in database_models.py")


if __name__ == "__main__":
    fix_validators()
