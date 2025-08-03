# SAE Connection Package: SAE cLRyqRTP

## Overview
This package contains everything needed to connect this SAE to the KME.

## File Structure
```
./
├── client_example.py          # Python client example
├── test_connection.sh         # Connection test script
├── README.md                  # This file
└── SECURITY_README.md         # Security warnings and instructions

.config/
├── sae_package.json           # Configuration and metadata
├── sae_certificate.pem        # SAE certificate for authentication
├── sae_private_key.pem        # SAE private key (keep secure!)
└── kme_ca_certificate.pem     # KME CA certificate for verification
```

## Quick Start
1. Install dependencies: `pip install requests cryptography`
2. Test connection: `./test_connection.sh`
3. Use client example: `python client_example.py`

## Configuration
The `.config/sae_package.json` file contains all connection parameters:
- KME endpoint URL
- SAE ID and name
- API endpoint paths
- Connection settings

## Security Notes
- Sensitive files are stored in `.config/` directory with proper permissions
- Keep private key secure and restrict access
- Verify KME CA certificate before connecting
- Use HTTPS for all communications
- Review SECURITY_README.md for detailed security information

## Support
For issues or questions, contact your KME administrator.
