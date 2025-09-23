#!/usr/bin/env python3
"""
XenCDN v8.2 - Enterprise CDN Platform API
Production-ready Flask application with JWT authentication and complete DNS management
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from werkzeug.security import generate_password_hash, check_password_hash

# Import models and routes
from models import db, User, Domain, EdgeNode, SSLCertificate, CacheStats, DNSZone, DNSRecord, ISPRegistration, ClientRegistration
from routes.auth import auth_bp
from routes.domains import domains_bp
from routes.cache import cache_bp
from routes.ssl import ssl_bp
from routes.auto_scale import auto_scale_bp
from routes.stats import stats_bp
from routes.dns_zones import dns_zones_bp
from routes.isp_portal import isp_portal_bp
from routes.client_portal import client_portal_bp
from routes.speed_test import speed_test_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///xencdn.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    
    # Redis configuration for rate limiting
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app, origins=os.getenv('ALLOWED_ORIGINS', '*').split(','))
    
    # Rate limiting
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["100 per minute"],
        storage_uri=redis_url
    )
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(domains_bp, url_prefix='/api/domains')
    app.register_blueprint(cache_bp, url_prefix='/api/cache')
    app.register_blueprint(ssl_bp, url_prefix='/api/ssl')
    app.register_blueprint(auto_scale_bp, url_prefix='/api/auto-scale')
    app.register_blueprint(stats_bp, url_prefix='/api/stats')
    app.register_blueprint(dns_zones_bp)  # DNS management routes
    app.register_blueprint(isp_portal_bp)  # ISP portal routes
    app.register_blueprint(client_portal_bp)  # Client portal routes
    app.register_blueprint(speed_test_bp)  # Speed test routes
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint for load balancers"""
        try:
            # Check database connection
            db.session.execute('SELECT 1')
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '8.2.0',
                'platform': 'XenCDN Enterprise'
            }), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # API info endpoint
    @app.route('/api/info')
    def api_info():
        """API information endpoint"""
        return jsonify({
            'name': 'XenCDN v8.2 Enterprise Platform',
            'version': '8.2.0',
            'description': 'Complete self-hosted CDN + DNS + SSL platform',
            'features': [
                'DNS Zone Management',
                'BGP Anycast',
                'ISP Portal',
                'Client Portal',
                'Speed Testing',
                'SSL Automation',
                'Real-time Analytics'
            ],
            'endpoints': {
                'auth': '/api/auth',
                'domains': '/api/domains',
                'cache': '/api/cache',
                'ssl': '/api/ssl',
                'auto_scale': '/api/auto-scale',
                'dns_zones': '/api/dns',
                'isp_portal': '/api/isp',
                'client_portal': '/api/client',
                'speed_test': '/api/speed-test'
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Enhanced dashboard stats endpoint
    @app.route('/api/dashboard/stats')
    @jwt_required()
    def dashboard_stats():
        """Get comprehensive dashboard statistics"""
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get user's domains
            domains = Domain.query.filter_by(user_id=user_id).all()
            
            # Calculate total bandwidth and performance stats
            total_bandwidth_saved = 0
            total_requests = 0
            total_cache_hits = 0
            
            for domain in domains:
                stats = CacheStats.query.filter_by(domain_id=domain.id).all()
                for stat in stats:
                    total_bandwidth_saved += stat.bandwidth_saved or 0
                    total_requests += stat.requests or 0
                    total_cache_hits += stat.cache_hits or 0
            
            cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            # Get DNS zones count
            dns_zones_count = DNSZone.query.count() if user.is_admin else 0
            
            # Get ISP registrations count (admin only)
            isp_registrations = ISPRegistration.query.count() if user.is_admin else 0
            pending_isps = ISPRegistration.query.filter_by(status='pending').count() if user.is_admin else 0
            
            # Get client registrations
            total_clients = ClientRegistration.query.count() if user.is_admin else 0
            
            # Get active edge nodes
            active_edges = EdgeNode.query.filter_by(status='active').count()
            
            # Get SSL certificates
            ssl_certs = SSLCertificate.query.filter_by(user_id=user_id).count()
            
            # Calculate cost savings (estimate)
            bandwidth_saved_gb = total_bandwidth_saved / (1024**3)
            estimated_cost_saved = bandwidth_saved_gb * 0.05  # $0.05 per GB
            
            stats_data = {
                'domains_count': len(domains),
                'active_domains': len([d for d in domains if d.status == 'active']),
                'active_edges': active_edges,
                'total_bandwidth_saved_gb': round(bandwidth_saved_gb, 2),
                'cache_hit_ratio': round(cache_hit_ratio, 2),
                'total_requests': total_requests,
                'ssl_certificates': ssl_certs,
                'estimated_cost_saved_usd': round(estimated_cost_saved, 2)
            }
            
            # Add admin-specific stats
            if user.is_admin:
                stats_data.update({
                    'dns_zones_count': dns_zones_count,
                    'isp_registrations': isp_registrations,
                    'pending_isps': pending_isps,
                    'total_clients': total_clients,
                    'edge_deployment_mode': os.getenv('EDGE_MODE', 'single_ip'),
                    'bgp_enabled': os.getenv('EDGE_MODE') == 'bgp_anycast'
                })
            
            return jsonify(stats_data)
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Platform status endpoint
    @app.route('/api/platform/status')
    def platform_status():
        """Get platform-wide status information"""
        try:
            # Basic platform stats
            total_domains = Domain.query.count()
            active_domains = Domain.query.filter_by(status='active').count()
            total_dns_zones = DNSZone.query.count()
            active_edges = EdgeNode.query.filter_by(status='active').count()
            total_isps = ISPRegistration.query.filter_by(status='approved').count()
            
            # Performance metrics (last 24 hours)
            from datetime import timedelta
            since_yesterday = datetime.utcnow() - timedelta(days=1)
            
            recent_stats = CacheStats.query.filter(
                CacheStats.date >= since_yesterday.date()
            ).all()
            
            total_requests_24h = sum(stat.requests for stat in recent_stats)
            total_bandwidth_saved_24h = sum(stat.bandwidth_saved for stat in recent_stats) / (1024**3)  # GB
            
            return jsonify({
                'platform': 'XenCDN v8.2',
                'status': 'operational',
                'uptime': '99.99%',  # In production, calculate actual uptime
                'edge_network': {
                    'active_nodes': active_edges,
                    'deployment_mode': os.getenv('EDGE_MODE', 'single_ip'),
                    'anycast_enabled': os.getenv('EDGE_MODE') == 'bgp_anycast'
                },
                'dns_service': {
                    'zones_managed': total_dns_zones,
                    'nameservers': [
                        os.getenv('DNS_SERVER_NAME', 'ns1.xencdn.com'),
                        os.getenv('DNS_SERVER_NAME2', 'ns2.xencdn.com')
                    ]
                },
                'performance_24h': {
                    'total_requests': total_requests_24h,
                    'bandwidth_saved_gb': round(total_bandwidth_saved_24h, 2)
                },
                'network': {
                    'total_domains': total_domains,
                    'active_domains': active_domains,
                    'partner_isps': total_isps
                },
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting platform status: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token required'}), 401
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            
            # Create default admin user if not exists
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@xencdn.com')
            admin_user = User.query.filter_by(email=admin_email).first()
            if not admin_user:
                admin_user = User(
                    email=admin_email,
                    username='admin',
                    first_name='XenCDN',
                    last_name='Administrator',
                    password_hash=generate_password_hash(os.getenv('ADMIN_PASSWORD', 'xencdn123!')),
                    is_admin=True,
                    is_active=True
                )
                db.session.add(admin_user)
                db.session.commit()
                logger.info(f"Default admin user created: {admin_email}")
            
            # Create default DNS zones for platform
            default_zones = [
                os.getenv('HOMEPAGE_DOMAIN', 'xencdn.com'),
                os.getenv('API_DOMAIN', 'api.xencdn.com'),
                os.getenv('ADMIN_DOMAIN', 'admin.xencdn.com'),
                os.getenv('CLIENT_PORTAL_DOMAIN', 'client.xencdn.com'),
                os.getenv('ISP_PORTAL_DOMAIN', 'isp.xencdn.com')
            ]
            
            for zone_name in default_zones:
                existing_zone = DNSZone.query.filter_by(name=zone_name).first()
                if not existing_zone:
                    zone = DNSZone(
                        name=zone_name,
                        kind='Native',
                        ns_records='["ns1.xencdn.com", "ns2.xencdn.com"]',
                        status='active'
                    )
                    db.session.add(zone)
            
            db.session.commit()
            logger.info("Database initialization completed")
                
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting XenCDN v8.2 API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)