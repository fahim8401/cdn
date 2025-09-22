#!/usr/bin/env python3
"""
XenCDN v8.1 ISP Portal API Routes
Routes for ISP registration, authentication, and peering management
"""

from flask import Blueprint, request, jsonify, current_app, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import os
import jinja2

from ..models import db, ISPRegistration, ISPTrafficStats, User
from ..tasks.email_report import send_email

isp_portal_bp = Blueprint('isp_portal', __name__, url_prefix='/api/isp')

@isp_portal_bp.route('/register', methods=['POST'])
def register_isp():
    """Register a new ISP"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['company_name', 'contact_name', 'contact_email', 'password', 'asn']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if email already exists
        existing_isp = ISPRegistration.query.filter_by(contact_email=data['contact_email']).first()
        if existing_isp:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Validate email format
        if '@' not in data['contact_email'] or '.' not in data['contact_email']:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Validate ASN format
        asn = data['asn'].replace('AS', '').replace('as', '')
        if not asn.isdigit():
            return jsonify({'error': 'Invalid ASN format'}), 400
        
        # Validate peering method
        valid_methods = ['ixp', 'direct', 'gre_tunnel', 'hosted_node']
        peering_method = data.get('peering_method', 'ixp')
        if peering_method not in valid_methods:
            return jsonify({'error': f'Invalid peering method. Must be one of: {", ".join(valid_methods)}'}), 400
        
        # Create new ISP registration
        isp = ISPRegistration(
            company_name=data['company_name'],
            contact_name=data['contact_name'],
            contact_email=data['contact_email'],
            contact_phone=data.get('contact_phone', ''),
            website=data.get('website', ''),
            country=data.get('country', ''),
            city=data.get('city', ''),
            asn=f"AS{asn}",
            peering_method=peering_method,
            peering_point=data.get('peering_point', ''),
            public_ip=data.get('public_ip', ''),
            tunnel_endpoint=data.get('tunnel_endpoint', ''),
            bandwidth_limit_gbps=data.get('bandwidth_limit_gbps', 10)
        )
        isp.set_password(data['password'])
        
        db.session.add(isp)
        db.session.commit()
        
        # Notify admins of new ISP registration
        try:
            notify_admin_new_isp(isp)
        except Exception as e:
            current_app.logger.error(f"Failed to notify admin of new ISP: {e}")
        
        return jsonify({
            'message': 'ISP registration submitted successfully. Your request is pending approval.',
            'isp_id': isp.id,
            'status': 'pending'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"ISP registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@isp_portal_bp.route('/login', methods=['POST'])
def login_isp():
    """Login ISP and return JWT token"""
    try:
        data = request.get_json()
        
        if not data.get('contact_email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        isp = ISPRegistration.query.filter_by(contact_email=data['contact_email']).first()
        
        if not isp or not isp.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Create JWT token with ISP role
        additional_claims = {
            'role': 'isp',
            'isp_id': isp.id,
            'status': isp.status
        }
        access_token = create_access_token(
            identity=str(isp.id),
            additional_claims=additional_claims,
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'access_token': access_token,
            'isp': isp.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"ISP login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@isp_portal_bp.route('/me', methods=['GET'])
@jwt_required()
def get_isp_profile():
    """Get ISP profile (JWT protected)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'isp':
            return jsonify({'error': 'ISP access required'}), 403
        
        isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get(isp_id)
        
        if not isp:
            return jsonify({'error': 'ISP not found'}), 404
        
        return jsonify(isp.to_dict()), 200
        
    except Exception as e:
        current_app.logger.error(f"Get ISP profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500

@isp_portal_bp.route('/request', methods=['PUT'])
@jwt_required()
def submit_peering_request():
    """Submit or update peering request"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'isp':
            return jsonify({'error': 'ISP access required'}), 403
        
        isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get(isp_id)
        
        if not isp:
            return jsonify({'error': 'ISP not found'}), 404
        
        data = request.get_json()
        
        # Update peering configuration
        if 'peering_method' in data:
            valid_methods = ['ixp', 'direct', 'gre_tunnel', 'hosted_node']
            if data['peering_method'] not in valid_methods:
                return jsonify({'error': f'Invalid peering method. Must be one of: {", ".join(valid_methods)}'}), 400
            isp.peering_method = data['peering_method']
        
        if 'peering_point' in data:
            isp.peering_point = data['peering_point']
        
        if 'public_ip' in data:
            isp.public_ip = data['public_ip']
        
        if 'tunnel_endpoint' in data:
            isp.tunnel_endpoint = data['tunnel_endpoint']
        
        if 'bgp_config' in data:
            isp.bgp_config = data['bgp_config']
        
        # Reset status to pending if making changes
        if isp.status != 'pending':
            isp.status = 'pending'
        
        isp.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Peering request updated successfully',
            'isp': isp.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Submit peering request error: {e}")
        return jsonify({'error': 'Failed to submit request'}), 500

@isp_portal_bp.route('/approve/<int:isp_id>', methods=['PUT'])
@jwt_required()
def approve_isp(isp_id):
    """Admin approves ISP → assigns anycast IP"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        admin_id = get_jwt_identity()
        isp = ISPRegistration.query.get(isp_id)
        
        if not isp:
            return jsonify({'error': 'ISP not found'}), 404
        
        # Assign anycast IP
        anycast_ip = isp.assign_anycast_ip()
        if not anycast_ip:
            return jsonify({'error': 'No available anycast IPs'}), 409
        
        isp.status = 'approved'
        isp.approved_at = datetime.utcnow()
        isp.approved_by = admin_id
        isp.is_active = True
        
        db.session.commit()
        
        # Generate BGP configuration
        bgp_config = generate_bgp_config(isp)
        isp.bgp_config = bgp_config
        db.session.commit()
        
        # Send approval email
        try:
            send_approval_email(isp)
        except Exception as e:
            current_app.logger.error(f"Failed to send approval email: {e}")
        
        return jsonify({
            'message': 'ISP approved successfully',
            'isp': isp.to_dict(),
            'anycast_ip': anycast_ip
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Approve ISP error: {e}")
        return jsonify({'error': 'Failed to approve ISP'}), 500

@isp_portal_bp.route('/reject/<int:isp_id>', methods=['PUT'])
@jwt_required()
def reject_isp(isp_id):
    """Admin rejects ISP"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        isp = ISPRegistration.query.get(isp_id)
        
        if not isp:
            return jsonify({'error': 'ISP not found'}), 404
        
        data = request.get_json()
        reason = data.get('reason', 'Application rejected')
        
        isp.status = 'rejected'
        isp.admin_notes = reason
        isp.is_active = False
        
        db.session.commit()
        
        # Send rejection email
        try:
            send_rejection_email(isp, reason)
        except Exception as e:
            current_app.logger.error(f"Failed to send rejection email: {e}")
        
        return jsonify({
            'message': 'ISP rejected',
            'isp': isp.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Reject ISP error: {e}")
        return jsonify({'error': 'Failed to reject ISP'}), 500

@isp_portal_bp.route('/configs/bgp/<int:isp_id>', methods=['GET'])
@jwt_required()
def get_bgp_config(isp_id):
    """Serve BGP configuration (Bird2/FRR)"""
    try:
        claims = get_jwt()
        
        # Allow ISP to access their own config or admin to access any
        if claims.get('role') == 'isp':
            if str(isp_id) != get_jwt_identity():
                return jsonify({'error': 'Access denied'}), 403
        elif claims.get('role') != 'admin':
            return jsonify({'error': 'ISP or admin access required'}), 403
        
        isp = ISPRegistration.query.get(isp_id)
        
        if not isp:
            return jsonify({'error': 'ISP not found'}), 404
        
        if isp.status != 'approved':
            return jsonify({'error': 'ISP not approved'}), 403
        
        config_type = request.args.get('type', 'bird')  # bird or frr
        
        if config_type == 'bird':
            config = generate_bird_config(isp)
            mimetype = 'text/plain'
            filename = f'bird-{isp.asn.lower()}.conf'
        elif config_type == 'frr':
            config = generate_frr_config(isp)
            mimetype = 'text/plain'
            filename = f'frr-{isp.asn.lower()}.conf'
        else:
            return jsonify({'error': 'Invalid config type. Use "bird" or "frr"'}), 400
        
        response = make_response(config)
        response.headers['Content-Type'] = mimetype
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Get BGP config error: {e}")
        return jsonify({'error': 'Failed to get BGP config'}), 500

@isp_portal_bp.route('/configs/gre/<int:isp_id>', methods=['GET'])
@jwt_required()
def get_gre_config(isp_id):
    """Serve GRE tunnel setup script"""
    try:
        claims = get_jwt()
        
        # Allow ISP to access their own config or admin to access any
        if claims.get('role') == 'isp':
            if str(isp_id) != get_jwt_identity():
                return jsonify({'error': 'Access denied'}), 403
        elif claims.get('role') != 'admin':
            return jsonify({'error': 'ISP or admin access required'}), 403
        
        isp = ISPRegistration.query.get(isp_id)
        
        if not isp:
            return jsonify({'error': 'ISP not found'}), 404
        
        if isp.status != 'approved':
            return jsonify({'error': 'ISP not approved'}), 403
        
        if isp.peering_method != 'gre_tunnel':
            return jsonify({'error': 'GRE tunnel not configured for this ISP'}), 400
        
        script = generate_gre_script(isp)
        
        response = make_response(script)
        response.headers['Content-Type'] = 'application/x-sh'
        response.headers['Content-Disposition'] = f'attachment; filename=gre-setup-{isp.asn.lower()}.sh'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Get GRE config error: {e}")
        return jsonify({'error': 'Failed to get GRE config'}), 500

@isp_portal_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_isp_stats():
    """Get ISP traffic statistics (read-only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'isp':
            return jsonify({'error': 'ISP access required'}), 403
        
        isp_id = get_jwt_identity()
        isp = ISPRegistration.query.get(isp_id)
        
        if not isp:
            return jsonify({'error': 'ISP not found'}), 404
        
        # Get date range from query params
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Get traffic stats
        stats = ISPTrafficStats.query.filter(
            ISPTrafficStats.isp_id == isp.id,
            ISPTrafficStats.date >= start_date
        ).order_by(ISPTrafficStats.date.desc()).all()
        
        # Calculate totals
        total_requests = sum(s.requests for s in stats)
        total_bandwidth_gb = sum(s.bandwidth_gb for s in stats)
        total_cache_hits = sum(s.cache_hits for s in stats)
        total_cache_misses = sum(s.cache_misses for s in stats)
        avg_response_time = sum(s.response_time_avg for s in stats) / len(stats) if stats else 0
        cache_hit_ratio = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return jsonify({
            'isp': isp.to_dict(),
            'period_days': days,
            'stats': [s.to_dict() for s in stats],
            'totals': {
                'requests': total_requests,
                'bandwidth_gb': round(total_bandwidth_gb, 2),
                'cache_hits': total_cache_hits,
                'cache_misses': total_cache_misses,
                'cache_hit_ratio': round(cache_hit_ratio, 2),
                'avg_response_time': round(avg_response_time, 2)
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get ISP stats error: {e}")
        return jsonify({'error': 'Failed to get stats'}), 500

def generate_bgp_config(isp):
    """Generate BGP configuration for ISP"""
    # Get environment variables for BGP
    xencdn_asn = os.getenv('BGP_ASN', '64512')
    xencdn_ip = os.getenv('BGP_ANYCAST_IP', '203.0.113.10')
    
    config = f"""# XenCDN BGP Configuration for {isp.company_name}
# ASN: {isp.asn}
# Anycast IP: {isp.anycast_ip}
# Generated: {datetime.utcnow().isoformat()}

# Basic BGP configuration
router id {isp.anycast_ip};
local as {isp.asn.replace('AS', '')};

# Define the anycast prefix
route {isp.anycast_ip}/32 via "lo";

# Peer with XenCDN
protocol bgp xencdn {{
    local as {isp.asn.replace('AS', '')};
    neighbor as {xencdn_asn};
    neighbor {xencdn_ip};
    
    ipv4 {{
        import filter {{
            # Accept XenCDN routes
            accept;
        }};
        export filter {{
            # Announce our anycast prefix
            if net ~ [{isp.anycast_ip}/32] then accept;
            reject;
        }};
    }};
}}

# Static route for anycast IP
protocol static {{
    route {isp.anycast_ip}/32 blackhole;
}}
"""
    
    return config

def generate_bird_config(isp):
    """Generate Bird2 configuration"""
    return generate_bgp_config(isp)

def generate_frr_config(isp):
    """Generate FRRouting configuration"""
    xencdn_asn = os.getenv('BGP_ASN', '64512')
    xencdn_ip = os.getenv('BGP_ANYCAST_IP', '203.0.113.10')
    
    config = f"""! XenCDN FRR Configuration for {isp.company_name}
! ASN: {isp.asn}
! Anycast IP: {isp.anycast_ip}
! Generated: {datetime.utcnow().isoformat()}

hostname {isp.company_name.lower().replace(' ', '-')}
password xencdn

interface lo
 ip address {isp.anycast_ip}/32

router bgp {isp.asn.replace('AS', '')}
 bgp router-id {isp.anycast_ip}
 network {isp.anycast_ip}/32
 
 neighbor {xencdn_ip} remote-as {xencdn_asn}
 neighbor {xencdn_ip} description XenCDN
 
 address-family ipv4 unicast
  network {isp.anycast_ip}/32
  neighbor {xencdn_ip} activate
  neighbor {xencdn_ip} route-map XENCDN-OUT out
 exit-address-family

route-map XENCDN-OUT permit 10
 match ip address prefix-list ANYCAST-PREFIXES

ip prefix-list ANYCAST-PREFIXES seq 10 permit {isp.anycast_ip}/32

line vty
"""
    
    return config

def generate_gre_script(isp):
    """Generate GRE tunnel setup script"""
    xencdn_endpoint = os.getenv('BGP_PEER_IP', '203.0.113.1')
    
    script = f"""#!/bin/bash
# XenCDN GRE Tunnel Setup Script
# ISP: {isp.company_name}
# ASN: {isp.asn}
# Generated: {datetime.utcnow().isoformat()}

set -e

echo "Setting up GRE tunnel for XenCDN..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# Install required packages
apt-get update
apt-get install -y iproute2 iptables

# Remove existing tunnel if exists
ip tunnel del gre-xencdn 2>/dev/null || true

# Create GRE tunnel
ip tunnel add gre-xencdn mode gre remote {xencdn_endpoint} local {isp.public_ip} ttl 255
ip link set gre-xencdn up
ip addr add {isp.anycast_ip}/30 dev gre-xencdn

# Add route for XenCDN traffic
ip route add 0.0.0.0/0 dev gre-xencdn table 100
ip rule add from {isp.anycast_ip} table 100

# Configure iptables for traffic forwarding
iptables -t nat -A POSTROUTING -o gre-xencdn -j MASQUERADE
iptables -A FORWARD -i gre-xencdn -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o gre-xencdn -j ACCEPT

# Make configuration persistent
echo "# XenCDN GRE Tunnel" >> /etc/rc.local
echo "ip tunnel add gre-xencdn mode gre remote {xencdn_endpoint} local {isp.public_ip} ttl 255" >> /etc/rc.local
echo "ip link set gre-xencdn up" >> /etc/rc.local
echo "ip addr add {isp.anycast_ip}/30 dev gre-xencdn" >> /etc/rc.local

echo "GRE tunnel setup complete!"
echo "Tunnel IP: {isp.anycast_ip}"
echo "Remote endpoint: {xencdn_endpoint}"
echo ""
echo "Please configure your traffic routing to use the anycast IP: {isp.anycast_ip}"
"""
    
    return script

def notify_admin_new_isp(isp):
    """Notify admin of new ISP registration"""
    admin_users = User.query.filter_by(is_admin=True).all()
    
    for admin in admin_users:
        subject = f"New ISP Registration - {isp.company_name}"
        body = f"""
        A new ISP has registered for XenCDN:
        
        Company: {isp.company_name}
        Contact: {isp.contact_name} ({isp.contact_email})
        ASN: {isp.asn}
        Peering Method: {isp.peering_method}
        
        Please review and approve/reject the registration in the admin panel.
        """
        
        send_email(admin.email, subject, body)

def send_approval_email(isp):
    """Send ISP approval email"""
    subject = "XenCDN ISP Application Approved"
    body = f"""
    Congratulations! Your ISP application has been approved.
    
    Company: {isp.company_name}
    ASN: {isp.asn}
    Assigned Anycast IP: {isp.anycast_ip}
    
    You can now download your BGP configuration and GRE tunnel scripts from the ISP portal.
    
    Next steps:
    1. Log into the ISP portal
    2. Download your BGP configuration
    3. Configure your routers
    4. Start announcing the anycast IP
    
    Welcome to the XenCDN network!
    
    Best regards,
    The XenCDN Team
    """
    
    send_email(isp.contact_email, subject, body)

def send_rejection_email(isp, reason):
    """Send ISP rejection email"""
    subject = "XenCDN ISP Application Rejected"
    body = f"""
    We regret to inform you that your ISP application has been rejected.
    
    Reason: {reason}
    
    If you have questions or would like to reapply, please contact our support team.
    
    Best regards,
    The XenCDN Team
    """
    
    send_email(isp.contact_email, subject, body)