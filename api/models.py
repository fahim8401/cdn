#!/usr/bin/env python3
"""
XenCDN v8.1 Platform Database Models
SQLAlchemy models for all platform entities including Client and ISP portals
"""

from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import json
import os
import secrets

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    company = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    api_key = db.Column(db.String(64), unique=True, index=True)
    max_domains = db.Column(db.Integer, default=10)
    max_bandwidth_gb = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    domains = db.relationship('Domain', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    ssl_certificates = db.relationship('SSLCertificate', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company': self.company,
            'phone': self.phone,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'max_domains': self.max_domains,
            'max_bandwidth_gb': self.max_bandwidth_gb,
            'domains_count': self.domains.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ClientRegistration(db.Model):
    """Client registration model for website owners using client portal"""
    __tablename__ = 'client_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    company = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    reset_token = db.Column(db.String(100))
    reset_token_expires = db.Column(db.DateTime)
    plan = db.Column(db.String(20), default='free')  # free, pro, enterprise
    max_domains = db.Column(db.Integer, default=5)
    max_bandwidth_gb = db.Column(db.Integer, default=100)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client_domains = db.relationship('ClientDomain', backref='client', lazy='dynamic', cascade='all, delete-orphan')
    cpanel_configs = db.relationship('ClientCPanels', backref='client', lazy='dynamic', cascade='all, delete-orphan')
    speed_test_logs = db.relationship('SpeedTestLog', backref='client', lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_verification_token(self):
        """Generate email verification token"""
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token
    
    def generate_reset_token(self):
        """Generate password reset token"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
        return self.reset_token
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company': self.company,
            'phone': self.phone,
            'email_verified': self.email_verified,
            'plan': self.plan,
            'max_domains': self.max_domains,
            'max_bandwidth_gb': self.max_bandwidth_gb,
            'is_active': self.is_active,
            'domains_count': self.client_domains.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ISPRegistration(db.Model):
    """ISP registration model for Internet Service Providers"""
    __tablename__ = 'isp_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    contact_phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    website = db.Column(db.String(255))
    country = db.Column(db.String(2))  # ISO country code
    city = db.Column(db.String(100))
    asn = db.Column(db.String(20), nullable=False)  # Autonomous System Number
    peering_method = db.Column(db.String(50))  # 'ixp', 'direct', 'gre_tunnel', 'hosted_node'
    peering_point = db.Column(db.String(255))  # IXP name or location
    public_ip = db.Column(db.String(45))  # IPv4 or IPv6
    anycast_ip = db.Column(db.String(45))  # Assigned anycast IP
    tunnel_endpoint = db.Column(db.String(45))  # For GRE tunnels
    bgp_config = db.Column(db.Text)  # BGP configuration
    status = db.Column(db.String(20), default='pending')  # pending, approved, active, rejected, disconnected
    admin_notes = db.Column(db.Text)
    bandwidth_limit_gbps = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    approver = db.relationship('User', backref='approved_isps')
    traffic_stats = db.relationship('ISPTrafficStats', backref='isp', lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def assign_anycast_ip(self):
        """Assign next available anycast IP from pool"""
        # Simple IP assignment from 203.0.113.10 to 203.0.113.250
        used_ips = db.session.query(ISPRegistration.anycast_ip).filter(
            ISPRegistration.anycast_ip.isnot(None)
        ).all()
        used_ips = [ip[0] for ip in used_ips]
        
        base_ip = "203.0.113."
        for i in range(10, 251):
            candidate_ip = f"{base_ip}{i}"
            if candidate_ip not in used_ips:
                self.anycast_ip = candidate_ip
                return candidate_ip
        
        return None  # No available IPs
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'website': self.website,
            'country': self.country,
            'city': self.city,
            'asn': self.asn,
            'peering_method': self.peering_method,
            'peering_point': self.peering_point,
            'public_ip': self.public_ip,
            'anycast_ip': self.anycast_ip,
            'tunnel_endpoint': self.tunnel_endpoint,
            'status': self.status,
            'bandwidth_limit_gbps': self.bandwidth_limit_gbps,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }

class Domain(db.Model):
    """Domain model for CDN-enabled domains"""
    __tablename__ = 'domains'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    domain_name = db.Column(db.String(255), nullable=False, index=True)
    origin_server = db.Column(db.String(255), nullable=False)
    cdn_enabled = db.Column(db.Boolean, default=True)
    ssl_enabled = db.Column(db.Boolean, default=False)
    ssl_certificate_id = db.Column(db.Integer, db.ForeignKey('ssl_certificates.id'))
    cache_ttl = db.Column(db.Integer, default=3600)  # seconds
    purge_key = db.Column(db.String(64), unique=True, index=True)
    status = db.Column(db.String(20), default='pending')  # pending, active, suspended, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ssl_certificate = db.relationship('SSLCertificate', backref='domains')
    cache_stats = db.relationship('CacheStats', backref='domain', lazy='dynamic', cascade='all, delete-orphan')
    dns_records = db.relationship('DNSRecord', backref='domain', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'domain_name': self.domain_name,
            'origin_server': self.origin_server,
            'cdn_enabled': self.cdn_enabled,
            'ssl_enabled': self.ssl_enabled,
            'ssl_certificate_id': self.ssl_certificate_id,
            'cache_ttl': self.cache_ttl,
            'purge_key': self.purge_key,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ClientDomain(db.Model):
    """Client domain model for domains managed through client portal"""
    __tablename__ = 'client_domains'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client_registrations.id'), nullable=False)
    domain_name = db.Column(db.String(255), nullable=False, index=True)
    origin_server = db.Column(db.String(255), nullable=False)
    dns_method = db.Column(db.String(20), default='nameservers')  # nameservers, cpanel
    cpanel_id = db.Column(db.Integer, db.ForeignKey('client_cpanels.id'))
    cdn_enabled = db.Column(db.Boolean, default=False)
    ssl_enabled = db.Column(db.Boolean, default=False)
    ssl_certificate_id = db.Column(db.Integer, db.ForeignKey('ssl_certificates.id'))
    cache_ttl = db.Column(db.Integer, default=3600)  # seconds
    purge_key = db.Column(db.String(64), unique=True, index=True)
    status = db.Column(db.String(20), default='pending')  # pending, active, suspended, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ssl_certificate = db.relationship('SSLCertificate', backref='client_domains')
    cpanel_config = db.relationship('ClientCPanels', backref='domains')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'domain_name': self.domain_name,
            'origin_server': self.origin_server,
            'dns_method': self.dns_method,
            'cdn_enabled': self.cdn_enabled,
            'ssl_enabled': self.ssl_enabled,
            'ssl_certificate_id': self.ssl_certificate_id,
            'cache_ttl': self.cache_ttl,
            'purge_key': self.purge_key,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ClientCPanels(db.Model):
    """Client cPanel configuration model for encrypted storage"""
    __tablename__ = 'client_cpanels'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client_registrations.id'), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)  # Fernet encrypted
    port = db.Column(db.Integer, default=2083)
    ssl = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='active')  # active, inactive, error
    last_tested = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """Encrypt and store cPanel password"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        fernet = Fernet(encryption_key.encode())
        self.password_encrypted = fernet.encrypt(password.encode()).decode()
    
    def get_password(self):
        """Decrypt and return cPanel password"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        fernet = Fernet(encryption_key.encode())
        return fernet.decrypt(self.password_encrypted.encode()).decode()
    
    def to_dict(self, include_password=False):
        """Convert to dictionary for JSON serialization"""
        data = {
            'id': self.id,
            'host': self.host,
            'username': self.username,
            'port': self.port,
            'ssl': self.ssl,
            'status': self.status,
            'last_tested': self.last_tested.isoformat() if self.last_tested else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_password:
            data['password'] = self.get_password()
        
        return data

class SpeedTestLog(db.Model):
    """Speed test log model for tracking speed test results"""
    __tablename__ = 'speed_test_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client_registrations.id'))
    test_url = db.Column(db.String(500), nullable=False)
    origin_ttfb = db.Column(db.Float)  # Time to first byte (ms)
    origin_load_time = db.Column(db.Float)  # Full load time (ms)
    origin_size = db.Column(db.Integer)  # Response size (bytes)
    cdn_ttfb = db.Column(db.Float)  # Time to first byte via CDN (ms)
    cdn_load_time = db.Column(db.Float)  # Full load time via CDN (ms)
    cdn_size = db.Column(db.Integer)  # Response size via CDN (bytes)
    cache_status = db.Column(db.String(20))  # hit, miss, bypass
    improvement_percent = db.Column(db.Float)  # Performance improvement
    user_ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    edge_location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'test_url': self.test_url,
            'origin_ttfb': self.origin_ttfb,
            'origin_load_time': self.origin_load_time,
            'origin_size': self.origin_size,
            'cdn_ttfb': self.cdn_ttfb,
            'cdn_load_time': self.cdn_load_time,
            'cdn_size': self.cdn_size,
            'cache_status': self.cache_status,
            'improvement_percent': self.improvement_percent,
            'edge_location': self.edge_location,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ISPTrafficStats(db.Model):
    """ISP traffic statistics model"""
    __tablename__ = 'isp_traffic_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    isp_id = db.Column(db.Integer, db.ForeignKey('isp_registrations.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    requests = db.Column(db.BigInteger, default=0)
    bandwidth_gb = db.Column(db.Float, default=0.0)
    cache_hits = db.Column(db.BigInteger, default=0)
    cache_misses = db.Column(db.BigInteger, default=0)
    response_time_avg = db.Column(db.Float, default=0.0)  # milliseconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        cache_hit_ratio = (self.cache_hits / self.requests * 100) if self.requests > 0 else 0
        
        return {
            'id': self.id,
            'isp_id': self.isp_id,
            'date': self.date.isoformat() if self.date else None,
            'requests': self.requests,
            'bandwidth_gb': self.bandwidth_gb,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_ratio': round(cache_hit_ratio, 2),
            'response_time_avg': self.response_time_avg,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class EmailReport(db.Model):
    """Email report model for automated weekly reports"""
    __tablename__ = 'email_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client_registrations.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    report_type = db.Column(db.String(20), default='weekly')  # weekly, monthly
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255))
    content = db.Column(db.Text)
    bandwidth_saved_gb = db.Column(db.Float, default=0.0)
    requests_served = db.Column(db.BigInteger, default=0)
    cache_hit_ratio = db.Column(db.Float, default=0.0)
    cost_savings = db.Column(db.Float, default=0.0)  # USD
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    client = db.relationship('ClientRegistration', backref='email_reports')
    user = db.relationship('User', backref='email_reports')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'report_type': self.report_type,
            'email': self.email,
            'subject': self.subject,
            'bandwidth_saved_gb': self.bandwidth_saved_gb,
            'requests_served': self.requests_served,
            'cache_hit_ratio': self.cache_hit_ratio,
            'cost_savings': self.cost_savings,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    """Domain model for CDN-enabled domains"""
    __tablename__ = 'domains'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    domain_name = db.Column(db.String(255), nullable=False, index=True)
    origin_server = db.Column(db.String(255), nullable=False)
    cdn_enabled = db.Column(db.Boolean, default=True)
    ssl_enabled = db.Column(db.Boolean, default=False)
    ssl_certificate_id = db.Column(db.Integer, db.ForeignKey('ssl_certificates.id'))
    cache_ttl = db.Column(db.Integer, default=3600)  # seconds
    purge_key = db.Column(db.String(64), unique=True, index=True)
    status = db.Column(db.String(20), default='pending')  # pending, active, suspended, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ssl_certificate = db.relationship('SSLCertificate', backref='domains')
    cache_stats = db.relationship('CacheStats', backref='domain', lazy='dynamic', cascade='all, delete-orphan')
    dns_records = db.relationship('DNSRecord', backref='domain', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'domain_name': self.domain_name,
            'origin_server': self.origin_server,
            'cdn_enabled': self.cdn_enabled,
            'ssl_enabled': self.ssl_enabled,
            'ssl_certificate_id': self.ssl_certificate_id,
            'cache_ttl': self.cache_ttl,
            'purge_key': self.purge_key,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class EdgeNode(db.Model):
    """Edge node model for CDN edge servers with BGP support"""
    __tablename__ = 'edge_nodes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hostname = db.Column(db.String(255), nullable=False, unique=True)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv4 or IPv6
    region = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(2))  # ISO country code
    city = db.Column(db.String(100))
    provider = db.Column(db.String(50))  # digitalocean, linode, vultr, hetzner, manual
    instance_id = db.Column(db.String(100))  # Cloud provider instance ID
    deployment_mode = db.Column(db.String(20), default='single_ip')  # single_ip, bgp_anycast
    anycast_ip = db.Column(db.String(45))  # For BGP anycast mode
    bgp_asn = db.Column(db.String(20))  # BGP ASN (if applicable)
    bgp_config = db.Column(db.Text)  # BGP configuration
    ssh_user = db.Column(db.String(50), default='root')
    ssh_port = db.Column(db.Integer, default=22)
    ssh_key_path = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')  # pending, active, maintenance, error
    load_score = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    client_count = db.Column(db.Integer, default=0)
    max_clients = db.Column(db.Integer, default=25)
    bandwidth_usage_gb = db.Column(db.Float, default=0.0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dns_records = db.relationship('DNSRecord', backref='edge_node', lazy='dynamic')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'region': self.region,
            'country': self.country,
            'city': self.city,
            'provider': self.provider,
            'instance_id': self.instance_id,
            'deployment_mode': self.deployment_mode,
            'anycast_ip': self.anycast_ip,
            'bgp_asn': self.bgp_asn,
            'ssh_user': self.ssh_user,
            'ssh_port': self.ssh_port,
            'status': self.status,
            'load_score': self.load_score,
            'client_count': self.client_count,
            'max_clients': self.max_clients,
            'bandwidth_usage_gb': self.bandwidth_usage_gb,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SSLCertificate(db.Model):
    """SSL certificate model for domain certificates"""
    __tablename__ = 'ssl_certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    domain_name = db.Column(db.String(255), nullable=False)
    certificate_path = db.Column(db.String(500))
    private_key_path = db.Column(db.String(500))
    chain_path = db.Column(db.String(500))
    issuer = db.Column(db.String(100), default='Let\'s Encrypt')
    status = db.Column(db.String(20), default='pending')  # pending, active, expired, error
    issued_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    auto_renew = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'domain_name': self.domain_name,
            'issuer': self.issuer,
            'status': self.status,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'auto_renew': self.auto_renew,
            'days_until_expiry': (self.expires_at - datetime.utcnow()).days if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DNSRecord(db.Model):
    """DNS record model for PowerDNS management"""
    __tablename__ = 'dns_records'
    
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    edge_node_id = db.Column(db.Integer, db.ForeignKey('edge_nodes.id'), nullable=False)
    record_type = db.Column(db.String(10), default='A')  # A, AAAA, CNAME
    record_name = db.Column(db.String(255), nullable=False)
    record_value = db.Column(db.String(255), nullable=False)
    ttl = db.Column(db.Integer, default=300)
    priority = db.Column(db.Integer, default=10)
    weight = db.Column(db.Integer, default=10)
    geo_location = db.Column(db.String(50))  # Geographic location for geo-routing
    status = db.Column(db.String(20), default='active')  # active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'domain_id': self.domain_id,
            'edge_node_id': self.edge_node_id,
            'record_type': self.record_type,
            'record_name': self.record_name,
            'record_value': self.record_value,
            'ttl': self.ttl,
            'priority': self.priority,
            'weight': self.weight,
            'geo_location': self.geo_location,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CacheStats(db.Model):
    """Cache statistics model for analytics"""
    __tablename__ = 'cache_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    edge_node_id = db.Column(db.Integer, db.ForeignKey('edge_nodes.id'))
    date = db.Column(db.Date, default=datetime.utcnow().date)
    requests = db.Column(db.BigInteger, default=0)
    cache_hits = db.Column(db.BigInteger, default=0)
    cache_misses = db.Column(db.BigInteger, default=0)
    bandwidth_saved = db.Column(db.BigInteger, default=0)  # bytes
    bandwidth_total = db.Column(db.BigInteger, default=0)  # bytes
    response_time_avg = db.Column(db.Float, default=0.0)  # milliseconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    edge_node = db.relationship('EdgeNode', backref='cache_stats')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        cache_hit_ratio = (self.cache_hits / self.requests * 100) if self.requests > 0 else 0
        bandwidth_saved_gb = self.bandwidth_saved / (1024**3) if self.bandwidth_saved else 0
        
        return {
            'id': self.id,
            'domain_id': self.domain_id,
            'edge_node_id': self.edge_node_id,
            'date': self.date.isoformat() if self.date else None,
            'requests': self.requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_ratio': round(cache_hit_ratio, 2),
            'bandwidth_saved': self.bandwidth_saved,
            'bandwidth_saved_gb': round(bandwidth_saved_gb, 2),
            'bandwidth_total': self.bandwidth_total,
            'response_time_avg': self.response_time_avg,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TaskLog(db.Model):
    """Task log model for background task tracking"""
    __tablename__ = 'task_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    task_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    result = db.Column(db.Text)
    error_message = db.Column(db.Text)
    progress = db.Column(db.Integer, default=0)  # 0-100
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'task_name': self.task_name,
            'status': self.status,
            'result': json.loads(self.result) if self.result else None,
            'error_message': self.error_message,
            'progress': self.progress,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }