# Cachenet Enterprise CDN API Documentation

## Overview

The Cachenet Enterprise CDN API provides programmatic access to all CDN management functions including domain configuration, cache management, SSL certificates, edge node monitoring, and analytics. The API follows RESTful principles and uses JSON for data exchange.

## Base URL

```
Production: https://api.cachenet.enterprise
Staging: https://staging-api.cachenet.enterprise
Development: http://localhost:5000
```

## Authentication

All API requests require authentication using JWT Bearer tokens.

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user",
    "is_admin": false
  }
}
```

### Using the Token
Include the JWT token in the Authorization header:
```http
Authorization: Bearer YOUR_JWT_TOKEN
```

## Rate Limiting

- **100 requests per minute** per API key
- **1000 requests per hour** per API key
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`: Request limit per window
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when window resets

## Response Format

All API responses follow a consistent format:

**Success Response:**
```json
{
  "data": { ... },
  "message": "Success message",
  "timestamp": "2024-09-21T10:30:00Z"
}
```

**Error Response:**
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": { ... },
  "timestamp": "2024-09-21T10:30:00Z"
}
```

## HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

---

## 🌐 Domain Management

### List Domains
```http
GET /api/domains?page=1&per_page=20&status=active&search=example.com
```

**Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)
- `status` (optional): Filter by status (`pending`, `active`, `suspended`, `error`)
- `search` (optional): Search by domain name

**Response:**
```json
{
  "domains": [
    {
      "id": 1,
      "domain_name": "example.com",
      "origin_server": "https://origin.example.com",
      "cdn_enabled": true,
      "ssl_enabled": true,
      "cache_ttl": 3600,
      "status": "active",
      "created_at": "2024-09-01T10:00:00Z",
      "updated_at": "2024-09-21T10:00:00Z"
    }
  ],
  "total": 1,
  "pages": 1,
  "current_page": 1,
  "per_page": 20
}
```

### Create Domain
```http
POST /api/domains
Content-Type: application/json

{
  "domain_name": "example.com",
  "origin_server": "https://origin.example.com",
  "cache_ttl": 3600
}
```

**Response:**
```json
{
  "message": "Domain created successfully",
  "domain": {
    "id": 1,
    "domain_name": "example.com",
    "origin_server": "https://origin.example.com",
    "cdn_enabled": true,
    "ssl_enabled": false,
    "cache_ttl": 3600,
    "purge_key": "abc123def456",
    "status": "pending",
    "created_at": "2024-09-21T10:00:00Z"
  }
}
```

### Get Domain Details
```http
GET /api/domains/{domain_id}
```

### Update Domain
```http
PUT /api/domains/{domain_id}
Content-Type: application/json

{
  "origin_server": "https://new-origin.example.com",
  "cache_ttl": 7200,
  "cdn_enabled": true
}
```

### Delete Domain
```http
DELETE /api/domains/{domain_id}
```

### Toggle CDN Status
```http
POST /api/domains/{domain_id}/toggle
```

### Regenerate Purge Key
```http
POST /api/domains/{domain_id}/regenerate-purge-key
```

---

## 🗑️ Cache Management

### Purge Domain Cache
```http
POST /api/cache/purge/domain
Content-Type: application/json

{
  "domain_id": 1
}
```

### Purge URL Cache
```http
POST /api/cache/purge/url
Content-Type: application/json

{
  "domain_id": 1,
  "url_path": "/images/logo.png"
}
```

### Purge Cache by Key (Webhook)
```http
POST /api/cache/purge/by-key
Content-Type: application/json

