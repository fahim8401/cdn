#!/usr/bin/env python3
"""
XenCDN v8.2 - ISP Portal API Routes
ISP registration, peering requests, and BGP management
"""

import os
import json
import secrets
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, ISPRegistration, User
from tasks.edge_config import generate_bgp_config, generate_gre_tunnel_script

isp_portal_bp = Blueprint('isp_portal', __name__)

@isp_portal_bp.route('/api/isp/register', methods=['POST'])
def register_isp():
    """Register new ISP"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['company_name', 'email', 'password', 'contact_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if email already exists
        existing_isp = ISPRegistration.query.filter_by(email=data['email']).first()
        if existing_isp:
            return jsonify({'error': 'Email address already registered'}), 409
        
        # Create ISP registration
        isp = ISPRegistration(
            company_name=data['company_name'],
            email=data['email'].lower(),
            contact_name=data['contact_name'],
            phone=data.get('phone', ''),
            asn=data.get('asn'),
            public_ip=data.get('public_ip', ''),
            peering_method=data.get('peering_method', 'IXP'),
            peering_point=data.get('peering_point', ''),
            tunnel_endpoint=data.get('tunnel_endpoint', ''),
            status='pending'
        )
        
        isp.set_password(data['password'])
        
        db.session.add(isp)
        db.session.commit()
        
        # Generate access token
        access_token = create_access_token(
            identity=isp.id,
            additional_claims={'type': 'isp'},
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'message': 'ISP registration successful. Your application is under review.',
            'access_token': access_token,
            'isp': isp.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/isp/login', methods=['POST'])
def login_isp():
    """ISP login"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find ISP
        isp = ISPRegistration.query.filter_by(email=email).first()
        if not isp or not isp.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not isp.is_active:
            return jsonify({'error': 'Account is disabled'}), 403
        
        # Generate access token
        access_token = create_access_token(
            identity=isp.id,
            additional_claims={'type': 'isp'},
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'access_token': access_token,
            'isp': isp.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/isp/profile', methods=['GET'])
@jwt_required()
def get_isp_profile():
    """Get ISP profile"""
    try:
        current_isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get_or_404(current_isp_id)
        
        return jsonify({'isp': isp.to_dict()})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/isp/profile', methods=['PUT'])
@jwt_required()
def update_isp_profile():
    """Update ISP profile"""
    try:
        current_isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get_or_404(current_isp_id)
        
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['company_name', 'contact_name', 'phone', 'asn', 'public_ip', 
                         'peering_method', 'peering_point', 'tunnel_endpoint']
        
        for field in allowed_fields:
            if field in data:
                setattr(isp, field, data[field])
        
        isp.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'isp': isp.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/isp/peering-request', methods=['POST'])
@jwt_required()
def submit_peering_request():
    """Submit or update peering request"""
    try:
        current_isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get_or_404(current_isp_id)
        
        data = request.get_json()
        
        # Update peering details
        isp.asn = data.get('asn', isp.asn)
        isp.public_ip = data.get('public_ip', isp.public_ip)
        isp.peering_method = data.get('peering_method', isp.peering_method)
        isp.peering_point = data.get('peering_point', isp.peering_point)
        isp.tunnel_endpoint = data.get('tunnel_endpoint', isp.tunnel_endpoint)
        isp.bgp_config = data.get('bgp_config', isp.bgp_config)
        
        # Reset status to pending if was rejected
        if isp.status == 'rejected':
            isp.status = 'pending'
        
        isp.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Peering request submitted successfully',
            'isp': isp.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/isp/bgp-config', methods=['GET'])
@jwt_required()
def get_bgp_config():
    """Get BGP configuration template"""
    try:
        current_isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get_or_404(current_isp_id)
        
        if isp.status != 'approved':
            return jsonify({'error': 'BGP config only available for approved ISPs'}), 403
        
        if not isp.anycast_ip:
            return jsonify({'error': 'No anycast IP assigned yet'}), 400
        
        # Generate BGP config
        config_data = {
            'isp_asn': isp.asn,
            'anycast_ip': isp.anycast_ip,
            'peer_ip': os.getenv('BGP_PEER_IP', '203.0.113.1'),
            'local_asn': os.getenv('BGP_ASN', '65000'),
            'peering_method': isp.peering_method
        }
        
        bgp_config = generate_bgp_config(config_data)
        
        return jsonify({
            'bgp_config': bgp_config,
            'download_filename': f'bgp-config-{isp.company_name.lower().replace(" ", "-")}.conf'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/isp/gre-tunnel-script', methods=['GET'])
@jwt_required()
def get_gre_tunnel_script():
    """Get GRE tunnel setup script"""
    try:
        current_isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get_or_404(current_isp_id)
        
        if isp.status != 'approved':
            return jsonify({'error': 'GRE script only available for approved ISPs'}), 403
        
        if isp.peering_method != 'GRE':
            return jsonify({'error': 'GRE script only available for GRE peering method'}), 400
        
        if not isp.tunnel_endpoint or not isp.anycast_ip:
            return jsonify({'error': 'Tunnel endpoint and anycast IP required'}), 400
        
        # Generate GRE tunnel script
        script_data = {
            'local_ip': isp.public_ip,
            'remote_ip': os.getenv('BGP_PEER_IP', '203.0.113.1'),
            'tunnel_ip': isp.anycast_ip,
            'tunnel_endpoint': isp.tunnel_endpoint
        }
        
        gre_script = generate_gre_tunnel_script(script_data)
        
        return jsonify({
            'gre_script': gre_script,
            'download_filename': f'gre-setup-{isp.company_name.lower().replace(" ", "-")}.sh'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/isp/traffic-stats', methods=['GET'])
@jwt_required()
def get_traffic_stats():
    """Get ISP traffic statistics (read-only)"""
    try:
        current_isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get_or_404(current_isp_id)
        
        if isp.status not in ['approved', 'active']:
            return jsonify({'error': 'Traffic stats only available for active ISPs'}), 403
        
        # Get time range
        days = int(request.args.get('days', 30))
        
        # Mock traffic stats (in production, this would come from monitoring)
        stats = {
            'period_days': days,
            'total_traffic_gb': 1250.5,
            'peak_traffic_gbps': 2.3,
            'avg_traffic_gbps': 0.8,
            'cache_hit_ratio': 89.2,
            'uptime_percent': 99.97,
            'cost_savings_usd': 450.75,
            'daily_stats': []
        }
        
        # Generate daily stats for chart
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        current_date = start_date
        while current_date <= end_date:
            daily_stat = {
                'date': current_date.isoformat(),
                'traffic_gb': round(40 + (hash(str(current_date)) % 20), 1),
                'cache_hits': round(85 + (hash(str(current_date)) % 10), 1),
                'cost_saved_usd': round(15 + (hash(str(current_date)) % 5), 2)
            }
            stats['daily_stats'].append(daily_stat)
            current_date += timedelta(days=1)
        
        return jsonify({'stats': stats})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/isp/support-ticket', methods=['POST'])
@jwt_required()
def create_support_ticket():
    """Create support ticket"""
    try:
        current_isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get_or_404(current_isp_id)
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('subject') or not data.get('message'):
            return jsonify({'error': 'Subject and message are required'}), 400
        
        # In production, this would create a ticket in your support system
        ticket_id = f"ISP-{current_isp_id}-{int(datetime.utcnow().timestamp())}"
        
        # Mock response
        ticket = {
            'ticket_id': ticket_id,
            'subject': data['subject'],
            'message': data['message'],
            'priority': data.get('priority', 'medium'),
            'status': 'open',
            'created_at': datetime.utcnow().isoformat(),
            'estimated_response': '24 hours'
        }
        
        return jsonify({
            'message': 'Support ticket created successfully',
            'ticket': ticket
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin routes for managing ISPs
@isp_portal_bp.route('/api/admin/isps', methods=['GET'])
@jwt_required()
def list_isps():
    """List all ISP registrations (admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        # Get query parameters
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 25)), 100)
        
        # Build query
        query = ISPRegistration.query
        
        if status:
            query = query.filter_by(status=status)
        
        if search:
            query = query.filter(
                ISPRegistration.company_name.ilike(f'%{search}%') |
                ISPRegistration.email.ilike(f'%{search}%')
            )
        
        # Paginate results
        isps = query.order_by(ISPRegistration.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'isps': [isp.to_dict() for isp in isps.items],
            'pagination': {
                'page': page,
                'pages': isps.pages,
                'per_page': per_page,
                'total': isps.total
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/admin/isps/<int:isp_id>/approve', methods=['POST'])
@jwt_required()
def approve_isp(isp_id):
    """Approve ISP registration"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        isp = ISPRegistration.query.get_or_404(isp_id)
        data = request.get_json()
        
        # Assign anycast IP
        anycast_ip = data.get('anycast_ip')
        if not anycast_ip:
            # Auto-assign from BGP block
            base_ip = os.getenv('BGP_IP_BLOCK', '203.0.113.0/24').split('/')[0]
            # Simple IP assignment logic (in production, use proper IP management)
            base_parts = base_ip.split('.')
            assigned_ip = f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.{10 + isp_id}"
            anycast_ip = assigned_ip
        
        # Update ISP
        isp.status = 'approved'
        isp.anycast_ip = anycast_ip
        isp.traffic_limit_gbps = data.get('traffic_limit_gbps', 100)
        isp.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'ISP approved successfully',
            'isp': isp.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@isp_portal_bp.route('/api/admin/isps/<int:isp_id>/reject', methods=['POST'])
@jwt_required()
def reject_isp(isp_id):
    """Reject ISP registration"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        isp = ISPRegistration.query.get_or_404(isp_id)
        data = request.get_json()
        
        isp.status = 'rejected'
        isp.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'ISP rejected',
            'reason': data.get('reason', 'Not specified'),
            'isp': isp.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500