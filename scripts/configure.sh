#!/bin/bash

# Configuration wizard for Cachenet CDN Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration file path
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Helper functions
log() {
    echo -e "${GREEN}[CONFIG] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[CONFIG] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[CONFIG] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[CONFIG] $1${NC}"
}

generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

generate_secret() {
    openssl rand -hex 32
}

prompt_input() {
    local prompt="$1"
    local default="$2"
    local secret="$3"
    local value=""
    
    if [[ "$secret" == "true" ]]; then
        echo -n -e "${CYAN}$prompt${NC}"
        if [[ -n "$default" ]]; then
            echo -e " ${YELLOW}[press Enter for auto-generated]${NC}"
        fi
        read -s value
        echo
    else
        echo -n -e "${CYAN}$prompt${NC}"
        if [[ -n "$default" ]]; then
            echo -e " ${YELLOW}[default: $default]${NC}"
        fi
        read value
    fi
    
    if [[ -z "$value" ]]; then
        echo "$default"
    else
        echo "$value"
    fi
}

# Display banner
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Cachenet CDN Platform                     ║${NC}"
echo -e "${BLUE}║                   Configuration Wizard                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

info "This wizard will help you configure your Cachenet CDN platform."
info "You can modify any values later by editing the .env file."
echo ""

# Check if .env already exists
if [[ -f "$ENV_FILE" ]]; then
    warn ".env file already exists!"
    echo -n -e "${YELLOW}Do you want to recreate it? This will backup the existing file. (y/N): ${NC}"
    read recreate
    if [[ "$recreate" =~ ^[Yy]$ ]]; then
        mv "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        log "Existing .env backed up"
    else
        log "Using existing .env file. Exiting configuration wizard."
        exit 0
    fi
fi

