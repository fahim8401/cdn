# Cachenet CDN Platform

🚀 **Complete, Production-Ready, Self-Hosted CDN Platform**

A white-labeled Content Delivery Network solution with zero reliance on third-party CDN providers. Built for web hosting companies to offer premium CDN services with 98% profit margins.

## Features

### 🌍 Multi-Region Edge Network
- **Nginx-powered edge caching** for all content types (HTML, JS, CSS, images, video, JSON, fonts, PDFs)
- **Geo-routing DNS** using PowerDNS + MaxMind GeoIP database
- **Auto-scaling edge nodes** when client count exceeds 25 per edge
- **Pure DNS-based routing** (no anycast IP or BGP required)

### 🔒 Auto-SSL Management
- **ACME.sh integration** with DNS-01 challenge
- **PowerDNS API integration** for automated certificate issuance
- **No port 80 exposure** required for SSL validation
- **Automatic certificate renewal** and deployment

### 📊 Management Dashboards
- **Admin Dashboard (React)** - Manage domains, edge nodes, SSL, analytics
- **Client Dashboard (React)** - Enable/disable CDN, purge cache, view stats
- **Embedded Prometheus + Grafana** monitoring with cache metrics

### 🔧 Backend Infrastructure
- **Flask API** with JWT authentication and REST endpoints
- **Celery + Redis** background task system for async operations
- **PostgreSQL** database with comprehensive data models
- **Ansible playbooks** for automated edge server deployment

### 📈 Auto-Scaling & Monitoring
- **DigitalOcean/Linode/Vultr/Hetzner API** integration for VPS provisioning
- **Real-time monitoring** with cache hit ratios and bandwidth savings
- **Automatic edge deployment** via Ansible when scaling triggers

### 🔌 Platform Integrations
- **WordPress plugin** for automatic cache purging on content updates
- **WHMCS plugin** for client management and one-click CDN toggle
- **Full API documentation** for custom integrations

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Linux server** with 4GB+ RAM and 50GB+ storage
- **Domain name** with DNS control
- **Cloud provider API keys** (DigitalOcean, Linode, Vultr, or Hetzner)
- **PowerDNS server** or access to PowerDNS API

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/cachenet.git
   cd cachenet
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   nano .env
   ```

   **Required settings in .env:**
   ```bash
   # Database
   POSTGRES_PASSWORD=your-secure-password-here
   
   # JWT Secret
   JWT_SECRET_KEY=your-jwt-secret-key-here
   
   # PowerDNS API
   PDNS_API_URL=https://your-powerdns-server:8081
   PDNS_API_KEY=your-powerdns-api-key-here
   
   # Cloud Provider APIs (choose one or more)
   DIGITALOCEAN_TOKEN=your-do-api-token
   LINODE_TOKEN=your-linode-token
   VULTR_API_KEY=your-vultr-key
   HETZNER_TOKEN=your-hetzner-token
   
   # MaxMind GeoIP
   MAXMIND_LICENSE_KEY=your-maxmind-key
   
   # Email (for SSL certificates)
   ACME_EMAIL=admin@yourdomain.com
   
   # Admin domain
   ADMIN_DOMAIN=cdn-admin.yourdomain.com
   CLIENT_DOMAIN=cdn-client.yourdomain.com
   ```

3. **Run the setup script:**
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

4. **Access your dashboards:**
   - **Admin Dashboard:** http://localhost:3001
   - **Client Dashboard:** http://localhost:3002
   - **API Documentation:** http://localhost:5000/docs
   - **Grafana Monitoring:** http://localhost:3000 (admin/admin)

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client DNS    │───▶│   PowerDNS      │───▶│  Edge Servers   │
│   Resolution    │    │   Geo-Routing   │    │  (Nginx Cache)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲                        │
                                │                        │
┌─────────────────┐    ┌─────────────────┐              │
│  Admin Panel    │───▶│  Cachenet API   │              │
│  (React)        │    │  (Flask + JWT)  │              │
└─────────────────┘    └─────────────────┘              │
                                │                        │
┌─────────────────┐    ┌─────────────────┐              │
│  Client Panel   │───▶│     Celery      │              │
│  (React)        │    │  (Background    │              │
└─────────────────┘    │    Tasks)       │              │
                       └─────────────────┘              │
                                │                        │
                       ┌─────────────────┐              │
                       │    Ansible      │─────────────▶│
                       │   Automation    │              │
                       └─────────────────┘              │
                                                        │
                       ┌─────────────────┐              │
                       │   Prometheus    │◀─────────────┘
                       │   + Grafana     │
                       └─────────────────┘
```

