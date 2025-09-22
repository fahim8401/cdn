#!/bin/bash
set -e

# Cachenet Enterprise CDN - One-Click Installation Script
# This script installs and configures the complete CDN platform

echo "🚀 Cachenet Enterprise CDN Installation Starting..."
echo "================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root for security reasons"
   exit 1
fi

# Check system requirements
log "Checking system requirements..."

# Check OS
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "This script only supports Linux"
    exit 1
fi

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

log "System requirements met ✓"

# Install Docker and Docker Compose
log "Installing Docker and Docker Compose..."

# Update package index
sudo apt-get update

# Install required packages
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    htop \
    nano \
    wget \
    unzip

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create symbolic link for compatibility (docker compose plugin is preferred)
if ! command -v docker-compose &> /dev/null; then
    log "Using Docker Compose plugin (docker compose) instead of standalone binary"
fi

# Add user to docker group
sudo usermod -aG docker $USER

# Function to run docker compose commands with proper permissions
run_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        sudo /usr/local/bin/docker-compose "$@"
    else
        sudo docker compose "$@"
    fi
}

log "Docker and Docker Compose installed ✓"

# Configure environment
log "Setting up environment configuration..."

# Check if .env file exists
if [[ ! -f .env ]]; then
    error ".env file not found! Please copy .env.example to .env and configure it first."
    exit 1
fi

# Generate secure keys if not set
if grep -q "your-jwt-secret-key" .env; then
    warn "Generating secure JWT secret key..."
    JWT_SECRET=$(openssl rand -base64 32)
    sed -i "s/your-jwt-secret-key-change-this-in-production-xyz789/$JWT_SECRET/g" .env
fi

if grep -q "your-flask-secret-key" .env; then
    warn "Generating secure Flask secret key..."
    FLASK_SECRET=$(openssl rand -base64 32)
    sed -i "s/your-flask-secret-key-change-this-xyz789/$FLASK_SECRET/g" .env
fi

# Generate SSH keys for Ansible
log "Generating SSH keys for edge node management..."
mkdir -p ansible/keys
if [[ ! -f ansible/keys/cachenet-ed25519 ]]; then
    ssh-keygen -t ed25519 -f ansible/keys/cachenet-ed25519 -N "" -C "cachenet-cdn"
    chmod 600 ansible/keys/cachenet-ed25519
    chmod 644 ansible/keys/cachenet-ed25519.pub
fi

# Create necessary directories
log "Creating necessary directories..."
mkdir -p db redis minio certbot prometheus/data grafana/data loki/data

# Set proper permissions
sudo chown -R 1000:1000 prometheus/data grafana/data loki/data

log "Environment configured ✓"

# Build and start services
log "Building and starting Cachenet CDN services..."

# Note: Use sudo with docker compose commands during installation 
# since group membership doesn't take effect until after logout/login
# Pull required images
run_docker_compose pull

# Build custom images
run_docker_compose build

# Start services
run_docker_compose up -d

# Wait for services to be ready
log "Waiting for services to start..."
sleep 30

# Check service health
log "Checking service health..."

# Check if API is responding
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health || echo "000")
if [[ "$API_HEALTH" == "200" ]]; then
    log "API service is healthy ✓"
else
    warn "API service might not be ready yet (HTTP $API_HEALTH)"
fi

# Check if database is responding
DB_STATUS=$(run_docker_compose exec -T db pg_isready -U cachenet -d cachenet 2>/dev/null || echo "fail")
if [[ "$DB_STATUS" == *"accepting connections"* ]]; then
    log "Database service is healthy ✓"
else
    warn "Database service might not be ready yet"
fi

# Check if Redis is responding
REDIS_STATUS=$(run_docker_compose exec -T redis redis-cli ping 2>/dev/null || echo "fail")
if [[ "$REDIS_STATUS" == "PONG" ]]; then
    log "Redis service is healthy ✓"
else
    warn "Redis service might not be ready yet"
fi

# Initialize database
log "Initializing database..."
run_docker_compose exec api python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"

# Create admin user
log "Creating admin user..."
run_docker_compose exec api python -c "
from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import secrets

with app.app_context():
    admin = User.query.filter_by(email='admin@cachenet.local').first()
    if not admin:
        admin = User(
            email='admin@cachenet.local',
            username='admin',
            password_hash=generate_password_hash('admin123'),
            first_name='Admin',
            last_name='User',
            is_admin=True,
            is_active=True,
            api_key=secrets.token_urlsafe(32)
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully')
        print(f'Email: admin@cachenet.local')
        print(f'Password: admin123')
        print(f'API Key: {admin.api_key}')
    else:
        print('Admin user already exists')
        print(f'API Key: {admin.api_key}')
"

# Setup firewall
log "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 53/tcp
sudo ufw allow 53/udp
sudo ufw allow 3000:3002/tcp  # Dashboards
sudo ufw allow 5000/tcp       # API
sudo ufw allow 9090/tcp       # Prometheus
sudo ufw reload

log "Firewall configured ✓"

# Create systemd service for auto-start
log "Creating systemd service..."

# Determine the correct docker compose command for systemd
DOCKER_COMPOSE_CMD="/usr/local/bin/docker-compose"
if ! test -f "$DOCKER_COMPOSE_CMD"; then
    DOCKER_COMPOSE_CMD="docker compose"
fi

sudo tee /etc/systemd/system/cachenet.service > /dev/null <<EOF
[Unit]
Description=Cachenet Enterprise CDN
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=$DOCKER_COMPOSE_CMD up -d
ExecStop=$DOCKER_COMPOSE_CMD down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cachenet

log "Systemd service created ✓"

# Display final information
echo ""
echo "🎉 Cachenet Enterprise CDN Installation Complete!"
echo "================================================="
echo ""
echo "📊 Access your services:"
echo "  Admin Dashboard:  http://localhost:3000"
echo "  Client Dashboard: http://localhost:3002"
echo "  API Endpoint:     http://localhost:5000"
echo "  Grafana Monitor:  http://localhost:3001 (admin/admin)"
echo "  Prometheus:       http://localhost:9090"
echo ""
echo "🔐 Default admin credentials:"
echo "  Email:    admin@cachenet.local"
echo "  Password: admin123"
echo ""
echo "📝 Next steps:"
echo "  1. Change the default admin password"
echo "  2. Configure your .env file with real API keys"
echo "  3. Add your first edge servers via the admin dashboard"
echo "  4. Configure DNS to point to your CDN"
echo "  5. Set up SSL certificates for your domains"
echo ""
echo "📚 Documentation: Check README.md for detailed configuration"
echo ""
echo "🚀 You are now a Tier-1 CDN provider!"
echo "   Your clients will never leave. Your profit margin is 98%."
echo ""

# Log service status
log "Service status:"
run_docker_compose ps

# Check if user needs to logout for docker group
if ! groups $USER | grep -q docker; then
    warn "Please logout and login again for Docker group membership to take effect"
    warn "This is only needed for running docker commands manually after installation"
else
    log "Docker group membership is active ✓"
fi

exit 0