# SAE Connection Package: {sae_name}

## Overview
This package contains everything needed to connect this SAE to the KME.

## File Structure
```
./
├── client_example.py          # Python client example
├── test_connection.sh         # Comprehensive ETSI QKD 014 test script
├── requirements.txt           # Python dependencies
├── venv/                      # Python virtual environment (created by installer)
├── README.md                  # This file
└── SECURITY_README.md         # Security warnings and instructions

.config/
├── sae_package.json           # Configuration and metadata
├── sae_certificate.pem        # SAE certificate for authentication
├── sae_private_key.pem        # SAE private key (keep secure!)
└── kme_ca_certificate.pem     # KME CA certificate for verification
```

## Quick Start
1. Extract the package: `./package_name.sh [password]`
2. The installer will automatically create a virtual environment and install dependencies
3. Run comprehensive ETSI QKD 014 tests: `./test_connection.sh`
4. Use client example: `python client_example.py` (automatically activates venv)

## Virtual Environment
The package installer automatically creates a Python virtual environment (`venv/`) and installs all required dependencies from `requirements.txt`. This ensures:
- Isolated Python environment
- Correct dependency versions
- No conflicts with system Python packages

**Automatic Activation**: The `client_example.py` script automatically activates the virtual environment when run.

To manually activate the virtual environment:
```bash
source venv/bin/activate
```

## Configuration
The `.config/sae_package.json` file contains all connection parameters:
- KME endpoint URL
- SAE ID and name
- API endpoint paths
- Connection settings

## Testing
The `test_connection.sh` script provides comprehensive testing of all ETSI QKD 014 V1.1.1 workflows:
- **Phase 1**: Basic connectivity and health checks
- **Phase 2**: Core ETSI API endpoints (Get Status, Get Key, Get Key with Key IDs)
- **Phase 3**: Master SAE workflows (key request operations)
- **Phase 4**: Slave SAE workflows (key retrieval operations)
- **Phase 5**: Error handling and edge cases
- **Phase 6**: Performance and stress testing
- **Phase 7**: ETSI compliance verification

The test script validates:
- All required ETSI data formats
- Error handling and edge cases
- Performance under load
- Full compliance with ETSI GS QKD 014 V1.1.1 specification

## Security Notes
- Sensitive files are stored in `.config/` directory with proper permissions
- Keep private key secure and restrict access
- Verify KME CA certificate before connecting
- Use HTTPS for all communications
- Review SECURITY_README.md for detailed security information

## Support
For issues or questions, contact your KME administrator.