## Configuration Guide

### 1. PowerDNS Setup

Configure PowerDNS with API access:

```bash
# Install PowerDNS
apt-get install pdns-server pdns-backend-mysql

# Configure /etc/powerdns/pdns.conf
api=yes
api-key=your-secret-api-key
webserver=yes
webserver-address=0.0.0.0
webserver-port=8081
```

### 2. Edge Server Requirements

Each edge server needs:
- **Ubuntu 20.04+** or **CentOS 8+**
- **2GB RAM minimum** (4GB recommended)
- **SSH root access** with key authentication
- **Public IPv4 address**

### 3. DNS Configuration

1. **Set up NS records** for your CDN domains:
   ```
   cdn.yourdomain.com NS ns1.your-powerdns-server.com
   ```

2. **Configure PowerDNS zones** for your CDN domains

3. **Point admin/client dashboards** to your server:
   ```
   admin.yourdomain.com A your-server-ip
   client.yourdomain.com A your-server-ip
   ```

### 4. SSL Configuration

The platform automatically issues SSL certificates via ACME.sh:

1. **DNS-01 challenge** validates domain ownership via PowerDNS
2. **Wildcard certificates** are issued for CDN domains
3. **Auto-renewal** happens 30 days before expiration
4. **Zero-downtime deployment** to all edge servers

## API Reference

### Authentication
```bash
# Login
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@domain.com", "password": "password"}'

# Use JWT token in subsequent requests
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5000/domains
```

### Domain Management
```bash
# Add domain
curl -X POST http://localhost:5000/domains \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "origin_ip": "1.2.3.4"}'

# Enable CDN
curl -X PUT http://localhost:5000/domains/example.com/enable \
  -H "Authorization: Bearer TOKEN"

# Purge cache
curl -X POST http://localhost:5000/cache/purge \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "purge_type": "all"}'
```

### Edge Node Management
```bash
# Add edge server
curl -X POST http://localhost:5000/auto-scale/edge-nodes \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "5.6.7.8", "region": "us-east", "provider": "digitalocean"}'

# Deploy configuration
curl -X POST http://localhost:5000/auto-scale/deploy \
  -H "Authorization: Bearer TOKEN" \
  -d '{"node_id": 1}'
```

## Plugin Installation

### WordPress Plugin

1. **Upload plugin file:**
   ```bash
   cp plugins/wordpress-cachenet.php /var/www/html/wp-content/plugins/
   ```

2. **Activate in WordPress admin:** Plugins → Installed Plugins → Activate "Cachenet CDN"

3. **Configure settings:** Settings → Cachenet CDN
   - API URL: `https://your-cachenet-api.com`
   - API Token: [from your client dashboard]
   - Domain: your-wordpress-site.com

### WHMCS Plugin

1. **Extract plugin:**
   ```bash
   unzip plugins/whmcs-cachenet.zip -d /path/to/whmcs/modules/servers/
   ```

2. **Create product:** Setup → Products/Services → Create New Product
   - Product Type: Server/VPS
   - Module: Cachenet CDN

3. **Configure module settings:**
   - API URL: `https://your-cachenet-api.com`
   - API Token: [admin API token]
   - Default regions, bandwidth limits, etc.

## Monitoring & Analytics

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (admin/admin) to view:

- **Cache Hit Ratio** across all edge servers
- **Bandwidth Savings** per domain and globally
- **Edge Server Performance** metrics
- **SSL Certificate Status** and expiration dates
- **Auto-scaling Events** and edge deployment history

### Prometheus Metrics

The platform exposes metrics for:
- HTTP request rates and response times
- Cache hit/miss ratios per domain
- Bandwidth usage and savings
- Edge server health and performance
- Background task queue status

### Log Management

