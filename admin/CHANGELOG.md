# KME Admin Package - Changelog

## Version 1.1.0 - 2024-01-15

### Changed
- **Modified admin shell script to run from admin directory**
  - Updated `kme-admin-menu.sh` configuration to use relative paths
  - Changed `KME_ADMIN` from `"python admin/kme_admin.py"` to `"python kme_admin.py"`
  - Changed `PACKAGE_DIR` from `"admin/packages"` to `"packages"`
  - Updated prerequisite checking to look for `kme_admin.py` in current directory
  - Updated help messages to reflect new usage pattern

### Updated Documentation
- **README.md**: Updated all usage examples to show `cd admin` first
- **IMPLEMENTATION_SUMMARY.md**: Updated workflow examples
- **demo.py**: Updated next steps instructions

### Usage Changes
**Before:**
```bash
# Run from project root
./admin/kme-admin-menu.sh
python admin/kme_admin.py sae list
```

**After:**
```bash
# Run from admin directory
cd admin
./kme-admin-menu.sh
python kme_admin.py sae list
```

### Benefits
- **Self-contained**: Admin tools can be run from their own directory
- **Cleaner organization**: All admin files are co-located
- **Easier deployment**: Can copy admin directory independently
- **Better isolation**: Admin functionality is separate from main KME

### Files Modified
- `admin/kme-admin-menu.sh` - Updated configuration and paths
- `admin/README.md` - Updated usage examples
- `admin/IMPLEMENTATION_SUMMARY.md` - Updated workflow documentation
- `admin/demo.py` - Updated next steps

### Testing
- ✅ Menu script runs successfully from admin directory
- ✅ CLI commands work from admin directory
- ✅ Prerequisite checking works correctly
- ✅ Package generation paths are correct

## Version 1.2.0 - 2024-01-15

### Added
- **Certificate Generation System**
  - New `certificate_generator.py` module for creating SAE certificates
  - CA-signed certificate generation using KME CA
  - Serial number tracking for unique certificates
  - Certificate revocation functionality
  - Proper X.509 extensions and security permissions

- **Enhanced CLI Commands**
  - `sae generate-certificate` - Create new SAE certificates
  - `sae list-certificates` - List all generated certificates
  - `sae revoke-certificate` - Revoke SAE certificates

- **Enhanced Menu Interface**
  - Option 7: Generate SAE Certificate
  - Option 8: List SAE Certificates
  - Option 9: Revoke SAE Certificate
  - Updated registration flow to offer certificate generation

- **Certificate Management Features**
  - Automatic certificate generation during SAE registration
  - Certificate storage in `sae_certs/` directory
  - Revoked certificate tracking in `sae_certs/revoked/`
  - Certificate validation and CA setup checking

### Updated Documentation
- **README.md**: Added certificate generation section and examples
- **Menu Interface**: Updated to include certificate management options
- **CLI Help**: Added certificate generation command documentation

### CA Management
- **Uses existing CA**: Leverages `../test_certs/ca_cert.pem` and `ca_key.pem`
- **Production ready**: Can be easily adapted for production CA setup
- **Security focused**: Proper permissions and certificate extensions

### Files Added
- `admin/certificate_generator.py` - Certificate generation module
- `admin/sae_certs/` - Directory for generated certificates
- `admin/sae_certs/serial` - Serial number tracking file

### Files Modified
- `admin/kme_admin.py` - Added certificate generation commands
- `admin/kme-admin-menu.sh` - Added certificate management options
- `admin/README.md` - Added certificate generation documentation

## Version 1.3.0 - 2024-01-15

### Added
- **Random SAE ID Generation System**
  - New `sae_id_generator.py` module for secure SAE ID generation
  - **16-character Base64 encoded** identifiers with 96 bits of entropy
  - **URL-safe Base64** encoding (A-Z, a-z, 0-9, -, _)
  - **Cryptographically secure** random generation using `secrets` module
  - **SAE ID validation** with proper format checking

- **Enhanced Certificate Generation**
  - **Auto-generated SAE IDs** when not provided
  - **Auto-generated SAE names** when not provided
  - **Flexible CLI options** for custom or auto-generated values
  - **Improved user experience** with smart defaults

- **Enhanced Menu Interface**
  - **SAE ID generation options** during registration
  - **Auto-generation prompts** for SAE IDs and names
  - **Improved workflow** with recommended defaults

### Security Improvements
- **Cryptographically secure** SAE ID generation
- **96 bits of entropy** for each SAE ID
- **Unique and unpredictable** identifiers
- **Proper validation** of SAE ID format

### Updated CLI Commands
- `sae generate-certificate` now supports auto-generated SAE IDs
- `--sae-id` and `--name` are now optional parameters
- **Smart defaults** for better user experience

### Files Added
- `admin/sae_id_generator.py` - SAE ID generation module

### Files Modified
- `admin/certificate_generator.py` - Integrated SAE ID generation
- `admin/kme_admin.py` - Updated CLI for auto-generated IDs
- `admin/kme-admin-menu.sh` - Enhanced menu with auto-generation options
- `admin/README.md` - Added SAE ID generation documentation

## Version 1.3.1 - 2024-01-15

### Fixed
- **SAE Registration Flow**: Fixed SAE ID not being passed to package generation
  - Updated `generate_sae_package()` function to accept SAE ID as parameter
  - Modified registration flow to pass SAE ID to package generation
  - Eliminated redundant SAE ID prompt during package creation
  - Maintained backward compatibility for standalone package generation