{
  "purge_key": "abc123def456",
  "urls": ["/page1.html", "/images/*"]
}
```

### Get Cache Statistics
```http
GET /api/cache/stats/domain/{domain_id}?days=7
```

**Response:**
```json
{
  "domain_id": 1,
  "period_days": 7,
  "total_requests": 1500000,
  "cache_hits": 1275000,
  "cache_misses": 225000,
  "cache_hit_ratio": 85.0,
  "bandwidth_saved_gb": 456.7,
  "avg_response_time_ms": 45,
  "daily_stats": [
    {
      "date": "2024-09-21",
      "requests": 215000,
      "cache_hits": 182750,
      "cache_hit_ratio": 85.0,
      "bandwidth_saved_gb": 65.2
    }
  ]
}
```

---

## 🔒 SSL Certificate Management

### List SSL Certificates
```http
GET /api/ssl/certificates?page=1&status=active
```

**Response:**
```json
{
  "certificates": [
    {
      "id": 1,
      "domain_name": "example.com",
      "issuer": "Let's Encrypt",
      "status": "active",
      "issued_at": "2024-09-01T00:00:00Z",
      "expires_at": "2024-12-01T00:00:00Z",
      "days_until_expiry": 71,
      "auto_renew": true
    }
  ],
  "total": 1,
  "pages": 1
}
```

### Issue SSL Certificate
```http
POST /api/ssl/issue
Content-Type: application/json

{
  "domain_id": 1
}
```

### Renew SSL Certificate
```http
POST /api/ssl/certificates/{cert_id}/renew
```

### Get Expiring Certificates
```http
GET /api/ssl/expiring?days=30
```

---

## 🖥️ Edge Node Management

### List Edge Nodes
```http
GET /api/auto-scale/edge-nodes?page=1&region=us-east&status=active
```

**Response:**
```json
{
  "edge_nodes": [
    {
      "id": 1,
      "name": "edge-us-east-1",
      "hostname": "edge-us-east-1.cachenet.enterprise",
      "ip_address": "203.0.113.10",
      "region": "us-east",
      "country": "US",
      "city": "New York",
      "provider": "digitalocean",
      "status": "active",
      "load_score": 0.65,
      "client_count": 18,
      "max_clients": 25,
      "bandwidth_usage_gb": 1250.5,
      "last_seen": "2024-09-21T10:25:00Z"
    }
  ],
  "total": 1
}
```

### Create Edge Node
```http
POST /api/auto-scale/edge-nodes
Content-Type: application/json

{
  "name": "edge-eu-west-1",
  "ip_address": "203.0.113.20",
  "region": "eu-west",
  "provider": "digitalocean",
  "instance_id": "droplet-123456"
}
```

### Deploy Edge Configuration
```http
POST /api/auto-scale/deploy
Content-Type: application/json

{
  "node_id": 1
}
```

### Get Edge Node Metrics
```http
GET /api/stats/edge-nodes/{edge_id}/metrics?days=7
```

---

## 📊 Analytics & Statistics

### Dashboard Statistics
```http
GET /api/stats/dashboard
```

**Response:**
```json
{
  "period": "30 days",
  "domains": {
    "total": 25,
    "active": 22,
    "pending": 3
  },
  "edge_nodes": {
    "active": 12,
    "total": 15
  },
  "ssl_certificates": {
    "total": 25,
    "active": 22,
    "expiring_soon": 2
  },
  "traffic": {
    "total_requests": 45000000,
    "cache_hit_ratio": 87.5,
    "bandwidth_saved_gb": 12500.75,
    "bandwidth_total_gb": 15000.50,
    "bandwidth_savings_ratio": 83.3,
    "avg_response_time_ms": 42
  }
}
```

### Domain Analytics
```http
GET /api/stats/domains/{domain_id}/analytics?days=30
```

### Bandwidth Report
```http
GET /api/stats/bandwidth-report?days=30
```

**Response:**
```json
{
  "period": "30 days",
  "summary": {
    "total_bandwidth_gb": 15000.50,
    "saved_bandwidth_gb": 12500.75,
    "overall_savings_ratio": 83.3,
    "domains_count": 25
  },
  "domain_breakdown": [
    {
      "domain_name": "example.com",
      "total_bandwidth_gb": 5000.25,
      "saved_bandwidth_gb": 4250.75,
      "savings_ratio": 85.0,
      "total_requests": 15000000
    }
  ]
}
```

### Real-time Statistics
```http
GET /api/stats/real-time
```

---

## 🚀 Auto-scaling

### Get Scaling Statistics
```http
GET /api/auto-scale/stats
```

### Trigger Scale Up
```http
POST /api/auto-scale/scale-up
Content-Type: application/json

