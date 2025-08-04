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

# Embedded encrypted data
ENCRYPTED_DATA="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"

# Create extraction directory
EXTRACT_DIR="multi_sae_test_package"
mkdir -p "$EXTRACT_DIR"
cd "$EXTRACT_DIR"

print_status "Extracting package contents..."

# Decrypt and extract
if ! echo "$ENCRYPTED_DATA" | base64 -d |     openssl enc -aes-256-cbc -d -salt -pbkdf2         -pass "pass:$PASSWORD"         -out "package.tar.gz" 2>/dev/null; then
    print_error "Invalid password or corrupted package"
    rm -f "package.tar.gz"
    exit 1
fi

# Extract package contents
if ! tar -xzf package.tar.gz; then
    print_error "Failed to extract package contents"
    exit 1
fi

# Remove temporary archive
rm package.tar.gz

print_status "Package extracted successfully!"
print_status "Directory: $EXTRACT_DIR"

echo ""
echo "Next steps:"
echo "1. cd $EXTRACT_DIR"
echo "2. ./multi_sae_test.sh"
echo ""
echo "This will run the comprehensive multi-SAE test suite."
