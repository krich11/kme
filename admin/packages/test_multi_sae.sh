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
