#!/bin/bash
# Multi-SAE Test Package Self-Extractor
# ETSI QKD 014 V1.1.1 Multi-SAE Testing Package

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
    echo -e "${BLUE}  Multi-SAE Test Package${NC}"
    echo -e "${BLUE}  ETSI QKD 014 V1.1.1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header

# Check for password
if [[ $# -eq 0 ]]; then
    read -s -p "Enter package password: " PASSWORD
    echo
else
    PASSWORD="$1"
fi

# Create extraction directory
EXTRACT_DIR="multi_sae_test_package"
mkdir -p "$EXTRACT_DIR"
cd "$EXTRACT_DIR"

print_status "Extracting package contents..."

# Decrypt and extract
echo "$PASSWORD" | openssl enc -d -aes-256-cbc -a -salt -pass stdin << 'ENCRYPTED_DATA'
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
ENCRYPTED_DATA
| tar -xzf -

print_status "Package extracted successfully!"
print_status "Directory: $EXTRACT_DIR"

echo ""
echo "Next steps:"
echo "1. cd $EXTRACT_DIR"
echo "2. ./multi_sae_test.sh"
echo ""
echo "This will run the comprehensive multi-SAE test suite."