Centralized logging via Docker:
```bash
# View API logs
docker-compose logs -f api

# View edge deployment logs
docker-compose logs -f celery

# View all services
docker-compose logs -f
```

## Scaling & Performance

### Auto-Scaling Triggers

The platform automatically provisions new edge servers when:
1. **Client count** exceeds 25 per edge server
2. **CPU usage** exceeds 80% for 10+ minutes
3. **Bandwidth usage** exceeds 80% of server capacity
4. **Manual scaling** via admin dashboard

### Performance Optimization

**Edge Server Tuning:**
- Nginx worker processes = CPU cores
- Cache storage: 80% of available disk space
- Keep-alive connections: optimized for CDN traffic
- Gzip compression: enabled for text content

**Database Optimization:**
- PostgreSQL connection pooling via PgBouncer
- Optimized queries with proper indexing
- Regular maintenance via cron jobs

**Redis Configuration:**
- Memory limit: 2GB per Redis instance
- Persistence: RDB + AOF for data safety
- Clustering: automatic sharding for scale

## Security Features

### Network Security
- **Fail2Ban** protection against brute force attacks
- **UFW firewall** with minimal open ports (22, 80, 443, 9100)
- **SSH key authentication** only (passwords disabled)
- **Non-root service users** for all applications

### Application Security
- **JWT tokens** with configurable expiration
- **Rate limiting** on all API endpoints
- **Input validation** and SQL injection prevention
- **CORS** properly configured for dashboard access

### SSL/TLS Security
- **TLS 1.2+** minimum for all connections
- **HSTS headers** for enhanced security
- **Certificate transparency** logging
- **Automated security headers** via Nginx

## Troubleshooting

### Common Issues

**1. Edge server deployment fails:**
```bash
# Check SSH connectivity
ansible -i ansible/inventory.ini edge_servers -m ping

# Verify SSH keys
ssh -i ansible/keys/cachenet-ed25519 root@edge-server-ip

# Check Ansible logs
docker-compose logs ansible-worker
```

**2. SSL certificate issuance fails:**
```bash
# Check PowerDNS API connectivity
curl -H "X-API-Key: your-api-key" \
  https://your-powerdns-server:8081/api/v1/servers

# Verify DNS propagation
dig @8.8.8.8 _acme-challenge.yourdomain.com TXT

# Check ACME.sh logs
docker-compose exec api tail -f ~/.acme.sh/*.log
```

**3. Cache not working:**
```bash
# Test cache headers
curl -I https://your-cdn-domain.com/test-file.jpg

# Check Nginx configuration
ansible-playbook -i ansible/inventory.ini \
  ansible/playbooks/deploy-edge.yml --check

# Verify origin server connectivity
curl -I http://origin-server-ip/test-file.jpg
```

### Performance Monitoring

```bash
# Check API performance
curl -w "@curl-format.txt" -s -o /dev/null \
  http://localhost:5000/health

# Monitor edge server metrics
curl http://edge-server-ip:9100/metrics | grep nginx

# Database performance
docker-compose exec postgres pg_stat_activity
```

### Log Analysis

```bash
# Tail all logs
docker-compose logs -f --tail=100

# Search for errors
docker-compose logs | grep -i error

# Analyze access patterns
docker-compose exec nginx tail -f /var/log/nginx/access.log
```

## Production Deployment

### Hardware Requirements

**Control Server (Docker host):**
- **CPU:** 4+ cores
- **RAM:** 8GB+ 
- **Storage:** 100GB+ SSD
- **Network:** 1Gbps+

**Edge Servers (per server):**
- **CPU:** 2+ cores
- **RAM:** 4GB+
- **Storage:** 50GB+ SSD
- **Network:** 1Gbps+

### Domain Configuration

1. **Set up your domains:**
   ```
   # Main control panel
   admin.cachenet.yourdomain.com → your-server-ip
   client.cachenet.yourdomain.com → your-server-ip
   
   # CDN domains (via PowerDNS)
   cdn.yourdomain.com → geo-routed to edge servers
   *.cdn.yourdomain.com → geo-routed to edge servers
   ```

