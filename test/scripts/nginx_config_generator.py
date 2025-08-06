#!/usr/bin/env python3
"""
Nginx Configuration Generator

Generates nginx configuration for KME testing.
"""

import sys
from pathlib import Path


def generate_nginx_config(kme_cert: str, kme_key: str, output_path: str = "nginx.conf"):
    """Generate nginx configuration"""

    config_content = f"""
events {{
    worker_connections 1024;
}}

http {{
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    server {{
        listen 443 ssl;
        server_name localhost;

        ssl_certificate {kme_cert};
        ssl_certificate_key {kme_key};

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location / {{
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
    }}
}}
"""

    with open(output_path, "w") as f:
        f.write(config_content)

    print(f"✅ Nginx configuration generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python nginx_config_generator.py <kme_cert> <kme_key> [output_path]"
        )
        sys.exit(1)

    kme_cert = sys.argv[1]
    kme_key = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else "nginx.conf"

    generate_nginx_config(kme_cert, kme_key, output_path)