### Improved User Experience
- **Seamless Registration**: SAE ID flows automatically from registration to package generation
- **No Redundant Prompts**: Users no longer need to re-enter SAE ID during package creation
- **Consistent Workflow**: Registration and package generation are now properly integrated

### Files Modified
- `admin/kme-admin-menu.sh` - Updated package generation function and registration flow
- `admin/test_registration_flow.sh` - Added test script to verify registration flow

## Version 1.3.2 - 2024-01-15

### Fixed
- **Package Generation Command**: Fixed incorrect CLI parameter usage
  - Changed `--sae-id` to positional argument `sae_id` for `generate-package` command
  - `generate-certificate` command correctly uses `--sae-id` as named parameter
  - Package generation now works correctly during registration flow

### Technical Details
- **CLI Command Structure**:
  - `generate-package`: `sae_id` (positional) + `--password` + `--output`
  - `generate-certificate`: `--sae-id` (named) + `--name` + `--validity-days` + `--key-size`

### Files Modified
- `admin/kme-admin-menu.sh` - Fixed package generation CLI command syntax

## Version 1.3.3 - 2024-01-15

### Fixed
- **Package Generation Path Issues**: Fixed multiple path-related problems
  - **Certificate Paths**: Updated `_get_sae_data()` to use actual certificate paths from `sae_certs/`
  - **Template Path**: Fixed package template path to use relative `templates/` directory
  - **Encryption Encoding**: Fixed subprocess encoding issue in `_encrypt_archive()`
  - **CA Certificate Path**: Updated to use correct CA certificate path `../test_certs/ca_cert.pem`

### Technical Details
- **Certificate Detection**: Package creator now checks for actual certificate files in `sae_certs/`
- **Fallback Support**: Maintains fallback to mock data if certificates don't exist
- **Binary Data Handling**: Fixed subprocess to handle binary data correctly
- **Path Resolution**: All paths now work correctly from admin directory

### Files Modified
- `admin/kme_admin.py` - Fixed certificate path detection and datetime import
- `admin/package_creator.py` - Fixed template path and encryption encoding

## Version 1.4.0 - 2024-01-15

### Added
- **Improved Package Structure**: Reorganized package layout for better user experience
  - **Current Directory**: Client examples, test scripts, and documentation (easy to find)
  - **`.config` Directory**: Sensitive files (certificates, keys, config) with proper permissions
  - **Smart Client Defaults**: Clients automatically look in `.config` directory first

### Package Structure Changes
```
Before:
sae_package/
├── sae_package.json
├── sae_certificate.pem
├── sae_private_key.pem
├── kme_ca_certificate.pem
├── client_example.py
├── test_connection.sh
├── README.md
└── SECURITY_README.md

After:
./
├── client_example.py          # Easy to find and use
├── test_connection.sh         # Easy to find and use
├── README.md                  # Easy to find and use
└── SECURITY_README.md         # Easy to find and use

.config/
├── sae_package.json           # Sensitive config
├── sae_certificate.pem        # Sensitive cert
├── sae_private_key.pem        # Sensitive key (600 permissions)
└── kme_ca_certificate.pem     # Sensitive CA cert
```

### Enhanced User Experience
- **Easy Discovery**: Users immediately see examples and documentation
- **Secure Storage**: Sensitive files are properly isolated and secured
- **Smart Defaults**: Clients automatically find files in `.config` directory
- **Fallback Support**: Clients can still work with files in current directory
- **Proper Permissions**: `.config` directory (700) and private key (600) properly secured

### Files Modified
- `admin/package_creator.py` - Updated package structure and file organization
- `admin/templates/package_template.sh` - Updated extraction and permission setting

## Version 1.4.1 - 2024-01-15

### Fixed
- **Certificate Generation Bug**: Fixed SAE certificate generation to use SAE ID in Common Name (CN) field instead of human-readable name
  - **Issue**: Certificates were generated with human-readable names in CN field, causing authentication failures
  - **Fix**: Changed certificate subject to use `sae_id` for Common Name instead of `sae_name`
  - **Impact**: SAE authentication now works correctly with KME server

### Technical Details
- **Before**: `CN = Test SAE 3` (human-readable name)
- **After**: `CN = TEST003ABCDEFGHIJ` (16-character SAE ID)
- **Server Expectation**: KME server extracts SAE ID from certificate CN field for authentication

### Files Modified
- `admin/certificate_generator.py` - Fixed certificate subject generation to use SAE ID in CN field

## Version 1.4.2 - 2024-01-15

### Fixed
- **Removed Hardcoded Values**: Eliminated hardcoded SAE names, IDs, and KME IDs from main logic
  - **SAE Name Extraction**: Now extracts actual SAE name from certificate OU field
  - **SAE ID Extraction**: Properly extracts SAE ID from certificate CN field
  - **KME ID Detection**: Automatically detects KME ID from server certificate or environment variable
  - **Dynamic Registration Date**: Uses current timestamp instead of hardcoded date

### Enhanced Certificate Structure
- **CN Field**: Contains SAE ID for authentication (`TEST003ABCDEFGHIJ`)
- **OU Field**: Contains SAE name for display (`SAE TEST003A`)
- **Proper Extraction**: Admin tools now read actual values from certificates

### KME ID Detection
- **Server Certificate**: Extracts KME ID from `../test_certs/kme_server_certificate.pem`
- **Environment Variable**: Falls back to `KME_ID` environment variable
- **Default Fallback**: Uses `KME001ABCDEFGHIJ` if detection fails

### Files Modified
- `admin/kme_admin.py` - Added certificate parsing, KME ID detection, and dynamic name extraction
- `admin/certificate_generator.py` - Store SAE name in OU field for proper extraction
