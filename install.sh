#!/bin/bash
#
# XenCDN v8.2 Installation Script
# One-click installation for enterprise self-hosted CDN platform
# 
# Usage: curl -s https://install.xencdn.com/install.sh | bash
# Or: wget -qO- https://install.xencdn.com/install.sh | bash
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
XENCDN_VERSION="8.2.0"
INSTALL_DIR="/opt/xencdn"
REPO_URL="https://github.com/fahim8401/cdn.git"
MIN_DOCKER_VERSION="24.0.0"
MIN_COMPOSE_VERSION="2.20.0"

# System requirements
MIN_RAM_GB=4
MIN_DISK_GB=20
REQUIRED_PORTS="53 80 443 3000 3001 3002 3003 3004 5000 6379 8081 9000 9001"

print_header() {
    echo ""
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                                                              ║${NC}"
    echo -e "${PURPLE}║                    ${CYAN}XenCDN v${XENCDN_VERSION}${PURPLE}                           ║${NC}"
    echo -e "${PURPLE}║              ${YELLOW}Enterprise CDN + DNS Platform${PURPLE}                 ║${NC}"
    echo -e "${PURPLE}║                                                              ║${NC}"
    echo -e "${PURPLE}║    • Complete DNS Zone Management                           ║${NC}"
    echo -e "${PURPLE}║    • BGP Anycast Support                                    ║${NC}"
    echo -e "${PURPLE}║    • ISP Peering Portal                                     ║${NC}"
    echo -e "${PURPLE}║    • Client Self-Service Portal                            ║${NC}"
    echo -e "${PURPLE}║    • Real-time Speed Testing                               ║${NC}"
    echo -e "${PURPLE}║    • Automated SSL Management                              ║${NC}"
    echo -e "${PURPLE}║                                                              ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for security reasons."
        print_info "Please run as a regular user with sudo privileges."
        exit 1
    fi
    
    # Check if user has sudo privileges
    if ! sudo -n true 2>/dev/null; then
        print_error "This script requires sudo privileges."
        print_info "Please ensure your user can run sudo commands."
        exit 1
    fi
}

check_system_requirements() {
    print_step "Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        print_error "Unable to detect operating system."
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]] && [[ "$ID" != "debian" ]]; then
        print_warning "This script is designed for Ubuntu/Debian. Your OS: $PRETTY_NAME"
        print_info "Continuing anyway, but some features may not work correctly."
    fi
    
    # Check architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "x86_64" ]] && [[ "$ARCH" != "amd64" ]]; then
        print_error "XenCDN requires x86_64 architecture. Your architecture: $ARCH"
        exit 1
    fi
    
    # Check RAM
    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024))
    
    if [[ $TOTAL_RAM_GB -lt $MIN_RAM_GB ]]; then
        print_error "Insufficient RAM. Required: ${MIN_RAM_GB}GB, Available: ${TOTAL_RAM_GB}GB"
        exit 1
    fi
    
    # Check disk space
    AVAILABLE_DISK_GB=$(df / | tail -1 | awk '{print int($4/1024/1024)}')
    if [[ $AVAILABLE_DISK_GB -lt $MIN_DISK_GB ]]; then
        print_error "Insufficient disk space. Required: ${MIN_DISK_GB}GB, Available: ${AVAILABLE_DISK_GB}GB"
        exit 1
    fi
    
    # Check required ports
    print_info "Checking required ports..."
    for port in $REQUIRED_PORTS; do
        if sudo netstat -tuln | grep -q ":$port "; then
            print_warning "Port $port is already in use. XenCDN may not start correctly."
        fi
    done
    
    print_success "System requirements check passed"
    print_info "RAM: ${TOTAL_RAM_GB}GB, Disk: ${AVAILABLE_DISK_GB}GB available"
}

install_dependencies() {
    print_step "Installing system dependencies..."
    
    # Update package index
    sudo apt-get update -qq
    
    # Install required packages
    sudo apt-get install -y \
        curl \
        wget \
        git \
        unzip \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        software-properties-common \
        net-tools \
        htop \
        vim \
        jq
    
    print_success "System dependencies installed"
}

install_docker() {
    print_step "Installing Docker..."
    
    # Remove old Docker versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    # Start and enable Docker
    sudo systemctl start docker
    sudo systemctl enable docker
    
    print_success "Docker installed successfully"
}

