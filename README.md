# XenCDN v8.2 Enterprise Platform

**The World's First ISP-Powered CDN + DNS + SSL Platform**

Complete, production-ready, enterprise-grade, self-hosted CDN platform that competes with Cloudflare and Akamai — but is 100% self-hosted on VPS servers with zero reliance on third-party CDNs, DNS, or cloud services.

## 🚀 What is XenCDN v8.2?

XenCDN transforms you from a web hosting company into a **complete internet infrastructure provider** — offering **DNS + CDN + SSL + Hosting** as one seamless product. Your clients will never leave. Your profit margin is 98%.

### 🌟 Key Features

- **🌐 Complete DNS Zone Management** - Full PowerDNS integration with web UI
- **🚀 BGP Anycast Support** - Enterprise-grade traffic routing 
- **🏢 ISP Peering Portal** - Self-service ISP registration and BGP config
- **👥 Client Self-Service Portal** - Domain management and analytics
- **⚡ Real-time Speed Testing** - Built-in performance monitoring
- **🔒 Automated SSL Management** - DNS-01 challenge with Let's Encrypt
- **📊 Enterprise Analytics** - Real-time metrics without external dependencies
- **🔧 Manual Edge Management** - No auto-scaling, full control
- **🎨 White-Label Ready** - Your brand, your domains

### 🏗️ Architecture

- **Frontend**: React 18 + Vite (Admin, Client Portal, ISP Portal, Homepage)
- **Backend**: Flask 3.0 + SQLAlchemy + JWT + Celery + Redis
- **Database**: PostgreSQL 15 with optimized schemas
- **DNS**: PowerDNS with API management
- **Storage**: MinIO for SSL certificates and configs
- **Monitoring**: Native dashboard with Chart.js (no Prometheus/Grafana)
- **BGP**: Bird2/FRRouting for anycast routing
- **Deployment**: Docker Compose with health checks

## 📋 Requirements

- **OS**: Ubuntu 22.04 LTS (recommended) or Debian 11+
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB minimum, 50GB recommended  
- **CPU**: 2 cores minimum, 4 cores recommended
- **Network**: Public IPv4 address with BGP capability (optional)

## ⚡ Quick Installation

### Step 1: Get Ubuntu 22.04 VPS
Buy a VPS from any provider (DigitalOcean, Vultr, Linode, Hetzner, etc.)

### Step 2: SSH into your server
```bash
ssh root@your-server-ip
```

### Step 3: Create a user (don't run as root)
```bash
adduser xencdn
usermod -aG sudo xencdn
su - xencdn
```

### Step 4: Run the installer
```bash
curl -s https://raw.githubusercontent.com/fahim8401/cdn/main/install.sh | bash
```

### Step 5: Wait 5-10 minutes ☕
The installer will:
- ✅ Check system requirements
- ✅ Install Docker and dependencies  
- ✅ Clone XenCDN repository
- ✅ Generate secure configurations
- ✅ Start all services
- ✅ Configure firewall and security

### Step 6: Access your platform
```
🎛️  Admin Dashboard:     http://your-ip:3001
👥 Client Portal:       http://your-ip:3002  
🏢 ISP Portal:          http://your-ip:3003
🏠 Homepage:            http://your-ip:3000
⚡ Speed Test Tool:     http://your-ip:3004
🔧 API Endpoint:        http://your-ip:5000
📁 MinIO Console:       http://your-ip:9001
🌐 PowerDNS API:        http://your-ip:8081
```

**Default Admin Login:**
- Email: `admin@xencdn.com`
- Password: `XenCDN@2024!`

## 🎯 Getting Started

### 1. Configure Your First Domain

