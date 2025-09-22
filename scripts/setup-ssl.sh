#!/bin/bash

# SSL Certificate management script for Cachenet CDN

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SSL: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] SSL WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] SSL ERROR: $1${NC}"
}

# Load environment variables
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
ACME_DIR="$HOME/.acme.sh"
CERT_DIR="./ssl-certs"
NGINX_CERT_DIR="./nginx/ssl"

# Create certificate directories
mkdir -p "$CERT_DIR" "$NGINX_CERT_DIR"

# Install ACME.sh if not already installed
install_acme() {
    if [[ ! -d "$ACME_DIR" ]]; then
        log "Installing ACME.sh..."
        curl https://get.acme.sh | sh -s email=${ACME_EMAIL}
        source ~/.bashrc
        
        # Set default CA
        $ACME_DIR/acme.sh --set-default-ca --server letsencrypt
        log "ACME.sh installed successfully"
    else
        log "ACME.sh already installed"
    fi
}

# Configure PowerDNS for ACME challenge
configure_pdns() {
    log "Configuring PowerDNS for ACME challenges..."
    
    # Export PowerDNS configuration for ACME.sh
    export PDNS_Url="${PDNS_API_URL}"
    export PDNS_ServerId="localhost"
    export PDNS_Token="${PDNS_API_KEY}"
    export PDNS_Ttl="60"
    
    # Test PowerDNS API connectivity
    if curl -s -H "X-API-Key: ${PDNS_API_KEY}" "${PDNS_API_URL}/zones" >/dev/null; then
        log "PowerDNS API connection successful"
    else
        error "Cannot connect to PowerDNS API"
        return 1
    fi
}

# Issue SSL certificate for a domain
issue_certificate() {
    local domain="$1"
    local wildcard="$2"
    
    log "Issuing SSL certificate for $domain"
    
    if [[ "$wildcard" == "true" ]]; then
        log "Issuing wildcard certificate for *.$domain"
        $ACME_DIR/acme.sh --issue --dns dns_pdns --dnssleep 120 \
            -d "$domain" -d "*.$domain" \
            --cert-file "$CERT_DIR/$domain.crt" \
            --key-file "$CERT_DIR/$domain.key" \
            --fullchain-file "$CERT_DIR/$domain.pem" \
            --ca-file "$CERT_DIR/$domain.ca.crt"
    else
        log "Issuing single domain certificate for $domain"
        $ACME_DIR/acme.sh --issue --dns dns_pdns --dnssleep 120 \
            -d "$domain" \
            --cert-file "$CERT_DIR/$domain.crt" \
            --key-file "$CERT_DIR/$domain.key" \
            --fullchain-file "$CERT_DIR/$domain.pem" \
            --ca-file "$CERT_DIR/$domain.ca.crt"
    fi
    
    if [[ $? -eq 0 ]]; then
        log "Certificate issued successfully for $domain"
        
        # Copy certificates to nginx directory
        cp "$CERT_DIR/$domain.pem" "$NGINX_CERT_DIR/$domain.pem"
        cp "$CERT_DIR/$domain.key" "$NGINX_CERT_DIR/$domain.key"
        
        # Set proper permissions
        chmod 644 "$NGINX_CERT_DIR/$domain.pem"
        chmod 600 "$NGINX_CERT_DIR/$domain.key"
        
        log "Certificates copied to nginx directory"
        return 0
    else
        error "Failed to issue certificate for $domain"
        return 1
    fi
}