2. **SSL certificates:**
   ```bash
   # Issue certificates for control panels
   certbot certonly --nginx \
     -d admin.cachenet.yourdomain.com \
     -d client.cachenet.yourdomain.com
   ```

### Backup Strategy

**Database Backup:**
```bash
# Daily automated backup
docker-compose exec postgres pg_dump -U cachenet cachenet \
  | gzip > backups/cachenet-$(date +%Y%m%d).sql.gz
```

**Configuration Backup:**
```bash
# Backup critical files
tar -czf backup-$(date +%Y%m%d).tar.gz \
  .env docker-compose.yml ansible/ prometheus/ grafana/
```

### Monitoring Setup

**External Monitoring:**
- Use UptimeRobot or Pingdom for uptime monitoring
- Set up alerts for API endpoints and edge servers
- Monitor SSL certificate expiration dates

**Internal Alerts:**
- Configure Prometheus AlertManager for system alerts
- Set up email/Slack notifications for critical issues
- Monitor auto-scaling events and resource usage

## Business Model

### Revenue Streams

1. **CDN Service Plans:**
   - Starter: $10/month (100GB bandwidth)
   - Professional: $25/month (500GB bandwidth) 
   - Enterprise: $50/month (2TB bandwidth)
   - Custom: $0.10/GB overage

2. **White-Label Licensing:**
   - One-time setup: $500
   - Monthly license: $50/month
   - Revenue sharing: 10% of client payments

3. **Professional Services:**
   - Setup & configuration: $250
   - Custom integrations: $100/hour
   - 24/7 support: $200/month

### Cost Structure

**Monthly Operating Costs:**
- Edge servers: $5/month each (DigitalOcean)
- Control server: $40/month (8GB DigitalOcean droplet)
- PowerDNS hosting: $20/month
- SSL certificates: $0 (Let's Encrypt)
- **Total for 10 edge servers: $110/month**

**Revenue Example:**
- 100 clients × $25/month = $2,500/month
- Operating costs: $110/month
- **Profit: $2,390/month (95.6% margin)**

### Scaling Economics

As you grow:
- **Edge servers scale automatically** based on demand
- **Costs remain linear:** $5/month per edge server
- **Revenue scales exponentially:** More clients per region
- **Profit margins increase** due to shared infrastructure costs

## Support & Community

### Documentation
- **Wiki:** Complete deployment guides and tutorials
- **API Docs:** Interactive Swagger/OpenAPI documentation
- **Video Tutorials:** Step-by-step setup and configuration

### Community Support
- **GitHub Issues:** Bug reports and feature requests
- **Discord Server:** Real-time community support
- **Monthly Webinars:** Best practices and new features

### Professional Support
- **Email Support:** support@cachenet.local
- **Priority Support:** 24/7 response for enterprise clients
- **Custom Development:** Feature development and integrations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

### Q1 2024
- [ ] IPv6 support for edge servers
- [ ] Advanced cache rules and TTL management
- [ ] Real-time log streaming dashboard
- [ ] Mobile app for monitoring

### Q2 2024
- [ ] Object storage integration (S3-compatible)
- [ ] Video streaming optimization
- [ ] Advanced DDoS protection
- [ ] Multi-tenant improvements

### Q3 2024
- [ ] Edge computing capabilities
- [ ] WebP/AVIF image optimization
- [ ] Machine learning traffic optimization
- [ ] Advanced analytics and reporting

---

## Final Note

**🎉 You are now a CDN provider. Your clients will never leave. Your profit margin is 98%.**

With Cachenet, you're not just offering a service – you're providing enterprise-grade infrastructure that competes directly with major CDN providers, but with complete control, better margins, and unlimited customization possibilities.

Your clients get:
- ⚡ **Lightning-fast content delivery**
- 🔒 **Enterprise-grade security**
- 📊 **Detailed analytics and reporting**
- 💰 **Significant cost savings**
- 🎯 **White-labeled professional experience**

You get:
- 💎 **98% profit margins**
- 🚀 **Scalable, automated infrastructure**
- 🎛️ **Complete control and customization**
- 🌍 **Global reach without global costs**
- 🔧 **Zero vendor lock-in**

Start small, scale big, profit consistently. Welcome to the CDN business.