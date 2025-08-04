#!/bin/bash
# SAE Package Self-Extractor
# Package: {{PACKAGE_NAME}}
# SAE ID: {{SAE_ID}}
# Version: {{PACKAGE_VERSION}}

# Embedded encrypted data
ENCRYPTED_DATA="{{ENCRYPTED_DATA}}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  SAE Package Self-Extractor${NC}"
    echo -e "${BLUE}================================${NC}"
    echo "Package: {{PACKAGE_NAME}}"
    echo "SAE ID: {{SAE_ID}}"
    echo "Version: {{PACKAGE_VERSION}}"
    echo ""
}

# Function to extract package
extract_package() {
    local password="$1"

    print_status "Extracting SAE package..."

    # Create .config directory
    local config_dir=".config"
    mkdir -p "$config_dir"

    # Decrypt and extract data
    print_status "Decrypting package data..."

    if ! echo "$ENCRYPTED_DATA" | base64 -d | \
        openssl enc -aes-256-cbc -d -salt -pbkdf2 \
            -pass "pass:$password" \
            -out "package.tar.gz" 2>/dev/null; then
        print_error "Invalid password or corrupted package"
        rm -f "package.tar.gz"
        return 1
    fi

    # Extract package contents
    print_status "Extracting package contents..."

    if ! tar -xzf package.tar.gz; then
        print_error "Failed to extract package contents"
        return 1
    fi

    # Remove temporary archive
    rm package.tar.gz

    # Set proper permissions for .config directory and files
    print_status "Setting file permissions..."
    chmod 700 .config
    chmod 600 .config/sae_private_key.pem
    chmod 644 .config/sae_certificate.pem
    chmod 644 .config/kme_ca_certificate.pem
    chmod 644 .config/sae_package.json
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
        return 1
    fi

    print_status "Package installed successfully!"
    echo ""
    echo "Files installed:"
    echo "Current directory:"
    ls -la *.sh *.py *.md 2>/dev/null || echo "  (no files)"
    echo ""
    echo ".config directory:"
    ls -la .config/

    echo ""
    print_status "Next steps:"
    echo "1. Review SECURITY_README.md"
    echo "2. Test connection: ./test_connection.sh"
    echo "3. Use client: python client_example.py (automatically activates venv)"

    return 0
}

# Function to show help
show_help() {
    echo "Usage: $0 [password]"
    echo ""
    echo "Options:"
    echo "  password    Password to decrypt package (if not provided, will prompt)"
    echo "  --help      Show this help message"
    echo ""
    echo "The package will be extracted to the current directory with:"
    echo "- Python virtual environment (venv/)"
    echo "- Dependencies installed from requirements.txt"
    echo "- Configuration files in .config/"
    echo "- Executable scripts with proper permissions"
}

# Main execution
main() {
    print_header

    # Check for help
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        show_help
        exit 0
    fi

    # Check if openssl is available
    if ! command -v openssl &> /dev/null; then
        print_error "OpenSSL is required but not installed"
        exit 1
    fi

    # Get password
    local password
    if [[ -n "$1" ]]; then
        password="$1"
    else
        read -s -p "Enter package password: " password
        echo
    fi

    # Extract package
    if extract_package "$password"; then
        print_status "Installation completed successfully!"
        exit 0
    else
        print_error "Installation failed!"
        exit 1
    fi
}

# Run main function
main "$@"
