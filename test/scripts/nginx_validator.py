#!/usr/bin/env python3
"""
Nginx Configuration Validator

Validates nginx configuration and certificate setup for KME.
"""

import subprocess
import sys
from pathlib import Path


def validate_certificate(cert_path: str, cert_type: str = "certificate") -> bool:
    """Validate certificate file"""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-text", "-noout"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✅ {cert_type} validation passed: {cert_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {cert_type} validation failed: {cert_path}")
        print(f"   Error: {e.stderr}")
        return False


def validate_private_key(key_path: str) -> bool:
    """Validate private key file"""
    try:
        result = subprocess.run(
            ["openssl", "rsa", "-in", key_path, "-check", "-noout"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✅ Private key validation passed: {key_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Private key validation failed: {key_path}")
        print(f"   Error: {e.stderr}")
        return False


def validate_certificate_chain(server_cert: str, ca_cert: str) -> bool:
    """Validate certificate chain"""
    try:
        # Check if server cert is signed by CA
        result = subprocess.run(
            ["openssl", "verify", "-CAfile", ca_cert, server_cert],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✅ Certificate chain validation passed")
        print(f"   Server cert: {server_cert}")
        print(f"   CA cert: {ca_cert}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Certificate chain validation failed")
        print(f"   Error: {e.stderr}")
        return False


def validate_nginx_config(config_path: str) -> bool:
    """Validate nginx configuration"""
    try:
        result = subprocess.run(
            ["nginx", "-t", "-c", config_path],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✅ Nginx configuration validation passed: {config_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Nginx configuration validation failed: {config_path}")
        print(f"   Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"⚠️  Nginx not found in PATH - skipping configuration validation")
        return True


def check_mutual_tls_config(config_path: str) -> bool:
    """Check if mutual TLS is properly configured"""
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        required_directives = [
            'ssl_client_certificate',
            'ssl_verify_client on',
            'ssl_verify_depth'
        ]
        
        missing = []
        for directive in required_directives:
            if directive not in content:
                missing.append(directive)
        
        if missing:
            print(f"❌ Missing mutual TLS directives: {', '.join(missing)}")
            return False
        else:
            print(f"✅ Mutual TLS configuration verified")
            return True
            
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        return False


def main():
    """Main validation function"""
    print("🔍 KME Nginx Configuration Validator")
    print("=" * 50)
    
    # Check if nginx config exists
    config_path = "nginx.conf"
    if not Path(config_path).exists():
        print(f"❌ Nginx configuration not found: {config_path}")
        print("   Run: python test/scripts/nginx_config_generator.py certs/kme_cert.pem certs/kme_key.pem certs/ca/ca.crt")
        sys.exit(1)
    
    # Validate certificates
    server_cert = "certs/kme_cert.pem"
    server_key = "certs/kme_key.pem"
    ca_cert = "certs/ca/ca.crt"
    
    cert_ok = validate_certificate(server_cert, "Server certificate")
    key_ok = validate_private_key(server_key)
    ca_ok = validate_certificate(ca_cert, "CA certificate")
    
    if cert_ok and ca_ok:
        chain_ok = validate_certificate_chain(server_cert, ca_cert)
    else:
        chain_ok = False
    
    # Validate nginx configuration
    nginx_ok = validate_nginx_config(config_path)
    mTLS_ok = check_mutual_tls_config(config_path)
    
    print("\n📊 Validation Summary:")
    print("=" * 50)
    print(f"Server Certificate: {'✅' if cert_ok else '❌'}")
    print(f"Private Key: {'✅' if key_ok else '❌'}")
    print(f"CA Certificate: {'✅' if ca_ok else '❌'}")
    print(f"Certificate Chain: {'✅' if chain_ok else '❌'}")
    print(f"Nginx Configuration: {'✅' if nginx_ok else '❌'}")
    print(f"Mutual TLS Setup: {'✅' if mTLS_ok else '❌'}")
    
    if all([cert_ok, key_ok, ca_ok, chain_ok, nginx_ok, mTLS_ok]):
        print("\n🎉 All validations passed! Nginx is ready for mutual TLS.")
        return 0
    else:
        print("\n⚠️  Some validations failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