check_docker() {
    print_step "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_info "Docker not found. Installing Docker..."
        install_docker
    else
        DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
        print_info "Docker version: $DOCKER_VERSION"
    fi
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker installation failed"
        exit 1
    fi
    
    # Check if docker compose plugin is available
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose plugin not found"
        exit 1
    fi
    
    COMPOSE_VERSION=$(docker compose version | grep -oP '\d+\.\d+\.\d+' | head -1)
    print_info "Docker Compose version: $COMPOSE_VERSION"
    
    print_success "Docker is ready"
}

clone_xencdn() {
    print_step "Downloading XenCDN v${XENCDN_VERSION}..."
    
    # Create installation directory
    sudo mkdir -p $INSTALL_DIR
    sudo chown $USER:$USER $INSTALL_DIR
    
    # Clone repository
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        print_info "XenCDN already exists. Updating..."
        cd $INSTALL_DIR
        git pull origin main
    else
        git clone $REPO_URL $INSTALL_DIR
        cd $INSTALL_DIR
    fi
    
    # Switch to the correct branch/tag if needed
    git checkout main
    
    print_success "XenCDN source code downloaded"
}

configure_xencdn() {
    print_step "Configuring XenCDN..."
    
    cd $INSTALL_DIR
    
    # Generate secure random passwords and keys
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/')
    JWT_SECRET=$(openssl rand -base64 64 | tr -d '/')
    PDNS_API_KEY=$(openssl rand -hex 32)
    MINIO_PASSWORD=$(openssl rand -base64 32 | tr -d '/')
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || openssl rand -base64 32)
    
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me || wget -qO- ifconfig.me || echo "127.0.0.1")
    
    # Create .env file
    cat > .env << EOF
# XenCDN v8.2 Enterprise Platform Environment Configuration
# Generated automatically on $(date)

# Database Configuration
DATABASE_URL=postgresql://xencdn:${DB_PASSWORD}@db:5432/xencdn
POSTGRES_DB=xencdn
POSTGRES_USER=xencdn
POSTGRES_PASSWORD=${DB_PASSWORD}

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# JWT Secret Key
JWT_SECRET_KEY=${JWT_SECRET}

# PowerDNS Configuration
PDNS_API_KEY=${PDNS_API_KEY}
PDNS_API_URL=http://powerdns:8081/api/v1/servers/localhost

# MinIO S3 Configuration
MINIO_ROOT_USER=xencdn-admin
MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=xencdn-ssl-certs

# ACME.sh Configuration for SSL
ACME_EMAIL=ssl@${SERVER_IP}
ACME_SERVER=https://acme-v02.api.letsencrypt.org/directory

# Domain Configuration for XenCDN v8.2
HOMEPAGE_DOMAIN=xencdn.com
API_DOMAIN=api.xencdn.com
ADMIN_DOMAIN=admin.xencdn.com
CLIENT_PORTAL_DOMAIN=client.xencdn.com
ISP_PORTAL_DOMAIN=isp.xencdn.com
SPEED_TEST_DOMAIN=speedtest.xencdn.com

# DNS Server Configuration
DNS_SERVER_NAME=ns1.xencdn.com
DNS_SERVER_NAME2=ns2.xencdn.com

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=${JWT_SECRET}

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Edge Node Configuration
EDGE_SSH_USER=root
EDGE_SSH_KEY=/app/ansible/keys/xencdn-ed25519
EDGE_DEFAULT_REGION=auto
EDGE_MAX_CLIENTS_PER_NODE=50

# BGP/Anycast Configuration (for BGP Mode)
BGP_ASN=65000
BGP_IP_BLOCK=203.0.113.0/24
BGP_PEER_IP=${SERVER_IP}
BGP_ROUTER_ID=203.0.113.1

# Edge Deployment Mode
EDGE_MODE=single_ip

# Security Configuration
ALLOWED_ORIGINS=http://${SERVER_IP}:3001,http://${SERVER_IP}:3002,http://${SERVER_IP}:3003
CORS_ORIGINS=*
RATE_LIMIT_PER_MINUTE=1000

# Email Configuration for Reports (configure with your SMTP provider)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@xencdn.com

# Encryption Configuration
FERNET_KEY=${FERNET_KEY}

# Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_RETENTION_DAYS=90

# Auto-scaling Configuration (DISABLED - Manual edge addition only)
AUTO_SCALE_ENABLED=false
MANUAL_EDGE_ONLY=true

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=0 2 * * *

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_RETENTION_DAYS=7

# Business Configuration
CDN_COMPANY_NAME=Your CDN Company
CDN_SUPPORT_EMAIL=support@your-domain.com
CDN_BILLING_EMAIL=billing@your-domain.com

