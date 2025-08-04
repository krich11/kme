# Multi-SAE Test Package

This package contains a comprehensive test suite for multi-SAE scenarios according to ETSI QKD 014 V1.1.1 specifications.

## Contents

- **4 SAE Certificates**: 1 Master SAE + 3 Slave SAEs
- **Multi-SAE Test Script**: Comprehensive testing of all multi-SAE scenarios
- **Configuration Files**: All necessary configuration for testing
- **CA Certificate**: KME CA certificate for authentication

## SAE Configurations

1. **Master SAE** (`qnFFr9m6Re3EWs7C`)
   - Role: Master SAE
   - Can request keys for slave SAEs
   - Can distribute keys to multiple SAEs

2. **Slave SAE 1** (`sae_slave_001`)
   - Role: Slave SAE
   - Can retrieve keys using key IDs
   - Tests key access permissions

3. **Slave SAE 2** (`sae_slave_002`)
   - Role: Slave SAE
   - Can retrieve keys using key IDs
   - Tests key access permissions

4. **Slave SAE 3** (`sae_slave_003`)
   - Role: Slave SAE
   - Can retrieve keys using key IDs
   - Tests key access permissions

## Quick Start

1. **Extract the package**:
   ```bash
   ./multi_sae_test_package.sh
   ```

2. **Run the test suite**:
   ```bash
   ./multi_sae_test.sh
   ```

## Test Scenarios

The test suite covers:

- **Basic Connectivity**: Each SAE can connect to the KME
- **Status Endpoints**: Each SAE can access status information
- **Key Distribution**: Master SAE can request keys for slave SAEs
- **Key Retrieval**: Slave SAEs can retrieve keys using key IDs
- **Access Control**: Proper validation of SAE permissions
- **Multi-SAE Workflows**: Complete ETSI QKD 014 multi-SAE scenarios

## Configuration

All configuration is stored in `.config/multi_sae_config.json`:

- KME endpoint configuration
- SAE certificate and key file paths
- API endpoint definitions
- Connection settings

## Security

- All certificates and private keys are stored in the `.config/` directory
- Certificates are placeholder certificates for testing
- In production, use properly generated certificates

## Troubleshooting

1. **Connection Issues**: Verify KME endpoint is accessible
2. **Certificate Errors**: Check certificate file paths in configuration
3. **Permission Errors**: Ensure script has execute permissions
4. **JSON Parsing Errors**: Verify `jq` is installed

## ETSI QKD 014 Compliance

This test suite validates compliance with:

- Section 5.1: Get Status endpoint
- Section 5.2: Get Key endpoint
- Section 5.3: Get Key with Key IDs endpoint
- Multi-SAE key distribution scenarios
- Access control and authorization
- Error handling and validation