# Copy example file as base
if [[ -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    log "Created .env file from template"
else
    error ".env.example template not found!"
    exit 1
fi

echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}                    DOMAIN CONFIGURATION                       ${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

info "Enter your domain names. These are REQUIRED for the CDN to function."
echo ""

CDN_DOMAIN=$(prompt_input "CDN Domain (where content will be served from): " "cdn.yourdomain.com")
API_DOMAIN=$(prompt_input "API Domain (for management API): " "api.yourdomain.com")
ADMIN_DOMAIN=$(prompt_input "Admin Dashboard Domain: " "admin.yourdomain.com")
CLIENT_DOMAIN=$(prompt_input "Client Dashboard Domain: " "client.yourdomain.com")

# Set default email based on CDN domain if provided
if [[ -n "$CDN_DOMAIN" && "$CDN_DOMAIN" != "cdn.yourdomain.com" ]]; then
    DEFAULT_EMAIL="admin@${CDN_DOMAIN}"
else
    DEFAULT_EMAIL="admin@yourdomain.com"
fi

echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}                   ADMIN USER CONFIGURATION                    ${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

ADMIN_EMAIL=$(prompt_input "Admin Email Address: " "$DEFAULT_EMAIL")
ADMIN_PASSWORD=$(prompt_input "Admin Password: " "$(generate_password)" "true")
ADMIN_FIRST_NAME=$(prompt_input "Admin First Name: " "Administrator")
ADMIN_LAST_NAME=$(prompt_input "Admin Last Name: " "User")

echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}                  DATABASE CONFIGURATION                      ${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

POSTGRES_PASSWORD=$(prompt_input "Database Password: " "$(generate_password)" "true")

echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}                  SECURITY CONFIGURATION                      ${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

info "Generating secure keys..."
JWT_SECRET_KEY=$(generate_secret)
SECRET_KEY=$(generate_secret)
PDNS_API_KEY=$(generate_secret)
MINIO_ROOT_PASSWORD=$(generate_password)
GRAFANA_ADMIN_PASSWORD=$(generate_password)

log "✓ JWT Secret Key generated"
log "✓ Flask Secret Key generated"
log "✓ PowerDNS API Key generated"
log "✓ MinIO password generated"
log "✓ Grafana admin password generated"

echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}                OPTIONAL: SSL CONFIGURATION                   ${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

info "SSL certificates can be automatically managed using ACME (Let's Encrypt)"
ACME_EMAIL=$(prompt_input "Email for SSL certificates: " "$ADMIN_EMAIL")

echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}            OPTIONAL: CLOUD PROVIDER CONFIGURATION            ${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

info "Cloud provider API keys are needed for automatic edge server provisioning."
info "You can skip these and add them later. Press Enter to skip any provider."
echo ""

DIGITALOCEAN_API_TOKEN=$(prompt_input "DigitalOcean API Token: " "" "true")
LINODE_API_TOKEN=$(prompt_input "Linode API Token: " "" "true")
VULTR_API_KEY=$(prompt_input "Vultr API Key: " "" "true")
HETZNER_API_TOKEN=$(prompt_input "Hetzner API Token: " "" "true")

echo ""
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}          OPTIONAL: MONITORING CONFIGURATION                  ${NC}"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

info "MaxMind GeoIP database provides geographical insights (optional)."
MAXMIND_LICENSE_KEY=$(prompt_input "MaxMind License Key: " "" "true")
MAXMIND_ACCOUNT_ID=$(prompt_input "MaxMind Account ID: " "")

# Update .env file with collected values
log "Updating configuration file..."

# Validate domains before replacement
if [[ -z "$CDN_DOMAIN" || -z "$API_DOMAIN" || -z "$ADMIN_DOMAIN" || -z "$CLIENT_DOMAIN" ]]; then
    error "Domain configuration incomplete. Please run the wizard again."
    exit 1
fi

# Domain configuration - use safe replacements
if [[ "$CDN_DOMAIN" != "cdn.yourdomain.com" ]]; then
    sed -i "s/CHANGE_ME_CDN_DOMAIN/$CDN_DOMAIN/g" "$ENV_FILE"
fi

if [[ "$API_DOMAIN" != "api.yourdomain.com" ]]; then
    sed -i "s/CHANGE_ME_API_DOMAIN/$API_DOMAIN/g" "$ENV_FILE"
fi

if [[ "$ADMIN_DOMAIN" != "admin.yourdomain.com" ]]; then
    sed -i "s/CHANGE_ME_ADMIN_DOMAIN/$ADMIN_DOMAIN/g" "$ENV_FILE"
fi

if [[ "$CLIENT_DOMAIN" != "client.yourdomain.com" ]]; then
    sed -i "s/CHANGE_ME_CLIENT_DOMAIN/$CLIENT_DOMAIN/g" "$ENV_FILE"
fi

# Admin user configuration
sed -i "s|admin@yourdomain.com|$ADMIN_EMAIL|g" "$ENV_FILE"
sed -i "s/CHANGE_ME_ADMIN_PASSWORD/$ADMIN_PASSWORD/g" "$ENV_FILE"
sed -i "s/Administrator/$ADMIN_FIRST_NAME/g" "$ENV_FILE"
sed -i "s/User/$ADMIN_LAST_NAME/g" "$ENV_FILE"

# Security configuration
sed -i "s/CHANGE_ME_DB_PASSWORD/$POSTGRES_PASSWORD/g" "$ENV_FILE"
sed -i "s/CHANGE_ME_JWT_SECRET/$JWT_SECRET_KEY/g" "$ENV_FILE"
sed -i "s/CHANGE_ME_FLASK_SECRET/$SECRET_KEY/g" "$ENV_FILE"
sed -i "s/CHANGE_ME_PDNS_API_KEY/$PDNS_API_KEY/g" "$ENV_FILE"
sed -i "s/CHANGE_ME_MINIO_PASSWORD/$MINIO_ROOT_PASSWORD/g" "$ENV_FILE"
sed -i "s/CHANGE_ME_GRAFANA_PASSWORD/$GRAFANA_ADMIN_PASSWORD/g" "$ENV_FILE"

# SSL configuration
sed -i "s|admin@yourdomain.com|$ACME_EMAIL|g" "$ENV_FILE"

# Cloud providers (only if provided)
if [[ -n "$DIGITALOCEAN_API_TOKEN" ]]; then
    sed -i "s/CHANGE_ME_DO_TOKEN/$DIGITALOCEAN_API_TOKEN/g" "$ENV_FILE"
fi

if [[ -n "$LINODE_API_TOKEN" ]]; then
    sed -i "s/CHANGE_ME_LINODE_TOKEN/$LINODE_API_TOKEN/g" "$ENV_FILE"
fi

if [[ -n "$VULTR_API_KEY" ]]; then
    sed -i "s/CHANGE_ME_VULTR_KEY/$VULTR_API_KEY/g" "$ENV_FILE"
fi

if [[ -n "$HETZNER_API_TOKEN" ]]; then
    sed -i "s/CHANGE_ME_HETZNER_TOKEN/$HETZNER_API_TOKEN/g" "$ENV_FILE"
fi

if [[ -n "$MAXMIND_LICENSE_KEY" ]]; then
    sed -i "s/CHANGE_ME_MAXMIND_KEY/$MAXMIND_LICENSE_KEY/g" "$ENV_FILE"
fi

if [[ -n "$MAXMIND_ACCOUNT_ID" ]]; then
    sed -i "s/CHANGE_ME_MAXMIND_ID/$MAXMIND_ACCOUNT_ID/g" "$ENV_FILE"
fi

# Update CORS origins - use | as delimiter to avoid issues with forward slashes
if [[ "$ADMIN_DOMAIN" != "admin.yourdomain.com" && "$CLIENT_DOMAIN" != "client.yourdomain.com" ]]; then
    sed -i "s|https://CHANGE_ME_ADMIN_DOMAIN,https://CHANGE_ME_CLIENT_DOMAIN|https://$ADMIN_DOMAIN,https://$CLIENT_DOMAIN|g" "$ENV_FILE"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                 Configuration Complete!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

log "Configuration saved to .env file"
echo ""
echo -e "${CYAN}📋 Configuration Summary:${NC}"
echo -e "   CDN Domain:      ${BLUE}$CDN_DOMAIN${NC}"
echo -e "   API Domain:      ${BLUE}$API_DOMAIN${NC}"
echo -e "   Admin Domain:    ${BLUE}$ADMIN_DOMAIN${NC}"
echo -e "   Client Domain:   ${BLUE}$CLIENT_DOMAIN${NC}"
echo -e "   Admin Email:     ${BLUE}$ADMIN_EMAIL${NC}"
echo -e "   Grafana Password: ${BLUE}$GRAFANA_ADMIN_PASSWORD${NC}"
echo ""

info "IMPORTANT: Save the Grafana admin password above!"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Run: ${GREEN}./install.sh${NC} to start the installation"
echo "2. Configure DNS records to point your domains to this server"
echo "3. Access the admin dashboard at: ${BLUE}https://$ADMIN_DOMAIN${NC}"
echo ""

# Offer to start installation immediately
echo -n -e "${CYAN}Do you want to start the installation now? (Y/n): ${NC}"
read start_install
if [[ ! "$start_install" =~ ^[Nn]$ ]]; then
    echo ""
    log "Starting installation..."
    exec ./install.sh
fi

echo ""
log "Configuration wizard completed. Run './install.sh' when ready to install."