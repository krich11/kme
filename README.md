# KME Project

This repository contains the KME (Key Management Entity) project, implementing the ETSI GS QKD 014 V1.1.1 specification for REST-based key delivery API.

## Project Structure

```
kme/
├── app/                    # Main application package
│   ├── core/              # Core infrastructure modules
│   ├── api/               # REST API endpoints
│   ├── models/            # Data models and schemas
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
├── docs/                  # Documentation
│   ├── phases/            # Phase-specific documentation
│   │   ├── Phase1_Core_Infrastructure.md
│   │   ├── Phase2_REST_API_Implementation.md
│   │   ├── Phase3_Key_Management.md
│   │   ├── Phase4_Security_Extensions.md
│   │   ├── Phase5_Testing_Validation.md
│   │   ├── Phase6_Documentation_Deployment.md
│   │   └── Master_ToDo_Tracker.md
│   ├── KME_Development_Plan.md
│   ├── Functional_Specifications.md
│   ├── Test_Suite_Specification.md
│   └── Programming_Language_Analysis.md
├── test/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── security/          # Security tests
│   ├── performance/       # Performance tests
│   └── test_template.py   # Test template
├── scripts/               # Utility scripts
│   └── script_template.py # Script template
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── env.template          # Environment configuration template
└── .gitignore           # Git ignore rules
```

## Overview

The KME project implements a Key Management Entity that conforms to the ETSI GS QKD 014 V1.1.1 specification. The system provides a REST-based API for secure key delivery between Secure Application Entities (SAEs) in a Quantum Key Distribution (QKD) network.

### Key Features

- **REST API**: Three core endpoints (Get Status, Get Key, Get Key with Key IDs)
- **Security**: Mutual TLS authentication, certificate validation, secure key storage
- **Modular Design**: Eight independent modules for flexible development
- **Compliance**: Full ETSI QKD 014 specification compliance
- **Performance**: High-throughput, low-latency key delivery
- **Testing**: Comprehensive test suite for validation and compliance

### Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI with async support
- **Security**: cryptography, pyOpenSSL
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for high-performance key storage
- **Testing**: pytest with comprehensive test coverage

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- Redis server
- TLS certificates for KME and SAE authentication

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kme
   ```

2. **Set up Python virtual environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp env.template .env
   # Edit .env with your configuration values
   ```

5. **Set up database and Redis**
   - Install PostgreSQL and Redis
   - Create database and configure connection

## Environment Configuration

The KME project uses environment variables for configuration. Copy `env.template` to `.env` and update the values:

### Required Configuration (No Defaults)

These values must be set in your `.env` file:

```bash
# KME Identity (16 characters)
KME_ID=AAAABBBBCCCCDDDD

# Database Connection URL
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/kme_db

# Security Keys (change these in production!)
SECRET_KEY=your-secret-key-here-change-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here-change-this-in-production
```

### Database Setup Variables

For the database setup script to work properly, also configure:

```bash
# Database Setup Script Variables
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
```

### Quick Database Setup

Once configured, set up the database:

```bash
# Create database and schema
python scripts/database_setup.py create

# Test the setup
python test/test_week3.py
```

### Optional Configuration

All other variables in `env.template` have sensible defaults and can be left as-is for development.
   - Update .env with connection details

6. **Set up TLS certificates**
   - Generate or obtain TLS certificates
   - Update certificate paths in .env

7. **Run the application**
   ```bash
   python main.py
   ```

8. **Run tests**
   ```bash
   pytest test/
   ```

### Code Standards

- All Python files include shebang for virtual environment
- Each file has comprehensive header with version tracking and ToDo list
- Environment variables used for all sensitive configuration
- Structured logging with JSON format
- Comprehensive error handling and validation

## Architecture

The KME system is designed with a modular architecture consisting of eight core modules:

1. **Core Infrastructure**: Configuration, logging, security, database management
2. **REST API Server**: Three ETSI-compliant API endpoints
3. **Data Format Handlers**: JSON validation and processing
4. **Key Management System**: Secure key storage and lifecycle management
5. **QKD Network Interface**: Communication with QKD infrastructure
6. **Authentication & Authorization**: SAE authentication and access control
7. **Extension Framework**: Vendor-specific and future extensions
8. **Testing Framework**: Comprehensive validation and compliance testing

## API Endpoints

### Get Status
- **Method**: `GET /api/v1/keys/{slave_SAE_ID}/status`
- **Purpose**: Retrieve KME status and capabilities

### Get Key
- **Method**: `POST /api/v1/keys/{slave_SAE_ID}/enc_keys`
- **Purpose**: Request keys for encryption (Master SAE)

### Get Key with Key IDs
- **Method**: `POST /api/v1/keys/{master_SAE_ID}/dec_keys`
- **Purpose**: Retrieve keys using key IDs (Slave SAE)

## Security

The KME implements comprehensive security measures:

- **Mutual TLS Authentication**: Certificate-based SAE authentication
- **Secure Key Storage**: Encryption at rest with secure key derivation
- **Access Control**: Strict authorization and rate limiting
- **Audit Logging**: Comprehensive security event tracking
- **Input Validation**: Strict validation of all API inputs

## Testing

The project includes a comprehensive test suite:

- **Unit Tests**: Individual module validation
- **Integration Tests**: End-to-end API testing
- **Security Tests**: Authentication and authorization validation
- **Compliance Tests**: ETSI specification compliance
- **Performance Tests**: Throughput and latency validation
- **Interoperability Tests**: Cross-vendor compatibility

## Documentation

### Development Phases
- [Phase 1: Core Infrastructure](docs/phases/Phase1_Core_Infrastructure.md) - Foundation setup
- [Phase 2: REST API Implementation](docs/phases/Phase2_REST_API_Implementation.md) - API endpoints
- [Phase 3: Key Management](docs/phases/Phase3_Key_Management.md) - Key storage and distribution
- [Phase 4: Security and Extensions](docs/phases/Phase4_Security_Extensions.md) - Security hardening
- [Phase 5: Testing and Validation](docs/phases/Phase5_Testing_Validation.md) - Comprehensive testing
- [Phase 6: Documentation and Deployment](docs/phases/Phase6_Documentation_Deployment.md) - Final deployment

### Project Documentation
- [Master ToDo Tracker](docs/phases/Master_ToDo_Tracker.md) - Complete task tracking
- [Development Plan](docs/KME_Development_Plan.md) - Complete development roadmap
- [Functional Specifications](docs/Functional_Specifications.md) - Detailed module specifications
- [Test Suite Specification](docs/Test_Suite_Specification.md) - Comprehensive testing framework
- [Technology Analysis](docs/Programming_Language_Analysis.md) - Technology stack recommendations

## Contributing

Please refer to the project documentation for contribution guidelines. All contributions must maintain ETSI QKD 014 specification compliance and security requirements.

## License

[License information to be added]

## Compliance

This implementation conforms to:
- ETSI GS QKD 014 V1.1.1 specification
- RFC 8259 (JSON)
- RFC 5246/8446 (TLS)
- RFC 4648 (Base64)
- RFC 4122 (UUID)
