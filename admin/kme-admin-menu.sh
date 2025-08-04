#!/bin/bash
# KME Admin Menu Interface
# Interactive SAE Management Interface

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
KME_ADMIN="python -m admin.kme_admin"
PACKAGE_DIR="admin/packages"

# Change to project root directory if running from admin directory
if [[ "$(basename "$PWD")" == "admin" ]]; then
    cd ..
fi

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
    echo -e "${BLUE}  KME SAE Management Interface${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_subheader() {
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..${#1}})${NC}"
}

# Function to register new SAE
register_new_sae() {
    print_subheader "SAE Registration"

    # Collect basic information
    echo "Enter SAE Information:"
    read -p "Human Readable Name: " sae_name

    # Ask if user wants to provide SAE ID or auto-generate
    echo ""
    echo "SAE ID Options:"
    echo "1. Auto-generate SAE ID (recommended)"
    echo "2. Provide custom SAE ID"
    read -p "Select option (1-2): " id_option

    if [[ "$id_option" == "1" ]]; then
        sae_id=""
        print_status "SAE ID will be auto-generated"
    else
        read -p "SAE ID: " sae_id
    fi

    # Ask if user wants to generate certificate or use existing
    echo ""
    echo "Certificate Options:"
    echo "1. Generate new certificate (recommended)"
    echo "2. Use existing certificate"
    read -p "Select option (1-2): " cert_option

    if [[ "$cert_option" == "1" ]]; then
        # Generate new certificate
        print_status "Generating new certificate..."
        read -p "Validity Days [365]: " validity_days
        validity_days=${validity_days:-365}
        read -p "Key Size [2048]: " key_size
        key_size=${key_size:-2048}

        if [[ -n "$sae_id" ]]; then
            output=$($KME_ADMIN sae generate-certificate \
                --sae-id "$sae_id" \
                --name "$sae_name" \
                --validity-days "$validity_days" \
                --key-size "$key_size" 2>&1)
        else
            output=$($KME_ADMIN sae generate-certificate \
                --name "$sae_name" \
                --validity-days "$validity_days" \
                --key-size "$key_size" 2>&1)
        fi

        if [[ $? -eq 0 ]]; then
            # Display the certificate generation output to user
            echo "$output"

            # Get the generated SAE ID from the output or use provided one
            if [[ -z "$sae_id" ]]; then
                # Extract SAE ID from the certificate generation output
                # Look for the "Generated SAE ID:" line in the output
                sae_id=$(echo "$output" | grep "Generated SAE ID:" | sed 's/Generated SAE ID: //')
                if [[ -z "$sae_id" ]]; then
                    print_error "Failed to extract SAE ID from certificate generation output"
                    print_error "Output was: $output"
                    return 1
                fi
            fi
            cert_path="sae_certs/${sae_id}_certificate.pem"
            key_path="sae_certs/${sae_id}_private_key.pem"
            print_status "Certificate generated successfully!"
        else
            print_error "Certificate generation failed"
            echo "$output"
            return 1
        fi
    else
        # Use existing certificate
        read -p "Certificate File Path: " cert_path
        read -p "Private Key File Path: " key_path

        # Validate inputs
        if [[ ! -f "$cert_path" ]]; then
            print_error "Certificate file not found"
            return 1
        fi

        if [[ ! -f "$key_path" ]]; then
            print_error "Private key file not found"
            return 1
        fi
    fi

    # Collect additional information
    read -p "Max Keys Per Request [128]: " max_keys
    max_keys=${max_keys:-128}
    read -p "Max Key Size [1024]: " max_key_size
    max_key_size=${max_key_size:-1024}
    read -p "Description: " description

    # Register SAE
    print_status "Registering SAE..."
    $KME_ADMIN sae register \
        --name "$sae_name" \
        --certificate "$cert_path" \
        --private-key "$key_path" \
        --max-keys "$max_keys" \
        --max-key-size "$max_key_size"

    if [[ $? -eq 0 ]]; then
        print_status "SAE registered successfully"

        # Generate package
        read -p "Generate SAE package? (y/n): " generate_package
        if [[ "$generate_package" == "y" ]]; then
            generate_sae_package "$sae_name" "$sae_id"
        fi
    else
        print_error "SAE registration failed"
        return 1
    fi
}

# Function to list SAEs
list_saes() {
    print_subheader "SAE List"
    $KME_ADMIN sae list
}

# Function to show SAE details
show_sae_details() {
    print_subheader "SAE Details"
    read -p "Enter SAE ID: " sae_id
    $KME_ADMIN sae show "$sae_id"
}

# Function to update SAE status
update_sae_status() {
    print_subheader "Update SAE Status"
    read -p "Enter SAE ID: " sae_id
    echo "Available statuses: active, inactive, suspended, expired"
    read -p "New status: " new_status
    $KME_ADMIN sae update-status "$sae_id" "$new_status"
}