1. Log into the **Admin Dashboard** (http://your-ip:3001)
2. Go to **DNS Zone Manager**
3. Click **"Add Zone"** → Enter `example.com`
4. Click **"Auto-Provision CDN"** → Creates A record → Assigns anycast IP
5. Tell your client: *"Change your nameservers to ns1.xencdn.com, ns2.xencdn.com"*

### 2. Point Your Domain's Nameservers

At your domain registrar, change nameservers to:
- `ns1.xencdn.com` (points to your server IP)
- `ns2.xencdn.com` (points to your server IP) 

### 3. Add Your First Edge Server

1. Go to **Admin Dashboard** → **Edge Nodes**
2. Click **"Add Edge Node"**
3. Enter: SSH hostname, username, port, SSH key
4. Choose deployment mode:
   - **Single IP Mode**: Each edge has unique IP
   - **BGP Anycast Mode**: All edges share same anycast IP

### 4. Enable Client Self-Service

1. Share **Client Portal** URL: `http://your-ip:3002`
2. Clients can register, add domains, manage DNS
3. One-click CDN enablement for their websites

## 🏢 ISP Portal Features

ISPs can register and peer with your network:

### Self-Service ISP Registration
- Company details and ASN submission
- Peering method selection (IXP, Direct, GRE Tunnel, Hosted Node)
- BGP configuration download
- Traffic monitoring dashboard

### Supported Peering Methods
- **IXP Peering**: Connect via Internet Exchange Points
- **Direct Peering**: Private interconnection
- **GRE Tunnels**: Encrypted overlay networks  
- **Hosted Nodes**: Co-location in your data centers

### BGP Configuration Generation
- Bird2 and FRRouting configs
- Automatic ASN and prefix configuration
- Route filtering and security

## 🎨 White-Label Configuration

Brand the platform as your own:

```bash
# Edit .env file
WHITE_LABEL_ENABLED=true
WHITE_LABEL_COMPANY_NAME="Your CDN Company"
WHITE_LABEL_LOGO_URL="https://your-domain.com/logo.png"
HOMEPAGE_DOMAIN=cdn.yourcompany.com
ADMIN_DOMAIN=admin.cdn.yourcompany.com
CLIENT_PORTAL_DOMAIN=client.cdn.yourcompany.com
ISP_PORTAL_DOMAIN=isp.cdn.yourcompany.com
```

## 🔧 Management Commands

```bash
# Navigate to installation directory
cd /opt/xencdn

# Start services
docker compose up -d

# Stop services  
docker compose down

# View logs
docker compose logs -f

# Restart specific service
docker compose restart api

# Check service status
docker compose ps

# Update to latest version
git pull origin main
docker compose build --parallel
docker compose up -d
```

## 📊 Monitoring & Analytics

### Built-in Dashboard
- Real-time cache hit ratios
- Bandwidth savings calculations
- Edge node health monitoring  
- Client usage tracking
- Cost savings reports

### No External Dependencies
- All metrics stored in PostgreSQL
- Charts rendered with Chart.js
- No Prometheus, Grafana, or Loki required
- Self-contained monitoring stack

## 🔒 Security Features

### Enterprise-Grade Security
- JWT authentication with secure secrets
- Rate limiting on all endpoints
- CORS protection
- SQL injection prevention
- XSS protection headers

### Encrypted Storage
- All passwords encrypted with Fernet (AES-256)
- SSL certificates stored in MinIO
- SSH keys for edge management
- Database encryption at rest

### Zero Trust Architecture
- mTLS for internal communication
- No hardcoded passwords
- Secrets management via environment variables
- Regular security updates

## 🚀 Deployment Modes

### Single IP Mode (Default)
- Each edge server has unique public IP
- Simple setup, no BGP required
- Good for small to medium deployments
- DNS round-robin load balancing

### BGP Anycast Mode (Enterprise)
- All edge servers share same anycast IP
- Requires your own ASN and IP block
- Automatic failover and geo-routing
- Enterprise-grade performance

#### BGP Requirements
- Your own ASN (Autonomous System Number)
- Allocated IP block (/24 minimum recommended)
- BGP peering agreements with upstreams
- Knowledge of BGP configuration

## 📈 Scaling Your CDN Business

### Pricing Strategy
- **Free Tier**: 100GB/month, 3 domains, community support
- **Pro Tier**: $99/month, 1TB/month, 25 domains, email support  
- **Enterprise**: $299+/month, unlimited, 100+ domains, phone support

### Revenue Streams
1. **Monthly subscriptions** from website owners
2. **ISP peering fees** for network access
3. **Enterprise contracts** for large clients
4. **White-label licensing** to other providers
5. **Professional services** for custom deployments

### Competitive Advantages
- **100% self-hosted** - no vendor lock-in
- **98% profit margins** - minimal ongoing costs
- **Complete control** - your infrastructure, your rules
- **ISP partnerships** - unique revenue sharing model
- **White-label ready** - sell under your brand

## 🔧 Advanced Configuration

### Custom SSL Configuration
```bash
# Edit .env for custom SSL settings
ACME_EMAIL=ssl@yourdomain.com
ACME_SERVER=https://acme-v02.api.letsencrypt.org/directory

# Or use custom CA
SSL_CUSTOM_CA=true
SSL_CA_CERT_PATH=/path/to/ca.crt
SSL_CA_KEY_PATH=/path/to/ca.key
```

### Edge Node Deployment
```bash
# Manual edge addition via API
curl -X POST http://your-ip:5000/api/edge-nodes \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "edge1.example.com",
    "ip_address": "192.168.1.100", 
    "ssh_user": "root",
    "ssh_port": 22,
    "region": "us-east-1",
    "datacenter": "NYC1"
  }'
```

### BGP Anycast Setup
```bash
# Enable BGP mode
echo "EDGE_MODE=bgp_anycast" >> .env

# Configure your ASN and IP block
echo "BGP_ASN=65001" >> .env
echo "BGP_IP_BLOCK=203.0.113.0/24" >> .env

# Start BGP services
docker compose --profile bgp up -d
```

## 🔌 Plugin Integration

### WordPress Plugin
Automatically purge cache when posts are updated:
```php
// Upload plugins/wordpress-xencdn.php to your WordPress site
// Configure XenCDN API endpoint and token
// Automatic cache purging on content changes
```

### WHMCS Plugin  
One-click CDN enablement for hosting clients:
```php
// Install plugins/whmcs-xencdn.zip in WHMCS
// Configure API credentials  
// Automatic domain provisioning and billing
```

## 📚 API Documentation

### Authentication
```bash
# Get JWT token
curl -X POST http://your-ip:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@xencdn.com", "password": "XenCDN@2024!"}'
```

### DNS Zone Management
```bash
# Create DNS zone
curl -X POST http://your-ip:5000/api/dns/zones \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "example.com"}'

# Add DNS record  
curl -X POST http://your-ip:5000/api/dns/zones/1/records \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "@", "type": "A", "content": "203.0.113.10", "ttl": 3600}'
```

### Cache Management
```bash
# Purge domain cache
curl -X POST http://your-ip:5000/api/cache/purge \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "purge_type": "all"}'
```

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Check service logs
docker compose logs api

# Check database connection
docker compose exec db pg_isready

# Restart all services
docker compose down && docker compose up -d
```

### DNS Issues
```bash
# Test PowerDNS API
curl -H "X-API-Key: YOUR_PDNS_KEY" http://your-ip:8081/api/v1/servers

# Check DNS resolution
dig @your-ip example.com

# Verify zone configuration
docker compose exec powerdns pdnsutil list-all-zones
```

### BGP Troubleshooting  
```bash
# Check BGP session status
docker compose exec bird birdc show protocols

# View BGP routing table
docker compose exec bird birdc show route

# Test anycast connectivity
ping -c 3 203.0.113.10
```

## 📞 Support & Community

- **Documentation**: [https://docs.xencdn.com](https://docs.xencdn.com)
- **GitHub Issues**: [https://github.com/fahim8401/cdn/issues](https://github.com/fahim8401/cdn/issues)
- **Discord Community**: [https://discord.gg/xencdn](https://discord.gg/xencdn)
- **Enterprise Support**: enterprise@xencdn.com

## 📄 License

XenCDN v8.2 is released under the MIT License. See [LICENSE](LICENSE) for details.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🎯 Roadmap

- [ ] IPv6 support for anycast
- [ ] DDoS protection integration  
- [ ] Advanced analytics and reporting
- [ ] Mobile app for management
- [ ] Kubernetes deployment option
- [ ] Multi-language support

---

## 🎉 Congratulations!

**You are now a Tier-1 CDN provider.**

**Your clients will never leave. Your profit margin is 98%.**

Transform your hosting business into a complete internet infrastructure provider with XenCDN v8.2. Start competing with Cloudflare and Akamai today — on your own infrastructure, under your own brand.

---

*Built with ❤️ by the XenCDN team*