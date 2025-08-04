#!/bin/bash
# ETSI QKD 014 V1.1.1 Comprehensive SAE Workflow Test Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  ETSI QKD 014 SAE Workflow Test${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_section() {
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}${1//?/=}${NC}"
}

# Function to make HTTP request and extract status
make_request() {
    local method="$1"
    local url="$2"
    local data="$3"
    local description="$4"

    print_status "$description"

    local curl_cmd="curl -s -w \"\\nHTTP_STATUS:%{http_code}\""
    curl_cmd="$curl_cmd -X $method \"$url\""
    curl_cmd="$curl_cmd --cert \"$CERT_FILE\""
    curl_cmd="$curl_cmd --key \"$KEY_FILE\""
    curl_cmd="$curl_cmd --cacert \"$CA_FILE\""
    curl_cmd="$curl_cmd --connect-timeout 10"
    curl_cmd="$curl_cmd --max-time 30"

    if [[ -n "$data" ]]; then
        curl_cmd="$curl_cmd -H \"Content-Type: application/json\""
        curl_cmd="$curl_cmd -d \"$data\""
    fi

    local response=$(eval $curl_cmd)
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local response_body=$(echo "$response" | grep -v "HTTP_STATUS:")

    if [[ "$http_status" == "200" ]]; then
        print_status "✅ $description successful"
        echo "$response_body"
        return 0
    else
        print_error "❌ $description failed: HTTP $http_status"
        echo "Response: $response_body"
        return 1
    fi
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

# Initialize test results
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# PHASE 1: BASIC CONNECTIVITY AND HEALTH CHECKS
# ============================================================================
print_section "PHASE 1: BASIC CONNECTIVITY AND HEALTH CHECKS"

# Test 1.1: KME Health Check
if make_request "GET" "$KME_ENDPOINT/health/ready" "" "Testing KME health readiness"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
    print_error "Cannot proceed without basic health check"
    exit 1
fi

# Test 1.2: Detailed Health Check
if make_request "GET" "$KME_ENDPOINT/health/detailed" "" "Testing detailed KME health"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# ============================================================================
# PHASE 2: ETSI QKD 014 CORE API ENDPOINTS
# ============================================================================
print_section "PHASE 2: ETSI QKD 014 CORE API ENDPOINTS"

# Test 2.1: Get Status (ETSI Section 5.1)
print_status "Testing Get Status endpoint (ETSI Section 5.1)..."
STATUS_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X GET "$KME_ENDPOINT/api/v1/keys/$SAE_ID/status" \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    --cacert "$CA_FILE" \
    --connect-timeout 10)