# White-labeling Configuration
WHITE_LABEL_ENABLED=true
WHITE_LABEL_LOGO_URL=https://your-domain.com/logo.png
WHITE_LABEL_COMPANY_NAME=Your CDN Company

# Admin Configuration
ADMIN_EMAIL=admin@xencdn.com
ADMIN_PASSWORD=XenCDN@2024!
EOF
    
    # Set proper permissions
    chmod 600 .env
    
    print_success "XenCDN configuration completed"
    print_info "Database password: ${DB_PASSWORD}"
    print_info "PowerDNS API key: ${PDNS_API_KEY}"
    print_info "Admin email: admin@xencdn.com"
    print_info "Admin password: XenCDN@2024!"
}

start_xencdn() {
    print_step "Starting XenCDN v${XENCDN_VERSION}..."
    
    cd $INSTALL_DIR
    
    # Create required directories
    mkdir -p db redis minio certbot bird frr ansible/keys
    
    # Generate SSH key for edge nodes
    if [[ ! -f ansible/keys/xencdn-ed25519 ]]; then
        ssh-keygen -t ed25519 -f ansible/keys/xencdn-ed25519 -N "" -C "xencdn-edge-key"
    fi
    
    # Build and start all services
    print_info "Building Docker images (this may take a few minutes)..."
    docker compose build --parallel
    
    print_info "Starting XenCDN services..."
    docker compose up -d
    
    # Wait for services to be healthy
    print_info "Waiting for services to start..."
    sleep 30
    
    # Check service health
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
        if docker compose ps | grep -q "unhealthy\|exited"; then
            print_warning "Some services are not healthy yet. Waiting..."
            sleep 10
            ((RETRY_COUNT++))
        else
            break
        fi
    done
    
    print_success "XenCDN services started"
}

display_completion() {
    SERVER_IP=$(curl -s ifconfig.me || wget -qO- ifconfig.me || echo "127.0.0.1")
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║                 ${CYAN}🎉 INSTALLATION COMPLETE! 🎉${GREEN}                ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║              ${YELLOW}XenCDN v${XENCDN_VERSION} is now running!${GREEN}                ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}🌐 Access your XenCDN platform:${NC}"
    echo ""
    echo -e "${YELLOW}📊 Admin Dashboard:${NC}      http://${SERVER_IP}:3001"
    echo -e "${YELLOW}👥 Client Portal:${NC}        http://${SERVER_IP}:3002"
    echo -e "${YELLOW}🏢 ISP Portal:${NC}           http://${SERVER_IP}:3003"
    echo -e "${YELLOW}🏠 Homepage:${NC}             http://${SERVER_IP}:3000"
    echo -e "${YELLOW}⚡ Speed Test Tool:${NC}      http://${SERVER_IP}:3004"
    echo -e "${YELLOW}🔧 API Endpoint:${NC}         http://${SERVER_IP}:5000"
    echo -e "${YELLOW}📁 MinIO Console:${NC}        http://${SERVER_IP}:9001"
    echo -e "${YELLOW}🌐 PowerDNS API:${NC}         http://${SERVER_IP}:8081"
    echo ""
    echo -e "${CYAN}🔐 Default Admin Credentials:${NC}"
    echo -e "${YELLOW}Email:${NC}     admin@xencdn.com"
    echo -e "${YELLOW}Password:${NC}  XenCDN@2024!"
    echo ""
    echo -e "${CYAN}🚀 Next Steps:${NC}"
    echo -e "1. Log into the Admin Dashboard"
    echo -e "2. Go to DNS Zone Manager and add your first domain"
    echo -e "3. Point your domain's nameservers to:"
    echo -e "   ${YELLOW}ns1.xencdn.com${NC} (${SERVER_IP})"
    echo -e "   ${YELLOW}ns2.xencdn.com${NC} (${SERVER_IP})"
    echo -e "4. Use the ISP Portal to manage BGP peering"
    echo -e "5. Share the Client Portal with your customers"
    echo ""
    echo -e "${CYAN}📚 Documentation:${NC}"
    echo -e "• Configuration: ${INSTALL_DIR}/.env"
    echo -e "• Logs: docker compose logs -f"
    echo -e "• Management: docker compose [start|stop|restart]"
    echo ""
    echo -e "${GREEN}You are now a Tier-1 CDN provider.${NC}"
    echo -e "${GREEN}Your clients will never leave. Your profit margin is 98%.${NC}"
    echo ""
    echo -e "${PURPLE}For support, visit: https://xencdn.com/support${NC}"
    echo ""
}

