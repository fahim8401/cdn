#!/bin/bash

# Nginx configuration generator for Cachenet CDN

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] NGINX: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] NGINX WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] NGINX ERROR: $1${NC}"
}

# Load environment variables
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration directories
NGINX_DIR="./nginx"
SSL_DIR="$NGINX_DIR/ssl"
CONF_FILE="$NGINX_DIR/cachenet.conf"

# Create directories
mkdir -p "$NGINX_DIR" "$SSL_DIR"

# Generate main nginx configuration
generate_nginx_config() {
    log "Generating Nginx configuration..."

    cat > "$CONF_FILE" << EOF
# Cachenet CDN - Nginx Configuration
# Generated automatically - modify with caution

# Rate limiting zones
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=admin:10m rate=5r/s;
limit_req_zone \$binary_remote_addr zone=client:10m rate=20r/s;

# SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# Gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_proxied any;
gzip_comp_level 6;
gzip_types
    text/plain
    text/css
    text/xml
    text/javascript
    application/json
    application/javascript
    application/xml+rss
    application/atom+xml
    image/svg+xml;

# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

EOF

    # Add CDN domain configuration
    if [[ -n "$CDN_DOMAIN" ]]; then
        cat >> "$CONF_FILE" << EOF
# CDN Domain - Content Delivery
server {
    listen 80;
    server_name ${CDN_DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${CDN_DOMAIN};

    ssl_certificate /etc/nginx/ssl/${CDN_DOMAIN}.pem;
    ssl_certificate_key /etc/nginx/ssl/${CDN_DOMAIN}.key;

    # CDN-specific configuration
    location / {
        # Caching headers
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Cache-Status "HIT";
        
        # Try to serve cached content, fallback to origin
        try_files \$uri @origin;
    }
    
    location @origin {
        # Proxy to backend origin servers
        proxy_pass http://api:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Enable caching
        proxy_cache_valid 200 1h;
        proxy_cache_valid 404 1m;
        add_header X-Cache-Status "MISS";
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}

EOF
    fi

    # Add API domain configuration
    if [[ -n "$API_DOMAIN" ]]; then
        cat >> "$CONF_FILE" << EOF
# API Domain - Management API
server {
    listen 80;
    server_name ${API_DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${API_DOMAIN};

    ssl_certificate /etc/nginx/ssl/${API_DOMAIN}.pem;
    ssl_certificate_key /etc/nginx/ssl/${API_DOMAIN}.key;

    # Rate limiting for API
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://api:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # API-specific headers
        proxy_set_header Accept-Encoding "";
        proxy_buffering off;
        
        # CORS headers
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always;
        add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always;
        
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type 'text/plain; charset=utf-8';
            add_header Content-Length 0;
            return 204;
        }
    }
}

EOF
    fi

    # Add Admin domain configuration
    if [[ -n "$ADMIN_DOMAIN" ]]; then
        cat >> "$CONF_FILE" << EOF
# Admin Domain - Administration Dashboard
server {
    listen 80;
    server_name ${ADMIN_DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${ADMIN_DOMAIN};

    ssl_certificate /etc/nginx/ssl/${ADMIN_DOMAIN}.pem;
    ssl_certificate_key /etc/nginx/ssl/${ADMIN_DOMAIN}.key;

    # Rate limiting for admin
    limit_req zone=admin burst=10 nodelay;

    location / {
        proxy_pass http://admin:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support for development
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

EOF
    fi

    # Add Client domain configuration
    if [[ -n "$CLIENT_DOMAIN" ]]; then
        cat >> "$CONF_FILE" << EOF
# Client Domain - Client Dashboard
server {
    listen 80;
    server_name ${CLIENT_DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${CLIENT_DOMAIN};

    ssl_certificate /etc/nginx/ssl/${CLIENT_DOMAIN}.pem;
    ssl_certificate_key /etc/nginx/ssl/${CLIENT_DOMAIN}.key;

    # Rate limiting for client dashboard
    limit_req zone=client burst=30 nodelay;

    location / {
        proxy_pass http://client:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support for development
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

EOF
    fi

    # Add default server block
    cat >> "$CONF_FILE" << EOF
# Default server - catch all undefined domains
server {
    listen 80 default_server;
    listen 443 ssl http2 default_server;
    server_name _;

    # Self-signed certificate for default server
    ssl_certificate /etc/nginx/ssl/default.pem;
    ssl_certificate_key /etc/nginx/ssl/default.key;

    return 444;
}

# Local development server blocks (when not using domains)
server {
    listen 80;
    server_name localhost;

    # Redirect based on port for local development
    location / {
        return 301 http://localhost:3000\$request_uri;
    }
    
    location /api/ {
        proxy_pass http://api:5000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    log "Nginx configuration generated successfully"
}

# Generate self-signed certificate for default server
generate_default_cert() {
    if [[ ! -f "$SSL_DIR/default.pem" ]]; then
        log "Generating default self-signed certificate..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$SSL_DIR/default.key" \
            -out "$SSL_DIR/default.pem" \
            -subj "/C=US/ST=Default/L=Default/O=Cachenet/CN=default.local"
        
        chmod 644 "$SSL_DIR/default.pem"
        chmod 600 "$SSL_DIR/default.key"
        log "Default certificate generated"
    fi
}

# Test nginx configuration
test_config() {
    log "Testing Nginx configuration..."
    if docker-compose exec nginx nginx -t 2>/dev/null; then
        log "Nginx configuration is valid"
        return 0
    else
        error "Nginx configuration has errors"
        return 1
    fi
}

# Reload nginx configuration
reload_nginx() {
    log "Reloading Nginx..."
    if docker-compose exec nginx nginx -s reload 2>/dev/null; then
        log "Nginx reloaded successfully"
    else
        warn "Failed to reload Nginx, container might not be running"
    fi
}

# Main function
case "${1:-generate}" in
    "generate")
        generate_nginx_config
        generate_default_cert
        ;;
    "test")
        test_config
        ;;
    "reload")
        reload_nginx
        ;;
    "all")
        generate_nginx_config
        generate_default_cert
        if test_config; then
            reload_nginx
        fi
        ;;
    *)
        echo "Usage: $0 {generate|test|reload|all}"
        echo ""
        echo "Commands:"
        echo "  generate - Generate Nginx configuration"
        echo "  test     - Test Nginx configuration"
        echo "  reload   - Reload Nginx configuration"
        echo "  all      - Generate, test, and reload"
        exit 1
        ;;
esac

log "Nginx configuration setup completed"