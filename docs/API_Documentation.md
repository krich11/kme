# KME API Documentation

## Overview

This document provides comprehensive documentation for the Key Management Entity (KME) REST API, which implements the ETSI GS QKD 014 V1.1.1 specification for REST-based key delivery.

## Base URL

```
https://kme.example.com/api/v1
```

## Authentication

All API endpoints require mutual TLS authentication using X.509 certificates. The KME validates SAE certificates and extracts the SAE_ID for authorization.

### Certificate Requirements

- **Protocol**: TLS 1.2 or higher
- **Certificate Format**: X.509 v3
- **Key Usage**: Digital Signature, Key Encipherment, or Key Agreement
- **Extended Key Usage**: Client Authentication
- **Subject Alternative Name**: Must contain the SAE_ID

## Common Response Formats

### Success Response

All successful responses return HTTP 200 with JSON payload.

### Error Response

```json
{
  "message": "Error description",
  "details": [
    {
      "parameter": "field_name",
      "error": "Specific error details"
    }
  ]
}
```

### HTTP Status Codes

- **200 OK**: Request successful
- **400 Bad Request**: Invalid request format or parameters
- **401 Unauthorized**: Authentication or authorization failed
- **503 Service Unavailable**: KME not operational or key exhaustion

## API Endpoints

### 1. Get Status

Retrieves KME status and capabilities for a specific slave SAE.

**Endpoint**: `GET /api/v1/keys/{slave_SAE_ID}/status`

**Path Parameters**:
- `slave_SAE_ID` (string, required): 16-character SAE ID of the slave SAE

**Response**: Status data format

**Example Request**:
```bash
curl -X GET "https://kme.example.com/api/v1/keys/MMMMNNNNOOOOPPPP/status" \
  --cert sae-cert.pem \
  --key sae-key.pem \
  --cacert kme-ca.pem
```

**Example Response**:
```json
{
  "source_KME_ID": "AAAABBBBCCCCDDDD",
  "target_KME_ID": "EEEEFFFFGGGGHHHH",
  "master_SAE_ID": "IIIIJJJJKKKKLLLL",
  "slave_SAE_ID": "MMMMNNNNOOOOPPPP",
  "key_size": 352,
  "stored_key_count": 25000,
  "max_key_count": 100000,
  "max_key_per_request": 128,
  "max_key_size": 1024,
  "min_key_size": 64,
  "max_SAE_ID_count": 10,
  "status_extension": null,
  "kme_status": "operational",
  "qkd_network_status": "connected",
  "key_generation_rate": 100.5,
  "last_key_generation": "2024-07-29T09:30:00Z",
  "certificate_valid_until": "2025-07-29T09:30:00Z"
}
```

**Error Responses**:

400 Bad Request - Invalid SAE ID:
```json
{
  "message": "Invalid slave_SAE_ID format",
  "details": [
    {
      "parameter": "slave_SAE_ID",
      "error": "SAE ID must be exactly 16 characters"
    }
  ]
}
```

401 Unauthorized - Authentication failed:
```json
{
  "message": "SAE authentication failed",
  "details": [
    {
      "parameter": "authentication",
      "error": "Invalid or expired certificate"
    }
  ]
}
```

### 2. Get Key

Requests keys for encryption (Master SAE operation).

**Endpoint**: `POST /api/v1/keys/{slave_SAE_ID}/enc_keys`

**Path Parameters**:
- `slave_SAE_ID` (string, required): 16-character SAE ID of the slave SAE

**Request Body**: Key request data format

**Example Request**:
```bash
curl -X POST "https://kme.example.com/api/v1/keys/MMMMNNNNOOOOPPPP/enc_keys" \
  --cert sae-cert.pem \
  --key sae-key.pem \
  --cacert kme-ca.pem \
  -H "Content-Type: application/json" \
  -d '{
    "number": 2,
    "size": 352,
    "additional_slave_SAE_IDs": ["MMMMNNNNOOOOPPPP"],
    "extension_mandatory": [],
    "extension_optional": []
  }'
```

**Request Body Schema**:
```json
{
  "number": 1,
  "size": 352,
  "additional_slave_SAE_IDs": ["SAE_ID1", "SAE_ID2"],
  "extension_mandatory": [
    {
      "name": "extension_name",
      "value": "extension_value"
    }
  ],
  "extension_optional": [
    {
      "name": "optional_extension",
      "value": "optional_value"
    }
  ]
}
```

**Response**: Key container data format