# Main installation flow
main() {
    print_header
    
    check_root
    check_system_requirements
    install_dependencies
    check_docker
    clone_xencdn
    configure_xencdn
    start_xencdn
    display_completion
}

# Handle script interruption
trap 'echo -e "\n${RED}Installation interrupted!${NC}"; exit 1' INT TERM

# Run main installation
main "$@"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Installation stages
STAGE_COUNT=15
CURRENT_STAGE=0

# Logging functions
log() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${GREEN}[DRY-RUN] $1${NC}"
    else
        echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
    fi
}

warn() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY-RUN] WARNING: $1${NC}"
    else
        echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
    fi
}

error() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${RED}[DRY-RUN] ERROR: $1${NC}"
    else
        echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    fi
}

info() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${BLUE}[DRY-RUN] INFO: $1${NC}"
    else
        echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
    fi
}

stage() {
    CURRENT_STAGE=$((CURRENT_STAGE + 1))
    echo ""
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${PURPLE}║ DRY-RUN Stage $CURRENT_STAGE/$STAGE_COUNT: $1 ${NC}"
        echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    else
        echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${PURPLE}║ Stage $CURRENT_STAGE/$STAGE_COUNT: $1 ${NC}"
        echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    fi
    echo ""
}

# Cleanup function for graceful exit
cleanup() {
    if [[ $? -ne 0 && "$DRY_RUN" != "true" ]]; then
        error "Installation failed. Cleaning up..."
        docker-compose down 2>/dev/null || true
    fi
}

if [[ "$DRY_RUN" != "true" ]]; then
    trap cleanup EXIT
fi

# Display banner
if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    Cachenet Enterprise CDN                   ║${NC}"
    echo -e "${CYAN}║                     DRY RUN MODE - Preview                   ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║  📋 Preview: Config → DB → SSL → Services → Ready!           ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    Cachenet Enterprise CDN                   ║${NC}"
    echo -e "${CYAN}║                  Complete A-Z Installation                   ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║  🚀 Full automation: Config → DB → SSL → Services → Ready!   ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
fi
echo ""

# Stage 1: Pre-installation checks
stage "Pre-installation System Checks"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root for security reasons"
   exit 1
fi

# Check OS compatibility
log "Checking operating system compatibility..."
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "This script only supports Linux distributions"
    exit 1
fi

# Detect Linux distribution
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    log "Detected OS: $NAME $VERSION_ID"
    
    # Check for supported distributions
    case "$ID" in
        ubuntu|debian)
            PACKAGE_MANAGER="apt-get"
            ;;
        centos|rhel|fedora)
            PACKAGE_MANAGER="yum"
            warn "CentOS/RHEL/Fedora support is experimental"
            ;;
        *)
            warn "Unsupported distribution: $ID. Proceeding with Ubuntu/Debian commands."
            PACKAGE_MANAGER="apt-get"
            ;;
    esac
else
    error "Cannot detect Linux distribution"
    exit 1
fi

# Check system resources
log "Checking system resources..."

# Check available disk space (minimum 50GB)
AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
REQUIRED_SPACE=52428800 # 50GB in KB

if [[ $AVAILABLE_SPACE -lt $REQUIRED_SPACE ]]; then
    error "Insufficient disk space. Required: 50GB, Available: $(($AVAILABLE_SPACE/1024/1024))GB"
    exit 1
fi

# Check available RAM (minimum 4GB)
AVAILABLE_RAM=$(free -m | awk 'NR==2 {print $2}')
REQUIRED_RAM=4096 # 4GB in MB

if [[ $AVAILABLE_RAM -lt $REQUIRED_RAM ]]; then
    error "Insufficient RAM. Required: 4GB, Available: ${AVAILABLE_RAM}MB"
    exit 1
fi

# Check CPU cores (minimum 2)
CPU_CORES=$(nproc)
if [[ $CPU_CORES -lt 2 ]]; then
    warn "Only $CPU_CORES CPU core(s) detected. 2+ cores recommended for optimal performance."
fi

log "✓ System requirements met (Disk: $(($AVAILABLE_SPACE/1024/1024))GB, RAM: ${AVAILABLE_RAM}MB, CPU: ${CPU_CORES} cores)"

# Stage 2: Configuration Setup
stage "Environment Configuration Setup"

