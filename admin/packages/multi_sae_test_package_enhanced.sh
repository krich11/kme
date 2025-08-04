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
