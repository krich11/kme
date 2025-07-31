# Mypy Error Fixes - KME Project

## Overview
This document outlines all mypy errors found in the KME project and provides solutions for each category.

## Current Status (Updated)

### ✅ Fixed Issues
1. **Pydantic Config Issues**: Fixed `schema_extra` → `json_schema_extra` in all model files
2. **Extension Service Type Issues**: Fixed missing arguments in ExtensionResponse constructor
3. **Vendor Extension Service Type Issues**: Fixed type annotation for doc_result dictionary

### ⚠️ Remaining Issues

#### 1. Pydantic Config Issues (Still Present)
**Problem**: `json_schema_extra` key still not recognized in TypedDict
**Files**: app/models/etsi_models.py, app/models/api_models.py, app/models/database_models.py
**Count**: ~20 errors

**Root Cause**: Pydantic v2 uses different configuration syntax
**Solution**: Use `model_config` with proper typing

```python
# Current (still causing error)
model_config = ConfigDict(
    json_schema_extra={
        "example": {...}
    }
)

# Solution: Use proper typing
from typing import Any, Dict

class MyModel(BaseModel):
    # ... fields ...
    
    model_config = {
        "json_schema_extra": {
            "example": {...}
        }
    }
```

#### 2. Extension Service Issues (3 remaining)
**Problem**: Type mismatches and missing arguments
**Files**: app/services/extension_service.py
**Count**: 3 errors

**Solutions**:
- Fix dict type mismatch in line 278
- Fix None argument in line 463
- Fix boolean context in line 547

#### 3. Database Model Issues
**Problem**: Dict entry type mismatch
**Files**: app/models/database_models.py
**Count**: 1 error

**Solution**: Fix type annotation for bytes field

#### 4. Config Issues
**Problem**: SettingsConfigDict type mismatch
**Files**: app/core/config.py
**Count**: 2 errors

**Solution**: Update BaseSettings configuration

## Implementation Plan

### Phase 1: Critical Pydantic Fixes (Immediate)
1. **Update all model configurations** to use proper Pydantic v2 syntax
2. **Remove ConfigDict usage** where not needed
3. **Use proper typing** for model configurations

### Phase 2: Extension Service Fixes (High Priority)
1. **Fix dict type annotations** in extension service
2. **Add proper None checks** for optional parameters
3. **Fix boolean context issues**

### Phase 3: Database and Config Fixes (Medium Priority)
1. **Fix database model type annotations**
2. **Update config.py** to use proper BaseSettings syntax

### Phase 4: Cleanup (Low Priority)
1. **Add missing type annotations** for untyped functions
2. **Fix remaining minor issues**

## Quick Fix Commands

### Fix Pydantic Config Issues
```bash
# Replace all ConfigDict usage with proper model_config
find app/models/ -name "*.py" -exec sed -i 's/model_config = ConfigDict(/model_config = {/g' {} \;
find app/models/ -name "*.py" -exec sed -i 's/)/}/g' {} \;
```

### Fix Extension Service Issues
```python
# In extension_service.py, line 278
# Change:
supported_extensions = ["route_type", "key_quality", "encryption_mode", "compression", "priority"]
# To:
supported_extensions: list[str] = ["route_type", "key_quality", "encryption_mode", "compression", "priority"]

# In extension_service.py, line 463
# Change:
self._validate_parameter(param_name, param_value, None)
# To:
self._validate_parameter(param_name, param_value, ext_def or ExtensionDefinition(...))

# In extension_service.py, line 547
# Change:
if ext_def and ext_def.handler:
# To:
if ext_def and ext_def.handler is not None:
```

## Expected Outcome

After implementing all fixes:
- **Mypy should pass** with 0 errors
- **Code will be fully type-safe**
- **Better IDE support** and error detection
- **Improved code maintainability**

## Testing Strategy

1. **Fix each category systematically**
2. **Run mypy after each fix** to verify progress
3. **Ensure no regressions** in functionality
4. **Update tests if needed**

## Files Requiring Immediate Attention

### High Priority
- app/models/etsi_models.py (Pydantic config)
- app/models/api_models.py (Pydantic config)
- app/models/database_models.py (Pydantic config)
- app/services/extension_service.py (Type issues)

### Medium Priority
- app/core/config.py (Settings config)
- app/services/vendor_extension_service.py (Type annotations)

### Low Priority
- Various files with missing type annotations (notes only) 