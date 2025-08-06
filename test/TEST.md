# KME End-to-End Testing Plan

## Overview
This document outlines the comprehensive testing strategy for the KME (Key Management Entity) service implementing ETSI GS QKD 014 V1.1.1 specifications. The testing approach focuses on real end-to-end validation without mocks, ensuring complete system functionality.

## Testing Philosophy
- **No Mocks**: All tests use real components, real certificates, real database operations
- **Start from Nothing**: Each test run begins with a completely clean environment
- **Build Everything**: CA, certificates, configurations built from scratch
- **Validate Incrementally**: Each stage must pass 100% before proceeding
- **Complete Cleanup**: Ability to reset to clean state after testing

## Test Environment Structure
```
test/
├── archive/           # Previous test assets (moved here)
├── results/           # Test result reports
├── scripts/           # Test implementation scripts
├── data/              # Test data and configurations
├── logs/              # Test execution logs
└── TEST.md           # This test plan document
```

## Phase 0: Complete Environment Reset & Admin Tool Validation

### Stage 0.1: Complete Environment Reset
**Objective**: Start with completely clean environment, remove all existing artifacts

**Tests**:
- [ ] Remove all existing certificates (sae_certs/, admin/sae_certs/, test_certs/)
- [ ] Remove all configuration files (.env, nginx.conf modifications)
- [ ] Clear all database entries (DROP SCHEMA public CASCADE)
- [ ] Reset nginx configuration to original state
- [ ] Verify no residual files or configurations exist
- [ ] Validate clean slate state

**Validation Criteria**:
- No certificate files exist in any directory
- Database contains only default schema
- Nginx configuration is original
- Environment variables are not set
- All test artifacts removed

### Stage 0.2: Admin Tool Configuration & CA Setup
**Objective**: Build CA from scratch using admin tools, validate all operations

**Tests**:
- [ ] Test admin tool CA generation (`./admin/kme_admin.py generate-ca`)
- [ ] Validate CA certificate structure and validity
- [ ] Test KME certificate generation from CA
- [ ] Validate certificate chain integrity
- [ ] Test nginx configuration with new KME certificate
- [ ] Verify admin tool can read/write all configurations

**Validation Criteria**:
- CA certificate exists and is valid
- KME certificate generated successfully
- Certificate chain validates correctly
- Nginx starts with new certificate
- Admin tool can access all configuration files

### Stage 0.3: Admin Tool SAE Management
**Objective**: Validate SAE certificate generation and registration

**Tests**:
- [ ] Generate SAE certificates using admin tools
- [ ] Validate SAE certificate structure and CA signing
- [ ] Test SAE registration through admin interface
- [ ] Verify SAE registration in database
- [ ] Test SAE certificate revocation
- [ ] Validate admin tool can list/manage all SAEs

**Validation Criteria**:
- SAE certificates generated successfully
- SAE certificates signed by CA
- SAE registration stored in database
- Admin tool can list registered SAEs
- Certificate revocation works correctly

### Stage 0.4: Admin Tool Database Operations
**Objective**: Validate all database operations through admin tools

**Tests**:
- [ ] Test database initialization and schema validation
- [ ] Test admin tool can read/write all database tables
- [ ] Test certificate storage and retrieval
- [ ] Test SAE registration and management
- [ ] Test key storage and retrieval operations
- [ ] Validate database transaction handling

**Validation Criteria**:
- Database schema is correct
- All CRUD operations work
- Transaction rollback works
- Data integrity maintained
- Performance acceptable

## Phase 1: KME Service Testing

### Stage 1.1: KME Configuration Validation
**Objective**: Validate KME service configuration and environment

**Tests**:
- [ ] Verify KME service loads all environment variables correctly
- [ ] Validate KME ID consistency across all components
- [ ] Test database connectivity and schema validation
- [ ] Test certificate loading and validation
- [ ] Validate logging configuration

**Validation Criteria**:
- All environment variables loaded correctly
- KME ID consistent everywhere
- Database connection successful
- Certificates loaded and valid
- Logging working properly

### Stage 1.2: Nginx Proxy Integration
**Objective**: Validate nginx proxy configuration and routing

**Tests**:
- [ ] Test nginx routes requests correctly to KME
- [ ] Validate SSL/TLS configuration
- [ ] Test mutual authentication setup
- [ ] Test proxy error handling
- [ ] Validate request/response headers

**Validation Criteria**:
- Requests routed to KME service
- SSL/TLS working correctly
- Mutual auth configured properly
- Error responses appropriate
- Headers set correctly

## Phase 2: End-to-End Testing

### Stage 2.1: Real Key Operations
**Objective**: Test actual key generation, storage, and retrieval

**Tests**:
- [ ] Test key generation using validated SAE certificates
- [ ] Test key storage in database with encryption
- [ ] Test key retrieval with proper authorization
- [ ] Test key pool management and replenishment
- [ ] Test key lifecycle management (expiration, cleanup)
- [ ] Test multi-SAE scenarios

**Validation Criteria**:
- Keys generated successfully
- Keys stored encrypted in database
- Keys retrieved with proper auth
- Key pool maintains correct levels
- Expired keys cleaned up
- Multi-SAE operations work

### Stage 2.2: ETSI Compliance
**Objective**: Validate ETSI QKD 014 V1.1.1 compliance

**Tests**:
- [ ] Test all ETSI API endpoints with real data
- [ ] Validate request/response format compliance
- [ ] Test error handling and status codes
- [ ] Test rate limiting and security headers
- [ ] Validate key format and encoding