{
  "region": "us-west",
  "provider": "digitalocean"
}
```

### Trigger Scale Down
```http
POST /api/auto-scale/scale-down
Content-Type: application/json

{
  "region": "us-west"
}
```

---

## 👥 User Management (Admin Only)

### List Users
```http
GET /api/auth/users?page=1
```

### Toggle User Status
```http
POST /api/auth/users/{user_id}/toggle
```

---

## 🔧 System Health

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-09-21T10:30:00Z",
  "version": "1.0.0"
}
```

### API Information
```http
GET /api/info
```

---

## 📝 Webhooks

Cachenet supports webhooks for real-time notifications of important events.

### Webhook Events

- `domain.created` - New domain added
- `domain.updated` - Domain configuration changed
- `domain.deleted` - Domain removed
- `ssl.issued` - SSL certificate issued
- `ssl.renewed` - SSL certificate renewed
- `ssl.expiring` - SSL certificate expiring soon
- `edge.provisioned` - New edge node provisioned
- `edge.deleted` - Edge node removed
- `cache.purged` - Cache purge completed
- `scaling.triggered` - Auto-scaling event occurred

### Webhook Payload Example
```json
{
  "event": "ssl.expiring",
  "timestamp": "2024-09-21T10:30:00Z",
  "data": {
    "certificate_id": 1,
    "domain_name": "example.com",
    "expires_at": "2024-10-01T00:00:00Z",
    "days_until_expiry": 10
  }
}
```

### Setting Up Webhooks
```http
POST /api/webhooks
Content-Type: application/json

{
  "url": "https://your-app.com/webhook",
  "events": ["ssl.expiring", "domain.created"],
  "secret": "your-webhook-secret"
}
```

---

## 💡 SDK and Libraries

### Official SDKs

- **Python**: `pip install cachenet-python`
- **Node.js**: `npm install cachenet-js`
- **PHP**: `composer require cachenet/php-sdk`
- **Go**: `go get github.com/cachenet/go-sdk`

### Python Example
```python
from cachenet import CachenetClient

client = CachenetClient(
    api_url="https://api.cachenet.enterprise",
    api_token="your_jwt_token"
)

# List domains
domains = client.domains.list(status="active")

# Purge cache
client.cache.purge_domain(domain_id=1)

# Get statistics
stats = client.stats.dashboard()
```

### JavaScript Example
```javascript
import { CachenetClient } from 'cachenet-js';

const client = new CachenetClient({
  apiUrl: 'https://api.cachenet.enterprise',
  apiToken: 'your_jwt_token'
});

// List domains
const domains = await client.domains.list({ status: 'active' });

// Purge cache
await client.cache.purgeDomain(1);

// Get statistics
const stats = await client.stats.dashboard();
```

---

## 🔍 Error Codes

| Code | Description |
|------|-------------|
| `INVALID_CREDENTIALS` | Authentication failed |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| `DOMAIN_NOT_FOUND` | Requested domain does not exist |
| `DOMAIN_ALREADY_EXISTS` | Domain already exists in system |
| `INVALID_DOMAIN_FORMAT` | Domain name format is invalid |
| `ORIGIN_SERVER_UNREACHABLE` | Cannot connect to origin server |
| `SSL_ISSUANCE_FAILED` | SSL certificate issuance failed |
| `EDGE_NODE_UNAVAILABLE` | Edge node is not responding |
| `RATE_LIMIT_EXCEEDED` | API rate limit exceeded |
| `VALIDATION_ERROR` | Request validation failed |
| `INTERNAL_SERVER_ERROR` | Unexpected server error |

---

## 📞 Support

### API Support
- **Email**: api-support@cachenet.enterprise
- **Documentation**: https://docs.cachenet.enterprise
- **Status Page**: https://status.cachenet.enterprise

### Developer Resources
- **GitHub**: https://github.com/cachenet/api-examples
- **Community Forum**: https://community.cachenet.enterprise
- **Discord**: https://discord.gg/cachenet

---

**API Version**: v1  
**Last Updated**: September 2024  
**Changelog**: https://docs.cachenet.enterprise/changelog

*This API documentation is subject to change. Subscribe to our developer newsletter for updates and new feature announcements.*