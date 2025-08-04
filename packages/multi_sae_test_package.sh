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