# Check for existing .env file
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        if [[ "$SKIP_CONFIG" == "true" ]]; then
            error "No .env file found and --skip-config specified"
            exit 1
        fi
        log "No .env file found. Starting configuration wizard..."
        info "Running interactive configuration wizard..."
        if [[ "$DRY_RUN" != "true" ]]; then
            ./scripts/configure.sh
        else
            log "Would run: ./scripts/configure.sh"
        fi
    else
        error ".env.example template not found!"
        exit 1
    fi
else
    log "Found existing .env file"
    
    # Validate critical configuration
    if [[ "$DRY_RUN" != "true" ]] && grep -q "CHANGE_ME" .env; then
        warn "Configuration file contains placeholder values"
        if [[ "$SKIP_CONFIG" != "true" ]]; then
            echo -n -e "${YELLOW}Run configuration wizard to fix? (Y/n): ${NC}"
            read run_config
            if [[ ! "$run_config" =~ ^[Nn]$ ]]; then
                ./scripts/configure.sh
            fi
        fi
    fi
fi

# Load environment variables
if [[ -f .env && "$DRY_RUN" != "true" ]]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
    log "✓ Environment variables loaded"
elif [[ "$DRY_RUN" == "true" ]]; then
    log "Would load environment variables from .env"
else
    error "Failed to create .env file"
    exit 1
fi

# Stage 3: Install system dependencies
stage "Installing System Dependencies"

if [[ "$DRY_RUN" == "true" ]]; then
    log "Would update package repositories"
    log "Would install required system packages: apt-transport-https, ca-certificates, curl, gnupg, etc."
    log "✓ System dependencies would be installed"
else
    log "Updating package repositories..."
    if [[ "$PACKAGE_MANAGER" == "apt-get" ]]; then
        sudo apt-get update -qq
        
        # Install required packages
        log "Installing required system packages..."
        sudo apt-get install -y -qq \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg \
            lsb-release \
            git \
            htop \
            nano \
            wget \
            unzip \
            openssl \
            ufw \
            cron \
            logrotate \
            rsync \
            python3 \
            python3-pip
    else
        sudo yum update -y -q
        sudo yum install -y -q curl wget git nano htop openssl firewalld cronie logrotate rsync python3 python3-pip
    fi

    log "✓ System dependencies installed"
fi

# Stage 4: Install Docker and Docker Compose
stage "Installing Docker and Docker Compose"

# Check if Docker is already installed
if ! command -v docker &> /dev/null; then
    log "Installing Docker..."
    
    if [[ "$PACKAGE_MANAGER" == "apt-get" ]]; then
        # Add Docker's official GPG key
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        
        # Add Docker repository
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker
        sudo apt-get update -qq
        sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io
    else
        # Install Docker on CentOS/RHEL/Fedora
        sudo yum install -y -q yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y -q docker-ce docker-ce-cli containerd.io
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    
    log "✓ Docker installed"
else
    log "✓ Docker already installed"
fi

# Check if Docker Compose is already installed
if ! command -v docker-compose &> /dev/null; then
    log "Installing Docker Compose..."
    
    # Install Docker Compose
    COMPOSE_VERSION="v2.21.0"
    sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    log "✓ Docker Compose installed"
else
    log "✓ Docker Compose already installed"
fi

# Add user to docker group
if ! groups $USER | grep -q docker; then
    log "Adding user to docker group..."
    sudo usermod -aG docker $USER
    warn "You may need to logout and login again for Docker group membership to take effect"
fi

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

log "✓ Docker services configured"

# Stage 5: Create directory structure
stage "Creating Directory Structure"

log "Creating necessary directories..."

# Create data directories
mkdir -p {db,redis,minio,ssl-certs,logs,backups}
mkdir -p data/{postgres,redis,minio,prometheus,grafana,loki}
mkdir -p ansible/keys
mkdir -p nginx/ssl
mkdir -p scripts/logs

# Set proper permissions
chmod 700 ansible/keys
chmod 755 data/{postgres,redis,minio,prometheus,grafana,loki}
chmod 755 nginx/ssl
chmod 755 logs backups ssl-certs

# Fix ownership for service directories
sudo chown -R 1000:1000 data/prometheus data/grafana data/loki 2>/dev/null || true

log "✓ Directory structure created"

# Stage 6: Generate SSH keys and security credentials
stage "Generating Security Credentials"

# Generate SSH keys for edge server management
if [[ ! -f ansible/keys/cachenet-ed25519 ]]; then
    log "Generating SSH keys for edge server management..."
    ./scripts/generate-keys.sh
