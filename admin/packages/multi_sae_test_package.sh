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
