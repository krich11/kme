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