**Validation Criteria**:
- All endpoints respond correctly
- Response format matches ETSI spec
- Error codes appropriate
- Security headers present
- Key format compliant

## Phase 3: Performance & Stress Testing

### Stage 3.1: Load Testing
**Objective**: Test system performance under load

**Tests**:
- [ ] Test concurrent key requests
- [ ] Test database performance under load
- [ ] Monitor memory and CPU usage
- [ ] Test response time under load
- [ ] Validate system stability

**Validation Criteria**:
- System handles concurrent requests
- Database performance acceptable
- Resource usage reasonable
- Response times within limits
- System remains stable

### Stage 3.2: Failure Scenarios
**Objective**: Test system behavior under failure conditions

**Tests**:
- [ ] Test database connection failures
- [ ] Test certificate expiration handling
- [ ] Test service restart and recovery
- [ ] Test network interruption handling
- [ ] Test resource exhaustion scenarios

**Validation Criteria**:
- Graceful failure handling
- Automatic recovery works
- Data integrity maintained
- Service restarts properly
- Error logging appropriate

## Phase 4: Cleanup & Reset

### Stage 4.1: Complete Cleanup
**Objective**: Remove all test artifacts and restore clean state

**Tests**:
- [ ] Remove all generated certificates
- [ ] Clear all database entries
- [ ] Reset all configuration files
- [ ] Restore original nginx configuration
- [ ] Clear all log files

**Validation Criteria**:
- All certificates removed
- Database clean
- Configurations restored
- Nginx original config
- No test artifacts remain

### Stage 4.2: Reset Validation
**Objective**: Verify clean state restoration

**Tests**:
- [ ] Verify no test artifacts remain
- [ ] Confirm fresh start capability
- [ ] Validate admin tools still functional
- [ ] Test system can restart cleanly
- [ ] Validate original functionality

**Validation Criteria**:
- No test files present
- Fresh start possible
- Admin tools work
- System starts clean
- Original functionality intact

## Test Implementation Strategy

### Test Scripts Structure
```
test/scripts/
├── stage_0_1_reset.py          # Complete environment reset
├── stage_0_2_ca_setup.py       # CA and certificate setup
├── stage_0_3_sae_management.py # SAE certificate and registration
├── stage_0_4_database_ops.py   # Database operation validation
├── stage_1_1_kme_config.py     # KME configuration validation
├── stage_1_2_nginx_proxy.py    # Nginx proxy validation
├── stage_2_1_key_operations.py # Real key operations
├── stage_2_2_etsi_compliance.py # ETSI compliance testing
├── stage_3_1_load_testing.py   # Performance testing
├── stage_3_2_failure_testing.py # Failure scenario testing
├── stage_4_1_cleanup.py        # Complete cleanup
├── stage_4_2_reset_validation.py # Reset validation
└── run_all_tests.py            # Complete test suite runner
```

### Test Data Management
- **Real Certificates**: Generate actual certificates using OpenSSL
- **Real Keys**: Generate and store actual cryptographic keys
- **Real Database**: Use actual PostgreSQL database with real data
- **Real Network**: Test through actual nginx proxy

### Test Execution Flow
1. **Pre-test**: Complete environment reset
2. **Stage 0**: Admin tool validation (must pass 100%)
3. **Stage 1**: KME service validation
4. **Stage 2**: End-to-end testing
5. **Stage 3**: Performance and stress testing
6. **Stage 4**: Cleanup and reset validation
7. **Post-test**: Generate test report

## Test Result Reporting

### Report Structure
Each test run generates a timestamped report in `test/results/` with:
- Test execution timestamp
- Stage-by-stage results
- Pass/fail status for each test
- Performance metrics
- Error details and recommendations
- Configuration validation results
- Cleanup verification

### Report Format
- **JSON format** for machine-readable results
- **HTML format** for human-readable reports
- **Log files** for detailed execution traces
- **Screenshots** for visual validation (where applicable)

## Success Criteria

### Overall Success
- All stages pass 100%
- No critical failures
- Performance within acceptable limits
- Clean state restored after testing
- All ETSI compliance requirements met

### Stage Success Criteria
- **Stage 0**: All admin tools functional, certificates valid
- **Stage 1**: KME service operational, nginx proxy working
- **Stage 2**: All key operations successful, ETSI compliance verified
- **Stage 3**: Performance acceptable, failure handling robust
- **Stage 4**: Complete cleanup, reset validation successful

## Risk Mitigation

### Potential Issues
- **Admin tool failures**: Stop testing, fix admin tools first
- **Certificate issues**: Regenerate certificates, validate chain
- **Database problems**: Reset database, validate schema
- **Performance issues**: Optimize configuration, retest
- **Cleanup failures**: Manual cleanup, document issues

### Contingency Plans
- **Rollback procedures**: Restore from backups
- **Manual intervention**: Step-by-step recovery procedures
- **Alternative approaches**: Different testing strategies
- **Documentation**: Detailed issue tracking and resolution

## Maintenance

### Regular Updates
- Update test scripts as system evolves
- Add new test cases for new features
- Update validation criteria as requirements change
- Maintain test data and configurations

### Version Control
- Track test script changes
- Version test data and configurations
- Document test environment changes
- Maintain test history and results

---

**Last Updated**: 2024-08-06
**Version**: 1.0
**Status**: Planning Phase
