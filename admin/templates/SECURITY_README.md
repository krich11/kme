# ⚠️ SECURITY WARNINGS ⚠️

## Critical Security Items

### 1. sae_private_key.pem - CRITICAL SECURITY
- This is your SAE's private key
- Keep it secure and restrict access
- File permissions should be 600 (owner read/write only)
- Never share this file
- Never transmit over insecure channels
- Store in secure location with limited access

### 2. sae_certificate.pem - HIGH SECURITY
- Your SAE's public certificate
- Protect from tampering
- File permissions should be 644
- Verify certificate integrity regularly
- Monitor for unauthorized changes

## Operational Security Items

### 3. SAE ID - MEDIUM SECURITY
- Your unique SAE identifier
- Treat as operational security
- Don't share unnecessarily
- Monitor for unauthorized usage
- Report suspicious activity

### 4. KME Endpoint - MEDIUM SECURITY
- KME server address
- May be internal-only
- Don't expose unnecessarily
- Use secure network connections
- Monitor for unauthorized access

## Installation Security

### File Permissions
The installation script automatically sets proper permissions:
- Private key: 600 (owner read/write only)
- Certificate: 644 (owner read/write, others read)
- Scripts: 755 (executable)
- Config: 644 (readable)

### Network Security
- Use HTTPS for all communications
- Verify SSL certificates
- Use secure network connections
- Monitor for unauthorized access

### Access Control
- Limit access to SAE files
- Use principle of least privilege
- Monitor file access
- Log security events

## Emergency Procedures
If you suspect compromise:
1. Immediately revoke SAE access
2. Generate new certificates
3. Update KME registration
4. Monitor for unauthorized activity
5. Report incident to administrator

## Contact Information
For security incidents or questions:
- KME Administrator: [Contact Information]
- Security Team: [Contact Information]
- Emergency: [Emergency Contact]
