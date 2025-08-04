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
echo "$PASSWORD" | openssl enc -d -aes-256-cbc -a -salt -pbkdf2 -pass stdin << 'ENCRYPTED_DATA'
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
