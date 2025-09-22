#!/usr/bin/env python3
"""
XenCDN v8.1 Client Portal API Routes
Routes for client registration, authentication, and domain management
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import os
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from ..models import db, ClientRegistration, ClientDomain, ClientCPanels, CacheStats, SpeedTestLog
from ..tasks.dns_provision import provision_client_domain
from ..tasks.ssl_issue import issue_ssl_certificate
from ..tasks.email_report import send_email

client_portal_bp = Blueprint('client_portal', __name__, url_prefix='/api/client')

@client_portal_bp.route('/register', methods=['POST'])
def register_client():
    """Register a new client"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if email already exists
        existing_client = ClientRegistration.query.filter_by(email=data['email']).first()
        if existing_client:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Validate email format
        if '@' not in data['email'] or '.' not in data['email']:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Create new client
        client = ClientRegistration(
            email=data['email'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            company=data.get('company', ''),
            phone=data.get('phone', ''),
            plan=data.get('plan', 'free')
        )
        client.set_password(data['password'])
        client.generate_verification_token()
        
        # Set plan limits
        if client.plan == 'free':
            client.max_domains = 5
            client.max_bandwidth_gb = 100
        elif client.plan == 'pro':
            client.max_domains = 25
            client.max_bandwidth_gb = 1000
        elif client.plan == 'enterprise':
            client.max_domains = -1  # Unlimited
            client.max_bandwidth_gb = 10000
        
        db.session.add(client)
        db.session.commit()
        
        # Send verification email
        try:
            send_verification_email(client.email, client.verification_token)
        except Exception as e:
            current_app.logger.error(f"Failed to send verification email: {e}")
        
        return jsonify({
            'message': 'Client registered successfully. Please check your email for verification.',
            'client_id': client.id,
            'email_verification_required': True
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Client registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@client_portal_bp.route('/login', methods=['POST'])
def login_client():
    """Login client and return JWT token"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        client = ClientRegistration.query.filter_by(email=data['email']).first()
        
        if not client or not client.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not client.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Create JWT token with client role
        additional_claims = {
            'role': 'client',
            'client_id': client.id,
            'email_verified': client.email_verified
        }
        access_token = create_access_token(
            identity=str(client.id),
            additional_claims=additional_claims,
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'access_token': access_token,
            'client': client.to_dict(),
            'email_verification_required': not client.email_verified
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Client login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@client_portal_bp.route('/verify', methods=['POST'])
def verify_email():
    """Verify client email with token"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Verification token required'}), 400
        
        client = ClientRegistration.query.filter_by(verification_token=token).first()
        
        if not client:
            return jsonify({'error': 'Invalid verification token'}), 400
        
        client.email_verified = True
        client.verification_token = None
        db.session.commit()
        
        return jsonify({'message': 'Email verified successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Email verification error: {e}")
        return jsonify({'error': 'Verification failed'}), 500

@client_portal_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Send password reset email"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        client = ClientRegistration.query.filter_by(email=email).first()
        
        if client:
            reset_token = client.generate_reset_token()
            db.session.commit()
            
            try:
                send_reset_email(client.email, reset_token)
            except Exception as e:
                current_app.logger.error(f"Failed to send reset email: {e}")
        
        # Always return success for security
        return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password reset error: {e}")
        return jsonify({'error': 'Reset failed'}), 500

@client_portal_bp.route('/set-password', methods=['POST'])
def set_password():
    """Set new password with reset token"""
    try:
        data = request.get_json()
        token = data.get('token')
        password = data.get('password')
        
        if not token or not password:
            return jsonify({'error': 'Token and password required'}), 400
        
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        client = ClientRegistration.query.filter_by(reset_token=token).first()
        
        if not client or not client.reset_token_expires or client.reset_token_expires < datetime.utcnow():
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        client.set_password(password)
        client.reset_token = None
        client.reset_token_expires = None
        db.session.commit()
        
        return jsonify({'message': 'Password updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Set password error: {e}")
        return jsonify({'error': 'Password update failed'}), 500

@client_portal_bp.route('/me', methods=['GET'])
@jwt_required()
def get_client_profile():
    """Get client profile (JWT protected)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'client':
            return jsonify({'error': 'Client access required'}), 403
        
        client_id = get_jwt_identity()
        client = ClientRegistration.query.get(client_id)
        
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        return jsonify(client.to_dict()), 200
        
    except Exception as e:
        current_app.logger.error(f"Get client profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500

@client_portal_bp.route('/domain', methods=['POST'])
@jwt_required()
def add_domain():
    """Add domain (requires JWT)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'client':
            return jsonify({'error': 'Client access required'}), 403
        
        if not claims.get('email_verified'):
            return jsonify({'error': 'Email verification required'}), 403
        
        client_id = get_jwt_identity()
        client = ClientRegistration.query.get(client_id)
        
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        data = request.get_json()
        domain_name = data.get('domain_name')
        origin_server = data.get('origin_server')
        dns_method = data.get('dns_method', 'nameservers')
        
        if not domain_name or not origin_server:
            return jsonify({'error': 'Domain name and origin server required'}), 400
        
        # Validate domain format
        if '.' not in domain_name or len(domain_name) < 3:
            return jsonify({'error': 'Invalid domain format'}), 400
        
        # Check domain limits
        if client.max_domains != -1 and client.client_domains.count() >= client.max_domains:
            return jsonify({'error': f'Domain limit reached ({client.max_domains})'}), 400
        
        # Check if domain already exists
        existing_domain = ClientDomain.query.filter_by(domain_name=domain_name).first()
        if existing_domain:
            return jsonify({'error': 'Domain already exists'}), 400
        
        # Create domain
        domain = ClientDomain(
            client_id=client.id,
            domain_name=domain_name,
            origin_server=origin_server,
            dns_method=dns_method,
            purge_key=secrets.token_urlsafe(32)
        )
        
        db.session.add(domain)
        db.session.commit()
        
        # Trigger DNS provisioning
        try:
            provision_client_domain.delay(domain.id)
        except Exception as e:
            current_app.logger.error(f"Failed to trigger DNS provisioning: {e}")
        
        return jsonify({
            'message': 'Domain added successfully',
            'domain': domain.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add domain error: {e}")
        return jsonify({'error': 'Failed to add domain'}), 500

@client_portal_bp.route('/domains', methods=['GET'])
@jwt_required()
def list_domains():
    """List client domains (JWT protected)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'client':
            return jsonify({'error': 'Client access required'}), 403
        
        client_id = get_jwt_identity()
        client = ClientRegistration.query.get(client_id)
        
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        domains = [domain.to_dict() for domain in client.client_domains.all()]
        
        return jsonify({
            'domains': domains,
            'total': len(domains),
            'limit': client.max_domains
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"List domains error: {e}")
        return jsonify({'error': 'Failed to list domains'}), 500

@client_portal_bp.route('/domain/<int:domain_id>/enable', methods=['PUT'])
@jwt_required()
def enable_cdn():
    """Enable CDN for domain"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'client':
            return jsonify({'error': 'Client access required'}), 403
        
        client_id = get_jwt_identity()
        domain = ClientDomain.query.filter_by(id=domain_id, client_id=client_id).first()
        
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        domain.cdn_enabled = True
        domain.status = 'active'
        db.session.commit()
        
        # Trigger SSL certificate issuance
        try:
            issue_ssl_certificate.delay(domain.id, 'client')
        except Exception as e:
            current_app.logger.error(f"Failed to trigger SSL issuance: {e}")
        
        return jsonify({
            'message': 'CDN enabled successfully',
            'domain': domain.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Enable CDN error: {e}")
        return jsonify({'error': 'Failed to enable CDN'}), 500

@client_portal_bp.route('/domain/<int:domain_id>/purge', methods=['POST'])
@jwt_required()
def purge_domain_cache():
    """Purge cache for domain"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'client':
            return jsonify({'error': 'Client access required'}), 403
        
        client_id = get_jwt_identity()
        domain = ClientDomain.query.filter_by(id=domain_id, client_id=client_id).first()
        
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        # Import purge task
        from ..tasks.purge_cache import purge_domain_cache
        
        # Trigger cache purge
        task = purge_domain_cache.delay(domain.domain_name)
        
        return jsonify({
            'message': 'Cache purge initiated',
            'task_id': task.id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Purge cache error: {e}")
        return jsonify({'error': 'Failed to purge cache'}), 500

@client_portal_bp.route('/cpanel', methods=['POST'])
@jwt_required()
def add_cpanel_config():
    """Add cPanel configuration"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'client':
            return jsonify({'error': 'Client access required'}), 403
        
        client_id = get_jwt_identity()
        data = request.get_json()
        
        required_fields = ['host', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        cpanel_config = ClientCPanels(
            client_id=client_id,
            host=data['host'],
            username=data['username'],
            port=data.get('port', 2083),
            ssl=data.get('ssl', True)
        )
        cpanel_config.set_password(data['password'])
        
        db.session.add(cpanel_config)
        db.session.commit()
        
        return jsonify({
            'message': 'cPanel configuration added successfully',
            'config': cpanel_config.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add cPanel config error: {e}")
        return jsonify({'error': 'Failed to add cPanel configuration'}), 500

@client_portal_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_client_stats():
    """Get cache stats (JWT protected)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'client':
            return jsonify({'error': 'Client access required'}), 403
        
        client_id = get_jwt_identity()
        client = ClientRegistration.query.get(client_id)
        
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        # Get stats for client domains
        domain_ids = [d.id for d in client.client_domains.all()]
        
        # This would need to be adapted since CacheStats references the old Domain model
        # For now, return mock data
        stats = {
            'domains': len(domain_ids),
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'bandwidth_saved_gb': 0,
            'bandwidth_total_gb': 0,
            'cache_hit_ratio': 0,
            'cost_savings': 0
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Get client stats error: {e}")
        return jsonify({'error': 'Failed to get stats'}), 500

def send_verification_email(email, token):
    """Send email verification"""
    subject = "XenCDN - Verify Your Email Address"
    
    # Get base URL from environment
    base_url = os.getenv('CLIENT_PORTAL_DOMAIN', 'localhost:3002')
    verify_url = f"https://{base_url}/verify?token={token}"
    
    body = f"""
    Welcome to XenCDN!
    
    Please click the link below to verify your email address:
    {verify_url}
    
    If you didn't create an account, please ignore this email.
    
    Best regards,
    The XenCDN Team
    """
    
    send_email(email, subject, body)

def send_reset_email(email, token):
    """Send password reset email"""
    subject = "XenCDN - Password Reset"
    
    # Get base URL from environment
    base_url = os.getenv('CLIENT_PORTAL_DOMAIN', 'localhost:3002')
    reset_url = f"https://{base_url}/reset-password?token={token}"
    
    body = f"""
    You have requested a password reset for your XenCDN account.
    
    Please click the link below to reset your password:
    {reset_url}
    
    This link will expire in 24 hours.
    
    If you didn't request this reset, please ignore this email.
    
    Best regards,
    The XenCDN Team
    """
    
    send_email(email, subject, body)