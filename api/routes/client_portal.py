#!/usr/bin/env python3
"""
XenCDN v8.2 - Client Portal API Routes
Client registration, domain management, and usage dashboard
"""

import os
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, ClientRegistration, Domain, CacheStats, DNSZone, DNSRecord
from tasks.dns_provision import auto_provision_domain_task
from tasks.ssl_issue import issue_ssl_certificate_task
from tasks.purge_cache import purge_domain_cache_task

client_portal_bp = Blueprint('client_portal', __name__)

@client_portal_bp.route('/api/client/register', methods=['POST'])
def register_client():
    """Register new client"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email address already registered'}), 409
        
        # Create user account
        user = User(
            email=data['email'].lower(),
            username=data['email'].lower(),
            first_name=data['first_name'],
            last_name=data['last_name'],
            company=data.get('company', ''),
            phone=data.get('phone', ''),
            is_admin=False,
            is_active=True
        )
        
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create client registration
        client_reg = ClientRegistration(
            user_id=user.id,
            plan_type=data.get('plan_type', 'free'),
            billing_email=data.get('billing_email', data['email']),
            billing_address=data.get('billing_address', ''),
            subscription_status='active'
        )
        
        # Set limits based on plan
        if client_reg.plan_type == 'free':
            client_reg.monthly_bandwidth_limit_gb = 100
            client_reg.domain_limit = 3
        elif client_reg.plan_type == 'pro':
            client_reg.monthly_bandwidth_limit_gb = 1000
            client_reg.domain_limit = 25
        elif client_reg.plan_type == 'enterprise':
            client_reg.monthly_bandwidth_limit_gb = 10000
            client_reg.domain_limit = 100
        
        db.session.add(client_reg)
        db.session.commit()
        
        # Generate access token
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'type': 'client'},
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'message': 'Registration successful',
            'access_token': access_token,
            'user': user.to_dict(),
            'client_info': client_reg.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/login', methods=['POST'])
def login_client():
    """Client login"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user
        user = User.query.filter_by(email=email, is_admin=False).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 403
        
        # Get client registration
        client_reg = ClientRegistration.query.filter_by(user_id=user.id).first()
        
        # Generate access token
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'type': 'client'},
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict(),
            'client_info': client_reg.to_dict() if client_reg else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Get client dashboard data"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        client_reg = ClientRegistration.query.filter_by(user_id=user.id).first()
        
        # Get domains
        domains = Domain.query.filter_by(user_id=user.id).all()
        
        # Calculate total stats
        total_requests = 0
        total_bandwidth_saved_gb = 0
        avg_cache_hit_ratio = 0
        
        for domain in domains:
            stats = CacheStats.query.filter_by(domain_id=domain.id).all()
            domain_requests = sum(stat.requests for stat in stats)
            domain_bandwidth_saved = sum(stat.bandwidth_saved for stat in stats)
            
            total_requests += domain_requests
            total_bandwidth_saved_gb += domain_bandwidth_saved / (1024**3)
        
        if domains:
            # Calculate average cache hit ratio
            recent_stats = CacheStats.query.join(Domain).filter(
                Domain.user_id == user.id,
                CacheStats.date >= datetime.utcnow().date() - timedelta(days=30)
            ).all()
            
            if recent_stats:
                total_hits = sum(stat.cache_hits for stat in recent_stats)
                total_reqs = sum(stat.requests for stat in recent_stats)
                avg_cache_hit_ratio = (total_hits / total_reqs * 100) if total_reqs > 0 else 0
        
        # Calculate cost savings (estimate $0.05 per GB)
        cost_saved_usd = total_bandwidth_saved_gb * 0.05
        
        dashboard_data = {
            'user': user.to_dict(),
            'client_info': client_reg.to_dict() if client_reg else None,
            'summary': {
                'total_domains': len(domains),
                'total_requests': total_requests,
                'bandwidth_saved_gb': round(total_bandwidth_saved_gb, 2),
                'cache_hit_ratio': round(avg_cache_hit_ratio, 1),
                'cost_saved_usd': round(cost_saved_usd, 2),
                'active_domains': len([d for d in domains if d.status == 'active']),
                'ssl_enabled_domains': len([d for d in domains if d.ssl_enabled])
            },
            'domains': [domain.to_dict() for domain in domains[-10:]],  # Last 10 domains
            'recent_activity': self._get_recent_activity(user.id)
        }
        
        return jsonify(dashboard_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _get_recent_activity(user_id, limit=10):
    """Get recent activity for user"""
    activities = []
    
    # Get recent domains
    recent_domains = Domain.query.filter_by(user_id=user_id).order_by(
        Domain.created_at.desc()
    ).limit(5).all()
    
    for domain in recent_domains:
        activities.append({
            'type': 'domain_added',
            'message': f'Domain {domain.domain_name} added',
            'timestamp': domain.created_at.isoformat(),
            'domain_id': domain.id
        })
    
    # Sort by timestamp and limit
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:limit]