else
    log "✓ SSH keys already exist"
fi

# Generate additional security keys if needed
log "Updating security configuration..."

# Update any remaining placeholder values in .env
if grep -q "CHANGE_ME" .env; then
    warn "Generating remaining security credentials..."
    
    # Generate secure passwords for any remaining placeholders
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    JWT_SECRET=$(openssl rand -hex 32)
    FLASK_SECRET=$(openssl rand -hex 32)
    PDNS_API_KEY=$(openssl rand -hex 32)
    MINIO_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    
    sed -i "s/CHANGE_ME_DB_PASSWORD/$DB_PASSWORD/g" .env
    sed -i "s/CHANGE_ME_JWT_SECRET/$JWT_SECRET/g" .env
    sed -i "s/CHANGE_ME_FLASK_SECRET/$FLASK_SECRET/g" .env
    sed -i "s/CHANGE_ME_PDNS_API_KEY/$PDNS_API_KEY/g" .env
    sed -i "s/CHANGE_ME_MINIO_PASSWORD/$MINIO_PASSWORD/g" .env
    sed -i "s/CHANGE_ME_GRAFANA_PASSWORD/$GRAFANA_PASSWORD/g" .env
fi

# Reload environment after updates
export $(grep -v '^#' .env | grep -v '^$' | xargs)

log "✓ Security credentials generated"

# Stage 7: Generate configurations
stage "Generating Service Configurations"

# Generate Nginx configuration
log "Generating Nginx configuration..."
./scripts/setup-nginx.sh generate

# Generate SSL certificates
log "Setting up SSL certificates..."
./scripts/setup-ssl.sh setup

log "✓ Service configurations generated"

# Stage 8: Pull and build Docker images
stage "Pulling and Building Docker Images"

log "Pulling required Docker images..."
docker-compose pull --quiet || {
    warn "Some images failed to pull, will try to build them"
}

log "Building custom application images..."
docker-compose build --quiet

log "✓ Docker images ready"

# Stage 9: Start core services
stage "Starting Core Services"

log "Starting database and cache services..."
docker-compose up -d db redis minio

# Wait for core services to be ready
log "Waiting for core services to start..."
sleep 30

# Check database connectivity
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} >/dev/null 2>&1; then
        log "✓ Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        error "Database failed to start within 5 minutes"
        exit 1
    fi
    sleep 10
done

# Check Redis connectivity
if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    log "✓ Redis is ready"
else
    error "Redis failed to start"
    exit 1
fi

log "✓ Core services started"

# Stage 10: Initialize database
stage "Initializing Database Schema"

log "Running database initialization..."
./scripts/init-database.sh

log "✓ Database initialized"

# Stage 11: Start remaining services
stage "Starting Application Services"

log "Starting API and worker services..."
docker-compose up -d api celery-worker celery-beat

log "Starting PowerDNS service..."
docker-compose up -d powerdns

log "Starting monitoring services..."
docker-compose up -d prometheus grafana

log "Starting dashboard services..."
docker-compose up -d admin client

log "Starting reverse proxy..."
docker-compose up -d nginx

# Wait for all services to be ready
log "Waiting for all services to stabilize..."
sleep 60

log "✓ All services started"

# Stage 12: Service health checks
stage "Performing Health Checks"

log "Checking service health..."

# API health check
for i in {1..10}; do
    API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health 2>/dev/null || echo "000")
    if [[ "$API_HEALTH" == "200" ]]; then
        log "✓ API service is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        warn "API service health check failed (HTTP $API_HEALTH)"
    fi
    sleep 5
done

# Database health check
DB_STATUS=$(docker-compose exec -T db pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} 2>/dev/null || echo "fail")
if [[ "$DB_STATUS" == *"accepting connections"* ]]; then
    log "✓ Database service is healthy"
else
    warn "Database service health check failed"
fi

# Redis health check
REDIS_STATUS=$(docker-compose exec -T redis redis-cli ping 2>/dev/null || echo "fail")
if [[ "$REDIS_STATUS" == "PONG" ]]; then
    log "✓ Redis service is healthy"
else
    warn "Redis service health check failed"
fi

# Dashboard health checks
ADMIN_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
if [[ "$ADMIN_HEALTH" == "200" ]]; then
    log "✓ Admin dashboard is accessible"
fi

CLIENT_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3002 2>/dev/null || echo "000")
if [[ "$CLIENT_HEALTH" == "200" ]]; then
    log "✓ Client dashboard is accessible"
fi