# Setup auto-renewal
setup_auto_renewal() {
    log "Setting up certificate auto-renewal..."
    
    # Create renewal script
    cat > "$CERT_DIR/renew-certificates.sh" << 'EOF'
#!/bin/bash
# Auto-renewal script for SSL certificates

ACME_DIR="$HOME/.acme.sh"
NGINX_CERT_DIR="./nginx/ssl"
CERT_DIR="./ssl-certs"

# Load environment
if [[ -f .env ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Export PowerDNS configuration
export PDNS_Url="${PDNS_API_URL}"
export PDNS_ServerId="localhost"
export PDNS_Token="${PDNS_API_KEY}"
export PDNS_Ttl="60"

# Renew all certificates
$ACME_DIR/acme.sh --cron --home $ACME_DIR

# Copy renewed certificates to nginx
for cert_file in $ACME_DIR/*.*/fullchain.cer; do
    if [[ -f "$cert_file" ]]; then
        domain=$(basename $(dirname "$cert_file"))
        cp "$cert_file" "$NGINX_CERT_DIR/$domain.pem"
        cp "$(dirname "$cert_file")/$domain.key" "$NGINX_CERT_DIR/$domain.key"
        chmod 644 "$NGINX_CERT_DIR/$domain.pem"
        chmod 600 "$NGINX_CERT_DIR/$domain.key"
    fi
done

# Reload nginx to pick up new certificates
docker-compose exec nginx nginx -s reload 2>/dev/null || true

echo "Certificate renewal completed at $(date)"
EOF

    chmod +x "$CERT_DIR/renew-certificates.sh"
    
    # Add to crontab for automatic renewal
    (crontab -l 2>/dev/null; echo "0 2 * * * cd $(pwd) && $CERT_DIR/renew-certificates.sh >> /var/log/ssl-renewal.log 2>&1") | crontab -
    
    log "Auto-renewal configured with daily cron job"
}

# Generate self-signed certificates as fallback
generate_self_signed() {
    local domain="$1"
    
    log "Generating self-signed certificate for $domain"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$NGINX_CERT_DIR/$domain.key" \
        -out "$NGINX_CERT_DIR/$domain.pem" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$domain"
    
    chmod 644 "$NGINX_CERT_DIR/$domain.pem"
    chmod 600 "$NGINX_CERT_DIR/$domain.key"
    
    log "Self-signed certificate generated for $domain"
}

# Main SSL setup function
setup_ssl() {
    log "Starting SSL certificate setup..."
    
    # Install ACME.sh
    install_acme
    
    # Configure PowerDNS
    if ! configure_pdns; then
        warn "PowerDNS configuration failed, will use self-signed certificates"
        USE_SELF_SIGNED=true
    fi
    
    # List of domains to secure
    domains=()
    [[ -n "$CDN_DOMAIN" ]] && domains+=("$CDN_DOMAIN")
    [[ -n "$API_DOMAIN" ]] && domains+=("$API_DOMAIN")
    [[ -n "$ADMIN_DOMAIN" ]] && domains+=("$ADMIN_DOMAIN")
    [[ -n "$CLIENT_DOMAIN" ]] && domains+=("$CLIENT_DOMAIN")
    
    # Issue certificates for each domain
    for domain in "${domains[@]}"; do
        if [[ "$USE_SELF_SIGNED" == "true" ]]; then
            generate_self_signed "$domain"
        else
            if ! issue_certificate "$domain" "false"; then
                warn "Failed to issue certificate for $domain, using self-signed"
                generate_self_signed "$domain"
            fi
        fi
    done
    
    # Setup auto-renewal if using ACME
    if [[ "$USE_SELF_SIGNED" != "true" ]]; then
        setup_auto_renewal
    fi
    
    log "SSL certificate setup completed"
}

# Command line interface
case "${1:-setup}" in
    "setup")
        setup_ssl
        ;;
    "issue")
        if [[ -z "$2" ]]; then
            error "Usage: $0 issue <domain> [wildcard]"
            exit 1
        fi
        configure_pdns
        issue_certificate "$2" "${3:-false}"
        ;;
    "renew")
        configure_pdns
        $ACME_DIR/acme.sh --cron --home $ACME_DIR
        ;;
    "self-signed")
        if [[ -z "$2" ]]; then
            error "Usage: $0 self-signed <domain>"
            exit 1
        fi
        generate_self_signed "$2"
        ;;
    *)
        echo "Usage: $0 {setup|issue|renew|self-signed} [options]"
        echo ""
        echo "Commands:"
        echo "  setup                 - Complete SSL setup for all configured domains"
        echo "  issue <domain> [wild] - Issue certificate for specific domain"
        echo "  renew                 - Renew all certificates"
        echo "  self-signed <domain>  - Generate self-signed certificate"
        exit 1
        ;;
esac