# Function to revoke SAE
revoke_sae() {
    print_subheader "Revoke SAE Access"
    read -p "Enter SAE ID: " sae_id
    read -p "Are you sure you want to revoke access for SAE $sae_id? (y/n): " confirm
    if [[ "$confirm" == "y" ]]; then
        $KME_ADMIN sae revoke "$sae_id"
    else
        print_status "Operation cancelled"
    fi
}

# Function to generate SAE package
generate_sae_package() {
    local sae_name="$1"
    local sae_id="$2"

    print_subheader "Generate SAE Package"

    if [[ -z "$sae_name" ]]; then
        read -p "Enter SAE Name: " sae_name
    fi

    if [[ -z "$sae_id" ]]; then
        read -p "Enter SAE ID: " sae_id
    fi

    # Prompt for package password
    read -s -p "Enter package encryption password: " package_password
    echo
    read -s -p "Confirm password: " confirm_password
    echo

    if [[ "$package_password" != "$confirm_password" ]]; then
        print_error "Passwords do not match"
        return 1
    fi

    # Create package name
    package_name=$(echo "$sae_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    package_file="$PACKAGE_DIR/${package_name}_sae_package.sh"

    # Ensure packages directory exists
    mkdir -p "$PACKAGE_DIR"

    # Generate encrypted package
    print_status "Generating encrypted package..."
    $KME_ADMIN sae generate-package \
        "$sae_id" \
        --password "$package_password" \
        --output "$package_file"

    if [[ $? -eq 0 ]]; then
        print_status "Package generated successfully: $package_file"
        echo ""
        echo "Package details:"
        echo "- File: $package_file"
        echo "- Size: $(du -h "$package_file" | cut -f1)"
        echo "- Permissions: $(ls -la "$package_file" | awk '{print $1}')"
        echo ""
        echo "To install on target system:"
        echo "1. Copy package to target system"
        echo "2. Run: ./${package_name}_sae_package.sh"
        echo "3. Enter password when prompted"
    else
        print_error "Package generation failed"
        return 1
    fi
}

# Function to generate Multi-SAE Test Package
generate_multi_sae_test_package() {
    print_subheader "Generate Multi-SAE Test Package"

    # Prompt for package password
    read -s -p "Enter package encryption password: " package_password
    echo
    read -s -p "Confirm password: " confirm_password
    echo

    if [[ "$package_password" != "$confirm_password" ]]; then
        print_error "Passwords do not match"
        return 1
    fi

    # Create package name
    package_name="multi_sae_test"
    package_file="$PACKAGE_DIR/${package_name}_package.sh"

    # Ensure packages directory exists
    mkdir -p "$PACKAGE_DIR"

    # Generate multi-SAE test package
    print_status "Generating multi-SAE test package..."
    $KME_ADMIN sae generate-multi-sae-package \
        --password "$package_password" \
        --output "$package_file"

    if [[ $? -eq 0 ]]; then
        print_status "Multi-SAE test package generated successfully: $package_file"
        echo ""
        echo "Package details:"
        echo "- File: $package_file"
        echo "- Size: $(du -h "$package_file" | cut -f1)"
        echo "- Permissions: $(ls -la "$package_file" | awk '{print $1}')"
        echo ""
        echo "This package contains:"
        echo "- 4 SAE certificates (1 master + 3 slaves)"
        echo "- Multi-SAE test script"
        echo "- SAE configuration file"
        echo "- Comprehensive ETSI QKD 014 multi-SAE testing"
        echo ""
        echo "To install on target system:"
        echo "1. Copy package to target system"
        echo "2. Run: ./${package_name}_package.sh"
        echo "3. Enter password when prompted"
        echo "4. Run: ./multi_sae_test.sh"
    else
        print_error "Multi-SAE test package generation failed"
        return 1
    fi
}

# Function to generate SAE certificate
generate_sae_certificate() {
    print_subheader "Generate SAE Certificate"

    # Ask if user wants to provide SAE ID or auto-generate
    echo "SAE ID Options:"
    echo "1. Auto-generate SAE ID (recommended)"
    echo "2. Provide custom SAE ID"
    read -p "Select option (1-2): " id_option

    if [[ "$id_option" == "1" ]]; then
        sae_id=""
        print_status "SAE ID will be auto-generated"
    else
        read -p "SAE ID: " sae_id
    fi

    # Ask if user wants to provide SAE name or auto-generate
    echo ""
    echo "SAE Name Options:"
    echo "1. Auto-generate SAE name"
    echo "2. Provide custom SAE name"
    read -p "Select option (1-2): " name_option

    if [[ "$name_option" == "1" ]]; then
        sae_name=""
        print_status "SAE name will be auto-generated"
    else
        read -p "SAE Name: " sae_name
    fi

    read -p "Validity Days [365]: " validity_days
    validity_days=${validity_days:-365}
    read -p "Key Size [2048]: " key_size
    key_size=${key_size:-2048}

    # Generate certificate
    print_status "Generating SAE certificate..."
    if [[ -n "$sae_id" ]]; then
        $KME_ADMIN sae generate-certificate \
            --sae-id "$sae_id" \
            --name "$sae_name" \
            --validity-days "$validity_days" \
            --key-size "$key_size"
    else
        $KME_ADMIN sae generate-certificate \
            --name "$sae_name" \
            --validity-days "$validity_days" \
            --key-size "$key_size"
    fi

    if [[ $? -eq 0 ]]; then
        print_status "Certificate generated successfully!"
    else
        print_error "Certificate generation failed"
        return 1
    fi
}

# Function to list SAE certificates
list_sae_certificates() {
    print_subheader "SAE Certificates"
    $KME_ADMIN sae list-certificates
}

# Function to revoke SAE certificate
revoke_sae_certificate() {
    print_subheader "Revoke SAE Certificate"
    read -p "Enter SAE ID: " sae_id
    read -p "Are you sure you want to revoke the certificate for SAE $sae_id? (y/n): " confirm
    if [[ "$confirm" == "y" ]]; then
        $KME_ADMIN sae revoke-certificate "$sae_id"
    else
        print_status "Operation cancelled"
    fi
}

# Function to launch database manager
launch_database_manager() {
    print_subheader "Database Manager"

    print_status "Launching KME Database Manager..."
    echo ""
    echo "The Database Manager provides:"
    echo "- Database browsing and inspection"
    echo "- Table management (drop, truncate, etc.)"
    echo "- Database reset and recreation"
    echo "- Schema management"
    echo "- Data export capabilities"
    echo ""

    # Check if database manager exists
    if [[ ! -f "admin/database_manager.py" ]]; then
        print_error "Database manager not found: admin/database_manager.py"
        return 1
    fi

    # Launch the database manager
    python admin/database_manager.py

    if [[ $? -eq 0 ]]; then
        print_status "Database manager completed successfully"
    else
        print_error "Database manager encountered an error"
        return 1
    fi
}

# Function to show help
show_help() {
    print_header
    echo ""
    echo "Available commands:"
    echo "1. Register New SAE - Register a new SAE with certificate"
    echo "2. List All SAEs - Show all registered SAEs"
    echo "3. View SAE Details - Show detailed information for a specific SAE"
    echo "4. Update SAE Status - Change SAE status (active, inactive, suspended, expired)"
    echo "5. Revoke SAE Access - Revoke access for a SAE"
    echo "6. Generate SAE Package - Create encrypted package for SAE distribution"
    echo "7. Generate Multi-SAE Test Package - Create package for multi-SAE testing"
    echo "8. Generate SAE Certificate - Create new certificate for SAE"
    echo "9. List SAE Certificates - Show all generated certificates"
    echo "10. Revoke SAE Certificate - Revoke a SAE certificate"
    echo "11. Database Manager - Browse and manage database"
    echo "h. Show Help - Display this help message"
    echo "q. Exit - Exit the admin interface"
    echo ""
    echo "For more detailed help, run: python -m admin.kme_admin --help"
}

# Function to check prerequisites
check_prerequisites() {
    # Check if Python is available
    if ! command -v python &> /dev/null; then
        print_error "Python is required but not installed"
        exit 1
    fi

    # Check if KME admin module exists
    if ! python -c "import admin.kme_admin" 2>/dev/null; then
        print_error "KME admin module not found: admin.kme_admin"
        exit 1
    fi

    # Check if virtual environment is activated
    if [[ -z "$VIRTUAL_ENV" ]]; then
        print_warning "Virtual environment not detected. Some features may not work correctly."
    fi
}

# Main menu loop
main_menu() {
    while true; do
        echo ""
        print_header
        echo "1. Register New SAE"
        echo "2. List All SAEs"
        echo "3. View SAE Details"
        echo "4. Update SAE Status"
        echo "5. Revoke SAE Access"
        echo "6. Generate SAE Package"
        echo "7. Generate Multi-SAE Test Package"
        echo "8. Generate SAE Certificate"
        echo "9. List SAE Certificates"
        echo "10. Revoke SAE Certificate"
        echo "11. Database Manager"
        echo "h. Show Help"
        echo "q. Exit"
        echo "=================================="

        read -p "Select option (1-11, h, q): " choice

        case $choice in
            1) register_new_sae ;;
            2) list_saes ;;
            3) show_sae_details ;;
            4) update_sae_status ;;
            5) revoke_sae ;;
            6) generate_sae_package "" "" ;;
            7) generate_multi_sae_test_package ;;
            8) generate_sae_certificate ;;
            9) list_sae_certificates ;;
            10) revoke_sae_certificate ;;
            11) launch_database_manager ;;
            h|H) show_help ;;
            q|Q) print_status "Goodbye!"; exit 0 ;;
            *) print_error "Invalid option. Please select 1-11, h, or q." ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
    done
}

# Main execution
main() {
    # Check prerequisites
    check_prerequisites

    # Show welcome message
    print_header
    echo "Welcome to the KME SAE Management Interface"
    echo "This tool helps you manage SAE registrations and generate packages."
    echo ""

    # Start main menu
    main_menu
}

# Run main function
main "$@"
