# KME Test Environment Installer

## Overview

The KME Test Environment Installer automates the setup of all infrastructure needed for comprehensive KME testing. This installer consolidates all the tools and scripts we've had to build from scratch during the testing process.

## What It Installs

### 1. CA and Certificate Tools
- **CA Generation Script** (`generate_ca.py`): Creates CA certificates and KME certificates from scratch
- **Certificate Validator** (`certificate_validator.py`): Validates certificate structure and chains
- **Test CA Generation**: Verifies CA generation works correctly

### 2. Database Tools
- **Database Setup Script** (`database_setup.py`): Sets up PostgreSQL database for KME testing
- **Database Validator** (`database_validator.py`): Tests database connectivity and schema
- **Database Connection Test**: Verifies database connection with proper credentials

### 3. Nginx Tools
- **Nginx Configuration Generator** (`nginx_config_generator.py`): Creates nginx config with KME certificates
- **Nginx Validator** (`nginx_validator.py`): Validates nginx configuration syntax
- **SSL/TLS Configuration**: Sets up proper SSL/TLS for KME service

### 4. Test Utilities
- **Test Runner** (`test_runner.py`): Runs KME test stages in sequence
- **Environment Validator** (`environment_validator.py`): Validates test environment setup
- **Report Generator** (`report_generator.py`): Generates HTML and JSON test reports

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (with user: krich, password: mustang)
- OpenSSL
- nginx (optional, for full testing)

### Quick Installation
```bash
# Install all components
python test/scripts/installer.py all

# Or install individual components
python test/scripts/installer.py ca          # CA and certificate tools
python test/scripts/installer.py database    # Database setup and configuration
python test/scripts/installer.py nginx       # Nginx configuration
python test/scripts/installer.py utils       # Test utilities
python test/scripts/installer.py validate    # Environment validation
```

## Usage

### 1. Environment Setup
```bash
# Validate environment
python test/scripts/environment_validator.py

# Set up database
python test/scripts/database_setup.py setup

# Reset database to clean state
python test/scripts/database_setup.py reset
```

### 2. Certificate Management
```bash
# Generate CA
python test/scripts/generate_ca.py ca

# Generate KME certificate
python test/scripts/generate_ca.py kme

# Validate certificates
python test/scripts/certificate_validator.py certs/kme_cert.pem certs/ca/ca.crt
```

### 3. Nginx Configuration
```bash
# Generate nginx config
python test/scripts/nginx_config_generator.py certs/kme_cert.pem certs/kme_key.pem

# Validate nginx config
python test/scripts/nginx_validator.py nginx.conf
```

### 4. Running Tests
```bash
# Run all test stages
python test/scripts/test_runner.py

# Generate reports
python test/scripts/report_generator.py test/results/test_result_20250806_185200.json
```

## Directory Structure

After installation, the following structure is created:

```
test/
├── scripts/
│   ├── installer.py                    # Main installer
│   ├── generate_ca.py                  # CA generation
│   ├── certificate_validator.py        # Certificate validation
│   ├── database_setup.py               # Database setup
│   ├── database_validator.py           # Database validation
│   ├── nginx_config_generator.py       # Nginx config generation
│   ├── nginx_validator.py              # Nginx validation
│   ├── test_runner.py                  # Test execution
│   ├── environment_validator.py        # Environment validation
│   └── report_generator.py             # Report generation
├── data/                               # Test data
├── logs/                               # Installation and test logs
├── results/                            # Test results
└── README_INSTALLER.md                 # This file
```

## Configuration

### Database Configuration
The installer uses the following database configuration:
- Host: localhost
- Port: 5432
- User: krich
- Password: mustang
- Database: kme_db

### Certificate Configuration
- CA Certificate: `certs/ca/ca.crt`
- CA Private Key: `certs/ca/ca.key`
- KME Certificate: `certs/kme_cert.pem`
- KME Private Key: `certs/kme_key.pem`

## Testing Workflow

1. **Install Environment**: Run `python test/scripts/installer.py all`
2. **Validate Setup**: Run `python test/scripts/environment_validator.py`
3. **Reset Environment**: Run `python test/scripts/stage_0_1_reset.py`
4. **Run Tests**: Execute test stages in sequence
5. **Generate Reports**: Create HTML and JSON reports

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify PostgreSQL is running
   - Check credentials in `.test_credentials`
   - Ensure database exists

2. **Certificate Generation Failed**
   - Verify OpenSSL is installed
   - Check file permissions
   - Ensure directories exist

3. **Nginx Configuration Failed**
   - Verify nginx is installed
   - Check certificate paths
   - Validate SSL configuration

### Logs
Installation logs are saved to `test/logs/install_log_YYYYMMDD_HHMMSS.txt`

## Security Notes

- Database credentials are stored in `.test_credentials` (gitignored)
- Certificate private keys have restricted permissions
- Test environment uses separate database from production

## Future Enhancements

- Docker containerization
- Automated dependency installation
- Configuration management
- Integration with CI/CD pipelines
- Performance testing tools
- Security scanning integration
