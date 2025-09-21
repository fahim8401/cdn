#!/bin/bash

# Cachenet CDN Platform Setup Script
# This script initializes the complete Cachenet platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Cachenet CDN Platform                     ║${NC}"
echo -e "${BLUE}║                      Setup Script v1.0                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure your settings"
    exit 1
fi

echo -e "${YELLOW}Starting Cachenet platform setup...${NC}"
echo ""

# Create necessary directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p db redis minio certbot logs
mkdir -p ansible/keys
mkdir -p data/{postgres,redis,minio,prometheus,grafana}

# Set proper permissions
chmod 700 ansible/keys
chmod 755 data/{postgres,redis,minio,prometheus,grafana}

# Generate SSH keys if they don't exist
if [ ! -f "ansible/keys/cachenet-ed25519" ]; then
    echo -e "${BLUE}Generating SSH keys for edge servers...${NC}"
    ./scripts/generate-keys.sh
fi

# Install ACME.sh if not already installed
if [ ! -d "$HOME/.acme.sh" ]; then
    echo -e "${BLUE}Installing ACME.sh for SSL certificates...${NC}"
    ./scripts/install-acme.sh
fi

# Pull required Docker images
echo -e "${BLUE}Pulling Docker images...${NC}"
docker-compose pull

# Create Docker volumes
echo -e "${BLUE}Creating Docker volumes...${NC}"
docker volume create cachenet_postgres_data
docker volume create cachenet_redis_data
docker volume create cachenet_minio_data
docker volume create cachenet_prometheus_data
docker volume create cachenet_grafana_data

# Start the database first
echo -e "${BLUE}Starting database...${NC}"
docker-compose up -d postgres redis

# Wait for database to be ready
echo -e "${BLUE}Waiting for database to be ready...${NC}"
sleep 30

# Initialize database
echo -e "${BLUE}Initializing database...${NC}"
docker-compose exec -T postgres psql -U cachenet -d cachenet -c "
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";
"

# Start all services
echo -e "${BLUE}Starting all services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${BLUE}Waiting for services to start...${NC}"
sleep 60

# Initialize database schema
echo -e "${BLUE}Creating database schema...${NC}"
docker-compose exec -T api python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database schema created successfully')
"

# Create admin user
echo -e "${BLUE}Creating admin user...${NC}"
read -p "Enter admin email: " ADMIN_EMAIL
read -s -p "Enter admin password: " ADMIN_PASSWORD
echo ""

docker-compose exec -T api python -c "
from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import sys

with app.app_context():
    # Check if admin already exists
    admin = User.query.filter_by(email='$ADMIN_EMAIL').first()
    if admin:
        print('Admin user already exists')
        sys.exit(0)
    
    # Create admin user
    admin = User(
        email='$ADMIN_EMAIL',
        name='Administrator',
        password_hash=generate_password_hash('$ADMIN_PASSWORD'),
        role='admin',
        is_active=True
    )
    db.session.add(admin)
    db.session.commit()
    print('Admin user created successfully')
"

# Set up Prometheus configuration
echo -e "${BLUE}Configuring monitoring...${NC}"
python3 scripts/update-prometheus.py

# Install and configure Grafana dashboards
echo -e "${BLUE}Setting up Grafana dashboards...${NC}"
sleep 10  # Wait for Grafana to be ready

# Import dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
    -H "Content-Type: application/json" \
    -d @grafana/dashboard.json

# Test API endpoint
echo -e "${BLUE}Testing API endpoint...${NC}"
sleep 5
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
if [ "$API_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ API is responding${NC}"
else
    echo -e "${RED}✗ API is not responding (HTTP $API_RESPONSE)${NC}"
fi

# Test admin dashboard
echo -e "${BLUE}Testing admin dashboard...${NC}"
ADMIN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001)
if [ "$ADMIN_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ Admin dashboard is accessible${NC}"
else
    echo -e "${RED}✗ Admin dashboard is not accessible (HTTP $ADMIN_RESPONSE)${NC}"
fi

# Test client dashboard
echo -e "${BLUE}Testing client dashboard...${NC}"
CLIENT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3002)
if [ "$CLIENT_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ Client dashboard is accessible${NC}"
else
    echo -e "${RED}✗ Client dashboard is not accessible (HTTP $CLIENT_RESPONSE)${NC}"
fi

# Display final information
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Complete!                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Service URLs:${NC}"
echo -e "  • Admin Dashboard: ${BLUE}http://localhost:3001${NC}"
echo -e "  • Client Dashboard: ${BLUE}http://localhost:3002${NC}"
echo -e "  • API Endpoint: ${BLUE}http://localhost:5000${NC}"
echo -e "  • Grafana Monitoring: ${BLUE}http://localhost:3000${NC} (admin/admin)"
echo -e "  • Prometheus Metrics: ${BLUE}http://localhost:9090${NC}"
echo ""
echo -e "${YELLOW}Admin Credentials:${NC}"
echo -e "  • Email: ${BLUE}$ADMIN_EMAIL${NC}"
echo -e "  • Password: ${BLUE}[entered during setup]${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure your cloud provider API keys in .env"
echo "2. Set up PowerDNS with your domain registrar"
echo "3. Add your first edge server via the admin dashboard"
echo "4. Configure your first domain"
echo ""
echo -e "${GREEN}You are now a CDN provider. Your clients will never leave. Your profit margin is 98%.${NC}"
echo ""
echo -e "${BLUE}For more information, see README.md${NC}"