#!/usr/bin/env python3
"""
Cachenet CDN Platform API
Production-ready Flask application with JWT authentication
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
from models import db, User, Domain, EdgeNode, SSLCertificate, CacheStats
from routes.auth import auth_bp
from routes.domains import domains_bp
from routes.cache import cache_bp
from routes.ssl import ssl_bp
from routes.auto_scale import auto_scale_bp

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
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///cachenet.db')
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
                'version': '1.0.0'
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
            'name': 'Cachenet CDN API',
            'version': '1.0.0',
            'description': 'Production-ready self-hosted CDN platform',
            'endpoints': {
                'auth': '/api/auth',
                'domains': '/api/domains',
                'cache': '/api/cache',
                'ssl': '/api/ssl',
                'auto_scale': '/api/auto-scale'
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Dashboard stats endpoint
    @app.route('/api/stats')
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
            
            return jsonify({
                'domains_count': len(domains),
                'active_edges': active_edges,
                'total_bandwidth_saved_gb': round(total_bandwidth_saved / (1024**3), 2),
                'cache_hit_ratio': round(cache_hit_ratio, 2),
                'total_requests': total_requests,
                'ssl_certificates': SSLCertificate.query.filter_by(user_id=user_id).count()
            })
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
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
            admin_user = User.query.filter_by(email='admin@cachenet.local').first()
            if not admin_user:
                admin_user = User(
                    email='admin@cachenet.local',
                    username='admin',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True,
                    is_active=True
                )
                db.session.add(admin_user)
                db.session.commit()
                logger.info("Default admin user created")
                
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
    
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Cachenet API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)