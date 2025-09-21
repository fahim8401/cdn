#!/usr/bin/env python3
"""
Cachenet CDN Platform Domain Management Routes
Domain CRUD operations with CDN configuration
"""

import os
import secrets
import logging
import re
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Domain, DNSRecord, EdgeNode
from tasks.dns_provision import provision_domain_dns
from tasks.edge_config import deploy_domain_config

logger = logging.getLogger(__name__)
domains_bp = Blueprint('domains', __name__)

def validate_domain_name(domain):
    """Validate domain name format"""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return re.match(pattern, domain) is not None

def validate_origin_server(origin):
    """Validate origin server URL"""
    pattern = r'^https?://[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*(/.*)?$'
    return re.match(pattern, origin) is not None

@domains_bp.route('/', methods=['GET'])
@jwt_required()
def list_domains():
    """List user's domains"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status')
        search = request.args.get('search', '').strip()
        
        # Build query
        query = Domain.query.filter_by(user_id=user_id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        if search:
            query = query.filter(Domain.domain_name.contains(search))
        
        domains = query.order_by(Domain.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'domains': [domain.to_dict() for domain in domains.items],
            'total': domains.total,
            'pages': domains.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        logger.error(f"List domains error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@domains_bp.route('/', methods=['POST'])
@jwt_required()
def create_domain():
    """Add new domain to CDN"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        domain_name = data.get('domain_name', '').strip().lower()
        origin_server = data.get('origin_server', '').strip()
        
        if not domain_name or not origin_server:
            return jsonify({'error': 'Domain name and origin server required'}), 400
        
        # Validate domain format
        if not validate_domain_name(domain_name):
            return jsonify({'error': 'Invalid domain name format'}), 400
        
        # Validate origin server format
        if not validate_origin_server(origin_server):
            return jsonify({'error': 'Invalid origin server URL format'}), 400
        
        # Check domain limits
        current_domains = Domain.query.filter_by(user_id=user_id).count()
        if current_domains >= user.max_domains:
            return jsonify({'error': f'Domain limit reached ({user.max_domains})'}), 409
        
        # Check if domain already exists
        existing_domain = Domain.query.filter_by(domain_name=domain_name).first()
        if existing_domain:
            return jsonify({'error': 'Domain already exists in the system'}), 409
        
        # Create domain
        domain = Domain(
            user_id=user_id,
            domain_name=domain_name,
            origin_server=origin_server,
            cache_ttl=data.get('cache_ttl', 3600),
            purge_key=secrets.token_urlsafe(32),
            status='pending'
        )
        
        db.session.add(domain)
        db.session.commit()
        
        # Trigger async DNS provisioning
        provision_domain_dns.delay(domain.id)
        
        logger.info(f"Domain created: {domain_name} for user: {user.email}")
        
        return jsonify({
            'message': 'Domain created successfully',
            'domain': domain.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Create domain error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@domains_bp.route('/<int:domain_id>', methods=['GET'])
@jwt_required()
def get_domain():
    """Get domain details"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        # Get DNS records
        dns_records = DNSRecord.query.filter_by(domain_id=domain.id).all()
        
        domain_data = domain.to_dict()
        domain_data['dns_records'] = [record.to_dict() for record in dns_records]
        
        return jsonify({'domain': domain_data}), 200
        
    except Exception as e:
        logger.error(f"Get domain error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@domains_bp.route('/<int:domain_id>', methods=['PUT'])
@jwt_required()
def update_domain():
    """Update domain configuration"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed fields
        if 'origin_server' in data:
            origin_server = data['origin_server'].strip()
            if not validate_origin_server(origin_server):
                return jsonify({'error': 'Invalid origin server URL format'}), 400
            domain.origin_server = origin_server
        
        if 'cache_ttl' in data:
            cache_ttl = data.get('cache_ttl', 3600)
            if not isinstance(cache_ttl, int) or cache_ttl < 60:
                return jsonify({'error': 'Cache TTL must be at least 60 seconds'}), 400
            domain.cache_ttl = cache_ttl
        
        if 'cdn_enabled' in data:
            domain.cdn_enabled = bool(data['cdn_enabled'])
        
        domain.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Trigger configuration update on edge nodes
        deploy_domain_config.delay(domain.id)
        
        logger.info(f"Domain updated: {domain.domain_name}")
        
        return jsonify({
            'message': 'Domain updated successfully',
            'domain': domain.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Update domain error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@domains_bp.route('/<int:domain_id>', methods=['DELETE'])
@jwt_required()
def delete_domain():
    """Delete domain from CDN"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        domain_name = domain.domain_name
        
        # Delete associated DNS records
        DNSRecord.query.filter_by(domain_id=domain.id).delete()
        
        # Delete domain
        db.session.delete(domain)
        db.session.commit()
        
        logger.info(f"Domain deleted: {domain_name}")
        
        return jsonify({'message': 'Domain deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Delete domain error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@domains_bp.route('/<int:domain_id>/toggle', methods=['POST'])
@jwt_required()
def toggle_domain_cdn():
    """Toggle CDN enabled/disabled for domain"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        domain.cdn_enabled = not domain.cdn_enabled
        domain.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Update edge node configurations
        deploy_domain_config.delay(domain.id)
        
        status = 'enabled' if domain.cdn_enabled else 'disabled'
        logger.info(f"CDN {status} for domain: {domain.domain_name}")
        
        return jsonify({
            'message': f'CDN {status} successfully',
            'domain': domain.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Toggle domain CDN error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@domains_bp.route('/<int:domain_id>/regenerate-purge-key', methods=['POST'])
@jwt_required()
def regenerate_purge_key():
    """Regenerate domain purge key"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        domain.purge_key = secrets.token_urlsafe(32)
        domain.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Purge key regenerated for domain: {domain.domain_name}")
        
        return jsonify({
            'message': 'Purge key regenerated successfully',
            'purge_key': domain.purge_key
        }), 200
        
    except Exception as e:
        logger.error(f"Regenerate purge key error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@domains_bp.route('/<int:domain_id>/dns-records', methods=['GET'])
@jwt_required()
def get_domain_dns_records():
    """Get domain DNS records"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        dns_records = DNSRecord.query.filter_by(domain_id=domain.id).all()
        
        return jsonify({
            'dns_records': [record.to_dict() for record in dns_records]
        }), 200
        
    except Exception as e:
        logger.error(f"Get DNS records error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@domains_bp.route('/verify', methods=['POST'])
@jwt_required()
def verify_domain():
    """Verify domain ownership via DNS TXT record"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('domain_name'):
            return jsonify({'error': 'Domain name required'}), 400
        
        domain_name = data['domain_name'].strip().lower()
        
        # Generate verification token
        verification_token = secrets.token_urlsafe(16)
        
        return jsonify({
            'verification_token': verification_token,
            'txt_record_name': f'_cachenet-verify.{domain_name}',
            'txt_record_value': verification_token,
            'instructions': 'Add this TXT record to your DNS and call /domains/verify-check endpoint'
        }), 200
        
    except Exception as e:
        logger.error(f"Domain verification error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500