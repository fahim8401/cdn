#!/usr/bin/env python3
"""
XenCDN v8.1 Platform API
Production-ready Flask application with JWT authentication, Client Portal, and ISP Portal
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
from models import db, User, Domain, EdgeNode, SSLCertificate, CacheStats, ClientRegistration, ISPRegistration
from routes.auth import auth_bp
from routes.domains import domains_bp
from routes.cache import cache_bp
from routes.ssl import ssl_bp
from routes.auto_scale import auto_scale_bp
from routes.stats import stats_bp
from routes.client_portal import client_portal_bp
from routes.isp_portal import isp_portal_bp
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
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)  # Longer for client/ISP portals
    
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
    
    # New XenCDN v8.1 routes
    app.register_blueprint(client_portal_bp)  # Already has /api/client prefix
    app.register_blueprint(isp_portal_bp)     # Already has /api/isp prefix
    app.register_blueprint(speed_test_bp)     # Already has /api/speed-test prefix
    
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
                'version': '8.1.0',
                'platform': 'XenCDN'
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
            'name': 'XenCDN Platform API',
            'version': '8.1.0',
            'description': 'Enterprise-grade self-hosted CDN platform with ISP partnership capabilities',
            'endpoints': {
                'auth': '/api/auth',
                'domains': '/api/domains',
                'cache': '/api/cache',
                'ssl': '/api/ssl',
                'auto_scale': '/api/auto-scale',
                'stats': '/api/stats',
                'client_portal': '/api/client',
                'isp_portal': '/api/isp',
                'speed_test': '/api/speed-test'
            },
            'features': [
                'Client Portal for website owners',
                'ISP Portal for peering partnerships',
                'BGP Anycast support',
                'GRE tunnel configuration',
                'Public speed testing tool',
                'Automated SSL certificates',
                'Real-time analytics'
            ],
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Enhanced dashboard stats endpoint
    @app.route('/api/dashboard/stats')
    @jwt_required()
    def dashboard_stats():
        """Get dashboard statistics"""
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Get user's domains
            domains = Domain.query.filter_by(user_id=user_id).all()
            
            # Calculate total bandwidth saved
            total_bandwidth_saved = 0
            total_requests = 0
            cache_hit_ratio = 0
            
            for domain in domains:
                stats = CacheStats.query.filter_by(domain_id=domain.id).all()
                for stat in stats:
                    total_bandwidth_saved += stat.bandwidth_saved or 0
                    total_requests += stat.requests or 0
            
            if total_requests > 0:
                cache_hits = CacheStats.query.filter_by(
                    domain_id__in=[d.id for d in domains]
                ).with_entities(db.func.sum(CacheStats.cache_hits)).scalar() or 0
                cache_hit_ratio = (cache_hits / total_requests) * 100
            
            # Get active edge nodes
            active_edges = EdgeNode.query.filter_by(status='active').count()
            
            # Get client and ISP counts (admin only)
            client_count = 0
            isp_count = 0
            if user.is_admin:
                client_count = ClientRegistration.query.filter_by(is_active=True).count()
                isp_count = ISPRegistration.query.filter_by(status='active').count()
            
            return jsonify({
                'domains_count': len(domains),
                'active_edges': active_edges,
                'total_bandwidth_saved_gb': round(total_bandwidth_saved / (1024**3), 2),
                'cache_hit_ratio': round(cache_hit_ratio, 2),
                'total_requests': total_requests,
                'ssl_certificates': SSLCertificate.query.filter_by(user_id=user_id).count(),
                'client_count': client_count,
                'isp_count': isp_count,
                'platform_version': '8.1.0'
            })
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # New admin endpoints for client and ISP management
    @app.route('/api/admin/clients')
    @jwt_required()
    def list_clients():
        """List all client registrations (admin only)"""
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user or not user.is_admin:
                return jsonify({'error': 'Admin access required'}), 403
            
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            clients_query = ClientRegistration.query.order_by(ClientRegistration.created_at.desc())
            clients_paginated = clients_query.paginate(page=page, per_page=per_page, error_out=False)
            
            return jsonify({
                'clients': [client.to_dict() for client in clients_paginated.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': clients_paginated.total,
                    'pages': clients_paginated.pages
                }
            })
            
        except Exception as e:
            logger.error(f"Error listing clients: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/admin/isps')
    @jwt_required()
    def list_isps():
        """List all ISP registrations (admin only)"""
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user or not user.is_admin:
                return jsonify({'error': 'Admin access required'}), 403
            
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            isps_query = ISPRegistration.query.order_by(ISPRegistration.created_at.desc())
            isps_paginated = isps_query.paginate(page=page, per_page=per_page, error_out=False)
            
            return jsonify({
                'isps': [isp.to_dict() for isp in isps_paginated.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': isps_paginated.total,
                    'pages': isps_paginated.pages
                }
            })
            
        except Exception as e:
            logger.error(f"Error listing ISPs: {str(e)}")
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
            admin_user = User.query.filter_by(email='admin@xencdn.com').first()
            if not admin_user:
                admin_user = User(
                    email='admin@xencdn.com',
                    username='admin',
                    password_hash=generate_password_hash('XenCDN@2024!'),
                    first_name='Admin',
                    last_name='User',
                    is_admin=True,
                    is_active=True
                )
                db.session.add(admin_user)
                db.session.commit()
                logger.info("Default admin user created - admin@xencdn.com / XenCDN@2024!")
                
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting XenCDN v8.1 API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)