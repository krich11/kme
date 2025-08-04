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
if ! echo "$ENCRYPTED_DATA" |     openssl enc -aes-256-cbc -d -salt -pbkdf2         -pass "pass:$PASSWORD"         -a         -out "package.tar.gz" 2>/dev/null; then
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
