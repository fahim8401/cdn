#!/usr/bin/env python3
"""
Cachenet CDN Platform SSL Certificate Management Routes
ACME.sh integration for automatic SSL certificate issuance
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Domain, SSLCertificate
from tasks.ssl_issue import issue_ssl_certificate, renew_ssl_certificate

logger = logging.getLogger(__name__)
ssl_bp = Blueprint('ssl', __name__)

@ssl_bp.route('/certificates', methods=['GET'])
@jwt_required()
def list_certificates():
    """List user's SSL certificates"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status')
        
        # Build query
        query = SSLCertificate.query.filter_by(user_id=user_id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        certificates = query.order_by(SSLCertificate.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'certificates': [cert.to_dict() for cert in certificates.items],
            'total': certificates.total,
            'pages': certificates.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        logger.error(f"List certificates error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/issue', methods=['POST'])
@jwt_required()
def issue_certificate():
    """Issue new SSL certificate for domain"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data or not data.get('domain_id'):
            return jsonify({'error': 'Domain ID required'}), 400
        
        domain_id = data['domain_id']
        domain = Domain.query.filter_by(id=domain_id, user_id=user_id).first()
        
        if not domain:
            return jsonify({'error': 'Domain not found'}), 404
        
        # Check if certificate already exists
        existing_cert = SSLCertificate.query.filter_by(
            user_id=user_id, 
            domain_name=domain.domain_name
        ).first()
        
        if existing_cert and existing_cert.status == 'active':
            # Check if certificate expires within 30 days
            if existing_cert.expires_at and existing_cert.expires_at > datetime.utcnow() + timedelta(days=30):
                return jsonify({'error': 'Certificate already exists and is valid'}), 409
        
        # Issue new certificate
        certificate = SSLCertificate(
            user_id=user_id,
            domain_name=domain.domain_name,
            status='pending'
        )
        
        db.session.add(certificate)
        db.session.commit()
        
        # Trigger async SSL certificate issuance
        task = issue_ssl_certificate.delay(certificate.id)
        
        logger.info(f"SSL certificate issuance initiated for: {domain.domain_name}")
        
        return jsonify({
            'message': 'SSL certificate issuance initiated',
            'task_id': task.id,
            'certificate': certificate.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Issue certificate error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/certificates/<int:cert_id>', methods=['GET'])
@jwt_required()
def get_certificate():
    """Get SSL certificate details"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificate = SSLCertificate.query.filter_by(id=cert_id, user_id=user_id).first()
        if not certificate:
            return jsonify({'error': 'Certificate not found'}), 404
        
        return jsonify({'certificate': certificate.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Get certificate error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/certificates/<int:cert_id>/renew', methods=['POST'])
@jwt_required()
def renew_certificate():
    """Renew SSL certificate"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificate = SSLCertificate.query.filter_by(id=cert_id, user_id=user_id).first()
        if not certificate:
            return jsonify({'error': 'Certificate not found'}), 404
        
        if certificate.status != 'active':
            return jsonify({'error': 'Only active certificates can be renewed'}), 400
        
        # Update certificate status
        certificate.status = 'pending'
        certificate.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Trigger async SSL certificate renewal
        task = renew_ssl_certificate.delay(certificate.id)
        
        logger.info(f"SSL certificate renewal initiated for: {certificate.domain_name}")
        
        return jsonify({
            'message': 'SSL certificate renewal initiated',
            'task_id': task.id,
            'certificate': certificate.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Renew certificate error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/certificates/<int:cert_id>/download', methods=['GET'])
@jwt_required()
def download_certificate():
    """Download SSL certificate files"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificate = SSLCertificate.query.filter_by(id=cert_id, user_id=user_id).first()
        if not certificate:
            return jsonify({'error': 'Certificate not found'}), 404
        
        if certificate.status != 'active' or not certificate.certificate_path:
            return jsonify({'error': 'Certificate not available for download'}), 400
        
        file_type = request.args.get('type', 'cert')  # cert, key, chain
        
        if file_type == 'cert':
            file_path = certificate.certificate_path
            filename = f"{certificate.domain_name}.crt"
        elif file_type == 'key':
            file_path = certificate.private_key_path
            filename = f"{certificate.domain_name}.key"
        elif file_type == 'chain':
            file_path = certificate.chain_path
            filename = f"{certificate.domain_name}-chain.crt"
        else:
            return jsonify({'error': 'Invalid file type'}), 400
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Certificate file not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/x-x509-ca-cert'
        )
        
    except Exception as e:
        logger.error(f"Download certificate error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/certificates/<int:cert_id>/toggle-auto-renew', methods=['POST'])
@jwt_required()
def toggle_auto_renew():
    """Toggle auto-renewal for SSL certificate"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificate = SSLCertificate.query.filter_by(id=cert_id, user_id=user_id).first()
        if not certificate:
            return jsonify({'error': 'Certificate not found'}), 404
        
        certificate.auto_renew = not certificate.auto_renew
        certificate.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'enabled' if certificate.auto_renew else 'disabled'
        logger.info(f"Auto-renewal {status} for certificate: {certificate.domain_name}")
        
        return jsonify({
            'message': f'Auto-renewal {status} successfully',
            'certificate': certificate.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Toggle auto-renew error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/certificates/<int:cert_id>', methods=['DELETE'])
@jwt_required()
def delete_certificate():
    """Delete SSL certificate"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        certificate = SSLCertificate.query.filter_by(id=cert_id, user_id=user_id).first()
        if not certificate:
            return jsonify({'error': 'Certificate not found'}), 404
        
        domain_name = certificate.domain_name
        
        # Remove SSL from associated domains
        Domain.query.filter_by(ssl_certificate_id=certificate.id).update({
            'ssl_certificate_id': None,
            'ssl_enabled': False,
            'updated_at': datetime.utcnow()
        })
        
        # Clean up certificate files
        if certificate.certificate_path and os.path.exists(certificate.certificate_path):
            os.remove(certificate.certificate_path)
        if certificate.private_key_path and os.path.exists(certificate.private_key_path):
            os.remove(certificate.private_key_path)
        if certificate.chain_path and os.path.exists(certificate.chain_path):
            os.remove(certificate.chain_path)
        
        # Delete certificate record
        db.session.delete(certificate)
        db.session.commit()
        
        logger.info(f"SSL certificate deleted: {domain_name}")
        
        return jsonify({'message': 'SSL certificate deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Delete certificate error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/expiring', methods=['GET'])
@jwt_required()
def get_expiring_certificates():
    """Get certificates expiring within specified days"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        days = request.args.get('days', 30, type=int)
        days = min(days, 90)  # Max 90 days
        
        expiry_date = datetime.utcnow() + timedelta(days=days)
        
        certificates = SSLCertificate.query.filter(
            SSLCertificate.user_id == user_id,
            SSLCertificate.status == 'active',
            SSLCertificate.expires_at <= expiry_date
        ).order_by(SSLCertificate.expires_at.asc()).all()
        
        return jsonify({
            'expiring_certificates': [cert.to_dict() for cert in certificates],
            'count': len(certificates),
            'days_threshold': days
        }), 200
        
    except Exception as e:
        logger.error(f"Get expiring certificates error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/check-status', methods=['GET'])
@jwt_required()
def check_ssl_status():
    """Check SSL certificate status for all user domains"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's domains
        domains = Domain.query.filter_by(user_id=user_id).all()
        
        ssl_status = []
        for domain in domains:
            domain_ssl = {
                'domain_id': domain.id,
                'domain_name': domain.domain_name,
                'ssl_enabled': domain.ssl_enabled,
                'certificate': None
            }
            
            if domain.ssl_certificate_id:
                certificate = SSLCertificate.query.get(domain.ssl_certificate_id)
                if certificate:
                    domain_ssl['certificate'] = certificate.to_dict()
            
            ssl_status.append(domain_ssl)
        
        return jsonify({
            'ssl_status': ssl_status,
            'total_domains': len(domains),
            'ssl_enabled_count': sum(1 for d in domains if d.ssl_enabled)
        }), 200
        
    except Exception as e:
        logger.error(f"Check SSL status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@ssl_bp.route('/bulk-issue', methods=['POST'])
@jwt_required()
def bulk_issue_certificates():
    """Issue SSL certificates for multiple domains"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data or not data.get('domain_ids'):
            return jsonify({'error': 'Domain IDs required'}), 400
        
        domain_ids = data['domain_ids']
        if not isinstance(domain_ids, list) or len(domain_ids) == 0:
            return jsonify({'error': 'Invalid domain IDs list'}), 400
        
        # Verify all domains belong to user
        domains = Domain.query.filter(
            Domain.id.in_(domain_ids),
            Domain.user_id == user_id
        ).all()
        
        if len(domains) != len(domain_ids):
            return jsonify({'error': 'Some domains not found or not accessible'}), 404
        
        task_ids = []
        certificates = []
        
        for domain in domains:
            # Check if certificate already exists
            existing_cert = SSLCertificate.query.filter_by(
                user_id=user_id,
                domain_name=domain.domain_name,
                status='active'
            ).first()
            
            if existing_cert and existing_cert.expires_at > datetime.utcnow() + timedelta(days=30):
                continue  # Skip if certificate is valid for more than 30 days
            
            # Create certificate record
            certificate = SSLCertificate(
                user_id=user_id,
                domain_name=domain.domain_name,
                status='pending'
            )
            
            db.session.add(certificate)
            certificates.append(certificate)
        
        db.session.commit()
        
        # Issue certificates asynchronously
        for certificate in certificates:
            task = issue_ssl_certificate.delay(certificate.id)
            task_ids.append(task.id)
        
        logger.info(f"Bulk SSL certificate issuance initiated for {len(certificates)} domains")
        
        return jsonify({
            'message': f'SSL certificate issuance initiated for {len(certificates)} domains',
            'task_ids': task_ids,
            'certificates': [cert.to_dict() for cert in certificates]
        }), 201
        
    except Exception as e:
        logger.error(f"Bulk issue certificates error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500