**Example Response**:
```json
{
  "keys": [
    {
      "key_ID": "550e8400-e29b-41d4-a716-446655440000",
      "key": "dGVzdC1rZXktZGF0YS1iYXNlNjQtZW5jb2RlZA==",
      "key_ID_extension": null,
      "key_extension": null,
      "key_size": 352,
      "created_at": "2024-07-29T09:30:00Z",
      "expires_at": "2024-07-30T09:30:00Z",
      "source_kme_id": "AAAABBBBCCCCDDDD",
      "target_kme_id": "EEEEFFFFGGGGHHHH",
      "key_metadata": {
        "quality_score": 0.99,
        "generation_method": "qkd"
      }
    },
    {
      "key_ID": "550e8400-e29b-41d4-a716-446655440001",
      "key": "YW5vdGhlci1rZXktZGF0YS1iYXNlNjQtZW5jb2RlZA==",
      "key_ID_extension": null,
      "key_extension": null,
      "key_size": 352,
      "created_at": "2024-07-29T09:30:00Z",
      "expires_at": "2024-07-30T09:30:00Z",
      "source_kme_id": "AAAABBBBCCCCDDDD",
      "target_kme_id": "EEEEFFFFGGGGHHHH",
      "key_metadata": {
        "quality_score": 0.98,
        "generation_method": "qkd"
      }
    }
  ],
  "key_container_extension": null,
  "container_id": "container-12345",
  "created_at": "2024-07-29T09:30:00Z",
  "master_sae_id": "IIIIJJJJKKKKLLLL",
  "slave_sae_id": "MMMMNNNNOOOOPPPP",
  "total_key_size": 704
}
```

**Error Responses**:

400 Bad Request - Invalid parameters:
```json
{
  "message": "Invalid request parameters",
  "details": [
    {
      "parameter": "number",
      "error": "Number of keys exceeds maximum allowed (128)"
    }
  ]
}
```

503 Service Unavailable - Key exhaustion:
```json
{
  "message": "Key pool exhausted",
  "details": [
    {
      "parameter": "key_pool",
      "error": "Insufficient keys available for request"
    }
  ]
}
```

### 3. Get Key with Key IDs

Retrieves specific keys using their key_IDs (Slave SAE operation).

**Endpoint**: `POST /api/v1/keys/{master_SAE_ID}/dec_keys`

**Path Parameters**:
- `master_SAE_ID` (string, required): 16-character SAE ID of the master SAE

**Request Body**: Key IDs data format

**Example Request**:
```bash
curl -X POST "https://kme.example.com/api/v1/keys/IIIIJJJJKKKKLLLL/dec_keys" \
  --cert sae-cert.pem \
  --key sae-key.pem \
  --cacert kme-ca.pem \
  -H "Content-Type: application/json" \
  -d '{
    "key_IDs": [
      {"key_ID": "550e8400-e29b-41d4-a716-446655440000"},
      {"key_ID": "550e8400-e29b-41d4-a716-446655440001"}
    ],
    "key_IDs_extension": {}
  }'
```

**Request Body Schema**:
```json
{
  "key_IDs": [
    {
      "key_ID": "uuid-string",
      "key_ID_extension": {}
    }
  ],
  "key_IDs_extension": {}
}
```

**Response**: Key container data format (same as Get Key)

**Error Responses**:

400 Bad Request - Invalid key ID:
```json
{
  "message": "Invalid key_ID format",
  "details": [
    {
      "parameter": "key_ID",
      "error": "Key ID 'invalid-uuid' is not a valid UUID"
    }
  ]
}
```

401 Unauthorized - Access denied:
```json
{
  "message": "Unauthorized access to keys",
  "details": [
    {
      "parameter": "authorization",
      "error": "SAE not authorized to access these keys"
    }
  ]
}
```

## Data Formats

### Status Data Format

```json
{
  "source_KME_ID": "string (16 chars)",
  "target_KME_ID": "string (16 chars)",
  "master_SAE_ID": "string (16 chars)",
  "slave_SAE_ID": "string (16 chars)",
  "key_size": "integer (bits)",
  "stored_key_count": "integer",
  "max_key_count": "integer",
  "max_key_per_request": "integer",
  "max_key_size": "integer (bits)",
  "min_key_size": "integer (bits)",
  "max_SAE_ID_count": "integer",
  "status_extension": "object | null"
}
```

### Key Request Data Format

```json
{
  "number": "integer | null (default: 1)",
  "size": "integer | null (default: key_size from status)",
  "additional_slave_SAE_IDs": "array of strings | null",
  "extension_mandatory": "array of objects | null",
  "extension_optional": "array of objects | null"
}
```

### Key Container Data Format