@client_portal_bp.route('/api/client/domains', methods=['GET'])
@jwt_required()
def list_domains():
    """List client's domains"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 25)), 100)
        search = request.args.get('search', '')
        
        # Build query
        query = Domain.query.filter_by(user_id=current_user_id)
        
        if search:
            query = query.filter(Domain.domain_name.ilike(f'%{search}%'))
        
        # Paginate results
        domains = query.order_by(Domain.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'domains': [domain.to_dict() for domain in domains.items],
            'pagination': {
                'page': page,
                'pages': domains.pages,
                'per_page': per_page,
                'total': domains.total
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/domains', methods=['POST'])
@jwt_required()
def add_domain():
    """Add new domain"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        client_reg = ClientRegistration.query.filter_by(user_id=user.id).first()
        
        data = request.get_json()
        domain_name = data.get('domain_name', '').strip().lower()
        origin_url = data.get('origin_url', '').strip()
        dns_method = data.get('dns_method', 'xencdn')  # 'xencdn' or 'own'
        
        if not domain_name or not origin_url:
            return jsonify({'error': 'Domain name and origin URL are required'}), 400
        
        # Check domain limit
        if client_reg:
            current_domain_count = Domain.query.filter_by(user_id=user.id).count()
            if current_domain_count >= client_reg.domain_limit:
                return jsonify({'error': f'Domain limit reached ({client_reg.domain_limit})'}), 403
        
        # Check if domain already exists
        existing_domain = Domain.query.filter_by(domain_name=domain_name).first()
        if existing_domain:
            return jsonify({'error': 'Domain already exists in the system'}), 409
        
        # Create domain
        domain = Domain(
            user_id=user.id,
            domain_name=domain_name,
            origin_server=origin_url,
            status='pending',
            cdn_enabled=False,
            ssl_enabled=False
        )
        
        db.session.add(domain)
        db.session.flush()  # Get domain ID
        
        # Handle DNS method
        if dns_method == 'xencdn':
            # Auto-provision DNS and CDN
            auto_provision_domain_task.delay(domain_name, origin_url, user.id)
            
            instructions = {
                'dns_method': 'xencdn',
                'nameservers': [
                    os.getenv('DNS_SERVER_NAME', 'ns1.xencdn.com'),
                    os.getenv('DNS_SERVER_NAME2', 'ns2.xencdn.com')
                ],
                'message': f'Update your domain nameservers to use XenCDN DNS'
            }
        else:
            # Client will use their own DNS
            anycast_ip = os.getenv('BGP_IP_BLOCK', '203.0.113.1').split('/')[0]
            
            instructions = {
                'dns_method': 'own',
                'a_record': {
                    'name': '@',
                    'type': 'A',
                    'value': anycast_ip,
                    'ttl': 300
                },
                'cname_record': {
                    'name': 'www',
                    'type': 'CNAME',
                    'value': domain_name,
                    'ttl': 300
                },
                'message': f'Add these DNS records to enable CDN'
            }
        
        db.session.commit()
        
        return jsonify({
            'message': 'Domain added successfully',
            'domain': domain.to_dict(),
            'instructions': instructions
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/domains/<int:domain_id>/enable-cdn', methods=['POST'])
@jwt_required()
def enable_cdn(domain_id):
    """Enable CDN for domain"""
    try:
        current_user_id = get_jwt_identity()
        domain = Domain.query.filter_by(id=domain_id, user_id=current_user_id).first_or_404()
        
        if domain.cdn_enabled:
            return jsonify({'error': 'CDN is already enabled for this domain'}), 400
        
        # Enable CDN
        domain.cdn_enabled = True
        domain.status = 'active'
        domain.updated_at = datetime.utcnow()
        
        # Auto-provision DNS if needed
        auto_provision_domain_task.delay(domain.domain_name, domain.origin_server, current_user_id)
        
        db.session.commit()
        
        return jsonify({
            'message': 'CDN enabled successfully',
            'domain': domain.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/domains/<int:domain_id>/disable-cdn', methods=['POST'])
@jwt_required()
def disable_cdn(domain_id):
    """Disable CDN for domain"""
    try:
        current_user_id = get_jwt_identity()
        domain = Domain.query.filter_by(id=domain_id, user_id=current_user_id).first_or_404()
        
        # Disable CDN
        domain.cdn_enabled = False
        domain.status = 'inactive'
        domain.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'CDN disabled successfully',
            'domain': domain.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/domains/<int:domain_id>/purge', methods=['POST'])
@jwt_required()
def purge_domain_cache(domain_id):
    """Purge cache for domain"""
    try:
        current_user_id = get_jwt_identity()
        domain = Domain.query.filter_by(id=domain_id, user_id=current_user_id).first_or_404()
        
        data = request.get_json()
        purge_type = data.get('type', 'all')  # 'all', 'url', 'pattern'
        urls = data.get('urls', [])
        
        # Start purge task
        task = purge_domain_cache_task.delay(domain_id, purge_type, urls)
        
        return jsonify({
            'message': 'Cache purge initiated',
            'task_id': task.id,
            'estimated_time': '2-5 minutes'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/domains/<int:domain_id>/ssl', methods=['POST'])
@jwt_required()
def enable_ssl(domain_id):
    """Enable SSL for domain"""
    try:
        current_user_id = get_jwt_identity()
        domain = Domain.query.filter_by(id=domain_id, user_id=current_user_id).first_or_404()
        
        if domain.ssl_enabled:
            return jsonify({'error': 'SSL is already enabled for this domain'}), 400
        
        # Start SSL certificate issuance
        task = issue_ssl_certificate_task.delay(domain_id)
        
        return jsonify({
            'message': 'SSL certificate issuance initiated',
            'task_id': task.id,
            'estimated_time': '5-10 minutes'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/domains/<int:domain_id>/stats', methods=['GET'])
@jwt_required()
def get_domain_stats(domain_id):
    """Get domain statistics"""
    try:
        current_user_id = get_jwt_identity()
        domain = Domain.query.filter_by(id=domain_id, user_id=current_user_id).first_or_404()
        
        # Get time range
        days = int(request.args.get('days', 30))
        
        # Get cache stats
        stats = CacheStats.query.filter_by(domain_id=domain_id).filter(
            CacheStats.date >= datetime.utcnow().date() - timedelta(days=days)
        ).all()
        
        if not stats:
            return jsonify({
                'domain': domain.to_dict(),
                'stats': {
                    'total_requests': 0,
                    'cache_hit_ratio': 0,
                    'bandwidth_saved_gb': 0,
                    'avg_response_time_ms': 0,
                    'daily_stats': []
                }
            })
        
        # Calculate totals
        total_requests = sum(stat.requests for stat in stats)
        total_hits = sum(stat.cache_hits for stat in stats)
        total_bandwidth_saved = sum(stat.bandwidth_saved for stat in stats)
        
        cache_hit_ratio = (total_hits / total_requests * 100) if total_requests > 0 else 0
        bandwidth_saved_gb = total_bandwidth_saved / (1024**3)
        
        # Calculate average response time
        avg_response_time = sum(stat.response_time_avg for stat in stats) / len(stats)
        
        # Group by date for chart
        daily_stats = {}
        for stat in stats:
            date_str = stat.date.isoformat()
            if date_str not in daily_stats:
                daily_stats[date_str] = {
                    'date': date_str,
                    'requests': 0,
                    'cache_hits': 0,
                    'bandwidth_saved_mb': 0
                }
            
            daily_stats[date_str]['requests'] += stat.requests
            daily_stats[date_str]['cache_hits'] += stat.cache_hits
            daily_stats[date_str]['bandwidth_saved_mb'] += stat.bandwidth_saved / (1024**2)
        
        return jsonify({
            'domain': domain.to_dict(),
            'stats': {
                'total_requests': total_requests,
                'cache_hit_ratio': round(cache_hit_ratio, 1),
                'bandwidth_saved_gb': round(bandwidth_saved_gb, 2),
                'avg_response_time_ms': round(avg_response_time, 1),
                'daily_stats': list(daily_stats.values())
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/domains/<int:domain_id>/ssl-certificate', methods=['GET'])
@jwt_required()
def download_ssl_certificate(domain_id):
    """Download SSL certificate"""
    try:
        current_user_id = get_jwt_identity()
        domain = Domain.query.filter_by(id=domain_id, user_id=current_user_id).first_or_404()
        
        if not domain.ssl_enabled:
            return jsonify({'error': 'SSL is not enabled for this domain'}), 400
        
        # In production, this would fetch the actual certificate from MinIO
        certificate_data = {
            'domain': domain.domain_name,
            'certificate': '-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----',
            'private_key': '-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----',
            'certificate_chain': '-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----',
            'expires_at': '2024-12-31T23:59:59Z',
            'issuer': 'Let\'s Encrypt Authority X3'
        }
        
        return jsonify({
            'certificate': certificate_data,
            'download_links': {
                'certificate': f'/api/client/domains/{domain_id}/ssl-certificate/cert.pem',
                'private_key': f'/api/client/domains/{domain_id}/ssl-certificate/private.key',
                'full_chain': f'/api/client/domains/{domain_id}/ssl-certificate/fullchain.pem'
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_portal_bp.route('/api/client/usage', methods=['GET'])
@jwt_required()
def get_usage():
    """Get client usage statistics"""
    try:
        current_user_id = get_jwt_identity()
        client_reg = ClientRegistration.query.filter_by(user_id=current_user_id).first()
        
        if not client_reg:
            return jsonify({'error': 'Client registration not found'}), 404
        
        # Calculate current usage
        domains = Domain.query.filter_by(user_id=current_user_id).all()
        
        # Calculate bandwidth usage for current month
        from datetime import date
        current_month_start = date.today().replace(day=1)
        
        monthly_stats = CacheStats.query.join(Domain).filter(
            Domain.user_id == current_user_id,
            CacheStats.date >= current_month_start
        ).all()
        
        current_bandwidth_gb = sum(stat.bandwidth_total for stat in monthly_stats) / (1024**3)
        
        # Update client registration
        client_reg.current_bandwidth_usage_gb = current_bandwidth_gb
        client_reg.current_domain_count = len(domains)
        db.session.commit()
        
        usage_data = {
            'plan_type': client_reg.plan_type,
            'domains': {
                'used': len(domains),
                'limit': client_reg.domain_limit,
                'percentage': (len(domains) / client_reg.domain_limit * 100) if client_reg.domain_limit > 0 else 0
            },
            'bandwidth': {
                'used_gb': round(current_bandwidth_gb, 2),
                'limit_gb': client_reg.monthly_bandwidth_limit_gb,
                'percentage': (current_bandwidth_gb / client_reg.monthly_bandwidth_limit_gb * 100) if client_reg.monthly_bandwidth_limit_gb > 0 else 0
            },
            'subscription': {
                'status': client_reg.subscription_status,
                'trial_expires_at': client_reg.trial_expires_at.isoformat() if client_reg.trial_expires_at else None
            }
        }
        
        return jsonify({'usage': usage_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500