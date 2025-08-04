#!/bin/bash
# Multi-SAE Test Script
# ETSI QKD 014 V1.1.1 Multi-SAE Testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Multi-SAE Test Suite${NC}"
    echo -e "${BLUE}  ETSI QKD 014 V1.1.1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_section() {
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..${#1}})${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load configuration
if [[ -f ".config/multi_sae_config.json" ]]; then
    CONFIG_FILE=".config/multi_sae_config.json"
else
    print_error "multi_sae_config.json not found in .config/"
    exit 1
fi

# Extract values from JSON (requires jq)
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed"
    exit 1
fi

KME_ENDPOINT=$(jq -r '.kme_endpoint' "$CONFIG_FILE")
CA_FILE=$(jq -r '.ca_certificate_file' "$CONFIG_FILE")

print_header
echo "Multi-SAE Test Suite"
echo "KME: $KME_ENDPOINT"
echo ""

# Test all SAE configurations
sae_count=$(jq '.sae_configurations | length' "$CONFIG_FILE")
print_status "Found $sae_count SAE configurations"

for i in $(seq 0 $((sae_count - 1))); do
    sae_id=$(jq -r ".sae_configurations[$i].sae_id" "$CONFIG_FILE")
    sae_name=$(jq -r ".sae_configurations[$i].sae_name" "$CONFIG_FILE")
    role=$(jq -r ".sae_configurations[$i].role" "$CONFIG_FILE")
    cert_file=$(jq -r ".sae_configurations[$i].certificate_file" "$CONFIG_FILE")
    key_file=$(jq -r ".sae_configurations[$i].private_key_file" "$CONFIG_FILE")

    print_section "Testing $sae_name ($sae_id) - Role: $role"

    # Test basic connectivity
    print_status "Testing basic connectivity for $sae_name..."
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$KME_ENDPOINT/health/ready"         --cert "$cert_file"         --key "$key_file"         --cacert "$CA_FILE"         --connect-timeout 10)
    if [[ "$http_code" == "200" ]]; then
        print_status "✅ $sae_name connectivity successful"
    else
        print_error "❌ $sae_name connectivity failed (HTTP $http_code)"
    fi

    # Test status endpoint
    print_status "Testing status endpoint for $sae_name..."
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$KME_ENDPOINT/api/v1/keys/$sae_id/status"         --cert "$cert_file"         --key "$key_file"         --cacert "$CA_FILE"         --connect-timeout 10)
    if [[ "$http_code" == "200" ]]; then
        print_status "✅ $sae_name status endpoint successful"
    else
        print_error "❌ $sae_name status endpoint failed (HTTP $http_code)"
    fi
done

print_section "Multi-SAE Key Distribution Testing"

# Test master SAE requesting keys for slave SAEs
master_sae=$(jq -r '.sae_configurations[] | select(.role == "master") | .sae_id' "$CONFIG_FILE")
slave_saes=$(jq -r '.sae_configurations[] | select(.role == "slave") | .sae_id' "$CONFIG_FILE")

if [[ -n "$master_sae" ]]; then
    master_cert=$(jq -r --arg sae_id "$master_sae" '.sae_configurations[] | select(.sae_id == $sae_id) | .certificate_file' "$CONFIG_FILE")
    master_key=$(jq -r --arg sae_id "$master_sae" '.sae_configurations[] | select(.sae_id == $sae_id) | .private_key_file' "$CONFIG_FILE")

    print_status "Testing master SAE ($master_sae) requesting keys for slave SAEs..."

    for slave_sae in $slave_saes; do
        print_status "Requesting keys for slave SAE: $slave_sae"

        # Create key request JSON
        key_request=$(jq -n '{"number": 1, "size": 352}')

        http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$KME_ENDPOINT/api/v1/keys/$slave_sae/enc_keys"             --cert "$master_cert"             --key "$master_key"             --cacert "$CA_FILE"             --header "Content-Type: application/json"             --data "$key_request"             --connect-timeout 10)
        if [[ "$http_code" == "200" ]]; then
            print_status "✅ Key request for $slave_sae successful"
        else
            print_error "❌ Key request for $slave_sae failed (HTTP $http_code)"
        fi
    done
fi

print_section "Test Summary"
echo "Multi-SAE test suite completed!"
echo "Check the output above for any errors or warnings."
