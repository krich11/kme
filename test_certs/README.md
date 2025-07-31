# Test Certificates for KME Development

This directory contains test certificates for KME development and testing.

## Certificate Overview

### CA Certificate
- **File**: `ca_cert.pem`
- **Key**: `ca_key.pem`
- **Purpose**: Certificate Authority for signing SAE certificates
- **Subject**: `/C=US/ST=CA/L=San Francisco/O=KME Test/CN=KME Test CA`

### Master SAE Certificate
- **File**: `master_sae_cert.pem`
- **Key**: `master_sae_key.pem`
- **Purpose**: Master SAE authentication
- **Subject**: `/C=US/ST=CA/L=San Francisco/O=KME Test/CN=Master SAE A1B2C3D4E5F6A7B8`
- **SAE ID**: `A1B2C3D4E5F6A7B8` (16 characters, hex format)

### Slave SAE Certificate
- **File**: `slave_sae_cert.pem`
- **Key**: `slave_sae_key.pem`
- **Purpose**: Slave SAE authentication
- **Subject**: `/C=US/ST=CA/L=San Francisco/O=KME Test/CN=Slave SAE C1D2E3F4A5B6C7D8`
- **SAE ID**: `C1D2E3F4A5B6C7D8` (16 characters, hex format)

### KME Server Certificate
- **File**: `kme_cert.pem`
- **Key**: `kme_key.pem`
- **Purpose**: KME server authentication
- **Subject**: `/C=US/ST=CA/L=San Francisco/O=KME Test/CN=KME Server E1F2A3B4C5D6E7F8`
- **KME ID**: `E1F2A3B4C5D6E7F8` (16 characters, hex format)

## Usage

### For Testing Authentication
```python
# Load certificate for testing
with open('test_certs/master_sae_cert.pem', 'rb') as f:
    cert_data = f.read()

# Extract SAE ID
sae_id = certificate_manager.extract_sae_id_from_certificate(cert_data)
# Returns: "A1B2C3D4E5F6A7B8"
```

### For API Testing
```bash
# Test with curl using certificate
curl --cert test_certs/master_sae_cert.pem \
     --key test_certs/master_sae_key.pem \
     --cacert test_certs/ca_cert.pem \
     https://localhost:8000/api/v1/keys/C1D2E3F4A5B6C7D8/status
```

## Security Notes

⚠️ **WARNING**: These are test certificates only!
- Do not use in production
- Keys are not protected with passwords
- Certificates are self-signed for testing
- SAE IDs are embedded in Common Name for easy extraction

## Certificate Details

All certificates are:
- RSA 2048-bit keys
- Valid for 365 days
- Signed by the test CA
- Include proper X.509 extensions
- Follow ETSI QKD 014 format requirements

## SAE ID Format

SAE IDs are 16-character hexadecimal strings embedded in the Common Name:
- Master SAE: `A1B2C3D4E5F6A7B8`
- Slave SAE: `C1D2E3F4A5B6C7D8`
- KME Server: `E1F2A3B4C5D6E7F8`

This format allows the authentication system to extract SAE IDs using regex pattern matching.
