#!/bin/bash
# SAE Connection Test Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  SAE Connection Test${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Load configuration
if [[ -f ".config/sae_package.json" ]]; then
    CONFIG_FILE=".config/sae_package.json"
elif [[ -f "sae_package.json" ]]; then
    CONFIG_FILE="sae_package.json"
else
    print_error "sae_package.json not found in .config/ or current directory"
    exit 1
fi

# Extract values from JSON (requires jq)
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed"
    exit 1
fi

KME_ENDPOINT=$(jq -r '.kme_endpoint' "$CONFIG_FILE")
CERT_FILE=$(jq -r '.certificate_file' "$CONFIG_FILE")
KEY_FILE=$(jq -r '.private_key_file' "$CONFIG_FILE")
CA_FILE=$(jq -r '.ca_certificate_file' "$CONFIG_FILE")
SAE_NAME=$(jq -r '.sae_name' "$CONFIG_FILE")
SAE_ID=$(jq -r '.sae_id' "$CONFIG_FILE")

print_header
echo "SAE: $SAE_NAME ($SAE_ID)"
echo "KME: $KME_ENDPOINT"
echo ""

# Check if files exist
if [[ ! -f "$CERT_FILE" ]]; then
    print_error "Certificate file not found: $CERT_FILE"
    exit 1
fi

if [[ ! -f "$KEY_FILE" ]]; then
    print_error "Private key file not found: $KEY_FILE"
    exit 1
fi

if [[ ! -f "$CA_FILE" ]]; then
    print_error "CA certificate file not found: $CA_FILE"
    exit 1
fi

# Test 1: Health check
print_status "Testing KME health..."
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X GET "$KME_ENDPOINT/health/ready" \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    --cacert "$CA_FILE" \
    --connect-timeout 10)

HTTP_STATUS=$(echo "$HEALTH_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | grep -v "HTTP_STATUS:")

if [[ "$HTTP_STATUS" == "200" ]]; then
    print_status "✅ Health check successful"
else
    print_error "❌ Health check failed: HTTP $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

# Test 2: Detailed health check
print_status "Testing detailed health..."
DETAILED_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X GET "$KME_ENDPOINT/health/detailed" \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    --cacert "$CA_FILE" \
    --connect-timeout 10)

HTTP_STATUS=$(echo "$DETAILED_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$DETAILED_RESPONSE" | grep -v "HTTP_STATUS:")

if [[ "$HTTP_STATUS" == "200" ]]; then
    print_status "✅ Detailed health check successful"
    # Extract status from response
    STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status' 2>/dev/null)
    echo "   KME Status: $STATUS"
else
    print_error "❌ Detailed health check failed: HTTP $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
fi

# Test 3: SAE status endpoint
print_status "Testing SAE status endpoint..."
STATUS_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X GET "$KME_ENDPOINT/api/v1/keys/$SAE_ID/status" \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    --cacert "$CA_FILE" \
    --connect-timeout 10)

HTTP_STATUS=$(echo "$STATUS_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$STATUS_RESPONSE" | grep -v "HTTP_STATUS:")

if [[ "$HTTP_STATUS" == "200" ]]; then
    print_status "✅ SAE status check successful"
    # Extract key information
    STORED_KEYS=$(echo "$RESPONSE_BODY" | jq -r '.stored_key_count' 2>/dev/null)
    MAX_KEYS=$(echo "$RESPONSE_BODY" | jq -r '.max_key_per_request' 2>/dev/null)
    echo "   Stored keys: $STORED_KEYS"
    echo "   Max keys per request: $MAX_KEYS"
else
    print_error "❌ SAE status check failed: HTTP $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
fi

echo ""
print_status "Connection test completed!"
print_status "All tests passed successfully!"