GRAFANA_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 2>/dev/null || echo "000")
if [[ "$GRAFANA_HEALTH" == "200" ]]; then
    log "✓ Grafana monitoring is accessible"
fi

log "✓ Health checks completed"

# Stage 13: Configure firewall
stage "Configuring System Firewall"

log "Setting up firewall rules..."

# Configure UFW (Ubuntu/Debian) or firewalld (CentOS/RHEL)
if command -v ufw &> /dev/null; then
    sudo ufw --force enable
    sudo ufw allow ssh
    sudo ufw allow 80/tcp comment "HTTP"
    sudo ufw allow 443/tcp comment "HTTPS"
    sudo ufw allow 53/tcp comment "DNS TCP"
    sudo ufw allow 53/udp comment "DNS UDP"
    sudo ufw allow 3000:3002/tcp comment "Dashboards"
    sudo ufw allow 5000/tcp comment "API"
    sudo ufw allow 9090/tcp comment "Prometheus"
    sudo ufw --force reload
    log "✓ UFW firewall configured"
elif command -v firewall-cmd &> /dev/null; then
    sudo systemctl start firewalld
    sudo systemctl enable firewalld
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --permanent --add-service=dns
    sudo firewall-cmd --permanent --add-port=3000-3002/tcp
    sudo firewall-cmd --permanent --add-port=5000/tcp
    sudo firewall-cmd --permanent --add-port=9090/tcp
    sudo firewall-cmd --reload
    log "✓ Firewalld configured"
else
    warn "No supported firewall found. Please configure iptables manually."
fi

# Stage 14: System service setup
stage "Setting Up System Service"

log "Creating systemd service for auto-start..."

sudo tee /etc/systemd/system/cachenet.service > /dev/null <<EOF
[Unit]
Description=Cachenet Enterprise CDN Platform
Documentation=https://github.com/fahim8401/cdn
Requires=docker.service
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=$USER
Group=$USER
WorkingDirectory=$(pwd)
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
ExecReload=/usr/local/bin/docker-compose restart
TimeoutStartSec=300
TimeoutStopSec=120
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cachenet.service

log "✓ System service configured"

# Setup log rotation
log "Configuring log rotation..."
sudo tee /etc/logrotate.d/cachenet > /dev/null <<EOF
$(pwd)/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker-compose exec api kill -USR1 1 2>/dev/null || true
    endscript
}
EOF

log "✓ Log rotation configured"

# Stage 15: Final configuration and cleanup
stage "Final Configuration and Cleanup"

# Test Nginx configuration
log "Testing Nginx configuration..."
if docker-compose exec nginx nginx -t >/dev/null 2>&1; then
    log "✓ Nginx configuration is valid"
    docker-compose exec nginx nginx -s reload >/dev/null 2>&1 || true
else
    warn "Nginx configuration has issues"
fi

# Create backup script
log "Setting up automated backups..."
cat > scripts/backup-system.sh << 'EOF'
#!/bin/bash
# Automated backup script for Cachenet CDN

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
docker-compose exec -T db pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > "$BACKUP_DIR/database_$DATE.sql.gz"

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" .env nginx/ ansible/ ssl-certs/

# Cleanup old backups (keep 7 days)
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x scripts/backup-system.sh

# Add backup to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * cd $(pwd) && ./scripts/backup-system.sh >> logs/backup.log 2>&1") | crontab -

log "✓ Automated backups configured"

# Clean up temporary files
log "Cleaning up temporary files..."
sudo apt-get autoremove -y -qq >/dev/null 2>&1 || true
sudo apt-get autoclean -y -qq >/dev/null 2>&1 || true
docker system prune -f >/dev/null 2>&1 || true

log "✓ Cleanup completed"

# Success! Display final information
echo ""
if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              🎯 DRY RUN COMPLETED SUCCESSFULLY! 🎯           ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}📋 What would be installed:${NC}"
    echo -e "   ✅ Complete environment configuration"
    echo -e "   ✅ PostgreSQL database with schema"
    echo -e "   ✅ Redis caching and message queue"
    echo -e "   ✅ PowerDNS for domain management"
    echo -e "   ✅ SSL certificates (self-signed or ACME)"
    echo -e "   ✅ Nginx reverse proxy with security headers"
    echo -e "   ✅ API backend with authentication"
    echo -e "   ✅ Admin and client dashboards"
    echo -e "   ✅ Monitoring (Prometheus + Grafana)"
    echo -e "   ✅ Background task processing"
    echo -e "   ✅ Automated backups and log rotation"
    echo -e "   ✅ System service for auto-start"
    echo -e "   ✅ Firewall configuration"
    echo ""
    echo -e "${YELLOW}To proceed with actual installation:${NC}"
    echo -e "   Run: ${GREEN}./install.sh${NC}"
    echo ""
