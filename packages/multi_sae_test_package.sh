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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
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

# Set proper permissions for .config directory and files
print_status "Setting file permissions..."
chmod 700 .config
chmod 600 .config/*.pem 2>/dev/null || true
chmod 644 .config/*.json 2>/dev/null || true
chmod 755 *.sh *.py 2>/dev/null || true

# Create virtual environment and install dependencies
print_status "Setting up Python virtual environment..."
if command -v python3 &> /dev/null; then
    python3 -m venv venv
    if [[ -f "requirements.txt" ]]; then
        print_status "Installing Python dependencies..."
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        print_status "✅ Virtual environment created and dependencies installed"
    else
        print_warning "No requirements.txt found, skipping dependency installation"
    fi
else
    print_error "Python3 is required but not installed"
    exit 1
fi

print_status "Package extracted successfully!"
print_status "Directory: $EXTRACT_DIR"

echo ""
echo "Files installed:"
echo "Current directory:"
ls -la *.sh *.py *.md 2>/dev/null || echo "  (no files)"
echo ""
echo ".config directory:"
ls -la .config/

echo ""
echo "Next steps:"
echo "1. cd $EXTRACT_DIR"
echo "2. ./multi_sae_test.sh"
echo ""
echo "This will run the comprehensive multi-SAE test suite."
