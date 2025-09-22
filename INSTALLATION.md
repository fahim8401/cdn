# Cachenet CDN - Complete A-Z Installation Guide

This guide covers the complete automated installation of the Cachenet CDN platform from configuration to running services.

## 🚀 Quick Start (Complete A-Z Installation)

### Option 1: Fully Automated Installation (Recommended)
```bash
# Clone the repository
git clone https://github.com/fahim8401/cdn.git
cd cdn

# Run the complete A-Z installation
chmod +x install.sh
./install.sh
```

The installation script will:
1. ✅ **System Checks** - Verify OS, resources, and dependencies
2. ✅ **Configuration Wizard** - Interactive setup for domains, credentials, and API keys
3. ✅ **Dependency Installation** - Docker, Docker Compose, and system packages
4. ✅ **Security Setup** - SSH keys, SSL certificates, secure passwords
5. ✅ **Database Initialization** - PostgreSQL with PowerDNS schema
6. ✅ **Service Configuration** - Nginx, monitoring, and all CDN services
7. ✅ **Health Checks** - Validate all services are running correctly
8. ✅ **System Integration** - Firewall, auto-start, backups, and monitoring

### Option 2: Step-by-Step Installation

#### Step 1: Configure Environment
```bash
# Run configuration wizard only
chmod +x scripts/configure.sh
./scripts/configure.sh
```

#### Step 2: Run Installation
```bash
# Run installation with existing configuration
./install.sh
```

## 📋 What Gets Automatically Configured

### 🌐 Core Services
- **PostgreSQL Database** - Complete schema with PowerDNS integration
- **Redis Cache** - Session storage and message queue
- **PowerDNS** - DNS server for domain management
- **MinIO** - S3-compatible storage for SSL certificates
- **Nginx** - Reverse proxy with SSL termination and security headers

### 🎛️ Management Interfaces
- **Admin Dashboard** - React-based administration interface
- **Client Dashboard** - Customer portal for CDN management
- **API Backend** - Flask-based REST API with JWT authentication
- **Monitoring** - Prometheus metrics and Grafana dashboards

### 🔒 Security Features
- **SSL Certificates** - Automatic ACME (Let's Encrypt) or self-signed fallback
- **SSH Key Management** - Automated key generation for edge servers
- **Firewall Configuration** - UFW/firewalld rules for secure access
- **Secure Defaults** - Auto-generated passwords and secrets

### ⚙️ Automation Features
- **Auto-scaling** - Cloud provider integration for edge servers
- **Monitoring** - Health checks and performance metrics
- **Backups** - Automated database and configuration backups
- **Log Rotation** - Automated log management
- **Service Management** - Systemd integration for auto-start

## 🔧 Configuration Options

The installation wizard will prompt for:

### Required Configuration
- **CDN Domain** - Main content delivery domain (e.g., `cdn.yourdomain.com`)
- **API Domain** - Management API domain (e.g., `api.yourdomain.com`)
- **Admin Domain** - Administration interface (e.g., `admin.yourdomain.com`)
- **Client Domain** - Customer portal (e.g., `client.yourdomain.com`)
- **Admin Credentials** - Email and password for admin user

### Optional Configuration
- **Cloud Provider APIs** - DigitalOcean, Linode, Vultr, Hetzner tokens
- **SSL Email** - Email for Let's Encrypt certificates
- **MaxMind GeoIP** - Geographic insights and analytics

## 📊 Access Your Services

After installation, access your services at:

### Web Interfaces
- **Admin Dashboard**: `https://admin.yourdomain.com` or `http://localhost:3000`
- **Client Dashboard**: `https://client.yourdomain.com` or `http://localhost:3002`
- **API Endpoint**: `https://api.yourdomain.com` or `http://localhost:5000`
- **Grafana Monitoring**: `http://localhost:3001` (admin/[generated-password])
- **Prometheus Metrics**: `http://localhost:9090`

### Default Credentials
- **Admin Email**: As configured during setup
- **Admin Password**: As configured during setup
- **Grafana**: admin/[shown during installation]

## 🛠️ Management Commands

### Service Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart api

# View service logs
docker-compose logs -f [service-name]

# View service status
docker-compose ps
```

### System Service Management
```bash
# Start CDN platform
sudo systemctl start cachenet

# Stop CDN platform
sudo systemctl stop cachenet

# Enable auto-start on boot
sudo systemctl enable cachenet

# Check service status
sudo systemctl status cachenet
```

### SSL Certificate Management
```bash
# Setup SSL certificates
./scripts/setup-ssl.sh setup

# Issue certificate for specific domain
./scripts/setup-ssl.sh issue example.com

# Renew all certificates
./scripts/setup-ssl.sh renew

# Generate self-signed certificate
./scripts/setup-ssl.sh self-signed example.com
```

### Configuration Management
```bash
# Reconfigure environment
./scripts/configure.sh

# Generate new Nginx configuration
./scripts/setup-nginx.sh generate

# Test Nginx configuration
./scripts/setup-nginx.sh test

# Reload Nginx
./scripts/setup-nginx.sh reload
```

### Database Management
```bash
# Initialize database (run once)
./scripts/init-database.sh

# Backup database
./scripts/backup-db.sh

# View database logs
docker-compose logs db
```

## 🔍 Troubleshooting

### Check Service Health
```bash
# Check all service status
docker-compose ps

# Check specific service logs
docker-compose logs [service-name]

# Check system logs
journalctl -u cachenet -f
```

### Common Issues

#### Services Not Starting
```bash
# Check Docker status
sudo systemctl status docker

# Check available resources
df -h
free -m

# Check for port conflicts
sudo netstat -tulpn | grep :80
```

#### SSL Certificate Issues
```bash
# Check certificate status
./scripts/setup-ssl.sh

# Generate self-signed certificates
./scripts/setup-ssl.sh self-signed yourdomain.com
```

#### Database Connection Issues
```bash
# Check database status
docker-compose exec db pg_isready -U cachenet -d cachenet

# Restart database
docker-compose restart db
```

## 📚 Next Steps

After successful installation:

1. **Configure DNS** - Point your domains to this server
2. **Add Cloud Providers** - Configure API keys in admin dashboard
3. **Deploy Edge Servers** - Add your first edge locations
4. **Configure Domains** - Set up your first CDN domain
5. **Monitor Performance** - Use Grafana dashboards

## 🆘 Support

- **Logs Location**: `./logs/` directory
- **Configuration**: `.env` file
- **Backups**: `./backups/` directory
- **Documentation**: Check README.md for detailed information

For issues, check the logs and verify your configuration meets the system requirements:
- **OS**: Linux (Ubuntu/Debian recommended)
- **RAM**: 4GB minimum
- **Disk**: 50GB minimum
- **Network**: Ports 80, 443, 53, 3000-3002, 5000, 9090 accessible