```json
{
  "keys": [
    {
      "key_ID": "string (UUID)",
      "key": "string (Base64 encoded)",
      "key_ID_extension": "object | null",
      "key_extension": "object | null"
    }
  ],
  "key_container_extension": "object | null"
}
```

### Key IDs Data Format

```json
{
  "key_IDs": [
    {
      "key_ID": "string (UUID)",
      "key_ID_extension": "object | null"
    }
  ],
  "key_IDs_extension": "object | null"
}
```

## Validation Rules

### SAE ID Validation

- Must be exactly 16 characters
- Alphanumeric characters only
- Case-sensitive

### Key ID Validation

- Must be valid UUID format (RFC 4122)
- Version 4 UUID recommended
- Case-insensitive

### Key Size Validation

- Must be between `min_key_size` and `max_key_size` from status
- Must be multiple of 8 bits
- Default: `key_size` from status response

### Number of Keys Validation

- Must be between 1 and `max_key_per_request`
- Default: 1

### Additional Slave SAE IDs Validation

- Array size must not exceed `max_SAE_ID_count`
- Each SAE ID must be valid format
- Must not contain duplicates

## Rate Limiting

Currently, no rate limiting is implemented. Future versions will include:

- Per-SAE request rate limiting
- IP-based rate limiting
- Burst protection
- Circuit breaker patterns

## Security Considerations

### Certificate Validation

- Certificate chain validation
- Certificate expiration checking
- Certificate revocation checking
- SAE_ID extraction and validation

### Key Security

- Keys are encrypted at rest
- Keys are transmitted over TLS 1.2+
- Keys have expiration timestamps
- Key access is audited

### Authorization

- SAE must be authenticated via certificate
- SAE must be authorized for requested operations
- Key access is restricted to authorized SAEs
- All access attempts are logged

## Error Handling

### Common Error Scenarios

1. **Invalid SAE ID**: 400 Bad Request
2. **Invalid key ID**: 400 Bad Request
3. **Authentication failure**: 401 Unauthorized
4. **Authorization failure**: 401 Unauthorized
5. **Key exhaustion**: 503 Service Unavailable
6. **KME not operational**: 503 Service Unavailable

### Error Response Format

All error responses follow the same format:

```json
{
  "message": "Human-readable error description",
  "details": [
    {
      "parameter": "Field name causing the error",
      "error": "Specific error details"
    }
  ]
}
```

## Logging and Monitoring

### Audit Logging

All API operations are logged with:

- Timestamp
- SAE ID
- Operation type
- Request parameters
- Response status
- Performance metrics

### Security Events

Security-related events are logged separately:

- Authentication attempts
- Authorization failures
- Certificate validation events
- Key access events

### Performance Monitoring

Performance metrics are collected:

- Response times
- Throughput
- Error rates
- Resource usage

## Examples

### Complete Workflow Example

1. **Get Status**:
```bash
curl -X GET "https://kme.example.com/api/v1/keys/MMMMNNNNOOOOPPPP/status" \
  --cert master-sae-cert.pem \
  --key master-sae-key.pem \
  --cacert kme-ca.pem
```

2. **Request Keys**:
```bash
curl -X POST "https://kme.example.com/api/v1/keys/MMMMNNNNOOOOPPPP/enc_keys" \
  --cert master-sae-cert.pem \
  --key master-sae-key.pem \
  --cacert kme-ca.pem \
  -H "Content-Type: application/json" \
  -d '{"number": 2, "size": 352}'
```

3. **Retrieve Keys** (by Slave SAE):
```bash
curl -X POST "https://kme.example.com/api/v1/keys/IIIIJJJJKKKKLLLL/dec_keys" \
  --cert slave-sae-cert.pem \
  --key slave-sae-key.pem \
  --cacert kme-ca.pem \
  -H "Content-Type: application/json" \
  -d '{
    "key_IDs": [
      {"key_ID": "550e8400-e29b-41d4-a716-446655440000"},
      {"key_ID": "550e8400-e29b-41d4-a716-446655440001"}
    ]
  }'
```

## Versioning

Current API version: `v1`

Version is included in the URL path: `/api/v1/`

Future versions will maintain backward compatibility where possible.

## Support

For API support and questions:

- **Documentation**: This document
- **Specification**: ETSI GS QKD 014 V1.1.1
- **Implementation**: KME Development Team
- **Issues**: GitHub repository issues

## Changelog

### Version 1.0.0 (Current)

- Initial implementation of ETSI QKD 014 V1.1.1
- All three core endpoints implemented
- TLS 1.2+ authentication
- Comprehensive error handling
- Structured logging and monitoring