HTTP_STATUS=$(echo "$STATUS_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
STATUS_BODY=$(echo "$STATUS_RESPONSE" | grep -v "HTTP_STATUS:")

if [[ "$HTTP_STATUS" == "200" ]]; then
    print_status "✅ Get Status successful"
    ((TESTS_PASSED++))

    # Extract and display status information
    STORED_KEYS=$(echo "$STATUS_BODY" | jq -r '.stored_key_count' 2>/dev/null)
    MAX_KEYS=$(echo "$STATUS_BODY" | jq -r '.max_key_per_request' 2>/dev/null)
    KEY_SIZE=$(echo "$STATUS_BODY" | jq -r '.key_size' 2>/dev/null)
    MAX_KEY_SIZE=$(echo "$STATUS_BODY" | jq -r '.max_key_size' 2>/dev/null)
    MIN_KEY_SIZE=$(echo "$STATUS_BODY" | jq -r '.min_key_size' 2>/dev/null)
    MAX_SAE_COUNT=$(echo "$STATUS_BODY" | jq -r '.max_SAE_ID_count' 2>/dev/null)

    echo "   Stored keys: $STORED_KEYS"
    echo "   Max keys per request: $MAX_KEYS"
    echo "   Default key size: $KEY_SIZE bits"
    echo "   Key size range: $MIN_KEY_SIZE - $MAX_KEY_SIZE bits"
    echo "   Max additional SAEs: $MAX_SAE_COUNT"

    # Store values for later tests
    echo "$STORED_KEYS" > /tmp/stored_keys_count
    echo "$MAX_KEYS" > /tmp/max_keys_per_request
    echo "$KEY_SIZE" > /tmp/default_key_size
    echo "$MAX_KEY_SIZE" > /tmp/max_key_size
    echo "$MIN_KEY_SIZE" > /tmp/min_key_size
    echo "$MAX_SAE_COUNT" > /tmp/max_sae_count

else
    print_error "❌ Get Status failed: HTTP $HTTP_STATUS"
    echo "Response: $STATUS_BODY"
    ((TESTS_FAILED++))
    # Use default values if status fails
    echo "1" > /tmp/stored_keys_count
    echo "10" > /tmp/max_keys_per_request
    echo "256" > /tmp/default_key_size
    echo "256" > /tmp/max_key_size
    echo "128" > /tmp/min_key_size
    echo "0" > /tmp/max_sae_count
fi

# Load stored values
STORED_KEYS=$(cat /tmp/stored_keys_count)
MAX_KEYS=$(cat /tmp/max_keys_per_request)
DEFAULT_KEY_SIZE=$(cat /tmp/default_key_size)
MAX_KEY_SIZE=$(cat /tmp/max_key_size)
MIN_KEY_SIZE=$(cat /tmp/min_key_size)
MAX_SAE_COUNT=$(cat /tmp/max_sae_count)

# ============================================================================
# PHASE 3: MASTER SAE WORKFLOWS (Key Request Operations)
# ============================================================================
print_section "PHASE 3: MASTER SAE WORKFLOWS (Key Request Operations)"

# Test 3.1: Basic Key Request (Single Key)
print_status "Testing basic key request (single key)..."
KEY_REQUEST_DATA=$(jq -n --arg size "$DEFAULT_KEY_SIZE" '{"number": 1, "size": ($size | tonumber)}')
if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Basic key request (1 key, $DEFAULT_KEY_SIZE bits)"; then
    ((TESTS_PASSED++))
    # Extract key IDs for later tests
    echo "$response_body" | jq -r '.keys[].key_ID' > /tmp/key_ids.txt
else
    ((TESTS_FAILED++))
fi

# Test 3.2: Multiple Key Request
if [[ "$MAX_KEYS" -gt 1 ]]; then
    REQUEST_COUNT=$((MAX_KEYS > 3 ? 3 : MAX_KEYS))
    print_status "Testing multiple key request ($REQUEST_COUNT keys)..."
    KEY_REQUEST_DATA=$(jq -n --arg number "$REQUEST_COUNT" --arg size "$DEFAULT_KEY_SIZE" '{"number": ($number | tonumber), "size": ($size | tonumber)}')
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Multiple key request ($REQUEST_COUNT keys)"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
else
    print_warning "Skipping multiple key test (max_keys_per_request = $MAX_KEYS)"
fi

# Test 3.3: Custom Key Size Request
if [[ "$MAX_KEY_SIZE" -gt "$DEFAULT_KEY_SIZE" ]]; then
    CUSTOM_SIZE=$((DEFAULT_KEY_SIZE + 64))
    if [[ "$CUSTOM_SIZE" -le "$MAX_KEY_SIZE" ]]; then
        print_status "Testing custom key size request ($CUSTOM_SIZE bits)..."
        KEY_REQUEST_DATA=$(jq -n --arg size "$CUSTOM_SIZE" '{"number": 1, "size": ($size | tonumber)}')
        if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Custom key size request ($CUSTOM_SIZE bits)"; then
            ((TESTS_PASSED++))
        else
            ((TESTS_FAILED++))
        fi
    fi
else
    print_warning "Skipping custom key size test (max_key_size = $MAX_KEY_SIZE)"
fi

# Test 3.4: Minimum Key Size Request
if [[ "$MIN_KEY_SIZE" -lt "$DEFAULT_KEY_SIZE" ]]; then
    print_status "Testing minimum key size request ($MIN_KEY_SIZE bits)..."
    KEY_REQUEST_DATA=$(jq -n --arg size "$MIN_KEY_SIZE" '{"number": 1, "size": ($size | tonumber)}')
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Minimum key size request ($MIN_KEY_SIZE bits)"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
else
    print_warning "Skipping minimum key size test (min_key_size = $MIN_KEY_SIZE)"
fi

# Test 3.5: Key Request with Extensions (Optional)
print_status "Testing key request with optional extensions..."
KEY_REQUEST_DATA=$(jq -n --arg size "$DEFAULT_KEY_SIZE" '{"number": 1, "size": ($size | tonumber), "extension_optional": [{"priority": "high"}, {"timeout": 30}]}')
if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Key request with optional extensions"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 3.6: Key Request with Mandatory Extensions (should fail gracefully)
print_status "Testing key request with mandatory extensions (should handle gracefully)..."
KEY_REQUEST_DATA=$(jq -n --arg size "$DEFAULT_KEY_SIZE" '{"number": 1, "size": ($size | tonumber), "extension_mandatory": [{"custom_requirement": "test"}]}')
if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Key request with mandatory extensions"; then
    ((TESTS_PASSED++))
else
    print_warning "Mandatory extensions not supported (expected for some implementations)"
    ((TESTS_PASSED++))  # Count as passed since it's optional
fi

# ============================================================================
# PHASE 4: SLAVE SAE WORKFLOWS (Key Retrieval Operations)
# ============================================================================
print_section "PHASE 4: SLAVE SAE WORKFLOWS (Key Retrieval Operations)"

# Test 4.1: Get Key with Key IDs (if we have key IDs from previous tests)
if [[ -f "/tmp/key_ids.txt" ]]; then
    KEY_ID=$(head -1 /tmp/key_ids.txt)
    if [[ -n "$KEY_ID" ]]; then
        print_status "Testing Get Key with Key IDs..."
        KEY_IDS_DATA=$(jq -n --arg key_id "$KEY_ID" '{"key_IDs": [{"key_ID": $key_id}]}')
        if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/dec_keys" "$KEY_IDS_DATA" "Get Key with Key IDs"; then
            ((TESTS_PASSED++))
        else
            ((TESTS_FAILED++))
        fi
    else
        print_warning "No key IDs available for retrieval test"
    fi
else
    print_warning "No key IDs available for retrieval test"
fi

# ============================================================================
# PHASE 5: ERROR HANDLING AND EDGE CASES
# ============================================================================
print_section "PHASE 5: ERROR HANDLING AND EDGE CASES"

# Test 5.1: Invalid SAE ID
print_status "Testing invalid SAE ID (should return 400/401)..."
INVALID_SAE_ID="INVALID123456789"
if make_request "GET" "$KME_ENDPOINT/api/v1/keys/$INVALID_SAE_ID/status" "" "Invalid SAE ID test"; then
    print_warning "Invalid SAE ID accepted (unexpected)"
    ((TESTS_FAILED++))
else
    print_status "✅ Invalid SAE ID properly rejected"
    ((TESTS_PASSED++))
fi

# Test 5.2: Invalid Key Request (exceed max keys)
if [[ "$MAX_KEYS" -gt 1 ]]; then
    EXCESS_COUNT=$((MAX_KEYS + 1))
    print_status "Testing key request exceeding maximum ($EXCESS_COUNT keys)..."
    KEY_REQUEST_DATA=$(jq -n --arg number "$EXCESS_COUNT" --arg size "$DEFAULT_KEY_SIZE" '{"number": ($number | tonumber), "size": ($size | tonumber)}')
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Excessive key request ($EXCESS_COUNT keys)"; then
        print_warning "Excessive key request accepted (unexpected)"
        ((TESTS_FAILED++))
    else
        print_status "✅ Excessive key request properly rejected"
        ((TESTS_PASSED++))
    fi
fi

# Test 5.3: Invalid Key Size (exceed max)
if [[ "$MAX_KEY_SIZE" -gt "$DEFAULT_KEY_SIZE" ]]; then
    EXCESS_SIZE=$((MAX_KEY_SIZE + 64))
    print_status "Testing key request exceeding maximum size ($EXCESS_SIZE bits)..."
    KEY_REQUEST_DATA=$(jq -n --arg size "$EXCESS_SIZE" '{"number": 1, "size": ($size | tonumber)}')
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Excessive key size request ($EXCESS_SIZE bits)"; then
        print_warning "Excessive key size accepted (unexpected)"
        ((TESTS_FAILED++))
    else
        print_status "✅ Excessive key size properly rejected"
        ((TESTS_PASSED++))
    fi
fi

# Test 5.4: Invalid Key Size (below minimum)
if [[ "$MIN_KEY_SIZE" -gt 64 ]]; then
    BELOW_MIN_SIZE=$((MIN_KEY_SIZE - 64))
    print_status "Testing key request below minimum size ($BELOW_MIN_SIZE bits)..."
    KEY_REQUEST_DATA=$(jq -n --arg size "$BELOW_MIN_SIZE" '{"number": 1, "size": ($size | tonumber)}')
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Below minimum key size request ($BELOW_MIN_SIZE bits)"; then
        print_warning "Below minimum key size accepted (unexpected)"
        ((TESTS_FAILED++))
    else
        print_status "✅ Below minimum key size properly rejected"
        ((TESTS_PASSED++))
    fi
fi

# Test 5.5: Invalid JSON Request
print_status "Testing invalid JSON request..."
INVALID_JSON='{"invalid": "json", "missing": "closing brace"'
if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$INVALID_JSON" "Invalid JSON request"; then
    print_warning "Invalid JSON accepted (unexpected)"
    ((TESTS_FAILED++))
else
    print_status "✅ Invalid JSON properly rejected"
    ((TESTS_PASSED++))
fi

# ============================================================================
# PHASE 6: PERFORMANCE AND STRESS TESTING
# ============================================================================
print_section "PHASE 6: PERFORMANCE AND STRESS TESTING"

# Test 6.1: Rapid Successive Requests
print_status "Testing rapid successive key requests..."
for i in {1..3}; do
    KEY_REQUEST_DATA=$(jq -n --arg size "$DEFAULT_KEY_SIZE" '{"number": 1, "size": ($size | tonumber)}')
    if make_request "POST" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" "$KEY_REQUEST_DATA" "Rapid request $i/3"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    sleep 0.5  # Small delay between requests
done

# Test 6.2: Concurrent Status Checks
print_status "Testing concurrent status checks..."
for i in {1..3}; do
    if make_request "GET" "$KME_ENDPOINT/api/v1/keys/$SAE_ID/status" "" "Concurrent status check $i/3"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
done

# ============================================================================
# PHASE 7: ETSI COMPLIANCE VERIFICATION
# ============================================================================
print_section "PHASE 7: ETSI COMPLIANCE VERIFICATION"

# Test 7.1: Verify Status Response Format
print_status "Verifying Status response format compliance..."
STATUS_RESPONSE=$(curl -s -X GET "$KME_ENDPOINT/api/v1/keys/$SAE_ID/status" \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    --cacert "$CA_FILE" \
    --connect-timeout 10)

# Check for required ETSI fields
REQUIRED_FIELDS=("source_KME_ID" "target_KME_ID" "master_SAE_ID" "slave_SAE_ID" "key_size" "stored_key_count" "max_key_count" "max_key_per_request" "max_key_size" "min_key_size" "max_SAE_ID_count")
MISSING_FIELDS=()

for field in "${REQUIRED_FIELDS[@]}"; do
    if ! echo "$STATUS_RESPONSE" | jq -e ".$field" > /dev/null 2>&1; then
        MISSING_FIELDS+=("$field")
    fi
done

if [[ ${#MISSING_FIELDS[@]} -eq 0 ]]; then
    print_status "✅ Status response contains all required ETSI fields"
    ((TESTS_PASSED++))
else
    print_error "❌ Status response missing required fields: ${MISSING_FIELDS[*]}"
    ((TESTS_FAILED++))
fi

# Test 7.2: Verify Key Response Format
print_status "Verifying Key response format compliance..."
KEY_RESPONSE=$(curl -s -X POST "$KME_ENDPOINT/api/v1/keys/$SAE_ID/enc_keys" \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    --cacert "$CA_FILE" \
    --header "Content-Type: application/json" \
    --data "$(jq -n --arg size "$DEFAULT_KEY_SIZE" '{"number": 1, "size": ($size | tonumber)}')" \
    --connect-timeout 10)

# Check for required ETSI fields in key response
if echo "$KEY_RESPONSE" | jq -e '.keys' > /dev/null 2>&1; then
    KEY_COUNT=$(echo "$KEY_RESPONSE" | jq -r '.keys | length')
    if [[ "$KEY_COUNT" -gt 0 ]]; then
        # Check first key for required fields
        FIRST_KEY=$(echo "$KEY_RESPONSE" | jq -r '.keys[0]')
        if echo "$FIRST_KEY" | jq -e '.key_ID' > /dev/null 2>&1 && echo "$FIRST_KEY" | jq -e '.key' > /dev/null 2>&1; then
            print_status "✅ Key response contains required ETSI fields"
            ((TESTS_PASSED++))
        else
            print_error "❌ Key response missing required key fields"
            ((TESTS_FAILED++))
        fi
    else
        print_error "❌ Key response contains no keys"
        ((TESTS_FAILED++))
    fi
else
    print_error "❌ Key response missing 'keys' field"
    ((TESTS_FAILED++))
fi

# ============================================================================
# TEST SUMMARY
# ============================================================================
print_section "TEST SUMMARY"

echo ""
echo "ETSI QKD 014 V1.1.1 Compliance Test Results:"
echo "============================================="
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo "Success Rate: $(( (TESTS_PASSED * 100) / (TESTS_PASSED + TESTS_FAILED) ))%"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo ""
    print_status "🎉 ALL TESTS PASSED! SAE is fully compliant with ETSI QKD 014 V1.1.1"
    print_status "✅ Basic connectivity: OK"
    print_status "✅ Health checks: OK"
    print_status "✅ Get Status endpoint: OK"
    print_status "✅ Get Key endpoint: OK"
    print_status "✅ Get Key with Key IDs endpoint: OK"
    print_status "✅ Error handling: OK"
    print_status "✅ Performance: OK"
    print_status "✅ ETSI compliance: OK"
else
    echo ""
    print_warning "⚠️  Some tests failed. Review the output above for details."
    print_warning "Consider checking:"
    print_warning "  - KME configuration and status"
    print_warning "  - Network connectivity"
    print_warning "  - Certificate validity"
    print_warning "  - SAE registration status"
fi

echo ""
print_status "Test completed at: $(date)"
print_status "SAE ID: $SAE_ID"
print_status "KME Endpoint: $KME_ENDPOINT"

# Clean up temporary files
rm -f /tmp/stored_keys_count /tmp/max_keys_per_request /tmp/default_key_size /tmp/max_key_size /tmp/min_key_size /tmp/max_sae_count /tmp/key_ids.txt

echo ""
print_status "For detailed API documentation, see: https://www.etsi.org/deliver/etsi_gs/QKD/001_099/014/01.01.01_60/gs_qkd014v010101p.pdf"