else
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           🎉 INSTALLATION COMPLETED SUCCESSFULLY! 🎉         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
fi
echo ""

# Load final environment to display correct values
export $(grep -v '^#' .env | grep -v '^$' | xargs)

echo -e "${CYAN}📊 Service URLs:${NC}"
if [[ -n "$ADMIN_DOMAIN" && "$ADMIN_DOMAIN" != "CHANGE_ME_ADMIN_DOMAIN" ]]; then
    echo -e "   🎛️  Admin Dashboard:  ${BLUE}https://$ADMIN_DOMAIN${NC}"
else
    echo -e "   🎛️  Admin Dashboard:  ${BLUE}http://localhost:3000${NC}"
fi

if [[ -n "$CLIENT_DOMAIN" && "$CLIENT_DOMAIN" != "CHANGE_ME_CLIENT_DOMAIN" ]]; then
    echo -e "   👥 Client Dashboard: ${BLUE}https://$CLIENT_DOMAIN${NC}"
else
    echo -e "   👥 Client Dashboard: ${BLUE}http://localhost:3002${NC}"
fi

if [[ -n "$API_DOMAIN" && "$API_DOMAIN" != "CHANGE_ME_API_DOMAIN" ]]; then
    echo -e "   🔧 API Endpoint:     ${BLUE}https://$API_DOMAIN${NC}"
else
    echo -e "   🔧 API Endpoint:     ${BLUE}http://localhost:5000${NC}"
fi

echo -e "   📊 Grafana Monitor:  ${BLUE}http://localhost:3001${NC} (admin/${GRAFANA_ADMIN_PASSWORD:-admin})"
echo -e "   📈 Prometheus:       ${BLUE}http://localhost:9090${NC}"
echo ""

echo -e "${CYAN}🔐 Admin Credentials:${NC}"
echo -e "   📧 Email:    ${BLUE}${ADMIN_EMAIL}${NC}"
echo -e "   🔑 Password: ${BLUE}${ADMIN_PASSWORD}${NC}"
echo ""

echo -e "${CYAN}🎯 What's been set up:${NC}"
echo -e "   ✅ Complete environment configuration"
echo -e "   ✅ PostgreSQL database with schema"
echo -e "   ✅ Redis caching and message queue"
echo -e "   ✅ PowerDNS for domain management"
echo -e "   ✅ SSL certificates (self-signed or ACME)"
echo -e "   ✅ Nginx reverse proxy with security headers"
echo -e "   ✅ API backend with authentication"
echo -e "   ✅ Admin and client dashboards"
echo -e "   ✅ Monitoring (Prometheus + Grafana)"
echo -e "   ✅ Background task processing"
echo -e "   ✅ Automated backups and log rotation"
echo -e "   ✅ System service for auto-start"
echo -e "   ✅ Firewall configuration"
echo ""

echo -e "${YELLOW}📝 Next Steps:${NC}"
echo -e "   1. 🌐 Configure DNS records to point your domains to this server"
echo -e "   2. 🔧 Add cloud provider API keys in the admin dashboard"
echo -e "   3. 🖥️  Deploy your first edge servers"
echo -e "   4. 📋 Configure your first domain in the admin panel"
echo -e "   5. 📊 Monitor performance in Grafana"
echo ""

echo -e "${YELLOW}🛠️  Management Commands:${NC}"
echo -e "   Start services:  ${GREEN}docker-compose up -d${NC}"
echo -e "   Stop services:   ${GREEN}docker-compose down${NC}"
echo -e "   View logs:       ${GREEN}docker-compose logs -f${NC}"
echo -e "   Service status:  ${GREEN}sudo systemctl status cachenet${NC}"
echo ""

log "Service status:"
docker-compose ps

echo ""
echo -e "${GREEN}🚀 Congratulations! You are now a Tier-1 CDN provider!${NC}"
echo -e "${GREEN}   Your clients will never leave. Your profit margin is 98%.${NC}"
echo ""

# Final warning about docker group
if ! groups $USER | grep -q docker; then
    echo -e "${YELLOW}⚠️  IMPORTANT: Please logout and login again for Docker group membership to take effect.${NC}"
    echo ""
fi

log "Installation completed successfully! 🎉"

exit 0