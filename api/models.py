#!/usr/bin/env python3
"""
Cachenet CDN Platform Database Models
SQLAlchemy models for all platform entities
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json

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

class EdgeNode(db.Model):
    """Edge node model for CDN edge servers"""
    __tablename__ = 'edge_nodes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hostname = db.Column(db.String(255), nullable=False, unique=True)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv4 or IPv6
    region = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(2))  # ISO country code
    city = db.Column(db.String(100))
    provider = db.Column(db.String(50))  # digitalocean, linode, vultr, hetzner
    instance_id = db.Column(db.String(100))  # Cloud provider instance ID
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