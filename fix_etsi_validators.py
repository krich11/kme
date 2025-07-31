#!/usr/bin/env python3
"""
Script to fix Pydantic V1 @validator decorators to V2 @field_validator in etsi_models.py
"""

import re


def fix_etsi_validators():
    """Fix all @validator decorators in etsi_models.py"""

    # Read the file
    with open("app/models/etsi_models.py") as f:
        content = f.read()

    # Replace all @validator with @field_validator and add @classmethod
    pattern = r'@validator\("([^"]+)"\)\s*\n\s*def\s+(\w+)\s*\('
    replacement = r'@field_validator("\1")\n    @classmethod\n    def \2('

    content = re.sub(pattern, replacement, content)

    # Replace @root_validator with @model_validator
    pattern2 = r"@root_validator\(skip_on_failure=True\)\s*\n\s*def\s+(\w+)\s*\("
    replacement2 = r'@model_validator(mode="before")\n    @classmethod\n    def \1('

    content = re.sub(pattern2, replacement2, content)

    # Write back to file
    with open("app/models/etsi_models.py", "w") as f:
        f.write(content)

    print("Fixed all @validator decorators in etsi_models.py")


if __name__ == "__main__":
    fix_etsi_validators()
